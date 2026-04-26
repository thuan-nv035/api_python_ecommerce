from sqlalchemy import Column, Integer, String, Text, ARRAY, JSON, Float, DateTime, func, ForeignKey, Boolean, \
    UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    avatar = Column(String)
    role = Column(String(20), default="user")

class Products(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    desc = Column(Text)
    img = Column(ARRAY(String(500)))
    categories = Column(JSON)
    size = Column(ARRAY(String(50)))
    color = Column(ARRAY(String(50)))
    price = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(Integer)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    brand = relationship("Brand")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    quantity = Column(Integer, nullable=False, default=1)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    product = relationship("Products")
    variant = relationship("ProductVariant")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(String(255), nullable=False)
    note = Column(Text)
    total_price = Column(Float, nullable=False, default=0)

    payment_method = Column(String(255), default='cod')
    status = Column(String(255), default='pending')

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    subtotal = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    coupon_code = Column(String(100))

    user = relationship("User")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Float, nullable=False, default=0)
    total_price = Column(Float, nullable=False, default=0)

    product_title = Column(String(255))
    product_img = Column(ARRAY(String(500)))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    variant_sku = Column(String(100))
    variant_size = Column(String(50))
    variant_color = Column(String(50))

    order = relationship("Order", back_populates="items")
    product = relationship("Products")
    variant = relationship("ProductVariant")

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)

    province = Column(String(255), nullable=False)
    district = Column(String(255), nullable=False)
    ward = Column(String(255), nullable=False)
    address_detail = Column(Text, nullable=False)

    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    amount = Column(Float, nullable=False, default=0)

    payment_method = Column(String(50), default="cod")
    payment_status = Column(String(50), default="pending")

    transaction_id = Column(String(255))
    paid_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    order = relationship("Order")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    desc = Column(Text)
    img = Column(String(500))

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    rating = Column(Integer, nullable=False)
    comment = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    product = relationship("Products")

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    product = relationship("Products")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="unique_user_product_wishlist"),
    )

class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)

    code = Column(String(100), unique=True, nullable=False, index=True)
    desc = Column(Text)

    # percent hoặc fixed
    discount_type = Column(String(20), nullable=False, default="percent")

    # Nếu percent: 10 nghĩa là giảm 10%
    # Nếu fixed: 50000 nghĩa là giảm 50.000đ
    discount_value = Column(Float, nullable=False, default=0)

    min_order_value = Column(Float, nullable=False, default=0)

    # Chỉ dùng cho percent, ví dụ giảm tối đa 100.000đ
    max_discount = Column(Float)

    usage_limit = Column(Integer)
    used_count = Column(Integer, default=0)

    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id = Column(Integer, primary_key=True, index=True)

    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    coupon = relationship("Coupon")
    user = relationship("User")
    order = relationship("Order")

    __table_args__ = (
        UniqueConstraint("coupon_id", "user_id", name="unique_coupon_user_usage"),
    )

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)

    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    size = Column(String(50))
    color = Column(String(50))

    quantity = Column(Integer, nullable=False, default=0)
    sold = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    warehouse = relationship("Warehouse")
    product = relationship("Products")
    variant = relationship("ProductVariant")

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    carrier = Column(String(100))  # Ví dụ: GHTK, GHN, Viettel Post
    tracking_code = Column(String(255))

    shipping_fee = Column(Float, nullable=False, default=0)

    status = Column(String(50), default="pending")
    # pending, preparing, shipping, delivered, failed, cancelled

    shipped_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))

    note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    order = relationship("Order")
    user = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    type = Column(String(50), default="system")
    # system, order, payment, shipping, promotion

    is_read = Column(Boolean, default=False)

    related_id = Column(Integer)
    # Có thể là order_id, payment_id, shipment_id...

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

