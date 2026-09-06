from fastapi import APIRouter, File, HTTPException, UploadFile
from ...schemas.source import AddInput, DeleteInput, ModifyInput
from ...services.source_service import SourceService
from ...database import SOURCE_DIR

router = APIRouter()
source = SourceService(SOURCE_DIR)

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

@router.post("/source/files")
async def upload_files(files: list[UploadFile] = File(...)) -> dict:
    try:
        uploaded = []
        for item in files:
            source.upload(item.filename or "uploaded-file", await item.read())
            uploaded.append(item.filename or "uploaded-file")
        return {
            "status": "success",
            "source": source.state(),
            "steps": [
                {"name": "upload_files", "status": "completed", "details": ", ".join(uploaded)},
                {"name": "read_file_metadata", "status": "completed", "details": f"{len(uploaded)} files"},
                {"name": "calculate_content_hashes", "status": "completed"},
                {"name": "register_source_files", "status": "completed"},
                {"name": "update_source_state", "status": "completed"},
            ],
        }
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
