import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from api.brands import brands_route
from api.chat import chat_route
from api.flash_sales import flash_sales_route
from api.invoices import invoices_route
from api.product_collections import product_collections_route
from api.product_questions import product_questions_route
from api.product_variants import product_variants_route
from api.recently_viewed import recently_viewed_route
from api.reports import reports_route
from api.returns import returns_route
from api.shipping_fee import shipping_fee_route
from database import Base, engine

from api.banners import banners_route
from api.inventory import inventory_route
from api.notifications import notifications_route
from api.shipments import shipments_route
from api.support import support_route
from api.uploads import uploads_route
from api.addresses import addresses_route
from api.admin import admin_route
from api.categories import categories_route
from api.coupons import coupons_route
from api.orders import orders_route
from api.payments import payments_route
from api.profile import profile_route
from api.reviews import reviews_route
from api.wishlist import wishlist_route
from api.user import user_route
from api.products import products_route
from api.cart import cart_route
from api.middleware import AuthMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(AuthMiddleware)
app.include_router(orders_route)
app.include_router(user_route)
app.include_router(products_route)
app.include_router(cart_route)
app.include_router(addresses_route)
app.include_router(categories_route)
app.include_router(reviews_route)
app.include_router(wishlist_route)
app.include_router(profile_route)
app.include_router(payments_route)
app.include_router(admin_route)
app.include_router(coupons_route)
app.include_router(inventory_route)
app.include_router(shipments_route)
app.include_router(notifications_route)
app.include_router(uploads_route)
app.include_router(banners_route)
app.include_router(support_route)
app.include_router(reports_route)
app.include_router(product_variants_route)
app.include_router(returns_route)
app.include_router(product_questions_route)
app.include_router(recently_viewed_route)
app.include_router(flash_sales_route)
app.include_router(brands_route)
app.include_router(product_collections_route)
app.include_router(invoices_route)
app.include_router(chat_route)
app.include_router(shipping_fee_route)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
