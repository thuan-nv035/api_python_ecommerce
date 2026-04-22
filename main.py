import uvicorn
from fastapi import FastAPI

from api.user import user_route

app = FastAPI()

app.include_router(user_route)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
