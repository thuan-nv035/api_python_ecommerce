import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, ShippingRate
from schemas.shipping_fee_schema import (
    ShippingFeeCalculate,
    ShippingRateCreate,
    ShippingRateUpdate
)


shipping_fee_route = APIRouter(
    prefix="/api/shipping-fee",
    tags=["shipping-fee"]
)


def get_current_user(request: Request, db: Session):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    user = db.query(User).filter(User.id == current_user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy user"
        )

    return user


def check_admin(user: User):
    if getattr(user, "role", "user") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )


def normalize_text(value):
    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    return value


def shipping_rate_to_dict(rate: ShippingRate):
    return {
        "id": rate.id,
        "province": rate.province,
        "district": rate.district,
        "ward": rate.ward,
        "fee": rate.fee,
        "free_shipping_from": rate.free_shipping_from,
        "estimated_delivery": rate.estimated_delivery,
        "is_active": rate.is_active,
        "created_at": rate.created_at,
        "updated_at": rate.updated_at,
    }


def find_best_shipping_rate(
        db: Session,
        province: str,
        district: str = None,
        ward: str = None
):
    province = normalize_text(province)
    district = normalize_text(district)
    ward = normalize_text(ward)

    if not province:
        raise HTTPException(
            status_code=400,
            detail="province là bắt buộc"
        )

    # Ưu tiên khớp chính xác nhất:
    # 1. province + district + ward
    if province and district and ward:
        rate = (
            db.query(ShippingRate)
            .filter(
                ShippingRate.province.ilike(province),
                ShippingRate.district.ilike(district),
                ShippingRate.ward.ilike(ward),
                ShippingRate.is_active == True
            )
            .first()
        )

        if rate:
            return rate

    # 2. province + district
    if province and district:
        rate = (
            db.query(ShippingRate)
            .filter(
                ShippingRate.province.ilike(province),
                ShippingRate.district.ilike(district),
                ShippingRate.ward == None,
                ShippingRate.is_active == True
            )
            .first()
        )

        if rate:
            return rate

    # 3. province
    rate = (
        db.query(ShippingRate)
        .filter(
            ShippingRate.province.ilike(province),
            ShippingRate.district == None,
            ShippingRate.ward == None,
            ShippingRate.is_active == True
        )
        .first()
    )

    if rate:
        return rate

    return None


# =========================
# CALCULATE SHIPPING FEE
# POST /api/shipping-fee/calculate
# Public
# =========================

@shipping_fee_route.post("/calculate")
def calculate_shipping_fee(
        data: ShippingFeeCalculate,
        db: Session = Depends(get_db)
):
    rate = find_best_shipping_rate(
        db=db,
        province=data.province,
        district=data.district,
        ward=data.ward
    )

    # Nếu chưa có cấu hình phí ship thì dùng mặc định
    default_fee = 30000
    default_estimated_delivery = "2-4 ngày"
    default_free_shipping_from = 500000

    if rate:
        shipping_fee = rate.fee
        free_shipping_from = rate.free_shipping_from
        estimated_delivery = rate.estimated_delivery
        matched_rate = shipping_rate_to_dict(rate)
    else:
        shipping_fee = default_fee
        free_shipping_from = default_free_shipping_from
        estimated_delivery = default_estimated_delivery
        matched_rate = None

    free_shipping = False

    if free_shipping_from is not None and data.cart_total >= free_shipping_from:
        shipping_fee = 0
        free_shipping = True

    final_total = data.cart_total + shipping_fee

    return {
        "message": "Tính phí vận chuyển thành công",
        "data": {
            "province": data.province,
            "district": data.district,
            "ward": data.ward,
            "cart_total": data.cart_total,
            "shipping_fee": shipping_fee,
            "free_shipping": free_shipping,
            "free_shipping_from": free_shipping_from,
            "estimated_delivery": estimated_delivery,
            "final_total": final_total,
            "matched_rate": matched_rate
        }
    }


# =========================
# GET ALL SHIPPING RATES
# GET /api/shipping-fee/rates
# Admin
# =========================

