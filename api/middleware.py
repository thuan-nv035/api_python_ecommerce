from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError

from database import SessionLocal
from models.models import User
from api.config import SECRET_KEY, ALGORITHM


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Các route không cần token
        public_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/user/login",
            "/api/user/register",
        ]

        # Cho phép truy cập ảnh upload
        if path.startswith("/uploads"):
            return await call_next(request)

        if path in public_paths:
            return await call_next(request)

        # Chỉ bắt đăng nhập với các API cần bảo vệ
        protected = (
            path.startswith("/api/products")
            and method in ["POST", "PUT", "PATCH", "DELETE"]
        )

        if not protected:
            return await call_next(request)

        # Lấy token từ header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Thiếu token hoặc token không đúng định dạng"}
            )

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM]
            )

            user_id = payload.get("id") or payload.get("user_id")
            username = payload.get("username")

            if not user_id and not username:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token không có thông tin người dùng"}
                )

            db = SessionLocal()

            try:
                if user_id:
                    user = db.query(User).filter(User.id == user_id).first()
                else:
                    user = db.query(User).filter(User.username == username).first()

                if not user:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Người dùng không tồn tại"}
                    )

                request.state.current_user = user
                request.state.current_user_id = user.id
                request.state.current_username = user.username

            finally:
                db.close()

        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token không hợp lệ hoặc đã hết hạn"}
            )

        return await call_next(request)