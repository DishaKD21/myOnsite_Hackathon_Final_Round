from __future__ import annotations
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import get_db, init_db
from .schemas import SourceFileInput, ModifyInput, AddInput, DeleteInput, RestoreInput
from .services.source_service import SourceService
from .services import engine
from .services.engine import source, create_full_backup, create_incremental_backup
from .services.validation_service import validate_backup
from .services.chain_service import verify_chain, find_alternate_delta
from .services.alternate_service import verify_alternate
from .services.recovery_service import restore_to_recovery_point, verify_restored_state
from .models import BackupPoint

app = FastAPI(title="BackupChain", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup() -> None: init_db()

def serialize(point: BackupPoint) -> dict:
    return {key: getattr(point, key) for key in ("id", "source_id", "type", "sequence", "parent_id", "start_version", "end_version", "change_count", "artifact_path", "manifest_path", "manifest_hash", "artifact_hash", "status", "created_at")}

@app.post("/source/seed")
def seed(files: list[SourceFileInput]) -> dict: return source.seed([item.model_dump() for item in files])
@app.post("/source/modify")
def modify(item: ModifyInput) -> dict:
    try: return source.modify(item.file_id, item.content)
    except KeyError: raise HTTPException(404, "file not found")
@app.post("/source/add")
def add(item: AddInput) -> dict:
    try: return source.add(item.file_id, item.filename, item.content)
    except ValueError as exc: raise HTTPException(409, str(exc))
@app.post("/source/delete")
def delete(item: DeleteInput) -> dict:
    try: return source.delete(item.file_id)
    except KeyError: raise HTTPException(404, "file not found")
@app.get("/source/state")
def get_source_state() -> dict: return source.state()

@app.post("/backup/full")
def full(db: Session = Depends(get_db)) -> dict: return serialize(create_full_backup(db))
@app.post("/backup/incremental")
def incremental(db: Session = Depends(get_db)) -> dict:
    try: return serialize(create_incremental_backup(db))
    except ValueError as exc: raise HTTPException(400, str(exc))
@app.get("/backups")
def backups(db: Session = Depends(get_db)) -> list[dict]: return [serialize(item) for item in db.query(BackupPoint).order_by(BackupPoint.sequence).all()]
@app.get("/backups/{backup_id}")
def backup(backup_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(BackupPoint, backup_id)
    if not item: raise HTTPException(404, "backup not found")
    return serialize(item)
@app.post("/backups/{backup_id}/validate")
def validate(backup_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(BackupPoint, backup_id)
    if not item: raise HTTPException(404, "backup not found")
    return validate_backup(db, item)
@app.get("/chain/verify")
def chain(db: Session = Depends(get_db)) -> dict: return verify_chain(db)
@app.get("/chain/problems")
def problems(db: Session = Depends(get_db)):
    result = verify_chain(db); return {"has_problem": result["chain_status"] == "BROKEN", "details": result}
@app.get("/recovery-points")
def recovery_points(db: Session = Depends(get_db)) -> list[dict]: return [serialize(item) for item in db.query(BackupPoint).order_by(BackupPoint.sequence).all()]
@app.post("/restore")
def restore(item: RestoreInput, db: Session = Depends(get_db)):
    try: return restore_to_recovery_point(db, item.recovery_point_id)
    except ValueError as exc: raise HTTPException(404, str(exc))
@app.post("/backups/{backup_id}/find-alternate")
def find_alternate(backup_id: str, db: Session = Depends(get_db)):
    item = db.get(BackupPoint, backup_id)
    if not item: raise HTTPException(404, "backup not found")
    return {"original_delta": backup_id, "candidates": [serialize(candidate) for candidate in find_alternate_delta(db, item)]}
@app.post("/backups/{backup_id}/verify-alternate")
def verify_alt(backup_id: str, alternate_id: str, db: Session = Depends(get_db)):
    original, alternate = db.get(BackupPoint, backup_id), db.get(BackupPoint, alternate_id)
    if not original or not alternate: raise HTTPException(404, "backup not found")
    return verify_alternate(db, original, alternate)
@app.post("/restore/verify")
def restore_verify(item: RestoreInput, db: Session = Depends(get_db)):
    result = restore_to_recovery_point(db, item.recovery_point_id)
    return verify_restored_state(result, source.state()) if result.get("restored") else result
