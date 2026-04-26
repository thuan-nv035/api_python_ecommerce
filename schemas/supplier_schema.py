from typing import Optional
from pydantic import BaseModel


class SupplierCreate(BaseModel):
    name: str
    code: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_code: Optional[str] = None
    contact_person: Optional[str] = None
    status: Optional[str] = "active"
    note: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_code: Optional[str] = None
    contact_person: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None