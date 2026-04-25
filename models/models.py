from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ARRAY, func
from database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    avatar = Column(String)

class Products(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    desc = Column(Text)
    # img là mảng các chuỗi (character varying(500)[])
    img = Column(ARRAY(String(500)))
    # categories là kiểu json
    categories = Column(JSON)
    # size và color là mảng (character varying(50)[])
    size = Column(ARRAY(String(50)))
    color = Column(ARRAY(String(50)))
    # price dùng double precision tương ứng Float hoặc Double trong SQLAlchemy
    price = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(Integer)  # ID của người tạo sản phẩm