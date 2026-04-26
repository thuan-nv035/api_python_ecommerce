from urllib.request import Request

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from api.config import SECRET_KEY, ALGORITHM
from database import get_db
from models.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")

def get_admin_user(request: Request):
    current_user = getattr(request.state, "current_user", None)
    print('current', current_user)
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    if getattr(current_user, "role", "user") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )

    return current_user

def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin người dùng",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise credentials_exception

    return user