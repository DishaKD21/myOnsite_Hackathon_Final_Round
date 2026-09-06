from __future__ import annotations
import json
import zipfile
from pathlib import Path
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import database
from ..backup_chain import BackupChain
from ..database import SOURCE_DIR
from ..models import BackupPoint, BackupChange, Resolution
from .hash_service import canonical_bytes, calculate_artifact_hash, sha256_content
from .manifest_service import manifest_hash, sorted_changes
from .source_service import SourceService

source = SourceService(SOURCE_DIR)

def _files(value: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(list(value.get("files", [])), key=lambda item: item["file_id"])

def _artifact_payload(point: BackupPoint) -> dict[str, Any]:
    compatibility_path = Path(point.artifact_path).with_name("artifact.json")
    return json.loads(compatibility_path.read_text(encoding="utf-8"))

def compare_file(previous: dict[str, Any] | None, current: dict[str, Any] | None, verify_hash: bool = False) -> dict[str, Any]:
    file_id = (current or previous)["file_id"]
    if previous is None:
        return {"file_id": file_id, "metadata_changed": True, "content_changed": True, "change_reason": "added", "previous": None, "current": current}
    if current is None:
        return {"file_id": file_id, "metadata_changed": True, "content_changed": True, "change_reason": "deleted", "previous": previous, "current": None}
    metadata_changed = any(previous.get(key) != current.get(key) for key in ("version", "size", "modified_timestamp"))
    content_changed = previous.get("content_hash") != current.get("content_hash")
    reason = "content changed" if content_changed else ("metadata changed without content change" if metadata_changed else "unchanged")
    return {"file_id": file_id, "metadata_changed": metadata_changed, "content_changed": content_changed, "change_reason": reason, "previous": previous, "current": current}

def state_for_point(db: Session, point: BackupPoint, replacements: dict[str, str] | None = None) -> dict[str, dict[str, Any]]:
    replacements = replacements or {}
    if point.type == "FULL":
        artifact = _artifact_payload(point)
        return {item["file_id"]: item for item in artifact["files"]}
    replacement = db.execute(select(Resolution).where(Resolution.approved.is_(True), Resolution.replacement_id == point.id).order_by(Resolution.id.desc())).scalars().first()
    parent_key = db.get(BackupPoint, replacement.original_id).parent_id if replacement else point.parent_id
    resolution = None if replacement else db.execute(select(Resolution).where(Resolution.original_id == parent_key, Resolution.approved.is_(True)).order_by(Resolution.id.desc())).scalars().first()
    parent_id = replacements.get(parent_key, resolution.replacement_id if resolution else parent_key)
    parent = db.get(BackupPoint, parent_id)
    if parent is None:
        raise ValueError(f"missing parent {point.parent_id}")
    state = state_for_point(db, parent, replacements)
    artifact = _artifact_payload(point)
    for change in artifact["changes"]:
        if change["new"] is None:
            state.pop(change["file_id"], None)
        else:
            state[change["file_id"]] = change["new"]
    return state

def detect_changes(previous_recovery_point: BackupPoint | BackupChain, current_source_state: dict[str, Any], db: Session) -> list[dict[str, Any]]:
    if isinstance(previous_recovery_point, BackupChain):
        return previous_recovery_point.compare_source(_files(current_source_state))
    previous = state_for_point(db, previous_recovery_point)
    current = {item["file_id"]: item for item in _files(current_source_state)}
    results = []
    for file_id in sorted(set(previous) | set(current)):
        result = compare_file(previous.get(file_id), current.get(file_id))
        if result["change_reason"] != "unchanged":
            results.append(result)
    return results

def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))

