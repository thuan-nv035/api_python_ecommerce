import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, Products, ProductCollection, ProductCollectionItem
from schemas.product_collection_schema import (
    ProductCollectionCreate,
    ProductCollectionUpdate,
    CollectionItemCreate,
    CollectionItemUpdate
)


product_collections_route = APIRouter(
    prefix="/api/product-collections",
    tags=["product-collections"]
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


def is_collection_available(collection: ProductCollection):
    now = datetime.now(timezone.utc)

    if not collection.is_active:
        return False

    if collection.start_at and now < collection.start_at:
        return False

    if collection.end_at and now > collection.end_at:
        return False

    return True


def product_to_dict(product: Products):
    return {
        "id": product.id,
        "title": product.title,
        "desc": product.desc,
        "img": product.img,
        "categories": product.categories,
        "size": product.size,
        "color": product.color,
        "price": product.price,
        "brand_id": getattr(product, "brand_id", None),
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


def collection_item_to_dict(item: ProductCollectionItem):
    return {
        "id": item.id,
        "collection_id": item.collection_id,
        "product_id": item.product_id,
        "sort_order": item.sort_order,
        "is_active": item.is_active,
        "created_at": item.created_at,
        "product": product_to_dict(item.product) if item.product else None
    }


def collection_to_dict(collection: ProductCollection):
    active_items = [
        item for item in collection.items
        if item.is_active
    ]

    active_items = sorted(
        active_items,
        key=lambda item: (item.sort_order or 0, item.id)
    )

    return {
        "id": collection.id,
        "title": collection.title,
        "slug": collection.slug,
        "desc": collection.desc,
        "banner_img": collection.banner_img,
        "is_active": collection.is_active,
        "start_at": collection.start_at,
        "end_at": collection.end_at,
        "created_at": collection.created_at,
        "updated_at": collection.updated_at,
        "items": [
            collection_item_to_dict(item)
            for item in active_items
        ]
    }


# =========================
# GET ACTIVE COLLECTIONS
# GET /api/product-collections/active
# Public
# =========================

@product_collections_route.get("/active")
def get_active_collections(
        db: Session = Depends(get_db)
):
    collections = (
        db.query(ProductCollection)
        .filter(ProductCollection.is_active == True)
        .order_by(ProductCollection.id.desc())
        .all()
    )

    active_collections = [
        collection for collection in collections
        if is_collection_available(collection)
    ]

    return {
        "message": "Lấy bộ sưu tập đang hoạt động thành công",
        "data": [
            collection_to_dict(collection)
            for collection in active_collections
        ]
    }


# =========================
# GET COLLECTION BY SLUG
# GET /api/product-collections/slug/{slug}
# Public
# =========================

@product_collections_route.get("/slug/{slug}")
def get_collection_by_slug(
        slug: str,
        db: Session = Depends(get_db)
):
    collection = (
        db.query(ProductCollection)
        .filter(ProductCollection.slug == slug)
        .first()
    )

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy bộ sưu tập"
        )

    if not is_collection_available(collection):
        raise HTTPException(
            status_code=404,
            detail="Bộ sưu tập hiện không hoạt động"
        )

    return {
        "message": "Lấy chi tiết bộ sưu tập thành công",
        "data": collection_to_dict(collection)
    }


# =========================
# GET ALL COLLECTIONS
# GET /api/product-collections/
# Admin
# =========================

@product_collections_route.get("/")
def get_all_collections(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        is_active: bool = Query(None)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    query = db.query(ProductCollection)

    if search:
        query = query.filter(
            or_(
                ProductCollection.title.ilike(f"%{search}%"),
                ProductCollection.slug.ilike(f"%{search}%")
            )
        )

    if is_active is not None:
        query = query.filter(ProductCollection.is_active == is_active)

    total = query.count()

    collections = (
        query
        .order_by(ProductCollection.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách bộ sưu tập thành công",
        "data": [
            collection_to_dict(collection)
            for collection in collections
        ],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET COLLECTION BY ID
# GET /api/product-collections/{collection_id}
# Admin
# =========================

@product_collections_route.get("/{collection_id}")
def get_collection_by_id(
        collection_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    collection = (
        db.query(ProductCollection)
        .filter(ProductCollection.id == collection_id)
        .first()
    )

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy bộ sưu tập"
        )

    return {
        "message": "Lấy chi tiết bộ sưu tập thành công",
        "data": collection_to_dict(collection)
    }


# =========================
# CREATE COLLECTION
# POST /api/product-collections/
# Admin
# =========================

@product_collections_route.post("/")
def create_collection(
        collection_data: ProductCollectionCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    slug = collection_data.slug.strip().lower()

    existed_collection = (
        db.query(ProductCollection)
        .filter(ProductCollection.slug == slug)
        .first()
    )

    if existed_collection:
        raise HTTPException(
            status_code=400,
            detail="Slug bộ sưu tập đã tồn tại"
        )

    if collection_data.start_at and collection_data.end_at:
        if collection_data.end_at <= collection_data.start_at:
            raise HTTPException(
                status_code=400,
                detail="Thời gian kết thúc phải lớn hơn thời gian bắt đầu"
            )

    new_collection = ProductCollection(
        title=collection_data.title,
        slug=slug,
        desc=collection_data.desc,
        banner_img=collection_data.banner_img,
        is_active=collection_data.is_active,
        start_at=collection_data.start_at,
        end_at=collection_data.end_at
    )

    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)

    return {
        "message": "Tạo bộ sưu tập thành công",
        "data": collection_to_dict(new_collection)
    }


# =========================
# UPDATE COLLECTION
# PUT/PATCH /api/product-collections/{collection_id}
# Admin
# =========================

@product_collections_route.put("/{collection_id}")
@product_collections_route.patch("/{collection_id}")
def update_collection(
        collection_id: int,
        collection_data: ProductCollectionUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    collection = (
        db.query(ProductCollection)
        .filter(ProductCollection.id == collection_id)
        .first()
    )

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy bộ sưu tập"
        )

    update_data = collection_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "slug" in update_data:
        new_slug = update_data["slug"].strip().lower()

        existed_collection = (
            db.query(ProductCollection)
            .filter(
                ProductCollection.slug == new_slug,
                ProductCollection.id != collection_id
            )
            .first()
        )

        if existed_collection:
            raise HTTPException(
                status_code=400,
                detail="Slug bộ sưu tập đã tồn tại"
            )

        update_data["slug"] = new_slug

    new_start = update_data.get("start_at", collection.start_at)
    new_end = update_data.get("end_at", collection.end_at)

    if new_start and new_end and new_end <= new_start:
        raise HTTPException(
            status_code=400,
            detail="Thời gian kết thúc phải lớn hơn thời gian bắt đầu"
        )

    for key, value in update_data.items():
        setattr(collection, key, value)

    db.commit()
    db.refresh(collection)

    return {
        "message": "Cập nhật bộ sưu tập thành công",
        "data": collection_to_dict(collection)
    }


# =========================
# DELETE COLLECTION
# DELETE /api/product-collections/{collection_id}
# Admin
# =========================

@product_collections_route.delete("/{collection_id}")
def delete_collection(
        collection_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    collection = (
        db.query(ProductCollection)
        .filter(ProductCollection.id == collection_id)
        .first()
    )

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy bộ sưu tập"
        )

    db.delete(collection)
    db.commit()

    return {
        "message": "Xóa bộ sưu tập thành công",
        "deleted_collection_id": collection_id
    }


# =========================
# ADD PRODUCT TO COLLECTION
# POST /api/product-collections/{collection_id}/items
# Admin
# =========================

@product_collections_route.post("/{collection_id}/items")
def add_product_to_collection(
        collection_id: int,
        item_data: CollectionItemCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    collection = (
        db.query(ProductCollection)
        .filter(ProductCollection.id == collection_id)
        .first()
    )

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy bộ sưu tập"
        )

    product = (
        db.query(Products)
        .filter(Products.id == item_data.product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    existed_item = (
        db.query(ProductCollectionItem)
        .filter(
            ProductCollectionItem.collection_id == collection_id,
            ProductCollectionItem.product_id == item_data.product_id
        )
        .first()
    )

    if existed_item:
        raise HTTPException(
            status_code=400,
            detail="Sản phẩm này đã có trong bộ sưu tập"
        )

    new_item = ProductCollectionItem(
        collection_id=collection_id,
        product_id=item_data.product_id,
        sort_order=item_data.sort_order,
        is_active=item_data.is_active
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "message": "Thêm sản phẩm vào bộ sưu tập thành công",
        "data": collection_item_to_dict(new_item)
    }


# =========================
# UPDATE COLLECTION ITEM
# PATCH /api/product-collections/items/{item_id}
# Admin
# =========================

@product_collections_route.patch("/items/{item_id}")
def update_collection_item(
        item_id: int,
        item_data: CollectionItemUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    item = (
        db.query(ProductCollectionItem)
        .filter(ProductCollectionItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm trong bộ sưu tập"
        )

    update_data = item_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)

    return {
        "message": "Cập nhật sản phẩm trong bộ sưu tập thành công",
        "data": collection_item_to_dict(item)
    }


# =========================
# REMOVE PRODUCT FROM COLLECTION
# DELETE /api/product-collections/items/{item_id}
# Admin
# =========================

@product_collections_route.delete("/items/{item_id}")
def remove_product_from_collection(
        item_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    item = (
        db.query(ProductCollectionItem)
        .filter(ProductCollectionItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm trong bộ sưu tập"
        )

    db.delete(item)
    db.commit()

    return {
        "message": "Xóa sản phẩm khỏi bộ sưu tập thành công",
        "deleted_item_id": item_id
    }