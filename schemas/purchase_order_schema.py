from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., gt=0)
    unit_cost: float = Field(..., ge=0)
    note: Optional[str] = None


class PurchaseOrderCreate(BaseModel):
    code: Optional[str] = None

    supplier_id: int
    warehouse_id: int

    expected_date: Optional[datetime] = None

    tax_amount: Optional[float] = 0
    shipping_fee: Optional[float] = 0
    discount_amount: Optional[float] = 0

    note: Optional[str] = None

    items: List[PurchaseOrderItemCreate]


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    expected_date: Optional[datetime] = None

    tax_amount: Optional[float] = None
    shipping_fee: Optional[float] = None
    discount_amount: Optional[float] = None

    note: Optional[str] = None


class PurchaseOrderReceiveItem(BaseModel):
    item_id: int
    received_quantity: int = Field(..., gt=0)


class PurchaseOrderReceive(BaseModel):
    items: Optional[List[PurchaseOrderReceiveItem]] = None
    note: Optional[str] = None