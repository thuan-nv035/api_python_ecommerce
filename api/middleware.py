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
                (
                        path.startswith("/api/products")
                        and method in ["POST", "PUT", "PATCH", "DELETE"]
                )
                or (
                        path.startswith("/api/categories")
                        and method in ["POST", "PUT", "PATCH", "DELETE"]
                )
                or (
                        path.startswith("/api/coupons")
                        and method in ["POST", "PUT", "PATCH", "DELETE"]
                )
                or (
                        path.startswith("/api/banners")
                        and method in ["POST", "PUT", "PATCH", "DELETE"]
                )
                or (
                        path.startswith("/api/support")
                        and not (path in ["/api/support", "/api/support/"] and method == "POST")
                )
                or (
                        path.startswith("/api/product-variants")
                        and method in ["POST", "PUT", "PATCH", "DELETE"]
                )
                or (
                        path.startswith("/api/product-questions")
                        and not (
                        method == "GET"
                        and path.startswith("/api/product-questions/product/")
                    )
                )
                or (
                        path.startswith("/api/flash-sales")
                        and method in ["POST", "PUT", "PATCH", "DELETE"]
                )
                or (
                        path.startswith("/api/brands")
                        and method in ["POST", "PUT", "PATCH", "DELETE"]
                )
                or (
                        path.startswith("/api/product-collections")
                        and not (
                        method == "GET"
                        and (
                                path == "/api/product-collections/active"
                                or path.startswith("/api/product-collections/slug/")
                        )
                    )
                )
                or (
                        path.startswith("/api/shipping-fee")
                        and not (
                        path == "/api/shipping-fee/calculate"
                        and method == "POST"
                )
                )
                or path.startswith("/api/cart")
                or path.startswith("/api/orders")
                or path.startswith("/api/addresses")
                or path.startswith("/api/reviews/my")
                or path.startswith("/api/wishlist")
                or path.startswith("/api/profile")
                or path.startswith("/api/payments")
                or path.startswith("/api/admin")
                or path.startswith("/api/inventory")
                or path.startswith("/api/shipments")
                or path.startswith("/api/notifications")
                or path.startswith("/api/uploads")
                or path.startswith("/api/reports")
                or path.startswith("/api/returns")
                or path.startswith("/api/reviews/my")
                or path.startswith("/api/invoices")
                or path.startswith("/api/chat")
                or path.startswith("/api/suppliers")
                or path.startswith("/api/warehouses")
                or path.startswith("/api/purchase-orders")
                or path.startswith("/api/stock-movements")
                or path.startswith("/api/expenses")
                or path.startswith("/api/expense-categories")
                or path.startswith("/api/accounting")
                or path.startswith("/api/departments")
                or path.startswith("/api/employees")
                or path.startswith("/api/roles")
                or path.startswith("/api/permissions")
                or path.startswith("/api/me/permissions")
                or (
                        path.startswith("/api/users")
                        and "/roles" in path
                )
                or path.startswith("/api/audit-logs")
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