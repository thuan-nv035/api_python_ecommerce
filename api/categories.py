import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models.models import Category
from schemas.category_schema import CategoryCreate, CategoryUpdate


categories_route = APIRouter(prefix="/api/categories", tags=["categories"])


def category_to_dict(category: Category):
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "desc": category.desc,
        "img": category.img,
        "is_active": category.is_active,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


# =========================
# GET ALL CATEGORIES
# GET /api/categories/
# =========================

@categories_route.get("/")
def get_all_categories(
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        is_active: bool = Query(None)
):
    query = db.query(Category)

    if search:
        query = query.filter(
            or_(
                Category.name.ilike(f"%{search}%"),
                Category.slug.ilike(f"%{search}%")
            )
        )

    if is_active is not None:
        query = query.filter(Category.is_active == is_active)

    total = query.count()

    categories = (
        query
        .order_by(Category.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách danh mục thành công",
        "data": [category_to_dict(category) for category in categories],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit),
            "current_page": page,
            "limit": limit,
        }
    }


# =========================
# GET CATEGORY BY ID
# GET /api/categories/{category_id}
# =========================

@categories_route.get("/{category_id}")
def get_category_by_id(
        category_id: int,
        db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy danh mục"
        )

    return {
        "message": "Lấy chi tiết danh mục thành công",
        "data": category_to_dict(category)
    }


# =========================
# CREATE CATEGORY
# POST /api/categories/
# =========================

@categories_route.post("/")
def create_category(
        category_data: CategoryCreate,
        db: Session = Depends(get_db)
):
    existed_category = (
        db.query(Category)
        .filter(Category.slug == category_data.slug)
        .first()
    )

    if existed_category:
        raise HTTPException(
            status_code=400,
            detail="Slug danh mục đã tồn tại"
        )

    new_category = Category(
        name=category_data.name,
        slug=category_data.slug,
        desc=category_data.desc,
        img=category_data.img,
        is_active=category_data.is_active
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return {
        "message": "Tạo danh mục thành công",
        "data": category_to_dict(new_category)
    }


# =========================
# UPDATE CATEGORY
# PUT /api/categories/{category_id}
# PATCH /api/categories/{category_id}
# =========================

@categories_route.put("/{category_id}")
@categories_route.patch("/{category_id}")
def update_category(
        category_id: int,
        category_data: CategoryUpdate,
        db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy danh mục"
        )

    update_data = category_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "slug" in update_data:
        existed_category = (
            db.query(Category)
            .filter(
                Category.slug == update_data["slug"],
                Category.id != category_id
            )
            .first()
        )

        if existed_category:
            raise HTTPException(
                status_code=400,
                detail="Slug danh mục đã tồn tại"
            )

    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)

    return {
        "message": "Cập nhật danh mục thành công",
        "data": category_to_dict(category)
    }


# =========================
# DELETE CATEGORY
# DELETE /api/categories/{category_id}
# =========================

@categories_route.delete("/{category_id}")
def delete_category(
        category_id: int,
        db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy danh mục"
        )

    db.delete(category)
    db.commit()

    return {
        "message": "Xóa danh mục thành công",
        "deleted_category_id": category_id
    }