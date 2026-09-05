from __future__ import annotations
import json
import zipfile
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import BackupPoint
from .engine import state_for_point
from .hash_service import calculate_artifact_hash
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
    if not errors:
        try: state_for_point(db, point); checks.append("artifact applies to parent state")
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc: errors.append(f"cannot apply backup: {exc}")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "checks_performed": checks}
