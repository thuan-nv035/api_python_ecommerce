from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ExpenseCategoryCreate(BaseModel):
    name: str
    code: str
    desc: Optional[str] = None
    is_active: Optional[bool] = True


class ExpenseCategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    desc: Optional[str] = None
    is_active: Optional[bool] = None


class ExpenseCreate(BaseModel):
    title: str
    code: Optional[str] = None
    category_id: Optional[int] = None
    amount: float = Field(..., ge=0)
    payment_method: Optional[str] = "cash"
    expense_date: Optional[datetime] = None
    note: Optional[str] = None


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    category_id: Optional[int] = None
    amount: Optional[float] = Field(None, ge=0)
    payment_method: Optional[str] = None
    expense_date: Optional[datetime] = None
    note: Optional[str] = None


class ExpenseStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None