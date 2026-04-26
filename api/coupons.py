import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import Coupon, CouponUsage, User
from schemas.coupon_schema import CouponCreate, CouponUpdate, ApplyCouponSchema


coupons_route = APIRouter(prefix="/api/coupons", tags=["coupons"])

def coupon_to_dict(coupon: Coupon):
    return {
        "id": coupon.id,
        "code": coupon.code,
        "desc": coupon.desc,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "min_order_value": coupon.min_order_value,
        "max_discount": coupon.max_discount,
        "usage_limit": coupon.usage_limit,
        "used_count": coupon.used_count,
        "start_date": coupon.start_date,
        "end_date": coupon.end_date,
        "is_active": coupon.is_active,
        "created_at": coupon.created_at,
        "updated_at": coupon.updated_at,
    }


def validate_coupon(
        db: Session,
        user_id: int,
        code: str,
        order_total: float
):
    coupon = (
        db.query(Coupon)
        .filter(Coupon.code == code.upper())
        .first()
    )

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Mã giảm giá không tồn tại"
        )

    if not coupon.is_active:
        raise HTTPException(
            status_code=400,
            detail="Mã giảm giá đã bị tắt"
        )

    now = datetime.now(timezone.utc)

    if coupon.start_date and now < coupon.start_date:
        raise HTTPException(
            status_code=400,
            detail="Mã giảm giá chưa đến thời gian sử dụng"
        )

    if coupon.end_date and now > coupon.end_date:
        raise HTTPException(
            status_code=400,
            detail="Mã giảm giá đã hết hạn"
        )

    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        raise HTTPException(
            status_code=400,
            detail="Mã giảm giá đã hết lượt sử dụng"
        )

    if order_total < coupon.min_order_value:
        raise HTTPException(
            status_code=400,
            detail=f"Đơn hàng phải từ {coupon.min_order_value} mới dùng được mã này"
        )

    existed_usage = (
        db.query(CouponUsage)
        .filter(
            CouponUsage.coupon_id == coupon.id,
            CouponUsage.user_id == user_id
        )
        .first()
    )

    if existed_usage:
        raise HTTPException(
            status_code=400,
            detail="Bạn đã sử dụng mã giảm giá này rồi"
        )

    if coupon.discount_type == "percent":
        discount_amount = order_total * coupon.discount_value / 100

        if coupon.max_discount is not None:
            discount_amount = min(discount_amount, coupon.max_discount)

    elif coupon.discount_type == "fixed":
        discount_amount = coupon.discount_value

    else:
        raise HTTPException(
            status_code=400,
            detail="Loại mã giảm giá không hợp lệ"
        )

    discount_amount = min(discount_amount, order_total)
    final_total = order_total - discount_amount

    return {
        "coupon": coupon,
        "subtotal": order_total,
        "discount_amount": round(discount_amount, 2),
        "final_total": round(final_total, 2)
    }


# =========================
# GET ALL COUPONS
# GET /api/coupons/
# =========================

@coupons_route.get("/")
def get_all_coupons(
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        active_only: bool = Query(False)
):
    query = db.query(Coupon)

    if active_only:
        query = query.filter(Coupon.is_active == True)

    total = query.count()

    coupons = (
        query
        .order_by(Coupon.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách mã giảm giá thành công",
        "data": [coupon_to_dict(coupon) for coupon in coupons],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit),
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET COUPON BY ID
# GET /api/coupons/{coupon_id}
# =========================

@coupons_route.get("/{coupon_id}")
def get_coupon_by_id(
        coupon_id: int,
        db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy mã giảm giá"
        )

    return {
        "message": "Lấy chi tiết mã giảm giá thành công",
        "data": coupon_to_dict(coupon)
    }


# =========================
# CREATE COUPON
# POST /api/coupons/
# =========================

@coupons_route.post("/")
def create_coupon(
        coupon_data: CouponCreate,
        db: Session = Depends(get_db)
):
    code = coupon_data.code.upper()

    existed_coupon = (
        db.query(Coupon)
        .filter(Coupon.code == code)
        .first()
    )

    if existed_coupon:
        raise HTTPException(
            status_code=400,
            detail="Mã giảm giá đã tồn tại"
        )

    if coupon_data.discount_type not in ["percent", "fixed"]:
        raise HTTPException(
            status_code=400,
            detail="discount_type chỉ được là percent hoặc fixed"
        )

    new_coupon = Coupon(
        code=code,
        desc=coupon_data.desc,
        discount_type=coupon_data.discount_type,
        discount_value=coupon_data.discount_value,
        min_order_value=coupon_data.min_order_value or 0,
        max_discount=coupon_data.max_discount,
        usage_limit=coupon_data.usage_limit,
        start_date=coupon_data.start_date,
        end_date=coupon_data.end_date,
        is_active=coupon_data.is_active
    )

    db.add(new_coupon)
    db.commit()
    db.refresh(new_coupon)

    return {
        "message": "Tạo mã giảm giá thành công",
        "data": coupon_to_dict(new_coupon)
    }


# =========================
# UPDATE COUPON
# PUT /api/coupons/{coupon_id}
# PATCH /api/coupons/{coupon_id}
# =========================

@coupons_route.put("/{coupon_id}")
@coupons_route.patch("/{coupon_id}")
def update_coupon(
        coupon_id: int,
        coupon_data: CouponUpdate,
        db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy mã giảm giá"
        )

    update_data = coupon_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "discount_type" in update_data:
        if update_data["discount_type"] not in ["percent", "fixed"]:
            raise HTTPException(
                status_code=400,
                detail="discount_type chỉ được là percent hoặc fixed"
            )

    if "code" in update_data:
        new_code = update_data["code"].upper()

        existed_coupon = (
            db.query(Coupon)
            .filter(
                Coupon.code == new_code,
                Coupon.id != coupon_id
            )
            .first()
        )

        if existed_coupon:
            raise HTTPException(
                status_code=400,
                detail="Mã giảm giá đã tồn tại"
            )

        update_data["code"] = new_code

    for key, value in update_data.items():
        setattr(coupon, key, value)

    db.commit()
    db.refresh(coupon)

    return {
        "message": "Cập nhật mã giảm giá thành công",
        "data": coupon_to_dict(coupon)
    }


# =========================
# APPLY COUPON
# POST /api/coupons/apply
# =========================

@coupons_route.post("/apply")
def apply_coupon(
        apply_data: ApplyCouponSchema,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user())
):
    current_user_id = current_user.id

    result = validate_coupon(
        db=db,
        user_id=current_user_id,
        code=apply_data.code,
        order_total=apply_data.order_total
    )

    coupon = result["coupon"]

    return {
        "message": "Áp dụng mã giảm giá thành công",
        "data": {
            "coupon": coupon_to_dict(coupon),
            "subtotal": result["subtotal"],
            "discount_amount": result["discount_amount"],
            "final_total": result["final_total"]
        }
    }


# =========================
# DELETE COUPON
# DELETE /api/coupons/{coupon_id}
# =========================

@coupons_route.delete("/{coupon_id}")
def delete_coupon(
        coupon_id: int,
        db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy mã giảm giá"
        )

    db.delete(coupon)
    db.commit()

    return {
        "message": "Xóa mã giảm giá thành công",
        "deleted_coupon_id": coupon_id
    }