class Banner(Base):
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    subtitle = Column(Text)

    img = Column(String(500), nullable=False)
    link = Column(String(500))

    position = Column(String(50), default="home")
    # home, product, category, sale

    sort_order = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    start_at = Column(DateTime(timezone=True))
    end_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    full_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))

    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    status = Column(String(50), default="pending")
    # pending, processing, resolved, rejected

    admin_reply = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    order = relationship("Order")

class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    sku = Column(String(100), unique=True, index=True)

    size = Column(String(50))
    color = Column(String(50))

    price = Column(Float)
    img = Column(ARRAY(String(500)))

    quantity = Column(Integer, nullable=False, default=0)
    sold = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    product = relationship("Products")

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "size",
            "color",
            name="unique_product_variant_size_color"
        ),
    )

class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)

    reason = Column(Text, nullable=False)
    images = Column(ARRAY(String(500)))

    status = Column(String(50), default="pending")
    # pending, approved, rejected, refunded, cancelled

    admin_note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    order = relationship("Order")
    order_item = relationship("OrderItem")

class ProductQuestion(Base):
    __tablename__ = "product_questions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    question = Column(Text, nullable=False)
    answer = Column(Text)

    status = Column(String(50), default="pending")
    # pending, answered, hidden

    is_public = Column(Boolean, default=True)

    answered_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    answered_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    answered_by = relationship("User", foreign_keys=[answered_by_id])
    product = relationship("Products")

class RecentlyViewedProduct(Base):
    __tablename__ = "recently_viewed_products"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    viewed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    product = relationship("Products")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id",
            name="unique_user_recently_viewed_product"
        ),
    )

class FlashSale(Base):
    __tablename__ = "flash_sales"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    desc = Column(Text)

    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship(
        "FlashSaleItem",
        back_populates="flash_sale",
        cascade="all, delete-orphan"
    )

