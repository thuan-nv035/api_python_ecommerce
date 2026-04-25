from typing import Optional
from pydantic import BaseModel


class PaymentCreate(BaseModel):
    order_id: int
    payment_method: Optional[str] = "cod"


class PaymentStatusUpdate(BaseModel):
    payment_status: str
    transaction_id: Optional[str] = None