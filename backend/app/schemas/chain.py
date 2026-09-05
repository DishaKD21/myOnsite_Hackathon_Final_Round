from typing import Any
from pydantic import BaseModel, Field

class ChainVerificationResult(BaseModel):
    chain_status: str
    latest_safe_recovery_point: str | None = None
    earliest_problem: str | None = None
    replacement: str | None = None
    details: dict[str, Any] | None = None
