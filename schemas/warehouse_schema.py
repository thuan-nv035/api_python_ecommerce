from typing import Optional
from pydantic import BaseModel


class WarehouseCreate(BaseModel):
    name: str
    code: str

    phone: Optional[str] = None
    address: Optional[str] = None

    province: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None

    manager_id: Optional[int] = None

    is_active: Optional[bool] = True
    note: Optional[str] = None


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

    phone: Optional[str] = None
    address: Optional[str] = None

    province: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None

    manager_id: Optional[int] = None

    is_active: Optional[bool] = None
    note: Optional[str] = None