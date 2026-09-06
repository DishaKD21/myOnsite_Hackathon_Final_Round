from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..backup_chain import BackupChain
from ..models import BackupPoint, Resolution
from .validation_service import validate_backup

def effective_id(db: Session, point_id: str) -> str:
    resolution = db.execute(select(Resolution).where(Resolution.original_id == point_id, Resolution.approved.is_(True)).order_by(Resolution.id.desc())).scalars().first()
    return resolution.replacement_id if resolution else point_id

def verify_chain(db: Session) -> dict:
    chain = BackupChain.load(db)
    full = chain.head
    if full is None: return {"chain_status": "BROKEN", "latest_safe_recovery_point": None, "earliest_problem": "no full backup", "replacement": None, "nodes": [], "steps": []}
    full_result = validate_backup(db, db.get(BackupPoint, effective_id(db, full.id)))
    nodes = [{"id": full.id, "status": "failed" if not full_result["valid"] else "passed", "steps": [{"name": check, "status": "completed"} for check in full_result.get("checks_performed", [])] + [{"name": error, "status": "failed"} for error in full_result.get("errors", [])]}]
    if not full_result["valid"]: return {"chain_status": "BROKEN", "latest_safe_recovery_point": None, "earliest_problem": full.id, "replacement": None, "details": full_result, "nodes": nodes, "steps": nodes[0]["steps"]}
    latest = full.id; expected_parent = full.id; expected_version = full.end_version; replacement = None; problem_point = None
    point = full.next
    while point:
        if point.parent_id != expected_parent:
            nodes.append({"id": point.id, "status": "failed", "steps": [{"name": "parent relationship", "status": "failed"}]})
            return {"chain_status": "BROKEN", "latest_safe_recovery_point": latest, "earliest_problem": point.id, "replacement": replacement, "nodes": nodes, "steps": nodes[-1]["steps"]}
        if point.start_version != expected_version:
            nodes.append({"id": point.id, "status": "failed", "steps": [{"name": "version continuity", "status": "failed"}]})
            return {"chain_status": "BROKEN", "latest_safe_recovery_point": latest, "earliest_problem": point.id, "replacement": replacement, "nodes": nodes, "steps": nodes[-1]["steps"]}
        actual_id = effective_id(db, point.id); actual = db.get(BackupPoint, actual_id)
        result = validate_backup(db, actual) if actual else {"valid": False, "errors": ["replacement missing"]}
        if not result["valid"]:
            node = {"id": point.id, "status": "failed", "steps": [{"name": check, "status": "completed"} for check in result.get("checks_performed", [])] + [{"name": error, "status": "failed"} for error in result.get("errors", [])]}
            nodes.append(node)
            return {"chain_status": "BROKEN", "latest_safe_recovery_point": latest, "earliest_problem": point.id, "replacement": replacement, "details": result, "nodes": nodes, "steps": node["steps"]}
        nodes.append({"id": point.id, "status": "passed", "steps": [{"name": check, "status": "completed"} for check in result.get("checks_performed", [])]})
        latest = actual.id; expected_parent = chain.logical_ids.get(point.id, point.id); expected_version = actual.end_version
        if actual.id != point.id:
            replacement = actual.id
            problem_point = point.id
        point = point.next

    approved_replacements = set(db.execute(select(Resolution.replacement_id).where(Resolution.approved.is_(True))).scalars().all())
    resolved_originals = set(db.execute(select(Resolution.original_id).where(Resolution.approved.is_(True))).scalars().all())
    orphan = db.execute(
        select(BackupPoint)
        .where(BackupPoint.source_id == full.source_id, BackupPoint.type == "INCREMENTAL", ~BackupPoint.id.in_(approved_replacements | resolved_originals), BackupPoint.id != full.id)
        .order_by(BackupPoint.sequence)
    ).scalars().first()
    visited = {node["id"] for node in nodes}
    if orphan and orphan.id not in visited:
        nodes.append({"id": orphan.id, "status": "failed", "steps": [{"name": "parent relationship", "status": "failed"}]})
        return {"chain_status": "BROKEN", "latest_safe_recovery_point": latest, "earliest_problem": orphan.id, "replacement": replacement, "nodes": nodes, "steps": nodes[-1]["steps"]}
    status = "RECOVERED_WITH_ALTERNATE" if replacement or any(chain.logical_ids.get(node["id"]) != node["id"] for node in nodes) else "VALID"
    if not replacement:
        replacement = next((node["id"] for node in nodes if chain.logical_ids.get(node["id"]) != node["id"]), None)
    return {"chain_status": status, "latest_safe_recovery_point": latest, "earliest_problem": problem_point, "replacement": replacement, "nodes": nodes, "steps": [step for node in nodes for step in node["steps"]]}

def find_alternate_delta(db: Session, original: BackupPoint) -> list[BackupPoint]:
    return db.execute(select(BackupPoint).where(BackupPoint.type == "INCREMENTAL", BackupPoint.id != original.id, BackupPoint.source_id == original.source_id, BackupPoint.parent_id == original.parent_id, BackupPoint.start_version == original.start_version, BackupPoint.end_version == original.end_version, BackupPoint.change_count == original.change_count)).scalars().all()
