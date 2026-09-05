from pydantic import BaseModel, Field
from typing import Any

class SourceFileInput(BaseModel):
    file_id: str
    filename: str
    content: str

class ModifyInput(BaseModel):
    file_id: str
    content: str

class AddInput(BaseModel):
    file_id: str
    filename: str
    content: str

class DeleteInput(BaseModel):
    file_id: str

class RestoreInput(BaseModel):
    recovery_point_id: str

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