def _write_zip(path: Path, files: list[dict[str, Any]], changes: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.writestr(item["filename"], item.get("content", "").encode("utf-8"))
        for change in changes:
            if change.get("new") is not None:
                archive.writestr(change["new"]["filename"], change["new"].get("content", "").encode("utf-8"))

def _change_payload(result: dict[str, Any]) -> dict[str, Any]:
    old, new = result["previous"], result["current"]
    return {"file_id": result["file_id"], "previous_version": old.get("version") if old else None, "new_version": new.get("version") if new else None, "previous_content_hash": old.get("content_hash") if old else None, "new_content_hash": new.get("content_hash") if new else None, "previous_size": old.get("size") if old else None, "new_size": new.get("size") if new else None, "previous_modified_timestamp": old.get("modified_timestamp") if old else None, "new_modified_timestamp": new.get("modified_timestamp") if new else None, "old": old, "new": new}

def create_full_backup(db: Session, source_id: str = "demo-source") -> BackupPoint:
    state = source.state(); sequence = db.query(BackupPoint).filter_by(source_id=source_id).count() + 1
    point_id = f"FULL-{sequence:03d}"
    directory = database.BACKUPS_DIR / point_id
    artifact = {"kind": "FULL", "point_id": point_id, "files": _files(state)}
    manifest = {"type": "FULL", "point_id": point_id, "source_id": source_id, "end_version": state["version"], "file_ids": [item["file_id"] for item in _files(state)], "file_count": len(_files(state))}
    artifact_path, manifest_path = directory / f"{point_id}.zip", directory / "manifest.json"
    _write_json(directory / "artifact.json", artifact); _write_zip(artifact_path, _files(state), []); _write_json(manifest_path, manifest)
    point = BackupPoint(id=point_id, source_id=source_id, type="FULL", sequence=sequence, start_version=state["version"], end_version=state["version"], change_count=len(_files(state)), artifact_path=str(artifact_path), manifest_path=str(manifest_path), manifest_hash=manifest_hash(manifest), artifact_hash=calculate_artifact_hash(artifact_path), status="VALID")
    db.add(point); db.commit(); return point

def create_incremental_backup(db: Session, source_id: str = "demo-source", chain: BackupChain | None = None) -> BackupPoint | None:
    chain = chain or BackupChain.load_for_comparison(db, source_id)
    chain.last_comparison_steps = [{"name": "start_linked_list_traversal", "status": "completed"}]
    parent = chain.tail
    if parent is None:
        raise ValueError("a full backup is required first")
    state = source.state(); comparisons = detect_changes(chain, state, db)
    if not comparisons:
        return None
    sequence = parent.sequence + 1; point_id = f"D{sequence - 1}"
    changes = sorted_changes([_change_payload(item) for item in comparisons])
    directory = database.BACKUPS_DIR / point_id
    artifact = {"kind": "DELTA", "point_id": point_id, "parent_id": parent.id, "changes": changes}
    manifest = {"type": "DELTA", "delta_id": point_id, "parent_id": parent.id, "source_id": source_id, "start_version": parent.end_version, "end_version": state["version"], "change_count": len(changes), "file_ids": [change["file_id"] for change in changes], "coverage": [{key: change[key] for key in ("file_id", "previous_version", "new_version", "previous_content_hash", "new_content_hash")} for change in changes]}
    artifact_path, manifest_path = directory / f"{point_id}.zip", directory / "manifest.json"
    _write_json(directory / "artifact.json", artifact); _write_zip(artifact_path, [], changes); _write_json(manifest_path, manifest)
    point = BackupPoint(id=point_id, source_id=source_id, type="INCREMENTAL", sequence=sequence, parent_id=parent.id, start_version=parent.end_version, end_version=state["version"], change_count=len(changes), artifact_path=str(artifact_path), manifest_path=str(manifest_path), manifest_hash=manifest_hash(manifest), artifact_hash=calculate_artifact_hash(artifact_path), status="VALID")
    db.add(point)
    for change in changes: db.add(BackupChange(backup_id=point_id, file_id=change["file_id"], payload_json=json.dumps(change, sort_keys=True)))
    db.commit(); return point
