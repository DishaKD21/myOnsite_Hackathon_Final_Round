from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...database import get_db
from ...services.chain_service import verify_chain

router = APIRouter()

@router.get("/chain/verify")
def chain(db: Session = Depends(get_db)) -> dict:
    return verify_chain(db)

@router.get("/chain/problems")
def problems(db: Session = Depends(get_db)) -> dict:
    result = verify_chain(db)
    return {"has_problem": result["chain_status"] == "BROKEN", "details": result}
