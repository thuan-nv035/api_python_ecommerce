from typing import Optional, List
from pydantic import BaseModel


class ReturnRequestCreate(BaseModel):
    order_id: int
    order_item_id: Optional[int] = None
    reason: str
    images: Optional[List[str]] = []


class ReturnStatusUpdate(BaseModel):
    status: str
    admin_note: Optional[str] = None