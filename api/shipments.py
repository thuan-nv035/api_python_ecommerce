from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.notifications import create_notification
from database import get_db
from models.models import Shipment, Order, User
from schemas.shipment_schema import ShipmentCreate, ShipmentUpdate

shipments_route = APIRouter(prefix="/api/shipments", tags=["shipments"])

def is_admin(user: User):
    return getattr(user, "role", "user") == "admin"


def shipment_to_dict(shipment: Shipment):
    return {
        "id": shipment.id,
        "order_id": shipment.order_id,
        "user_id": shipment.user_id,
        "carrier": shipment.carrier,
        "tracking_code": shipment.tracking_code,
        "shipping_fee": shipment.shipping_fee,
        "status": shipment.status,
        "shipped_at": shipment.shipped_at,
        "delivered_at": shipment.delivered_at,
        "note": shipment.note,
        "created_at": shipment.created_at,
        "updated_at": shipment.updated_at,
    }


# =========================
# CREATE SHIPMENT
# POST /api/shipments/
# Admin tạo đơn giao hàng
# =========================

@shipments_route.post("/")
def create_shipment(
        shipment_data: ShipmentCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới được tạo đơn giao hàng"
        )

    order = db.query(Order).filter(Order.id == shipment_data.order_id).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng"
        )

    existed_shipment = (
        db.query(Shipment)
        .filter(Shipment.order_id == shipment_data.order_id)
        .first()
    )

    if existed_shipment:
        raise HTTPException(
            status_code=400,
            detail="Đơn hàng này đã có thông tin giao hàng"
        )

    new_shipment = Shipment(
        order_id=order.id,
        user_id=order.user_id,
        carrier=shipment_data.carrier,
        tracking_code=shipment_data.tracking_code,
        shipping_fee=shipment_data.shipping_fee or 0,
        status="pending",
        note=shipment_data.note
    )

    db.add(new_shipment)

    # Khi tạo vận đơn, cập nhật order sang confirmed nếu đang pending
    if order.status == "pending":
        order.status = "confirmed"

    db.commit()
    db.refresh(new_shipment)

    return {
        "message": "Tạo thông tin giao hàng thành công",
        "data": shipment_to_dict(new_shipment)
    }


# =========================
# GET MY SHIPMENTS
# GET /api/shipments/my
# User xem đơn giao hàng của mình
# =========================

@shipments_route.get("/my")
def get_my_shipments(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    shipments = (
        db.query(Shipment)
        .filter(Shipment.user_id == current_user.id)
        .order_by(Shipment.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách giao hàng của tôi thành công",
        "data": [shipment_to_dict(item) for item in shipments]
    }


# =========================
# GET ALL SHIPMENTS
# GET /api/shipments/
# Admin xem tất cả đơn giao hàng
# =========================

@shipments_route.get("/")
def get_all_shipments(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        status: str = Query(None)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới được xem tất cả đơn giao hàng"
        )

    query = db.query(Shipment)

    if status:
        query = query.filter(Shipment.status == status)

    shipments = (
        query
        .order_by(Shipment.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách giao hàng thành công",
        "data": [shipment_to_dict(item) for item in shipments]
    }


# =========================
# GET SHIPMENT BY ORDER
# GET /api/shipments/order/{order_id}
# =========================

@shipments_route.get("/order/{order_id}")
def get_shipment_by_order(
        order_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    shipment = (
        db.query(Shipment)
        .filter(Shipment.order_id == order_id)
        .first()
    )

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thông tin giao hàng"
        )

    if shipment.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem thông tin giao hàng này"
        )

    return {
        "message": "Lấy giao hàng theo đơn hàng thành công",
        "data": shipment_to_dict(shipment)
    }


# =========================
# GET SHIPMENT BY ID
# GET /api/shipments/{shipment_id}
# =========================

@shipments_route.get("/{shipment_id}")
def get_shipment_by_id(
        shipment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thông tin giao hàng"
        )

    if shipment.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem thông tin giao hàng này"
        )

    return {
        "message": "Lấy chi tiết giao hàng thành công",
        "data": shipment_to_dict(shipment)
    }


# =========================
# UPDATE SHIPMENT
# PUT /api/shipments/{shipment_id}
# PATCH /api/shipments/{shipment_id}
# Admin cập nhật giao hàng
# =========================

@shipments_route.put("/{shipment_id}")
@shipments_route.patch("/{shipment_id}")
def update_shipment(
        shipment_id: int,
        shipment_data: ShipmentUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới được cập nhật giao hàng"
        )

    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thông tin giao hàng"
        )
    if shipment.status == "shipping":
        create_notification(
            db=db,
            user_id=shipment.user_id,
            title="Đơn hàng đang được giao",
            message=f"Đơn hàng #{shipment.order_id} của bạn đang được vận chuyển.",
            type="shipping",
            related_id=shipment.order_id
        )

    if shipment.status == "delivered":
        create_notification(
            db=db,
            user_id=shipment.user_id,
            title="Đơn hàng đã giao thành công",
            message=f"Đơn hàng #{shipment.order_id} đã được giao thành công.",
            type="shipping",
            related_id=shipment.order_id
        )

    if shipment.status == "cancelled":
        create_notification(
            db=db,
            user_id=shipment.user_id,
            title="Đơn giao hàng đã bị hủy",
            message=f"Đơn giao hàng của đơn hàng #{shipment.order_id} đã bị hủy.",
            type="shipping",
            related_id=shipment.order_id
        )
    allowed_status = [
        "pending",
        "preparing",
        "shipping",
        "delivered",
        "failed",
        "cancelled"
    ]

    update_data = shipment_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "status" in update_data:
        if update_data["status"] not in allowed_status:
            raise HTTPException(
                status_code=400,
                detail="Trạng thái giao hàng không hợp lệ"
            )

    for key, value in update_data.items():
        setattr(shipment, key, value)

    order = db.query(Order).filter(Order.id == shipment.order_id).first()

    if shipment.status == "shipping":
        shipment.shipped_at = datetime.utcnow()
        if order:
            order.status = "shipping"

    if shipment.status == "delivered":
        shipment.delivered_at = datetime.utcnow()
        if order:
            order.status = "completed"

    if shipment.status == "cancelled":
        if order and order.status not in ["completed"]:
            order.status = "cancelled"

    db.commit()
    db.refresh(shipment)

    return {
        "message": "Cập nhật giao hàng thành công",
        "data": shipment_to_dict(shipment)
    }


# =========================
# DELETE SHIPMENT
# DELETE /api/shipments/{shipment_id}
# Admin xóa giao hàng
# =========================

@shipments_route.delete("/{shipment_id}")
def delete_shipment(
        shipment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới được xóa giao hàng"
        )

    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thông tin giao hàng"
        )

    db.delete(shipment)
    db.commit()

    return {
        "message": "Xóa thông tin giao hàng thành công",
        "deleted_shipment_id": shipment_id
    }