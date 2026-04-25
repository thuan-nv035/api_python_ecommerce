from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "chuoi_bi_mat_cua_rieng_ban_123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # Token có hiệu lực trong 60 phút
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")