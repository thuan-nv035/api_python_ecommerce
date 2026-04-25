from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import Payment, Order, User
from schemas.payment_schema import PaymentCreate, PaymentStatusUpdate


payments_route = APIRouter(prefix="/api/payments", tags=["payments"])


def payment_to_dict(payment: Payment):
    return {
        "id": payment.id,
        "user_id": payment.user_id,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "payment_method": payment.payment_method,
        "payment_status": payment.payment_status,
        "transaction_id": payment.transaction_id,
        "paid_at": payment.paid_at,
        "created_at": payment.created_at,
        "updated_at": payment.updated_at,
    }


# =========================
# CREATE PAYMENT
# POST /api/payments/
# =========================

@payments_route.post("/")
def create_payment(
        payment_data: PaymentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    order = (
        db.query(Order)
        .filter(
            Order.id == payment_data.order_id,
            Order.user_id == current_user_id
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng"
        )

    existed_payment = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .first()
    )

    if existed_payment:
        raise HTTPException(
            status_code=400,
            detail="Đơn hàng này đã có thông tin thanh toán"
        )

    payment_method = payment_data.payment_method or "cod"

    # Nếu COD thì trạng thái thanh toán vẫn là pending
    # Nếu muốn test đã thanh toán thì dùng API update status bên dưới
    new_payment = Payment(
        user_id=current_user_id,
        order_id=order.id,
        amount=order.total_price,
        payment_method=payment_method,
        payment_status="pending"
    )

    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    return {
        "message": "Tạo thanh toán thành công",
        "data": payment_to_dict(new_payment)
    }


# =========================
# GET MY PAYMENTS
# GET /api/payments/
# =========================

@payments_route.get("/")
def get_my_payments(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    payments = (
        db.query(Payment)
        .filter(Payment.user_id == current_user_id)
        .order_by(Payment.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách thanh toán thành công",
        "data": [payment_to_dict(payment) for payment in payments]
    }


# =========================
# GET PAYMENT BY ORDER
# GET /api/payments/order/{order_id}
# =========================

@payments_route.get("/order/{order_id}")
def get_payment_by_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user = Depends(get_current_user)
):
    current_user_id = current_user.id

    payment = (
        db.query(Payment)
        .filter(
            Payment.order_id == order_id,
            Payment.user_id == current_user_id
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thanh toán của đơn hàng này"
        )

    return {
        "message": "Lấy thanh toán theo đơn hàng thành công",
        "data": payment_to_dict(payment)
    }


# =========================
# GET PAYMENT BY ID
# GET /api/payments/{payment_id}
# =========================

@payments_route.get("/{payment_id}")
def get_payment_by_id(
        payment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == current_user_id
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thanh toán"
        )

    return {
        "message": "Lấy chi tiết thanh toán thành công",
        "data": payment_to_dict(payment)
    }


# =========================
# UPDATE PAYMENT STATUS
# PATCH /api/payments/{payment_id}/status
# =========================

@payments_route.patch("/{payment_id}/status")
def update_payment_status(
        payment_id: int,
        status_data: PaymentStatusUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id
    allowed_status = [
        "pending",
        "paid",
        "failed",
        "refunded"
    ]

    if status_data.payment_status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái thanh toán không hợp lệ"
        )

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == current_user_id
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thanh toán"
        )

    payment.payment_status = status_data.payment_status

    if status_data.transaction_id is not None:
        payment.transaction_id = status_data.transaction_id

    if status_data.payment_status == "paid":
        payment.paid_at = datetime.utcnow()

        order = db.query(Order).filter(Order.id == payment.order_id).first()
        if order:
            order.status = "confirmed"

    if status_data.payment_status == "failed":
        order = db.query(Order).filter(Order.id == payment.order_id).first()
        if order and order.status == "pending":
            order.status = "pending"

    db.commit()
    db.refresh(payment)

    return {
        "message": "Cập nhật trạng thái thanh toán thành công",
        "data": payment_to_dict(payment)
    }