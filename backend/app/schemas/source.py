from pydantic import BaseModel

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
