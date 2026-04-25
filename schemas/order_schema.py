from typing import Optional
from pydantic import BaseModel


class CheckoutSchema(BaseModel):
    full_name: str
    phone: str
    address: str
    note: Optional[str] = None
    payment_method: Optional[str] = "cod"
    coupon_code: Optional[str] = None

class UpdateOrderStatusSchema(BaseModel):
    status: str