class FlashSaleItem(Base):
    __tablename__ = "flash_sale_items"

    id = Column(Integer, primary_key=True, index=True)

    flash_sale_id = Column(Integer, ForeignKey("flash_sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    sale_price = Column(Float, nullable=False)
    sale_quantity = Column(Integer, nullable=False, default=0)
    sold = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    flash_sale = relationship("FlashSale", back_populates="items")
    product = relationship("Products")
    variant = relationship("ProductVariant")

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)

    desc = Column(Text)
    logo = Column(String(500))

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ProductCollection(Base):
    __tablename__ = "product_collections"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    desc = Column(Text)

    banner_img = Column(String(500))

    is_active = Column(Boolean, default=True)

    start_at = Column(DateTime(timezone=True))
    end_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship(
        "ProductCollectionItem",
        back_populates="collection",
        cascade="all, delete-orphan"
    )


class ProductCollectionItem(Base):
    __tablename__ = "product_collection_items"

    id = Column(Integer, primary_key=True, index=True)

    collection_id = Column(Integer, ForeignKey("product_collections.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    collection = relationship("ProductCollection", back_populates="items")
    product = relationship("Products")

    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "product_id",
            name="unique_collection_product"
        ),
    )

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    invoice_number = Column(String(100), unique=True, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    subtotal = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    shipping_fee = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0)

    payment_method = Column(String(50), default="cod")
    payment_status = Column(String(50), default="pending")
    # pending, paid, failed, refunded

    status = Column(String(50), default="issued")
    # issued, paid, cancelled, refunded

    note = Column(Text)

    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    order = relationship("Order")

class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    assigned_admin_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    subject = Column(String(255))
    status = Column(String(50), default="open")
    # open, pending, closed

    last_message = Column(Text)
    last_message_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    assigned_admin = relationship("User", foreign_keys=[assigned_admin_id])

    messages = relationship(
        "ChatMessage",
        back_populates="room",
        cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)

    sender_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    sender_type = Column(String(50), nullable=False)
    # user, admin

    message = Column(Text, nullable=False)
    attachments = Column(ARRAY(String(500)))

    is_read_by_user = Column(Boolean, default=False)
    is_read_by_admin = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User")

class ShippingRate(Base):
    __tablename__ = "shipping_rates"

    id = Column(Integer, primary_key=True, index=True)

    province = Column(String(255), nullable=False)
    district = Column(String(255), nullable=True)
    ward = Column(String(255), nullable=True)

    fee = Column(Float, nullable=False, default=0)

    free_shipping_from = Column(Float, nullable=True)

    estimated_delivery = Column(String(100), default="2-4 ngày")

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(String(255))
    tax_code = Column(String(100))
    contact_person = Column(String(100))

    status = Column(String(50), default="active")
    # active, inactive
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)

    phone = Column(String(20))
    address = Column(Text)

    province = Column(String(255))
    district = Column(String(255))
    ward = Column(String(255))

    manager_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    is_active = Column(Boolean, default=True)

    note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    manager = relationship("User")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)

    code = Column(String(100), unique=True, nullable=False, index=True)

    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)

    status = Column(String(50), default="draft")
    # draft, pending, partial_received, received, cancelled

    order_date = Column(DateTime(timezone=True), server_default=func.now())
    expected_date = Column(DateTime(timezone=True))

    subtotal = Column(Float, nullable=False, default=0)
    tax_amount = Column(Float, nullable=False, default=0)
    shipping_fee = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0)

    note = Column(Text)

    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    confirmed_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    received_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")

    created_by = relationship("User", foreign_keys=[created_by_id])
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id])

    items = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)

    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    quantity = Column(Integer, nullable=False, default=1)
    received_quantity = Column(Integer, nullable=False, default=0)

    unit_cost = Column(Float, nullable=False, default=0)
    total_cost = Column(Float, nullable=False, default=0)

    note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Products")
    variant = relationship("ProductVariant")

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)

    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    movement_type = Column(String(50), nullable=False)
    # import, export, adjust, return, transfer

    quantity = Column(Integer, nullable=False)

    before_quantity = Column(Integer, nullable=False, default=0)
    after_quantity = Column(Integer, nullable=False, default=0)

    reference_type = Column(String(100))
    # purchase_order, order, return_request, manual_adjust

    reference_id = Column(Integer)

    note = Column(Text)

    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    warehouse = relationship("Warehouse")
    product = relationship("Products")
    variant = relationship("ProductVariant")
    created_by = relationship("User")

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)

    desc = Column(Text)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)

    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)

    amount = Column(Float, nullable=False, default=0)

    payment_method = Column(String(50), default="cash")
    # cash, bank_transfer, card, other

    status = Column(String(50), default="pending")
    # pending, approved, paid, cancelled

    expense_date = Column(DateTime(timezone=True), server_default=func.now())

    note = Column(Text)

    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    approved_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    approved_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("ExpenseCategory")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)

    desc = Column(Text)

    manager_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    manager = relationship("User")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)

    employee_code = Column(String(100), unique=True, nullable=False, index=True)

    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(Text)

    position = Column(String(255))
    salary = Column(Float, default=0)

    hire_date = Column(DateTime(timezone=True))
    birth_date = Column(DateTime(timezone=True))

    status = Column(String(50), default="active")
    # active, inactive, resigned

    note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    department = relationship("Department")

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)

    desc = Column(Text)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)

    module = Column(String(100))
    desc = Column(Text)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("Role")
    permission = relationship("Permission")

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="unique_role_permission"
        ),
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    role = relationship("Role")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role_id",
            name="unique_user_role"
        ),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    action = Column(String(100), nullable=False)
    # create, update, delete, login, logout, approve, cancel, adjust_stock...

    module = Column(String(100), nullable=False)
    # products, orders, inventory, accounting, hr, supplier...

    resource_type = Column(String(100))
    # Product, Order, PurchaseOrder, Expense...

    resource_id = Column(Integer)

    old_data = Column(JSON)
    new_data = Column(JSON)

    ip_address = Column(String(100))
    user_agent = Column(Text)

    note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")