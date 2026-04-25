import os
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from models.models import User
from schemas.profile_schema import ChangePasswordSchema
from utils import hash_password, verify_password


profile_route = APIRouter(prefix="/api/profile", tags=["profile"])

AVATAR_UPLOAD_DIR = "static/avatars"
os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)


def get_current_user_id(request: Request):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    return current_user_id


def user_to_dict(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar
    }


def save_avatar_file(file: UploadFile):
    if not file or not file.filename:
        return None

    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid4().hex}{ext}"

    file_path = os.path.join(AVATAR_UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    return f"/{file_path.replace(os.sep, '/')}"


# =========================
# GET MY PROFILE
# GET /api/profile/me
# =========================

@profile_route.get("/me")
def get_my_profile(
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = get_current_user_id(request)

    user = db.query(User).filter(User.id == current_user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy người dùng"
        )

    return {
        "message": "Lấy thông tin tài khoản thành công",
        "data": user_to_dict(user)
    }


# =========================
# UPDATE MY PROFILE
# PUT /api/profile/me
# =========================

@profile_route.put("/me")
def update_my_profile(
        request: Request,
        username: Optional[str] = Form(None),
        avatar: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db)
):
    current_user_id = get_current_user_id(request)

    user = db.query(User).filter(User.id == current_user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy người dùng"
        )

    if username is not None and username != user.username:
        existed_user = (
            db.query(User)
            .filter(
                User.username == username,
                User.id != current_user_id
            )
            .first()
        )

        if existed_user:
            raise HTTPException(
                status_code=400,
                detail="Username đã tồn tại"
            )

        user.username = username

    if avatar:
        # Xóa avatar cũ nếu avatar nằm trong server local
        if user.avatar and user.avatar.startswith("/static/avatars/"):
            old_avatar_path = user.avatar.lstrip("/")
            if os.path.exists(old_avatar_path):
                try:
                    os.remove(old_avatar_path)
                except Exception:
                    pass

        avatar_path = save_avatar_file(avatar)
        user.avatar = avatar_path

    db.commit()
    db.refresh(user)

    return {
        "message": "Cập nhật thông tin tài khoản thành công",
        "data": user_to_dict(user)
    }


# =========================
# CHANGE PASSWORD
# PUT /api/profile/change-password
# =========================

@profile_route.put("/change-password")
def change_password(
        password_data: ChangePasswordSchema,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = get_current_user_id(request)

    user = db.query(User).filter(User.id == current_user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy người dùng"
        )

    is_correct = verify_password(
        password_data.old_password,
        user.password
    )

    if not is_correct:
        raise HTTPException(
            status_code=400,
            detail="Mật khẩu cũ không đúng"
        )

    user.password = hash_password(password_data.new_password)

    db.commit()
    db.refresh(user)

    return {
        "message": "Đổi mật khẩu thành công"
    }