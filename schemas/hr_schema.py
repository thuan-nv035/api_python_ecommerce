from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str
    code: str
    desc: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = True


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    desc: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class EmployeeCreate(BaseModel):
    user_id: Optional[int] = None
    department_id: Optional[int] = None

    employee_code: str

    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

    position: Optional[str] = None
    salary: Optional[float] = Field(0, ge=0)

    hire_date: Optional[datetime] = None
    birth_date: Optional[datetime] = None

    status: Optional[str] = "active"
    note: Optional[str] = None


class EmployeeUpdate(BaseModel):
    user_id: Optional[int] = None
    department_id: Optional[int] = None

    employee_code: Optional[str] = None

    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

    position: Optional[str] = None
    salary: Optional[float] = Field(None, ge=0)

    hire_date: Optional[datetime] = None
    birth_date: Optional[datetime] = None

    status: Optional[str] = None
    note: Optional[str] = None