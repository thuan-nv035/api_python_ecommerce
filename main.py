import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import Base, engine
from api.products import products_route
from api.user import user_route
from api.middleware import AuthMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(AuthMiddleware)

app.include_router(user_route)
app.include_router(products_route)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
