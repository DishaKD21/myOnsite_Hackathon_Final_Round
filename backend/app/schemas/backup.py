from typing import Any
from pydantic import BaseModel, Field

class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks_performed: list[str] = Field(default_factory=list)

class ComparisonResult(BaseModel):
    file_id: str
    metadata_changed: bool
    content_changed: bool
    change_reason: str
    previous: dict[str, Any] | None
    current: dict[str, Any] | None
