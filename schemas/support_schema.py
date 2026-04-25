from typing import Optional
from pydantic import BaseModel


class SupportTicketCreate(BaseModel):
    order_id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    subject: str
    message: str


class SupportTicketStatusUpdate(BaseModel):
    status: str
    admin_reply: Optional[str] = None