"""
API Endpoints para Administración de Tenants, Productos, Órdenes
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Tenant, Product, Order, Client
from pydantic import BaseModel
import jwt
import json
from app.config import config
from typing import Optional, List
import uuid

router = APIRouter(prefix="/admin", tags=["admin"])


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    image_url: Optional[str] = None
    attributes: Optional[dict] = None
    category_id: Optional[str] = None


class TenantResponse(BaseModel):
    id: str
    business_name: str
    plan: str
    monthly_message_limit: int
    products_limit: int
    bot_is_active: bool
    created_at: str


class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    stock: int
    image_url: Optional[str]


class OrderResponse(BaseModel):
    id: str
    client_ci: str
    total_amount: float
    status: str
    payment_status: str
    created_at: str


class ClientResponse(BaseModel):
    ci: str
    full_name: str
    phone: str
    total_orders: int
    total_spent: float
    last_order_at: Optional[str]


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return TenantResponse(
        id=tenant.id,
        business_name=tenant.business_name,
        plan=tenant.plan,
        monthly_message_limit=tenant.monthly_message_limit,
        products_limit=tenant.products_limit,
        bot_is_active=tenant.bot_is_active,
        created_at=tenant.created_at.isoformat() if tenant.created_at else None,
    )


@router.post("/tenants/{tenant_id}/products", response_model=ProductResponse)
async def create_product(tenant_id: str, product: ProductCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    new_product = Product(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        image_url=product.image_url,
        attributes=product.attributes or {},
        category_id=product.category_id,
        is_active=True,
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return ProductResponse(
        id=new_product.id,
        name=new_product.name,
        price=float(new_product.price),
        stock=new_product.stock,
        image_url=new_product.image_url,
    )


@router.get("/tenants/{tenant_id}/products", response_model=List[ProductResponse])
async def list_products(tenant_id: str, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        Product.is_active == True,
    ).offset(skip).limit(limit)
    result = await db.execute(stmt)
    products = result.scalars().all()
    return [
        ProductResponse(
            id=p.id,
            name=p.name,
            price=float(p.price),
            stock=p.stock,
            image_url=p.image_url,
        )
        for p in products
    ]


@router.get("/tenants/{tenant_id}/orders", response_model=List[OrderResponse])
async def list_orders(tenant_id: str, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Order).where(Order.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(Order.status == status)
    stmt = stmt.order_by(Order.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    orders = result.scalars().all()
    return [
        OrderResponse(
            id=o.id,
            client_ci=o.client_ci,
            total_amount=float(o.total_amount),
            status=o.status,
            payment_status=o.payment_status,
            created_at=o.created_at.isoformat() if o.created_at else None,
        )
        for o in orders
    ]


@router.get("/tenants/{tenant_id}/orders/{order_id}")
async def get_order(tenant_id: str, order_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Order).where(
        Order.id == order_id,
        Order.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return {
        "id": order.id,
        "client_ci": order.client_ci,
        "subtotal": float(order.subtotal),
        "tax": float(order.tax),
        "delivery_fee": float(order.delivery_fee),
        "discount": float(order.discount),
        "total_amount": float(order.total_amount),
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_receipt_url": order.payment_receipt_url,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


@router.get("/tenants/{tenant_id}/clients", response_model=List[ClientResponse])
async def list_clients(tenant_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Client).where(Client.tenant_id == tenant_id).order_by(Client.total_spent.desc()).limit(100)
    result = await db.execute(stmt)
    clients = result.scalars().all()
    return [
        ClientResponse(
            ci=c.ci,
            full_name=c.full_name,
            phone=c.phone,
            total_orders=c.total_orders,
            total_spent=float(c.total_spent),
            last_order_at=c.last_order_at.isoformat() if c.last_order_at else None,
        )
        for c in clients
    ]


@router.get("/health")
async def health():
    return {"status": "healthy", "message": "API en línea"}


def _get_token_from_auth_header(authorization: str):
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


async def get_current_user(authorization: str = Header(None)):
    token = _get_token_from_auth_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="No autorizado")
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.get("/tenants/{tenant_id}/stats")
async def tenant_stats(tenant_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # Básicos: productos, órdenes, clientes
    q = text("SELECT COUNT(*) as products FROM products WHERE tenant_id = :tid")
    r = await db.execute(q, {"tid": tenant_id})
    products = r.scalar_one_or_none() or 0

    q = text("SELECT COUNT(*) as orders FROM orders WHERE tenant_id = :tid")
    r = await db.execute(q, {"tid": tenant_id})
    orders = r.scalar_one_or_none() or 0

    q = text("SELECT COUNT(*) as clients FROM clients WHERE tenant_id = :tid")
    r = await db.execute(q, {"tid": tenant_id})
    clients = r.scalar_one_or_none() or 0

    return {"products": int(products), "orders": int(orders), "clients": int(clients)}


@router.get("/tenants/{tenant_id}/charts/weekly-sales")
async def weekly_sales(tenant_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = text("""
        SELECT DATE(created_at) as day, SUM(total_amount) as total
        FROM orders
        WHERE tenant_id = :tid AND created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at) ASC
    """)
    r = await db.execute(q, {"tid": tenant_id})
    rows = [dict(row) for row in r.fetchall()]
    return {"series": rows}


@router.get("/tenants/{tenant_id}/orders/recent")
async def recent_orders(tenant_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = text("SELECT id, client_ci, total_amount, status, created_at FROM orders WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT 20")
    r = await db.execute(q, {"tid": tenant_id})
    rows = [dict(row) for row in r.fetchall()]
    return {"recent": rows}


@router.put("/tenants/{tenant_id}/orders/{order_id}/status")
async def update_order_status(tenant_id: str, order_id: str, status: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = text("UPDATE orders SET status = :status WHERE tenant_id = :tid AND id = :oid")
    await db.execute(q, {"status": status, "tid": tenant_id, "oid": order_id})
    await db.commit()
    return {"ok": True, "order_id": order_id, "status": status}


@router.put("/tenants/{tenant_id}/products/{product_id}")
async def update_product(tenant_id: str, product_id: str, product: ProductCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = text("""
        UPDATE products SET name = :name, description = :description, price = :price, stock = :stock, image_url = :image, attributes = :attributes
        WHERE id = :pid AND tenant_id = :tid
    """)
    await db.execute(q, {"name": product.name, "description": product.description, "price": product.price, "stock": product.stock, "image": product.image_url, "attributes": json.dumps(product.attributes or {}), "pid": product_id, "tid": tenant_id})
    await db.commit()
    return {"ok": True}


@router.delete("/tenants/{tenant_id}/products/{product_id}")
async def delete_product(tenant_id: str, product_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = text("UPDATE products SET is_active = FALSE WHERE id = :pid AND tenant_id = :tid")
    await db.execute(q, {"pid": product_id, "tid": tenant_id})
    await db.commit()
    return {"ok": True}


@router.get("/tenants/{tenant_id}/settings")
async def get_settings(tenant_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = text("SELECT settings FROM tenants WHERE id = :tid")
    r = await db.execute(q, {"tid": tenant_id})
    row = r.first()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    settings = row[0] or '{}'
    try:
        return json.loads(settings)
    except Exception:
        return {}


@router.put("/tenants/{tenant_id}/settings")
async def put_settings(tenant_id: str, payload: dict, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = text("UPDATE tenants SET settings = :settings WHERE id = :tid")
    await db.execute(q, {"settings": json.dumps(payload), "tid": tenant_id})
    await db.commit()
    return {"ok": True}
