from pydantic import BaseModel

class RestoreInput(BaseModel):
    recovery_point_id: str
