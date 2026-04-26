from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.auth import get_admin_user
from database import get_db
from models.models import User, Products, Order, OrderItem, CartItem, Review, Payment
from schemas.admin_schema import UpdateOrderStatusSchema, UpdateUserRoleSchema


admin_route = APIRouter(prefix="/api/admin", tags=["admin"])


def order_to_dict(order: Order):
    return {
        "id": order.id,
        "user_id": order.user_id,
        "full_name": order.full_name,
        "phone": order.phone,
        "address": order.address,
        "note": order.note,
        "total_price": order.total_price,
        "payment_method": order.payment_method,
        "status": order.status,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "total_price": item.total_price,
                "product_title": item.product_title,
                "product_img": item.product_img,
            }
            for item in order.items
        ]
    }


def user_to_dict(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar,
        "role": user.role
    }


# =========================
# ADMIN DASHBOARD
# GET /api/admin/dashboard
# =========================

@admin_route.get("/dashboard")
def get_admin_dashboard(
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    total_users = db.query(User).count()
    total_products = db.query(Products).count()
    total_orders = db.query(Order).count()
    total_reviews = db.query(Review).count()

    pending_orders = db.query(Order).filter(Order.status == "pending").count()
    completed_orders = db.query(Order).filter(Order.status == "completed").count()
    cancelled_orders = db.query(Order).filter(Order.status == "cancelled").count()

    total_revenue = (
        db.query(func.sum(Order.total_price))
        .filter(Order.status.in_(["confirmed", "shipping", "completed"]))
        .scalar()
    ) or 0

    paid_revenue = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.payment_status == "paid")
        .scalar()
    ) or 0

    recent_orders = (
        db.query(Order)
        .order_by(Order.id.desc())
        .limit(5)
        .all()
    )

    return {
        "message": "Lấy dashboard admin thành công",
        "data": {
            "total_users": total_users,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_reviews": total_reviews,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": total_revenue,
            "paid_revenue": paid_revenue,
            "recent_orders": [order_to_dict(order) for order in recent_orders]
        }
    }


# =========================
# GET ALL ORDERS
# GET /api/admin/orders
# =========================

@admin_route.get("/orders")
def get_all_orders_admin(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        status: str = Query(None)
):
    get_admin_user(request)

    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)

    total = query.count()

    orders = (
        query
        .order_by(Order.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách đơn hàng admin thành công",
        "data": [order_to_dict(order) for order in orders],
        "pagination": {
            "total_records": total,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# UPDATE ORDER STATUS
# PATCH /api/admin/orders/{order_id}/status
# =========================

@admin_route.patch("/orders/{order_id}/status")
def update_order_status_admin(
        order_id: int,
        status_data: UpdateOrderStatusSchema,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    allowed_status = [
        "pending",
        "confirmed",
        "shipping",
        "completed",
        "cancelled"
    ]

    if status_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái đơn hàng không hợp lệ"
        )

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng"
        )

    order.status = status_data.status

    db.commit()
    db.refresh(order)

    return {
        "message": "Cập nhật trạng thái đơn hàng thành công",
        "data": order_to_dict(order)
    }


# =========================
# GET ALL USERS
# GET /api/admin/users
# =========================

@admin_route.get("/users")
def get_all_users_admin(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0)
):
    get_admin_user(request)

    query = db.query(User)

    total = query.count()

    users = (
        query
        .order_by(User.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách user thành công",
        "data": [user_to_dict(user) for user in users],
        "pagination": {
            "total_records": total,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# UPDATE USER ROLE
# PATCH /api/admin/users/{user_id}/role
# =========================

@admin_route.patch("/users/{user_id}/role")
def update_user_role_admin(
        user_id: int,
        role_data: UpdateUserRoleSchema,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    allowed_roles = ["user", "admin"]

    if role_data.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Role không hợp lệ"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy user"
        )

    user.role = role_data.role

    db.commit()
    db.refresh(user)

    return {
        "message": "Cập nhật quyền user thành công",
        "data": user_to_dict(user)
    }