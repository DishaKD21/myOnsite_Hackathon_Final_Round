from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import BackupPoint, Resolution
from .engine import state_for_point
from .validation_service import validate_backup
from .hash_service import calculate_artifact_hash
from .manifest_service import manifest_hash

def create_alternate_copy(db: Session, original: BackupPoint, alternate_id: str) -> BackupPoint:
    """Create a separate-storage copy used by the deterministic demo."""
    if db.get(BackupPoint, alternate_id):
        return db.get(BackupPoint, alternate_id)
    alternate_dir = Path(original.artifact_path).parent.parent / alternate_id
    alternate_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = alternate_dir / "artifact.json"
    manifest_path = alternate_dir / "manifest.json"
    artifact_path.write_bytes(Path(original.artifact_path).read_bytes())
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
    for field in ("parent_id", "start_version", "end_version", "change_count"):
        if getattr(original, field) != getattr(alternate, field): errors.append(f"{field} differs")
    result = validate_backup(db, alternate)
    errors.extend(result["errors"])
    if not errors:
        old = json.loads(Path(original.artifact_path).read_text(encoding="utf-8")) if Path(original.artifact_path).exists() else None
        new = json.loads(open(alternate.artifact_path, encoding="utf-8").read())
        expected_changes = original.changes
        old_coverage = [(item.file_id, json.loads(item.payload_json).get("previous_version"), json.loads(item.payload_json).get("new_version"), json.loads(item.payload_json).get("previous_content_hash"), json.loads(item.payload_json).get("new_content_hash")) for item in expected_changes]
        if old:
            old_coverage = [(item["file_id"], item.get("previous_version"), item.get("new_version"), item.get("previous_content_hash"), item.get("new_content_hash")) for item in old.get("changes", [])]
        new_coverage = [(item["file_id"], item.get("previous_version"), item.get("new_version"), item.get("previous_content_hash"), item.get("new_content_hash")) for item in new.get("changes", [])]
        if sorted(old_coverage) != sorted(new_coverage): errors.append("change coverage differs")
    if errors: return {"accepted": False, "errors": errors}
    db.add(Resolution(original_id=original.id, replacement_id=alternate.id, reason="Equivalent coverage and content evidence verified")); db.commit()
    return {"accepted": True, "original_delta": original.id, "replacement_delta": alternate.id, "reason": "Equivalent coverage and content evidence verified"}
