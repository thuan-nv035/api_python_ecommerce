from typing import Optional
from pydantic import BaseModel


class InvoiceCreate(BaseModel):
    order_id: int
    note: Optional[str] = None


class InvoiceStatusUpdate(BaseModel):
    status: str
    payment_status: Optional[str] = None
    note: Optional[str] = None