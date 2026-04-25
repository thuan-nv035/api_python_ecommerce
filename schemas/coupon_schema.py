from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CouponCreate(BaseModel):
    code: str
    desc: Optional[str] = None

    discount_type: str = "percent"
    discount_value: float = Field(..., gt=0)

    min_order_value: Optional[float] = 0
    max_discount: Optional[float] = None

    usage_limit: Optional[int] = None

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    is_active: Optional[bool] = True


class CouponUpdate(BaseModel):
    code: Optional[str] = None
    desc: Optional[str] = None

    discount_type: Optional[str] = None
    discount_value: Optional[float] = None

    min_order_value: Optional[float] = None
    max_discount: Optional[float] = None

    usage_limit: Optional[int] = None

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    is_active: Optional[bool] = None


class ApplyCouponSchema(BaseModel):
    code: str
    order_total: float