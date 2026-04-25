from typing import Optional, List
from pydantic import BaseModel


class ChatRoomCreate(BaseModel):
    subject: Optional[str] = None
    message: str
    attachments: Optional[List[str]] = []


class ChatMessageCreate(BaseModel):
    message: str
    attachments: Optional[List[str]] = []


class ChatRoomStatusUpdate(BaseModel):
    status: str


class ChatAssignAdmin(BaseModel):
    admin_id: Optional[int] = None