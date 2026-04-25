import math
import os
from typing import Optional, List

from fastapi import APIRouter, Form, UploadFile, HTTPException
from fastapi.params import Depends, Query, File
from flask import request
from sqlalchemy import or_, cast, String
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import Products, User, Brand
from utils import parse_json_field, save_upload_files

products_route = APIRouter(prefix="/api/products", tags=["products"])

@products_route.get("/")
@products_route.get("/")
def get_all_products(
        db: Session = Depends(get_db),

        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),

        search: Optional[str] = Query(None),

        category: Optional[str] = Query(None),
        min_price: Optional[float] = Query(None, ge=0),
        max_price: Optional[float] = Query(None, ge=0),

        size: Optional[List[str]] = Query(None),
        color: Optional[List[str]] = Query(None),
        brand_id: Optional[int] = Query(None),
        brand_slug: Optional[str] = Query(None),

        sort: Optional[str] = Query("newest")
):
    query = db.query(Products)

    # =========================
    # SEARCH
    # =========================
    if search:
        query = query.filter(
            or_(
                Products.title.ilike(f"%{search}%"),
                Products.desc.ilike(f"%{search}%"),
                cast(Products.categories, String).ilike(f"%{search}%")
            )
        )

    # =========================
    # FILTER CATEGORY
    # =========================
    # categories đang là JSON nên cast sang String để tìm theo name / slug / id
    if category:
        query = query.filter(
            cast(Products.categories, String).ilike(f"%{category}%")
        )

    # =========================
    # FILTER PRICE
    # =========================
    if min_price is not None:
        query = query.filter(Products.price >= min_price)

    if max_price is not None:
        query = query.filter(Products.price <= max_price)

    # =========================
    # FILTER SIZE
    # =========================
    # Ví dụ: ?size=M&size=L
    if size:
        size_conditions = []

        for item in size:
            size_conditions.append(Products.size.any(item))

        query = query.filter(or_(*size_conditions))

    # =========================
    # FILTER COLOR
    # =========================
    # Ví dụ: ?color=Đen&color=Trắng
    if color:
        color_conditions = []

        for item in color:
            color_conditions.append(Products.color.any(item))

        query = query.filter(or_(*color_conditions))

    if brand_id is not None:
        query = query.filter(Products.brand_id == brand_id)

    if brand_slug:
        query = query.join(Brand).filter(Brand.slug == brand_slug)
    # =========================
    # SORT
    # =========================
    if sort == "price_asc":
        query = query.order_by(Products.price.asc())

    elif sort == "price_desc":
        query = query.order_by(Products.price.desc())

    elif sort == "oldest":
        query = query.order_by(Products.id.asc())

    elif sort == "title_asc":
        query = query.order_by(Products.title.asc())

    elif sort == "title_desc":
        query = query.order_by(Products.title.desc())

    else:
        # newest
        query = query.order_by(Products.id.desc())

    # =========================
    # PAGINATION
    # =========================
    total = query.count()

    products = (
        query
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách sản phẩm thành công",
        "data": products,
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit,
        },
        "filters": {
            "search": search,
            "category": category,
            "min_price": min_price,
            "max_price": max_price,
            "size": size,
            "color": color,
            "sort": sort
        }
    }

@products_route.post("/")
def create_product(
        title: str = Form(...),
        desc: Optional[str] = Form(None),
        categories: Optional[str] = Form(None),
        size: Optional[List[str]] = Form(None),
        color: Optional[List[str]] = Form(None),
        price: Optional[float] = Form(None),
        img: Optional[List[UploadFile]] = File(None),
        brand_id: Optional[int] = None,
        db: Session = Depends(get_db),
):
    image_paths = save_upload_files(img)

    new_product = Products(
        title=title,
        desc=desc,
        img=image_paths,
        categories=parse_json_field(categories),
        size=size or [],
        color=color or [],
        price=price,
        user_id=request.state.current_user_id,
        brand_id=brand_id,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return {
        "message": "Tạo sản phẩm thành công",
        "data": new_product
    }

@products_route.put("/{product_id}")
def update_product(
        product_id: int,
        title: Optional[str] = Form(None),
        desc: Optional[str] = Form(None),
        categories: Optional[str] = Form(None),
        size: Optional[List[str]] = Form(None),
        color: Optional[List[str]] = Form(None),
        price: Optional[float] = Form(None),
        user_id: Optional[int] = Form(None),
        img: Optional[List[UploadFile]] = File(None),
        db: Session = Depends(get_db)
):
    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    if title is not None:
        product.title = title

    if desc is not None:
        product.desc = desc

    if categories is not None:
        product.categories = parse_json_field(categories)

    if size is not None:
        product.size = size

    if color is not None:
        product.color = color

    if price is not None:
        product.price = price

    if user_id is not None:
        product.user_id = user_id

    # Nếu có gửi ảnh mới thì thay img cũ bằng ảnh mới
    if img:
        image_paths = save_upload_files(img)
        product.img = image_paths

    db.commit()
    db.refresh(product)

    return {
        "message": "Cập nhật sản phẩm thành công",
        "data": product
    }

@products_route.delete("/{product_id}")
def delete_product(
        product_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    product = db.query(Products).filter(Products.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail = 'product not found'
        )

    current_id = current_user.id

    if not current_id:
        raise HTTPException(
            status_code=404,
            detail = 'user not authenticated'
        )

    if not product.user_id != current_id:
        raise HTTPException(
            status_code=403,
            detail = 'Ban khong co quyen xoa'
        )

    if product.img:
        for image_path in product.img:
            try:
                file_path = image_path.lstrip("/")
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    db.delete(product)
    db.commit()

    return {
        "message" : 'product deleted successfully',
        "delete product_id": product_id
    }

@products_route.get("/{product_id}")
def get_product_by_id(
        product_id: int,
        db: Session = Depends(get_db)
):
    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    return {
        "message": "Lấy chi tiết sản phẩm thành công",
        "data": product
    }