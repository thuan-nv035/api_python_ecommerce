import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, Products, ProductQuestion
from schemas.product_question_schema import (
    ProductQuestionCreate,
    ProductQuestionUpdate,
    ProductQuestionAnswer
)


product_questions_route = APIRouter(
    prefix="/api/product-questions",
    tags=["product-questions"]
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


def is_admin(user: User):
    return getattr(user, "role", "user") == "admin"


def question_to_dict(question: ProductQuestion):
    return {
        "id": question.id,
        "user_id": question.user_id,
        "product_id": question.product_id,
        "question": question.question,
        "answer": question.answer,
        "status": question.status,
        "is_public": question.is_public,
        "answered_by_id": question.answered_by_id,
        "answered_at": question.answered_at,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "user": {
            "id": question.user.id,
            "username": question.user.username,
            "avatar": question.user.avatar
        } if question.user else None,
        "answered_by": {
            "id": question.answered_by.id,
            "username": question.answered_by.username,
            "avatar": question.answered_by.avatar
        } if question.answered_by else None,
        "product": {
            "id": question.product.id,
            "title": question.product.title,
            "img": question.product.img,
            "price": question.product.price
        } if question.product else None
    }


# =========================
# CREATE QUESTION
# POST /api/product-questions/
# User hỏi về sản phẩm
# =========================

@product_questions_route.post("/")
def create_product_question(
        question_data: ProductQuestionCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    product = (
        db.query(Products)
        .filter(Products.id == question_data.product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    new_question = ProductQuestion(
        user_id=current_user.id,
        product_id=question_data.product_id,
        question=question_data.question,
        is_public=question_data.is_public,
        status="pending"
    )

    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    return {
        "message": "Gửi câu hỏi sản phẩm thành công",
        "data": question_to_dict(new_question)
    }


# =========================
# GET QUESTIONS BY PRODUCT
# GET /api/product-questions/product/{product_id}
# Public: chỉ lấy câu đã trả lời và công khai
# =========================

@product_questions_route.get("/product/{product_id}")
def get_questions_by_product(
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

    query = (
        db.query(ProductQuestion)
        .filter(
            ProductQuestion.product_id == product_id,
            ProductQuestion.status == "answered",
            ProductQuestion.is_public == True
        )
    )

    total = query.count()

    questions = (
        query
        .order_by(ProductQuestion.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy hỏi đáp sản phẩm thành công",
        "data": [question_to_dict(item) for item in questions],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET MY QUESTIONS
# GET /api/product-questions/my
# =========================

@product_questions_route.get("/my")
def get_my_questions(
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    questions = (
        db.query(ProductQuestion)
        .filter(ProductQuestion.user_id == current_user.id)
        .order_by(ProductQuestion.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách câu hỏi của tôi thành công",
        "data": [question_to_dict(item) for item in questions]
    }


# =========================
# GET ALL QUESTIONS
# GET /api/product-questions/
# Admin xem tất cả câu hỏi
# =========================

@product_questions_route.get("/")
def get_all_questions(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        status: str = Query(None),
        product_id: int = Query(None)
):
    current_user = get_current_user(request, db)

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    query = db.query(ProductQuestion)

    if status:
        query = query.filter(ProductQuestion.status == status)

    if product_id:
        query = query.filter(ProductQuestion.product_id == product_id)

    total = query.count()

    questions = (
        query
        .order_by(ProductQuestion.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách câu hỏi sản phẩm thành công",
        "data": [question_to_dict(item) for item in questions],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET QUESTION BY ID
# GET /api/product-questions/{question_id}
# Owner hoặc admin
# =========================

@product_questions_route.get("/{question_id}")
def get_question_by_id(
        question_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    question = (
        db.query(ProductQuestion)
        .filter(ProductQuestion.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy câu hỏi"
        )

    is_owner = question.user_id == current_user.id
    admin = is_admin(current_user)

    if not is_owner and not admin:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem câu hỏi này"
        )

    return {
        "message": "Lấy chi tiết câu hỏi thành công",
        "data": question_to_dict(question)
    }


# =========================
# UPDATE MY QUESTION
# PATCH /api/product-questions/{question_id}
# User chỉ sửa khi câu hỏi còn pending
# =========================

@product_questions_route.patch("/{question_id}")
def update_my_question(
        question_id: int,
        question_data: ProductQuestionUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    question = (
        db.query(ProductQuestion)
        .filter(
            ProductQuestion.id == question_id,
            ProductQuestion.user_id == current_user.id
        )
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy câu hỏi"
        )

    if question.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể sửa câu hỏi khi đang chờ trả lời"
        )

    update_data = question_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    for key, value in update_data.items():
        setattr(question, key, value)

    db.commit()
    db.refresh(question)

    return {
        "message": "Cập nhật câu hỏi thành công",
        "data": question_to_dict(question)
    }


# =========================
# ANSWER QUESTION
# PATCH /api/product-questions/{question_id}/answer
# Admin trả lời câu hỏi
# =========================

@product_questions_route.patch("/{question_id}/answer")
def answer_product_question(
        question_id: int,
        answer_data: ProductQuestionAnswer,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    allowed_status = ["answered", "hidden"]

    if answer_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái câu trả lời không hợp lệ"
        )

    question = (
        db.query(ProductQuestion)
        .filter(ProductQuestion.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy câu hỏi"
        )

    question.answer = answer_data.answer
    question.status = answer_data.status
    question.is_public = answer_data.is_public
    question.answered_by_id = current_user.id
    question.answered_at = datetime.utcnow()

    db.commit()
    db.refresh(question)

    return {
        "message": "Trả lời câu hỏi thành công",
        "data": question_to_dict(question)
    }


# =========================
# HIDE QUESTION
# PATCH /api/product-questions/{question_id}/hide
# Admin ẩn câu hỏi
# =========================

@product_questions_route.patch("/{question_id}/hide")
def hide_product_question(
        question_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    question = (
        db.query(ProductQuestion)
        .filter(ProductQuestion.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy câu hỏi"
        )

    question.status = "hidden"
    question.is_public = False

    db.commit()
    db.refresh(question)

    return {
        "message": "Ẩn câu hỏi thành công",
        "data": question_to_dict(question)
    }


# =========================
# DELETE QUESTION
# DELETE /api/product-questions/{question_id}
# Owner hoặc admin
# =========================

@product_questions_route.delete("/{question_id}")
def delete_product_question(
        question_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    question = (
        db.query(ProductQuestion)
        .filter(ProductQuestion.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy câu hỏi"
        )

    is_owner = question.user_id == current_user.id
    admin = is_admin(current_user)

    if not is_owner and not admin:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xóa câu hỏi này"
        )

    if is_owner and not admin and question.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể xóa câu hỏi khi đang chờ trả lời"
        )

    db.delete(question)
    db.commit()

    return {
        "message": "Xóa câu hỏi thành công",
        "deleted_question_id": question_id
    }