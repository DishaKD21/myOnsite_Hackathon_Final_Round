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
    if full is None: return {"chain_status": "BROKEN", "latest_safe_recovery_point": None, "earliest_problem": "no full backup", "replacement": None, "nodes": [], "steps": []}
    full_result = validate_backup(db, db.get(BackupPoint, effective_id(db, full.id)))
    nodes = [{"id": full.id, "status": "failed" if not full_result["valid"] else "passed", "steps": [{"name": check, "status": "completed"} for check in full_result.get("checks_performed", [])] + [{"name": error, "status": "failed"} for error in full_result.get("errors", [])]}]
    if not full_result["valid"]: return {"chain_status": "BROKEN", "latest_safe_recovery_point": None, "earliest_problem": full.id, "replacement": None, "details": full_result, "nodes": nodes, "steps": nodes[0]["steps"]}
    latest = full.id; expected_parent = full.id; replacement = None; problem_point = None
    resolved_replacements = {item.replacement_id for item in db.execute(select(Resolution).where(Resolution.approved.is_(True))).scalars().all()}
    for point in [item for item in points if item.type == "INCREMENTAL" and item.id not in resolved_replacements]:
        if point.parent_id != expected_parent:
            nodes.append({"id": point.id, "status": "failed", "steps": [{"name": "parent relationship", "status": "failed"}]})
            return {"chain_status": "BROKEN", "latest_safe_recovery_point": latest, "earliest_problem": point.id, "replacement": replacement, "nodes": nodes, "steps": nodes[-1]["steps"]}
        actual_id = effective_id(db, point.id); actual = db.get(BackupPoint, actual_id)
        result = validate_backup(db, actual) if actual else {"valid": False, "errors": ["replacement missing"]}
        if not result["valid"]:
            node = {"id": point.id, "status": "failed", "steps": [{"name": check, "status": "completed"} for check in result.get("checks_performed", [])] + [{"name": error, "status": "failed"} for error in result.get("errors", [])]}
            nodes.append(node)
            return {"chain_status": "BROKEN", "latest_safe_recovery_point": latest, "earliest_problem": point.id, "replacement": replacement, "details": result, "nodes": nodes, "steps": node["steps"]}
        nodes.append({"id": point.id, "status": "passed", "steps": [{"name": check, "status": "completed"} for check in result.get("checks_performed", [])]})
        latest = actual.id; expected_parent = point.id
        if actual.id != point.id:
            replacement = actual.id
            problem_point = point.id
    status = "RECOVERED_WITH_ALTERNATE" if replacement else "VALID"
    return {"chain_status": status, "latest_safe_recovery_point": latest, "earliest_problem": problem_point, "replacement": replacement, "nodes": nodes, "steps": [step for node in nodes for step in node["steps"]]}

def find_alternate_delta(db: Session, original: BackupPoint) -> list[BackupPoint]:
    return db.execute(select(BackupPoint).where(BackupPoint.type == "INCREMENTAL", BackupPoint.id != original.id, BackupPoint.source_id == original.source_id, BackupPoint.parent_id == original.parent_id, BackupPoint.start_version == original.start_version, BackupPoint.end_version == original.end_version, BackupPoint.change_count == original.change_count)).scalars().all()
