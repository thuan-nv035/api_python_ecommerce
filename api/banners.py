import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from database import get_db
from models.models import Banner, User
from schemas.banner_schema import BannerCreate, BannerUpdate


banners_route = APIRouter(prefix="/api/banners", tags=["banners"])


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


def banner_to_dict(banner: Banner):
    return {
        "id": banner.id,
        "title": banner.title,
        "subtitle": banner.subtitle,
        "img": banner.img,
        "link": banner.link,
        "position": banner.position,
        "sort_order": banner.sort_order,
        "is_active": banner.is_active,
        "start_at": banner.start_at,
        "end_at": banner.end_at,
        "created_at": banner.created_at,
        "updated_at": banner.updated_at,
    }


def is_banner_available(banner: Banner):
    now = datetime.now(timezone.utc)

    if not banner.is_active:
        return False

    if banner.start_at and now < banner.start_at:
        return False

    if banner.end_at and now > banner.end_at:
        return False

    return True


# =========================
# GET ACTIVE BANNERS
# GET /api/banners/active
# Public
# =========================

@banners_route.get("/active")
def get_active_banners(
        db: Session = Depends(get_db),
        position: str = Query(None)
):
    query = db.query(Banner).filter(Banner.is_active == True)

    if position:
        query = query.filter(Banner.position == position)

    banners = (
        query
        .order_by(Banner.sort_order.asc(), Banner.id.desc())
        .all()
    )

    active_banners = [
        banner for banner in banners
        if is_banner_available(banner)
    ]

    return {
        "message": "Lấy banner đang hoạt động thành công",
        "data": [banner_to_dict(banner) for banner in active_banners]
    }


# =========================
# GET ALL BANNERS
# GET /api/banners/
# Public hoặc admin đều xem được
# =========================

@banners_route.get("/")
def get_all_banners(
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        position: str = Query(None),
        is_active: bool = Query(None)
):
    query = db.query(Banner)

    if position:
        query = query.filter(Banner.position == position)

    if is_active is not None:
        query = query.filter(Banner.is_active == is_active)

    total = query.count()

    banners = (
        query
        .order_by(Banner.sort_order.asc(), Banner.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách banner thành công",
        "data": [banner_to_dict(banner) for banner in banners],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET BANNER BY ID
# GET /api/banners/{banner_id}
# Public
# =========================

@banners_route.get("/{banner_id}")
def get_banner_by_id(
        banner_id: int,
        db: Session = Depends(get_db)
):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()

    if not banner:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy banner"
        )

    return {
        "message": "Lấy chi tiết banner thành công",
        "data": banner_to_dict(banner)
    }


# =========================
# CREATE BANNER
# POST /api/banners/
# Admin
# =========================

@banners_route.post("/")
def create_banner(
        banner_data: BannerCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    new_banner = Banner(
        title=banner_data.title,
        subtitle=banner_data.subtitle,
        img=banner_data.img,
        link=banner_data.link,
        position=banner_data.position,
        sort_order=banner_data.sort_order,
        is_active=banner_data.is_active,
        start_at=banner_data.start_at,
        end_at=banner_data.end_at
    )

    db.add(new_banner)
    db.commit()
    db.refresh(new_banner)

    return {
        "message": "Tạo banner thành công",
        "data": banner_to_dict(new_banner)
    }


# =========================
# UPDATE BANNER
# PUT /api/banners/{banner_id}
# PATCH /api/banners/{banner_id}
# Admin
# =========================

@banners_route.put("/{banner_id}")
@banners_route.patch("/{banner_id}")
def update_banner(
        banner_id: int,
        banner_data: BannerUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    banner = db.query(Banner).filter(Banner.id == banner_id).first()

    if not banner:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy banner"
        )

    update_data = banner_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    for key, value in update_data.items():
        setattr(banner, key, value)

    db.commit()
    db.refresh(banner)

    return {
        "message": "Cập nhật banner thành công",
        "data": banner_to_dict(banner)
    }


# =========================
# DELETE BANNER
# DELETE /api/banners/{banner_id}
# Admin
# =========================

@banners_route.delete("/{banner_id}")
def delete_banner(
        banner_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    banner = db.query(Banner).filter(Banner.id == banner_id).first()

    if not banner:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy banner"
        )

    db.delete(banner)
    db.commit()

    return {
        "message": "Xóa banner thành công",
        "deleted_banner_id": banner_id
    }