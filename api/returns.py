import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import User, Order, OrderItem, Payment, ReturnRequest
from schemas.return_schema import ReturnRequestCreate, ReturnStatusUpdate

returns_route = APIRouter(prefix="/api/returns", tags=["returns"])

def is_admin(user: User):
    return getattr(user, "role", "user") == "admin"


def return_to_dict(return_request: ReturnRequest):
    order_item = return_request.order_item

    return {
        "id": return_request.id,
        "user_id": return_request.user_id,
        "order_id": return_request.order_id,
        "order_item_id": return_request.order_item_id,
        "reason": return_request.reason,
        "images": return_request.images,
        "status": return_request.status,
        "admin_note": return_request.admin_note,
        "created_at": return_request.created_at,
        "updated_at": return_request.updated_at,
        "order_item": {
            "id": order_item.id,
            "product_id": order_item.product_id,
            "variant_id": order_item.variant_id,
            "quantity": order_item.quantity,
            "price": order_item.price,
            "total_price": order_item.total_price,
            "product_title": order_item.product_title,
            "product_img": order_item.product_img,
            "variant_sku": order_item.variant_sku,
            "variant_size": order_item.variant_size,
            "variant_color": order_item.variant_color,
        } if order_item else None
    }


# =========================
# CREATE RETURN REQUEST
# POST /api/returns/
# User tạo yêu cầu đổi trả
# =========================

@returns_route.post("/")
def create_return_request(
        return_data: ReturnRequestCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    order = (
        db.query(Order)
        .filter(
            Order.id == return_data.order_id,
            Order.user_id == current_user.id
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng"
        )

    if order.status not in ["completed"]:
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể yêu cầu đổi trả khi đơn hàng đã hoàn thành"
        )

    order_item = None

    if return_data.order_item_id:
        order_item = (
            db.query(OrderItem)
            .filter(
                OrderItem.id == return_data.order_item_id,
                OrderItem.order_id == order.id
            )
            .first()
        )

        if not order_item:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy sản phẩm trong đơn hàng"
            )

    existed_return = (
        db.query(ReturnRequest)
        .filter(
            ReturnRequest.user_id == current_user.id,
            ReturnRequest.order_id == return_data.order_id,
            ReturnRequest.order_item_id == return_data.order_item_id
        )
        .first()
    )

    if existed_return:
        raise HTTPException(
            status_code=400,
            detail="Bạn đã tạo yêu cầu đổi trả cho mục này rồi"
        )

    new_return = ReturnRequest(
        user_id=current_user.id,
        order_id=return_data.order_id,
        order_item_id=return_data.order_item_id,
        reason=return_data.reason,
        images=return_data.images or [],
        status="pending"
    )

    db.add(new_return)
    db.commit()
    db.refresh(new_return)

    return {
        "message": "Tạo yêu cầu đổi trả thành công",
        "data": return_to_dict(new_return)
    }


# =========================
# GET MY RETURNS
# GET /api/returns/my
# =========================

@returns_route.get("/my")
def get_my_returns(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    returns = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.user_id == current_user.id)
        .order_by(ReturnRequest.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách yêu cầu đổi trả của tôi thành công",
        "data": [return_to_dict(item) for item in returns]
    }


# =========================
# GET ALL RETURNS
# GET /api/returns/
# Admin xem tất cả yêu cầu đổi trả
# =========================

@returns_route.get("/")
def get_all_returns(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        status: str = Query(None)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    query = db.query(ReturnRequest)

    if status:
        query = query.filter(ReturnRequest.status == status)

    total = query.count()

    returns = (
        query
        .order_by(ReturnRequest.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách yêu cầu đổi trả thành công",
        "data": [return_to_dict(item) for item in returns],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET RETURN BY ID
# GET /api/returns/{return_id}
# Admin hoặc owner
# =========================

@returns_route.get("/{return_id}")
def get_return_by_id(
        return_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    return_request = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .first()
    )

    if not return_request:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy yêu cầu đổi trả"
        )

    if return_request.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem yêu cầu này"
        )

    return {
        "message": "Lấy chi tiết yêu cầu đổi trả thành công",
        "data": return_to_dict(return_request)
    }


# =========================
# UPDATE RETURN STATUS
# PATCH /api/returns/{return_id}/status
# Admin duyệt / từ chối / hoàn tiền
# =========================

@returns_route.patch("/{return_id}/status")
def update_return_status(
        return_id: int,
        status_data: ReturnStatusUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    allowed_status = [
        "pending",
        "approved",
        "rejected",
        "refunded",
        "cancelled"
    ]

    if status_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái đổi trả không hợp lệ"
        )

    return_request = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .first()
    )

    if not return_request:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy yêu cầu đổi trả"
        )

    return_request.status = status_data.status

    if status_data.admin_note is not None:
        return_request.admin_note = status_data.admin_note

    # Nếu admin xác nhận đã hoàn tiền thì cập nhật payment thành refunded
    if status_data.status == "refunded":
        payment = (
            db.query(Payment)
            .filter(Payment.order_id == return_request.order_id)
            .first()
        )

        if payment:
            payment.payment_status = "refunded"

    db.commit()
    db.refresh(return_request)

    return {
        "message": "Cập nhật trạng thái đổi trả thành công",
        "data": return_to_dict(return_request)
    }


# =========================
# USER CANCEL RETURN
# PATCH /api/returns/{return_id}/cancel
# User hủy yêu cầu nếu còn pending
# =========================

@returns_route.patch("/{return_id}/cancel")
def cancel_return_request(
        return_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    return_request = (
        db.query(ReturnRequest)
        .filter(
            ReturnRequest.id == return_id,
            ReturnRequest.user_id == current_user.id
        )
        .first()
    )

    if not return_request:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy yêu cầu đổi trả"
        )

    if return_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể hủy yêu cầu đang chờ xử lý"
        )

    return_request.status = "cancelled"

    db.commit()
    db.refresh(return_request)

    return {
        "message": "Hủy yêu cầu đổi trả thành công",
        "data": return_to_dict(return_request)
    }