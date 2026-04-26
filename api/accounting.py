import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from api.auth import get_admin_user, get_current_user
from database import get_db
from models.models import (
    User,
    Order,
    Payment,
    PurchaseOrder,
    ExpenseCategory,
    Expense
)
from schemas.accounting_schema import (
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseStatusUpdate
)


accounting_route = APIRouter(tags=["accounting"])

def generate_expense_code():
    return f"EXP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


def parse_date(date_str):
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Ngày phải có định dạng YYYY-MM-DD"
        )


def apply_date_filter(query, model, start_date, end_date, field_name="created_at"):
    field = getattr(model, field_name)

    if start_date:
        query = query.filter(field >= start_date)

    if end_date:
        query = query.filter(field < end_date + timedelta(days=1))

    return query


def expense_category_to_dict(category: ExpenseCategory):
    return {
        "id": category.id,
        "name": category.name,
        "code": category.code,
        "desc": category.desc,
        "is_active": category.is_active,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


def expense_to_dict(expense: Expense):
    return {
        "id": expense.id,
        "title": expense.title,
        "code": expense.code,
        "category_id": expense.category_id,
        "amount": expense.amount,
        "payment_method": expense.payment_method,
        "status": expense.status,
        "expense_date": expense.expense_date,
        "note": expense.note,
        "created_by_id": expense.created_by_id,
        "approved_by_id": expense.approved_by_id,
        "approved_at": expense.approved_at,
        "paid_at": expense.paid_at,
        "created_at": expense.created_at,
        "updated_at": expense.updated_at,
        "category": expense_category_to_dict(expense.category) if expense.category else None,
        "created_by": {
            "id": expense.created_by.id,
            "username": expense.created_by.username,
            "role": getattr(expense.created_by, "role", "user")
        } if expense.created_by else None,
        "approved_by": {
            "id": expense.approved_by.id,
            "username": expense.approved_by.username,
            "role": getattr(expense.approved_by, "role", "user")
        } if expense.approved_by else None,
    }


# =========================
# EXPENSE CATEGORY API
# =========================

@accounting_route.post("/api/expense-categories/")
def create_expense_category(
        data: ExpenseCategoryCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    code = data.code.strip().upper()

    existed = db.query(ExpenseCategory).filter(ExpenseCategory.code == code).first()

    if existed:
        raise HTTPException(status_code=400, detail="Mã loại chi phí đã tồn tại")

    category = ExpenseCategory(
        name=data.name,
        code=code,
        desc=data.desc,
        is_active=data.is_active
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return {
        "message": "Tạo loại chi phí thành công",
        "data": expense_category_to_dict(category)
    }


@accounting_route.get("/api/expense-categories/")
def get_expense_categories(
        request: Request,
        db: Session = Depends(get_db),
        search: str = Query(None),
        is_active: bool = Query(None)
):
    get_admin_user(request)

    query = db.query(ExpenseCategory)

    if search:
        query = query.filter(
            or_(
                ExpenseCategory.name.ilike(f"%{search}%"),
                ExpenseCategory.code.ilike(f"%{search}%")
            )
        )

    if is_active is not None:
        query = query.filter(ExpenseCategory.is_active == is_active)

    categories = query.order_by(ExpenseCategory.id.desc()).all()

    return {
        "message": "Lấy danh sách loại chi phí thành công",
        "data": [expense_category_to_dict(category) for category in categories]
    }


@accounting_route.put("/api/expense-categories/{category_id}")
@accounting_route.patch("/api/expense-categories/{category_id}")
def update_expense_category(
        category_id: int,
        data: ExpenseCategoryUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    category = db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Không tìm thấy loại chi phí")

    update_data = data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="Không có dữ liệu để cập nhật")

    if "code" in update_data:
        new_code = update_data["code"].strip().upper()

        existed = (
            db.query(ExpenseCategory)
            .filter(
                ExpenseCategory.code == new_code,
                ExpenseCategory.id != category_id
            )
            .first()
        )

        if existed:
            raise HTTPException(status_code=400, detail="Mã loại chi phí đã tồn tại")

        update_data["code"] = new_code

    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)

    return {
        "message": "Cập nhật loại chi phí thành công",
        "data": expense_category_to_dict(category)
    }


@accounting_route.delete("/api/expense-categories/{category_id}")
def delete_expense_category(
        category_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    category = db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Không tìm thấy loại chi phí")

    expense_count = db.query(Expense).filter(Expense.category_id == category_id).count()

    if expense_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa loại chi phí đã có phiếu chi. Hãy tắt is_active thay vì xóa."
        )

    db.delete(category)
    db.commit()

    return {
        "message": "Xóa loại chi phí thành công",
        "deleted_category_id": category_id
    }


# =========================
# EXPENSE API
# =========================

@accounting_route.post("/api/expenses/")
def create_expense(
        data: ExpenseCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    get_admin_user(request)

    if data.category_id:
        category = db.query(ExpenseCategory).filter(ExpenseCategory.id == data.category_id).first()

        if not category:
            raise HTTPException(status_code=404, detail="Không tìm thấy loại chi phí")

        if not category.is_active:
            raise HTTPException(status_code=400, detail="Loại chi phí đang bị tắt")

    code = data.code.strip().upper() if data.code else generate_expense_code()

    existed = db.query(Expense).filter(Expense.code == code).first()

    if existed:
        raise HTTPException(status_code=400, detail="Mã phiếu chi đã tồn tại")

    allowed_payment_methods = ["cash", "bank_transfer", "card", "other"]

    if data.payment_method not in allowed_payment_methods:
        raise HTTPException(status_code=400, detail="Phương thức thanh toán không hợp lệ")

    expense = Expense(
        title=data.title,
        code=code,
        category_id=data.category_id,
        amount=data.amount,
        payment_method=data.payment_method,
        status="pending",
        expense_date=data.expense_date or datetime.utcnow(),
        note=data.note,
        created_by_id=current_user.id
    )

    db.add(expense)
    db.commit()
    db.refresh(expense)

    return {
        "message": "Tạo phiếu chi thành công",
        "data": expense_to_dict(expense)
    }


@accounting_route.get("/api/expenses/")
def get_expenses(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        status: str = Query(None),
        category_id: int = Query(None),
        start_date: str = Query(None),
        end_date: str = Query(None)
):
    get_admin_user(request)

    start = parse_date(start_date)
    end = parse_date(end_date)

    query = db.query(Expense)

    if search:
        query = query.filter(
            or_(
                Expense.title.ilike(f"%{search}%"),
                Expense.code.ilike(f"%{search}%"),
                Expense.note.ilike(f"%{search}%")
            )
        )

    if status:
        query = query.filter(Expense.status == status)

    if category_id:
        query = query.filter(Expense.category_id == category_id)

    query = apply_date_filter(query, Expense, start, end, field_name="expense_date")

    total = query.count()

    expenses = (
        query
        .order_by(Expense.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách phiếu chi thành công",
        "data": [expense_to_dict(expense) for expense in expenses],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


@accounting_route.get("/api/expenses/{expense_id}")
def get_expense_by_id(
        expense_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu chi")

    return {
        "message": "Lấy chi tiết phiếu chi thành công",
        "data": expense_to_dict(expense)
    }


@accounting_route.put("/api/expenses/{expense_id}")
@accounting_route.patch("/api/expenses/{expense_id}")
def update_expense(
        expense_id: int,
        data: ExpenseUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu chi")

    if expense.status in ["paid", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail="Không thể sửa phiếu chi đã thanh toán hoặc đã hủy"
        )

    update_data = data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="Không có dữ liệu để cập nhật")

    if "code" in update_data and update_data["code"]:
        new_code = update_data["code"].strip().upper()

        existed = (
            db.query(Expense)
            .filter(
                Expense.code == new_code,
                Expense.id != expense_id
            )
            .first()
        )

        if existed:
            raise HTTPException(status_code=400, detail="Mã phiếu chi đã tồn tại")

        update_data["code"] = new_code

    if "category_id" in update_data and update_data["category_id"]:
        category = (
            db.query(ExpenseCategory)
            .filter(ExpenseCategory.id == update_data["category_id"])
            .first()
        )

        if not category:
            raise HTTPException(status_code=404, detail="Không tìm thấy loại chi phí")

    if "payment_method" in update_data:
        allowed_payment_methods = ["cash", "bank_transfer", "card", "other"]

        if update_data["payment_method"] not in allowed_payment_methods:
            raise HTTPException(status_code=400, detail="Phương thức thanh toán không hợp lệ")

    for key, value in update_data.items():
        setattr(expense, key, value)

    db.commit()
    db.refresh(expense)

    return {
        "message": "Cập nhật phiếu chi thành công",
        "data": expense_to_dict(expense)
    }


@accounting_route.patch("/api/expenses/{expense_id}/status")
def update_expense_status(
        expense_id: int,
        data: ExpenseStatusUpdate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    get_admin_user(request)

    allowed_status = ["pending", "approved", "paid", "cancelled"]

    if data.status not in allowed_status:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu chi không hợp lệ")

    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu chi")

    if expense.status == "cancelled":
        raise HTTPException(status_code=400, detail="Phiếu chi đã hủy")

    expense.status = data.status

    if data.status == "approved":
        expense.approved_by_id = current_user.id
        expense.approved_at = datetime.utcnow()

    if data.status == "paid":
        expense.approved_by_id = expense.approved_by_id or current_user.id
        expense.approved_at = expense.approved_at or datetime.utcnow()
        expense.paid_at = datetime.utcnow()

    if data.note is not None:
        expense.note = data.note

    db.commit()
    db.refresh(expense)

    return {
        "message": "Cập nhật trạng thái phiếu chi thành công",
        "data": expense_to_dict(expense)
    }


@accounting_route.delete("/api/expenses/{expense_id}")
def delete_expense(
        expense_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu chi")

    if expense.status == "paid":
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa phiếu chi đã thanh toán"
        )

    db.delete(expense)
    db.commit()

    return {
        "message": "Xóa phiếu chi thành công",
        "deleted_expense_id": expense_id
    }


# =========================
# ACCOUNTING REPORT API
# =========================

@accounting_route.get("/api/accounting/summary")
def get_accounting_summary(
        request: Request,
        db: Session = Depends(get_db),
        start_date: str = Query(None),
        end_date: str = Query(None)
):
    get_admin_user(request)

    start = parse_date(start_date)
    end = parse_date(end_date)

    payment_query = db.query(func.sum(Payment.amount)).filter(Payment.payment_status == "paid")
    payment_query = apply_date_filter(payment_query, Payment, start, end, field_name="paid_at")
    paid_revenue = payment_query.scalar() or 0

    order_query = db.query(func.sum(Order.total_price)).filter(
        Order.status.in_(["confirmed", "shipping", "completed"])
    )
    order_query = apply_date_filter(order_query, Order, start, end, field_name="created_at")
    order_revenue = order_query.scalar() or 0

    expense_query = db.query(func.sum(Expense.amount)).filter(Expense.status == "paid")
    expense_query = apply_date_filter(expense_query, Expense, start, end, field_name="expense_date")
    total_expense = expense_query.scalar() or 0

    purchase_query = db.query(func.sum(PurchaseOrder.total_amount)).filter(
        PurchaseOrder.status.in_(["partial_received", "received"])
    )
    purchase_query = apply_date_filter(purchase_query, PurchaseOrder, start, end, field_name="order_date")
    purchase_cost = purchase_query.scalar() or 0

    gross_profit = paid_revenue - purchase_cost
    net_profit = paid_revenue - purchase_cost - total_expense

    return {
        "message": "Lấy tổng quan kế toán thành công",
        "data": {
            "start_date": start_date,
            "end_date": end_date,
            "paid_revenue": float(paid_revenue),
            "order_revenue": float(order_revenue),
            "purchase_cost": float(purchase_cost),
            "total_expense": float(total_expense),
            "gross_profit": float(gross_profit),
            "net_profit": float(net_profit)
        }
    }


@accounting_route.get("/api/accounting/profit-loss")
def get_profit_loss_report(
        request: Request,
        db: Session = Depends(get_db),
        start_date: str = Query(None),
        end_date: str = Query(None)
):
    get_admin_user(request)

    start = parse_date(start_date)
    end = parse_date(end_date)

    revenue_query = (
        db.query(
            func.date(Payment.paid_at).label("date"),
            func.sum(Payment.amount).label("revenue")
        )
        .filter(Payment.payment_status == "paid")
    )

    revenue_query = apply_date_filter(revenue_query, Payment, start, end, field_name="paid_at")

    revenue_rows = (
        revenue_query
        .group_by(func.date(Payment.paid_at))
        .order_by(func.date(Payment.paid_at).asc())
        .all()
    )

    expense_query = (
        db.query(
            func.date(Expense.expense_date).label("date"),
            func.sum(Expense.amount).label("expense")
        )
        .filter(Expense.status == "paid")
    )

    expense_query = apply_date_filter(expense_query, Expense, start, end, field_name="expense_date")

    expense_rows = (
        expense_query
        .group_by(func.date(Expense.expense_date))
        .order_by(func.date(Expense.expense_date).asc())
        .all()
    )

    report_map = {}

    for row in revenue_rows:
        date_key = str(row.date)
        report_map[date_key] = {
            "date": date_key,
            "revenue": float(row.revenue or 0),
            "expense": 0,
            "profit": float(row.revenue or 0)
        }

    for row in expense_rows:
        date_key = str(row.date)

        if date_key not in report_map:
            report_map[date_key] = {
                "date": date_key,
                "revenue": 0,
                "expense": 0,
                "profit": 0
            }

        report_map[date_key]["expense"] = float(row.expense or 0)
        report_map[date_key]["profit"] = (
            report_map[date_key]["revenue"]
            - report_map[date_key]["expense"]
        )

    data = sorted(report_map.values(), key=lambda item: item["date"])

    total_revenue = sum(item["revenue"] for item in data)
    total_expense = sum(item["expense"] for item in data)

    return {
        "message": "Lấy báo cáo lãi lỗ thành công",
        "data": data,
        "summary": {
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "profit": total_revenue - total_expense
        }
    }