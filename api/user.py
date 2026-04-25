import math
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, status, HTTPException, Form, UploadFile, File
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from api.auth import get_current_user, SECRET_KEY, ALGORITHM
from api.config import ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
from models.models import User
from schemas.user import UserCreate, UserOut

user_route = APIRouter(prefix="/api/users", tags=["users"])

import bcrypt

def verify_password(plain_password, hashed_password):
    password_byte = plain_password.encode('utf-8')
    hashed_byte = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte, hashed_byte)

# Đây là chìa khóa bí mật, đừng cho ai biết!



@user_route.get("/")
def get_all_users(
    db: Session = Depends(get_db),
    page: int = Query(1, gt=0),
    limit: int = Query(20, gt=0, le=100),
    search: str = Query(None) # Thêm tham số search, mặc định là None
):
    query = db.query(User)

    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))

    # Đếm tổng số bản ghi SAU KHI lọc
    total_users = query.count()

    # Phân trang dữ liệu
    offset = (page - 1) * limit
    users_query = query.offset(offset).limit(limit).all()

    # Tính toán pagination
    total_pages = math.ceil(total_users / limit) if total_users > 0 else 0

    # Chuyển đổi dữ liệu sang list dict để tránh lỗi 500
    users_data = [
        {"id": u.id, "username": u.username, "avatar": u.avatar}
        for u in users_query
    ]

    return {
        "data": users_data,
        "pagination": {
            "total_records": total_users,
            "total_pages": total_pages,
            "current_page": page,
            "limit": limit
        }
    }

@user_route.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    # Nếu code chạy được vào đến đây, nghĩa là Token đã hợp lệ
    # current_user chính là thông tin của người đang gửi request
    return {
        "id": current_user.id,
        "username": current_user.username,
    }


@user_route.get('/{user_id}', response_model=UserOut)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def hash_password(password: str):
    # Chuyển mật khẩu sang dạng bytes
    pwd_bytes = password.encode('utf-8')
    # Tạo salt và mã hóa
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    # Trả về dạng chuỗi để lưu vào Database
    return hashed_password.decode('utf-8')

@user_route.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    # ĐÚNG: Lấy giá trị từ biến user_data mà bạn nhận từ Body
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    # Lấy mật khẩu thuần từ JSON (ví dụ: "123456")
    raw_password = str(user_data.password)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = hash_password(raw_password)

    new_user = User(
        username=user_data.username,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}

def create_access_token(data: dict):
    to_encode = data.copy()
    # Tính thời gian hết hạn
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Tạo chuỗi Token mã hóa
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@user_route.post('/login')
def login(
        user_data : dict,
        db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == user_data.get('username')).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_correct = verify_password(user_data.get('password'), user.password)
    if not is_correct:
        raise HTTPException(status_code=400, detail="Incorrect password")

    access_token = create_access_token(data={"username": user.username, "user_id": user.id, "avatar": user.avatar})
    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "avatar": user.avatar
        }
    }

@user_route.put('/update-profile')
def update_profile(
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    avatar: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if username and username != current_user.username:
        # Kiểm tra xem username mới có bị trùng với ai khác không
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username này đã có người sử dụng")
        current_user.username = username

    if password:
        current_user.password = hash_password(password)

    if avatar:
        upload_dir = 'static/avatars'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        file_extension = os.path.splitext(avatar.filename)[1]
        file_name = f"user_{current_user.id}.{file_extension}"
        file_location = f"{upload_dir}/{file_name}"

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

        current_user.avatar = f"/{file_location}"

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Profile updated successfully",
        "user": {
            "username": current_user.username,
            "avatar": current_user.avatar
        }
    }


