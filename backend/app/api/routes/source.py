from fastapi import APIRouter, HTTPException
from ...schemas.source import AddInput, DeleteInput, ModifyInput, SourceFileInput
from ...services.source_service import SourceService
from ...database import SOURCE_DIR

router = APIRouter()
source = SourceService(SOURCE_DIR)

@router.post("/source/seed")
def seed(files: list[SourceFileInput]) -> dict:
    return source.seed([item.model_dump() for item in files])

@router.post("/source/modify")
def modify(item: ModifyInput) -> dict:
    try:
        return source.modify(item.file_id, item.content)
    except KeyError as exc:
        raise HTTPException(404, "file not found") from exc

@router.post("/source/add")
def add(item: AddInput) -> dict:
    try:
        return source.add(item.file_id, item.filename, item.content)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

@router.post("/source/delete")
def delete(item: DeleteInput) -> dict:
    try:
        return source.delete(item.file_id)
    except KeyError as exc:
        raise HTTPException(404, "file not found") from exc

@router.get("/source/state")
def get_source_state() -> dict:
    return source.state()
