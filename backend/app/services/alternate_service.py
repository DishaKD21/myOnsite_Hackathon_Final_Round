from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import BackupPoint, Resolution
from .engine import state_for_point
from .validation_service import validate_backup
from .hash_service import calculate_artifact_hash
from .manifest_service import manifest_hash

def _change_evidence(change: dict) -> tuple:
    old, new = change.get("old"), change.get("new")
    operation = "ADD" if old is None else "DELETE" if new is None else "MODIFY"
    return (
        change.get("file_id"),
        operation,
        change.get("previous_version"),
        change.get("new_version"),
        change.get("previous_content_hash"),
        change.get("new_content_hash"),
    )

def _state_from_change_records(db: Session, point: BackupPoint) -> dict:
    parent = db.get(BackupPoint, point.parent_id)
    if parent is None:
        raise ValueError("parent is missing")
    state = state_for_point(db, parent)
    for item in point.changes:
        change = json.loads(item.payload_json)
        if change.get("new") is None:
            state.pop(change["file_id"], None)
        else:
            state[change["file_id"]] = change["new"]
    return state

def create_alternate_copy(db: Session, original: BackupPoint, alternate_id: str) -> BackupPoint:
    """Create a separate-storage copy used by the deterministic demo."""
    if db.get(BackupPoint, alternate_id):
        return db.get(BackupPoint, alternate_id)
    alternate_dir = Path(original.artifact_path).parent.parent / alternate_id
    alternate_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = alternate_dir / f"{alternate_id}.zip"
    manifest_path = alternate_dir / "manifest.json"
    artifact_path.write_bytes(Path(original.artifact_path).read_bytes())
    original_payload = Path(original.artifact_path).with_name("artifact.json")
    (alternate_dir / "artifact.json").write_bytes(original_payload.read_bytes())
    manifest_path.write_bytes(Path(original.manifest_path).read_bytes())
    alternate = BackupPoint(id=alternate_id, source_id=original.source_id, type=original.type, sequence=original.sequence, parent_id=original.parent_id, start_version=original.start_version, end_version=original.end_version, change_count=original.change_count, artifact_path=str(artifact_path), manifest_path=str(manifest_path), manifest_hash=manifest_hash(json.loads(manifest_path.read_text(encoding="utf-8"))), artifact_hash=calculate_artifact_hash(artifact_path), status="VALID")
    db.add(alternate)
    for change in original.changes:
        db.add(__import__("app.models", fromlist=["BackupChange"]).BackupChange(backup_id=alternate_id, file_id=change.file_id, payload_json=change.payload_json))
    db.commit()
    return alternate

def verify_alternate(db: Session, original: BackupPoint, alternate: BackupPoint) -> dict:
    errors = []
    if original.source_id != alternate.source_id: errors.append("source_id differs")
    if original.manifest_hash != alternate.manifest_hash: errors.append("manifest hash differs")
    for field in ("parent_id", "start_version", "end_version", "change_count"):
        if getattr(original, field) != getattr(alternate, field): errors.append(f"{field} differs")
    result = validate_backup(db, alternate)
    errors.extend(result["errors"])
    if not errors:
        old_payload = Path(original.artifact_path).with_name("artifact.json")
        new_payload = Path(alternate.artifact_path).with_name("artifact.json")
        old = json.loads(old_payload.read_text(encoding="utf-8")) if old_payload.exists() else None
        new = json.loads(new_payload.read_text(encoding="utf-8"))
        expected_changes = original.changes
        old_coverage = [_change_evidence(item) for item in old.get("changes", [])] if old else [_change_evidence(json.loads(item.payload_json)) for item in expected_changes]
        new_coverage = [_change_evidence(item) for item in new.get("changes", [])]
        if sorted(old_coverage) != sorted(new_coverage): errors.append("change evidence differs")
        try:
            try:
                original_state = state_for_point(db, original)
            except (OSError, ValueError, json.JSONDecodeError):
                original_state = _state_from_change_records(db, original)
            alternate_state = state_for_point(db, alternate)
            original_projection = {key: (value.get("version"), value.get("content_hash")) for key, value in original_state.items()}
            alternate_projection = {key: (value.get("version"), value.get("content_hash")) for key, value in alternate_state.items()}
            if original_projection != alternate_projection:
                errors.append("reconstructed state differs")
        except (AttributeError, KeyError, OSError, ValueError, json.JSONDecodeError):
            errors.append("cannot prove reconstructed state equivalence")
    if errors: return {"accepted": False, "errors": errors}
    db.add(Resolution(original_id=original.id, replacement_id=alternate.id, reason="Equivalent coverage and content evidence verified")); db.commit()
    return {"accepted": True, "original_delta": original.id, "replacement_delta": alternate.id, "reason": "Equivalent coverage and content evidence verified"}