@shipping_fee_route.get("/rates")
def get_shipping_rates(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        province: str = Query(None),
        is_active: bool = Query(None)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    query = db.query(ShippingRate)

    if province:
        query = query.filter(ShippingRate.province.ilike(f"%{province}%"))

    if is_active is not None:
        query = query.filter(ShippingRate.is_active == is_active)

    total = query.count()

    rates = (
        query
        .order_by(ShippingRate.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách phí vận chuyển thành công",
        "data": [shipping_rate_to_dict(rate) for rate in rates],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET SHIPPING RATE BY ID
# GET /api/shipping-fee/rates/{rate_id}
# Admin
# =========================

@shipping_fee_route.get("/rates/{rate_id}")
def get_shipping_rate_by_id(
        rate_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    rate = db.query(ShippingRate).filter(ShippingRate.id == rate_id).first()

    if not rate:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cấu hình phí vận chuyển"
        )

    return {
        "message": "Lấy chi tiết phí vận chuyển thành công",
        "data": shipping_rate_to_dict(rate)
    }


# =========================
# CREATE SHIPPING RATE
# POST /api/shipping-fee/rates
# Admin
# =========================

@shipping_fee_route.post("/rates")
def create_shipping_rate(
        rate_data: ShippingRateCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    province = normalize_text(rate_data.province)
    district = normalize_text(rate_data.district)
    ward = normalize_text(rate_data.ward)

    if not province:
        raise HTTPException(
            status_code=400,
            detail="province là bắt buộc"
        )

    existed_rate = (
        db.query(ShippingRate)
        .filter(
            ShippingRate.province.ilike(province),
            ShippingRate.district == district,
            ShippingRate.ward == ward
        )
        .first()
    )

    if existed_rate:
        raise HTTPException(
            status_code=400,
            detail="Khu vực này đã có cấu hình phí vận chuyển"
        )

    new_rate = ShippingRate(
        province=province,
        district=district,
        ward=ward,
        fee=rate_data.fee,
        free_shipping_from=rate_data.free_shipping_from,
        estimated_delivery=rate_data.estimated_delivery,
        is_active=rate_data.is_active
    )

    db.add(new_rate)
    db.commit()
    db.refresh(new_rate)

    return {
        "message": "Tạo phí vận chuyển thành công",
        "data": shipping_rate_to_dict(new_rate)
    }


# =========================
# UPDATE SHIPPING RATE
# PUT/PATCH /api/shipping-fee/rates/{rate_id}
# Admin
# =========================

@shipping_fee_route.put("/rates/{rate_id}")
@shipping_fee_route.patch("/rates/{rate_id}")
def update_shipping_rate(
        rate_id: int,
        rate_data: ShippingRateUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    rate = db.query(ShippingRate).filter(ShippingRate.id == rate_id).first()

    if not rate:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cấu hình phí vận chuyển"
        )

    update_data = rate_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "province" in update_data:
        update_data["province"] = normalize_text(update_data["province"])

    if "district" in update_data:
        update_data["district"] = normalize_text(update_data["district"])

    if "ward" in update_data:
        update_data["ward"] = normalize_text(update_data["ward"])

    new_province = update_data.get("province", rate.province)
    new_district = update_data.get("district", rate.district)
    new_ward = update_data.get("ward", rate.ward)

    existed_rate = (
        db.query(ShippingRate)
        .filter(
            ShippingRate.province.ilike(new_province),
            ShippingRate.district == new_district,
            ShippingRate.ward == new_ward,
            ShippingRate.id != rate_id
        )
        .first()
    )

    if existed_rate:
        raise HTTPException(
            status_code=400,
            detail="Khu vực này đã có cấu hình phí vận chuyển"
        )

    for key, value in update_data.items():
        setattr(rate, key, value)

    db.commit()
    db.refresh(rate)

    return {
        "message": "Cập nhật phí vận chuyển thành công",
        "data": shipping_rate_to_dict(rate)
    }


# =========================
# DELETE SHIPPING RATE
# DELETE /api/shipping-fee/rates/{rate_id}
# Admin
# =========================

@shipping_fee_route.delete("/rates/{rate_id}")
def delete_shipping_rate(
        rate_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    rate = db.query(ShippingRate).filter(ShippingRate.id == rate_id).first()

    if not rate:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cấu hình phí vận chuyển"
        )

    db.delete(rate)
    db.commit()

    return {
        "message": "Xóa phí vận chuyển thành công",
        "deleted_rate_id": rate_id
    }