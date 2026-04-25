from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import Address, User
from schemas.address_schema import AddressCreate, AddressUpdate


addresses_route = APIRouter(prefix="/api/addresses", tags=["addresses"])


def address_to_dict(address: Address):
    return {
        "id": address.id,
        "user_id": address.user_id,
        "full_name": address.full_name,
        "phone": address.phone,
        "province": address.province,
        "district": address.district,
        "ward": address.ward,
        "address_detail": address.address_detail,
        "is_default": address.is_default,
        "created_at": address.created_at,
        "updated_at": address.updated_at,
    }

def clear_default_address(db: Session, user_id: int):
    db.query(Address).filter(Address.user_id == user_id).update({
        Address.is_default: False
    })


# =========================
# CREATE ADDRESS
# POST /api/addresses/
# =========================

@addresses_route.post("/")
def create_address(
        address_data: AddressCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    total_address = (
        db.query(Address)
        .filter(Address.user_id == current_user_id)
        .count()
    )

    # Nếu là địa chỉ đầu tiên thì tự động set default
    is_default = address_data.is_default or total_address == 0

    if is_default:
        clear_default_address(db, current_user_id)

    new_address = Address(
        user_id=current_user_id,
        full_name=address_data.full_name,
        phone=address_data.phone,
        province=address_data.province,
        district=address_data.district,
        ward=address_data.ward,
        address_detail=address_data.address_detail,
        is_default=is_default
    )

    db.add(new_address)
    db.commit()
    db.refresh(new_address)

    return {
        "message": "Tạo địa chỉ thành công",
        "data": address_to_dict(new_address)
    }


# =========================
# GET MY ADDRESSES
# GET /api/addresses/
# =========================

@addresses_route.get("/")
def get_my_addresses(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    addresses = (
        db.query(Address)
        .filter(Address.user_id == current_user_id)
        .order_by(Address.is_default.desc(), Address.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách địa chỉ thành công",
        "data": [address_to_dict(address) for address in addresses]
    }


# =========================
# GET ADDRESS BY ID
# GET /api/addresses/{address_id}
# =========================

@addresses_route.get("/{address_id}")
def get_address_by_id(
        address_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == current_user_id
        )
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy địa chỉ"
        )

    return {
        "message": "Lấy chi tiết địa chỉ thành công",
        "data": address_to_dict(address)
    }


# =========================
# UPDATE ADDRESS
# PUT /api/addresses/{address_id}
# =========================

@addresses_route.put("/{address_id}")
def update_address(
        address_id: int,
        address_data: AddressUpdate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == current_user_id
        )
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy địa chỉ"
        )

    update_data = address_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if update_data.get("is_default") is True:
        clear_default_address(db, current_user_id)

    for key, value in update_data.items():
        setattr(address, key, value)

    db.commit()
    db.refresh(address)

    return {
        "message": "Cập nhật địa chỉ thành công",
        "data": address_to_dict(address)
    }


# =========================
# SET DEFAULT ADDRESS
# PATCH /api/addresses/{address_id}/default
# =========================

@addresses_route.patch("/{address_id}/default")
def set_default_address(
        address_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == current_user_id
        )
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy địa chỉ"
        )

    clear_default_address(db, current_user_id)

    address.is_default = True

    db.commit()
    db.refresh(address)

    return {
        "message": "Đặt địa chỉ mặc định thành công",
        "data": address_to_dict(address)
    }


# =========================
# DELETE ADDRESS
# DELETE /api/addresses/{address_id}
# =========================

@addresses_route.delete("/{address_id}")
def delete_address(
        address_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == current_user_id
        )
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy địa chỉ"
        )

    was_default = address.is_default

    db.delete(address)
    db.commit()

    # Nếu xóa địa chỉ mặc định thì lấy địa chỉ mới nhất làm mặc định
    if was_default:
        latest_address = (
            db.query(Address)
            .filter(Address.user_id == current_user_id)
            .order_by(Address.id.desc())
            .first()
        )

        if latest_address:
            latest_address.is_default = True
            db.commit()

    return {
        "message": "Xóa địa chỉ thành công",
        "deleted_address_id": address_id
    }