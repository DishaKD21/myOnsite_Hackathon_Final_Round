from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import BackupPoint, Resolution
from .validation_service import validate_backup

def effective_id(db: Session, point_id: str) -> str:
    resolution = db.execute(select(Resolution).where(Resolution.original_id == point_id, Resolution.approved.is_(True)).order_by(Resolution.id.desc())).scalars().first()
    return resolution.replacement_id if resolution else point_id

def verify_chain(db: Session) -> dict:
    points = db.execute(select(BackupPoint).order_by(BackupPoint.sequence)).scalars().all()
    full = next((item for item in points if item.type == "FULL"), None)
    if full is None: return {"chain_status": "BROKEN", "latest_safe_recovery_point": None, "earliest_problem": "no full backup", "replacement": None}
    full_result = validate_backup(db, db.get(BackupPoint, effective_id(db, full.id)))
    if not full_result["valid"]: return {"chain_status": "BROKEN", "latest_safe_recovery_point": None, "earliest_problem": full.id, "replacement": None, "details": full_result}
    latest = full.id; expected_parent = full.id; replacement = None; problem_point = None
    resolved_replacements = {item.replacement_id for item in db.execute(select(Resolution).where(Resolution.approved.is_(True))).scalars().all()}
    for point in [item for item in points if item.type == "INCREMENTAL" and item.id not in resolved_replacements]:
        if point.parent_id != expected_parent:
            return {"chain_status": "BROKEN", "latest_safe_recovery_point": latest, "earliest_problem": point.id, "replacement": replacement}
        actual_id = effective_id(db, point.id); actual = db.get(BackupPoint, actual_id)
        result = validate_backup(db, actual) if actual else {"valid": False, "errors": ["replacement missing"]}
        if not result["valid"]:
            return {"chain_status": "BROKEN", "latest_safe_recovery_point": latest, "earliest_problem": point.id, "replacement": replacement, "details": result}
        latest = actual.id; expected_parent = point.id
        if actual.id != point.id:
            replacement = actual.id
            problem_point = point.id
    status = "RECOVERED_WITH_ALTERNATE" if replacement else "VALID"
    return {"chain_status": status, "latest_safe_recovery_point": latest, "earliest_problem": problem_point, "replacement": replacement}

def find_alternate_delta(db: Session, original: BackupPoint) -> list[BackupPoint]:
    return db.execute(select(BackupPoint).where(BackupPoint.type == "INCREMENTAL", BackupPoint.id != original.id, BackupPoint.source_id == original.source_id, BackupPoint.parent_id == original.parent_id, BackupPoint.start_version == original.start_version, BackupPoint.end_version == original.end_version, BackupPoint.change_count == original.change_count)).scalars().all()
