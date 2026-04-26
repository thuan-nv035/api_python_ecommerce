import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import Products, Review, User
from schemas.review_schema import ReviewCreate, ReviewUpdate

reviews_route = APIRouter(prefix="/api/reviews", tags=["reviews"])

def review_to_dict(review: Review):
    return {
        "id": review.id,
        "user_id": review.user_id,
        "product_id": review.product_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "user": {
            "id": review.user.id,
            "username": review.user.username,
            "avatar": review.user.avatar
        } if review.user else None,
        "product": {
            "id": review.product.id,
            "title": review.product.title,
            "img": review.product.img,
            "price": review.product.price
        } if review.product else None
    }

# =========================
# CREATE REVIEW
# POST /api/reviews/
# =========================

@reviews_route.post("/")
def create_review(
        review_data: ReviewCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    product = db.query(Products).filter(Products.id == review_data.product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    existed_review = (
        db.query(Review)
        .filter(
            Review.user_id == current_user_id,
            Review.product_id == review_data.product_id
        )
        .first()
    )

    if existed_review:
        raise HTTPException(
            status_code=400,
            detail="Bạn đã đánh giá sản phẩm này rồi"
        )

    new_review = Review(
        user_id=current_user_id,
        product_id=review_data.product_id,
        rating=review_data.rating,
        comment=review_data.comment
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return {
        "message": "Đánh giá sản phẩm thành công",
        "data": review_to_dict(new_review)
    }


# =========================
# GET REVIEWS BY PRODUCT
# GET /api/reviews/product/{product_id}
# =========================

@reviews_route.get("/product/{product_id}")
def get_reviews_by_product(
        product_id: int,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(10, gt=0)
):
    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    query = db.query(Review).filter(Review.product_id == product_id)

    total = query.count()

    reviews = (
        query
        .order_by(Review.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    total_rating = sum(review.rating for review in query.all())
    average_rating = round(total_rating / total, 1) if total > 0 else 0

    return {
        "message": "Lấy đánh giá sản phẩm thành công",
        "data": [review_to_dict(review) for review in reviews],
        "summary": {
            "total_reviews": total,
            "average_rating": average_rating
        },
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit),
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET MY REVIEWS
# GET /api/reviews/my
# =========================

@reviews_route.get("/my")
def get_my_reviews(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    reviews = (
        db.query(Review)
        .filter(Review.user_id == current_user_id)
        .order_by(Review.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách đánh giá của tôi thành công",
        "data": [review_to_dict(review) for review in reviews]
    }


# =========================
# GET REVIEW BY ID
# GET /api/reviews/{review_id}
# =========================

@reviews_route.get("/{review_id}")
def get_review_by_id(
        review_id: int,
        db: Session = Depends(get_db)
):
    review = db.query(Review).filter(Review.id == review_id).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đánh giá"
        )

    return {
        "message": "Lấy chi tiết đánh giá thành công",
        "data": review_to_dict(review)
    }


# =========================
# UPDATE REVIEW
# PUT /api/reviews/{review_id}
# PATCH /api/reviews/{review_id}
# =========================

@reviews_route.put("/{review_id}")
@reviews_route.patch("/{review_id}")
def update_review(
        review_id: int,
        review_data: ReviewUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    review = (
        db.query(Review)
        .filter(
            Review.id == review_id,
            Review.user_id == current_user_id
        )
        .first()
    )

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đánh giá hoặc bạn không có quyền sửa"
        )

    update_data = review_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    for key, value in update_data.items():
        setattr(review, key, value)

    db.commit()
    db.refresh(review)

    return {
        "message": "Cập nhật đánh giá thành công",
        "data": review_to_dict(review)
    }


# =========================
# DELETE REVIEW
# DELETE /api/reviews/{review_id}
# =========================

@reviews_route.delete("/{review_id}")
def delete_review(
        review_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    review = (
        db.query(Review)
        .filter(
            Review.id == review_id,
            Review.user_id == current_user_id
        )
        .first()
    )

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đánh giá hoặc bạn không có quyền xóa"
        )

    db.delete(review)
    db.commit()

    return {
        "message": "Xóa đánh giá thành công",
        "deleted_review_id": review_id
    }