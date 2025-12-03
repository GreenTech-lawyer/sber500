from pydantic import BaseModel
from typing import Optional

class UploadRequest(BaseModel):
    bucket: str
    object_id: str
    user_id: str

class ChatMessage(BaseModel):
    user_id: str
    message: str

class UploadReq(BaseModel):
    filename: str
    user_id: str
    content_type: str

class NotifyReq(BaseModel):
    object_id: str
    bucket: str
    user_id: str
    file_id: str | None = None
    content_type: str | None = None