"""
Modelos ORM para multi-tenant SaaS Bot
"""
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Text, 
    JSON, DECIMAL, Enum, ForeignKey, Index, func
)
from sqlalchemy.dialects.mysql import VARCHAR
from app.database import Base
import uuid
from datetime import datetime


class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_name = Column(String(255), nullable=False)
    commercial_name = Column(String(255))
    rut = Column(String(20), unique=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    
    system_prompt = Column(Text, nullable=False)
    welcome_message = Column(Text)
    bot_temperature = Column(DECIMAL(3,2), default=0.70)
    bot_model = Column(String(50), default="llama3-70b-8192")
    bot_is_active = Column(Boolean, default=True)
    
    payment_info = Column(JSON, nullable=False, default=dict)
    
    plan = Column(String(50), default="free")
    monthly_message_limit = Column(Integer, default=100)
    products_limit = Column(Integer, default=50)
    
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class TenantUser(Base):
    __tablename__ = "tenant_users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Client(Base):
    __tablename__ = "clients"
    
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    ci = Column(String(20), primary_key=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    delivery_address = Column(Text)
    location_lat = Column(DECIMAL(10,8))
    location_lng = Column(DECIMAL(11,8))
    
    tags = Column(JSON, default=list)
    notes = Column(Text)
    total_orders = Column(Integer, default=0)
    total_spent = Column(DECIMAL(12,2), default=0)
    last_order_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    parent_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"))
    icon_url = Column(String(500))
    image_url = Column(String(500))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Product(Base):
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"))
    
    sku = Column(String(100))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(DECIMAL(12,2), nullable=False, default=0)
    compare_at_price = Column(DECIMAL(12,2))
    cost = Column(DECIMAL(12,2), default=0)
    stock = Column(Integer, default=0)
    stock_status = Column(String(20), default="in_stock")
    
    image_url = Column(String(500))
    gallery_urls = Column(JSON, default=list)
    attributes = Column(JSON, default=dict)
    
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    weight = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    client_ci = Column(String(20), nullable=False)
    
    subtotal = Column(DECIMAL(12,2), default=0)
    tax = Column(DECIMAL(12,2), default=0)
    delivery_fee = Column(DECIMAL(12,2), default=0)
    discount = Column(DECIMAL(12,2), default=0)
    total_amount = Column(DECIMAL(12,2), nullable=False, default=0)
    
    status = Column(String(50), default="pending")
    payment_method = Column(String(50))
    payment_status = Column(String(50), default="pending")
    payment_receipt_url = Column(String(500))
    
    delivery_address = Column(Text)
    delivery_lat = Column(DECIMAL(10,8))
    delivery_lng = Column(DECIMAL(11,8))
    scheduled_for = Column(DateTime)
    
    client_notes = Column(Text)
    internal_notes = Column(Text)
    
    channel = Column(String(20), default="whatsapp")
    order_metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    completed_at = Column(DateTime)


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(DECIMAL(12,2), nullable=False)
    total_price = Column(DECIMAL(12,2), nullable=False)
    selected_options = Column(JSON, default=dict)
    
    created_at = Column(DateTime, server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    client_ci = Column(String(20), nullable=False)
    channel = Column(String(20), default="whatsapp")
    
    started_at = Column(DateTime, server_default=func.now())
    last_activity = Column(DateTime, server_default=func.now(), onupdate=func.now())
    message_count = Column(Integer, default=0)
    
    current_intent = Column(String(100))
    current_order_id = Column(String(36), ForeignKey("orders.id"))
    conversation_state = Column(JSON, default=dict)
    
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default="text")
    
    media_url = Column(String(500))
    media_mime_type = Column(String(100))
    
    intent_detected = Column(String(100))
    tokens_used = Column(Integer)
    processing_time_ms = Column(Integer)
    cost_usd = Column(DECIMAL(10,6))
    
    created_at = Column(DateTime, server_default=func.now())


class RAGDocument(Base):
    __tablename__ = "rag_documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    keywords = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())


class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    message_id = Column(String(36), ForeignKey("messages.id"))
    message_type = Column(String(20), default="text")
    model_used = Column(String(50))
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost_usd = Column(DECIMAL(10,6), default=0)
    processing_time_ms = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())


class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"))
    
    endpoint = Column(String(255))
    method = Column(String(10))
    request_headers = Column(JSON)
    request_body = Column(JSON)
    response_status = Column(Integer)
    response_body = Column(Text)
    error_message = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False)
    price_monthly = Column(DECIMAL(10,2), nullable=False)
    price_yearly = Column(DECIMAL(10,2), nullable=False)
    conversations_limit = Column(Integer, nullable=False)
    products_limit = Column(Integer, nullable=False)
    agents_limit = Column(Integer, default=1)
    features = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())


class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=False)
    
    start_date = Column(DateTime, server_default=func.now())
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
