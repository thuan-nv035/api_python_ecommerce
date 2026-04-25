from typing import Optional
from pydantic import BaseModel


class ShipmentCreate(BaseModel):
    order_id: int
    carrier: Optional[str] = None
    tracking_code: Optional[str] = None
    shipping_fee: Optional[float] = 0
    note: Optional[str] = None


class ShipmentUpdate(BaseModel):
    carrier: Optional[str] = None
    tracking_code: Optional[str] = None
    shipping_fee: Optional[float] = None
    status: Optional[str] = None
    note: Optional[str] = None