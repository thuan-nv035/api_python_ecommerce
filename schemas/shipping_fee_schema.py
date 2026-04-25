from typing import Optional
from pydantic import BaseModel, Field


class ShippingFeeCalculate(BaseModel):
    province: str
    district: Optional[str] = None
    ward: Optional[str] = None
    cart_total: float = Field(..., ge=0)


class ShippingRateCreate(BaseModel):
    province: str
    district: Optional[str] = None
    ward: Optional[str] = None
    fee: float = Field(..., ge=0)
    free_shipping_from: Optional[float] = None
    estimated_delivery: Optional[str] = "2-4 ngày"
    is_active: Optional[bool] = True


class ShippingRateUpdate(BaseModel):
    province: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    fee: Optional[float] = Field(None, ge=0)
    free_shipping_from: Optional[float] = None
    estimated_delivery: Optional[str] = None
    is_active: Optional[bool] = None