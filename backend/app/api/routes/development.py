import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...services.reset_service import reset_runtime_data

router = APIRouter(prefix="/development", tags=["development"])


@router.post("/reset")
def reset(db: Session = Depends(get_db)) -> dict:
    if os.getenv("BACKUPCHAIN_ENV", "development").lower() != "development":
        raise HTTPException(status_code=404, detail="Not found")
    return reset_runtime_data(db)