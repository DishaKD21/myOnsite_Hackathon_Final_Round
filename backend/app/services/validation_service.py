from __future__ import annotations
import json
import zipfile
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import BackupPoint, Resolution
from .engine import state_for_point
from .hash_service import calculate_artifact_hash, sha256_content
from .manifest_service import manifest_hash

def validate_backup(db: Session, point: BackupPoint) -> dict:
    errors, warnings, checks = [], [], []
    artifact = Path(point.artifact_path); manifest_file = Path(point.manifest_path)
    if not artifact.exists(): errors.append("artifact is missing")
    else:
        checks.append("artifact exists")
        if calculate_artifact_hash(artifact) != point.artifact_hash: errors.append("artifact hash mismatch")
        else: checks.append("artifact hash matches")
    if not manifest_file.exists(): errors.append("manifest is missing")
    else:
        checks.append("manifest exists")
        try: manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError: manifest = {}; errors.append("manifest is not valid JSON")
        if manifest and manifest_hash(manifest) != point.manifest_hash: errors.append("manifest hash mismatch")
        if manifest and manifest.get("change_count", point.change_count) != point.change_count and point.type != "FULL": errors.append("change_count mismatch")
        if point.type == "INCREMENTAL":
            if not point.parent_id or db.get(BackupPoint, point.parent_id) is None: errors.append("parent is missing")
            if manifest.get("parent_id") != point.parent_id: errors.append("parent relationship mismatch")
            if manifest.get("start_version") != point.start_version or manifest.get("end_version") != point.end_version: errors.append("version coverage mismatch")
    payload = None
    if artifact.exists():
        try:
            with zipfile.ZipFile(artifact) as archive:
                if archive.testzip() is not None:
                    errors.append("artifact ZIP is corrupt")
            payload_path = artifact.with_name("artifact.json")
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            if point.type == "INCREMENTAL" and len(payload.get("changes", [])) != point.change_count: errors.append("artifact change count mismatch")
            if point.type == "FULL" and payload.get("kind") != "FULL": errors.append("full artifact kind mismatch")
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError): errors.append("artifact is not a valid backup ZIP")
    if payload and point.type == "FULL":
        for file in payload.get("files", []):
            if sha256_content(file.get("content", "")) != file.get("content_hash"):
                errors.append(f"content hash mismatch for {file.get('file_id')}")
    if payload and point.type == "INCREMENTAL":
        changes = payload.get("changes", [])
        manifest_changes = manifest.get("coverage", []) if manifest_file.exists() and 'manifest' in locals() else []
        payload_ids = sorted(change.get("file_id") for change in changes)
        manifest_ids = sorted(change.get("file_id") for change in manifest_changes)
        if payload_ids != manifest_ids:
            errors.append("change coverage file IDs mismatch")
        if len(payload_ids) != point.change_count:
            errors.append("expected change count mismatch")
        if point.parent_id:
            try:
                resolution = db.execute(select(Resolution).where(Resolution.original_id == point.parent_id, Resolution.approved.is_(True)).order_by(Resolution.id.desc())).scalars().first()
                parent = db.get(BackupPoint, resolution.replacement_id if resolution else point.parent_id)
                if parent is None:
                    raise ValueError("parent is missing")
                parent_state = state_for_point(db, parent)
                expected_state = state_for_point(db, point)
                for change in changes:
                    file_id = change.get("file_id")
                    old = change.get("old")
                    new = change.get("new")
                    parent_file = parent_state.get(file_id)
                    if old is None:
                        if parent_file is not None:
                            errors.append(f"old state mismatch for {file_id}")
                    elif not parent_file or parent_file.get("version") != change.get("previous_version") or parent_file.get("content_hash") != change.get("previous_content_hash"):
                        errors.append(f"old hash/version mismatch for {file_id}")
                    if new is not None:
                        if sha256_content(new.get("content", "")) != new.get("content_hash"):
                            errors.append(f"new content hash mismatch for {file_id}")
                        resulting_file = expected_state.get(file_id)
                        if not resulting_file or resulting_file.get("version") != change.get("new_version") or resulting_file.get("content_hash") != change.get("new_content_hash"):
                            errors.append(f"resulting state mismatch for {file_id}")
                    elif file_id in expected_state:
                        errors.append(f"delete was not applied for {file_id}")
            except (AttributeError, ValueError, KeyError, TypeError):
                errors.append("cannot verify change reconstruction")
    if not errors:
        try: state_for_point(db, point); checks.append("artifact applies to parent state")
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc: errors.append(f"cannot apply backup: {exc}")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "checks_performed": checks}
