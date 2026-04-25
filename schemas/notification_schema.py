from typing import Optional
from pydantic import BaseModel


class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    type: Optional[str] = "system"
    related_id: Optional[int] = None