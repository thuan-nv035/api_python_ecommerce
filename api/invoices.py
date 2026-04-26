import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import User, Order, Payment, Shipment, Invoice
from schemas.invoice_schema import InvoiceCreate, InvoiceStatusUpdate


invoices_route = APIRouter(prefix="/api/invoices", tags=["invoices"])


def is_admin(user: User):
    return getattr(user, "role", "user") == "admin"


def generate_invoice_number(order_id: int):
    now = datetime.utcnow()
    return f"INV-{now.strftime('%Y%m%d%H%M%S')}-{order_id}"


def invoice_to_dict(invoice: Invoice):
    order = invoice.order

    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "user_id": invoice.user_id,
        "order_id": invoice.order_id,
        "subtotal": invoice.subtotal,
        "discount_amount": invoice.discount_amount,
        "shipping_fee": invoice.shipping_fee,
        "total_amount": invoice.total_amount,
        "payment_method": invoice.payment_method,
        "payment_status": invoice.payment_status,
        "status": invoice.status,
        "note": invoice.note,
        "issued_at": invoice.issued_at,
        "paid_at": invoice.paid_at,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "order": {
            "id": order.id,
            "full_name": order.full_name,
            "phone": order.phone,
            "address": order.address,
            "status": order.status,
            "total_price": order.total_price,
            "payment_method": order.payment_method,
            "created_at": order.created_at,
        } if order else None
    }


# =========================
# CREATE INVOICE
# POST /api/invoices/
# Admin tạo hóa đơn từ order
# =========================

@invoices_route.post("/")
def create_invoice(
        invoice_data: InvoiceCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user())
):
    current_user = current_user

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    order = db.query(Order).filter(Order.id == invoice_data.order_id).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng"
        )

    existed_invoice = (
        db.query(Invoice)
        .filter(Invoice.order_id == order.id)
        .first()
    )

    if existed_invoice:
        raise HTTPException(
            status_code=400,
            detail="Đơn hàng này đã có hóa đơn"
        )

    payment = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .first()
    )

    shipment = (
        db.query(Shipment)
        .filter(Shipment.order_id == order.id)
        .first()
    )

    subtotal = getattr(order, "subtotal", None) or order.total_price or 0
    discount_amount = getattr(order, "discount_amount", 0) or 0
    shipping_fee = shipment.shipping_fee if shipment else 0

    total_amount = order.total_price or 0
    payment_method = payment.payment_method if payment else order.payment_method
    payment_status = payment.payment_status if payment else "pending"

    new_invoice = Invoice(
        invoice_number=generate_invoice_number(order.id),
        user_id=order.user_id,
        order_id=order.id,
        subtotal=subtotal,
        discount_amount=discount_amount,
        shipping_fee=shipping_fee,
        total_amount=total_amount,
        payment_method=payment_method,
        payment_status=payment_status,
        status="paid" if payment_status == "paid" else "issued",
        paid_at=datetime.utcnow() if payment_status == "paid" else None,
        note=invoice_data.note
    )

    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    return {
        "message": "Tạo hóa đơn thành công",
        "data": invoice_to_dict(new_invoice)
    }


# =========================
# GET MY INVOICES
# GET /api/invoices/my
# User xem hóa đơn của mình
# =========================

@invoices_route.get("/my")
def get_my_invoices(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    invoices = (
        db.query(Invoice)
        .filter(Invoice.user_id == current_user.id)
        .order_by(Invoice.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách hóa đơn của tôi thành công",
        "data": [invoice_to_dict(invoice) for invoice in invoices]
    }


# =========================
# GET INVOICE BY ORDER
# GET /api/invoices/order/{order_id}
# User hoặc admin xem hóa đơn theo order
# =========================

@invoices_route.get("/order/{order_id}")
def get_invoice_by_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    invoice = (
        db.query(Invoice)
        .filter(Invoice.order_id == order_id)
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy hóa đơn của đơn hàng này"
        )

    if invoice.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem hóa đơn này"
        )

    return {
        "message": "Lấy hóa đơn theo đơn hàng thành công",
        "data": invoice_to_dict(invoice)
    }


# =========================
# GET ALL INVOICES
# GET /api/invoices/
# Admin xem tất cả hóa đơn
# =========================

@invoices_route.get("/")
def get_all_invoices(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        status: str = Query(None),
        payment_status: str = Query(None),
        current_user: User = Depends(get_current_user)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    query = db.query(Invoice)

    if status:
        query = query.filter(Invoice.status == status)

    if payment_status:
        query = query.filter(Invoice.payment_status == payment_status)

    total = query.count()

    invoices = (
        query
        .order_by(Invoice.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách hóa đơn thành công",
        "data": [invoice_to_dict(invoice) for invoice in invoices],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET INVOICE BY ID
# GET /api/invoices/{invoice_id}
# User hoặc admin
# =========================

@invoices_route.get("/{invoice_id}")
def get_invoice_by_id(
        invoice_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy hóa đơn"
        )

    if invoice.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem hóa đơn này"
        )

    return {
        "message": "Lấy chi tiết hóa đơn thành công",
        "data": invoice_to_dict(invoice)
    }


# =========================
# UPDATE INVOICE STATUS
# PATCH /api/invoices/{invoice_id}/status
# Admin cập nhật trạng thái hóa đơn
# =========================

@invoices_route.patch("/{invoice_id}/status")
def update_invoice_status(
        invoice_id: int,
        status_data: InvoiceStatusUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    allowed_status = [
        "issued",
        "paid",
        "cancelled",
        "refunded"
    ]

    allowed_payment_status = [
        "pending",
        "paid",
        "failed",
        "refunded"
    ]

    if status_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái hóa đơn không hợp lệ"
        )

    if status_data.payment_status and status_data.payment_status not in allowed_payment_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái thanh toán không hợp lệ"
        )

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy hóa đơn"
        )

    invoice.status = status_data.status

    if status_data.payment_status:
        invoice.payment_status = status_data.payment_status

    if status_data.status == "paid" or status_data.payment_status == "paid":
        invoice.paid_at = datetime.utcnow()

    if status_data.note is not None:
        invoice.note = status_data.note

    payment = (
        db.query(Payment)
        .filter(Payment.order_id == invoice.order_id)
        .first()
    )

    if payment and status_data.payment_status:
        payment.payment_status = status_data.payment_status

    db.commit()
    db.refresh(invoice)

    return {
        "message": "Cập nhật trạng thái hóa đơn thành công",
        "data": invoice_to_dict(invoice)
    }


# =========================
# DELETE INVOICE
# DELETE /api/invoices/{invoice_id}
# Admin
# =========================

@invoices_route.delete("/{invoice_id}")
def delete_invoice(
        invoice_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy hóa đơn"
        )

    db.delete(invoice)
    db.commit()

    return {
        "message": "Xóa hóa đơn thành công",
        "deleted_invoice_id": invoice_id
    }