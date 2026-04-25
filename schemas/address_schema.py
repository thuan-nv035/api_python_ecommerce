from typing import Optional
from pydantic import BaseModel


class AddressCreate(BaseModel):
    full_name: str
    phone: str
    province: str
    district: str
    ward: str
    address_detail: str
    is_default: Optional[bool] = False


class AddressUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    address_detail: Optional[str] = None
    is_default: Optional[bool] = None