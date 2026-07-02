"""
Servicios de Órdenes - Lógica de negocio para gestión de pedidos
"""
import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List
from app.models import Order, OrderItem, Product, Client
from sqlalchemy import select

logger = logging.getLogger(__name__)


class OrderService:
    """Gestión de órdenes y carrito de compras"""
    
    async def create_order(self, db, tenant_id: str, client_ci: str, items: List[Dict]) -> Dict:
        """
        Crear una orden con cálculo automático de totales.
        
        items: [
            {"product_id": "uuid", "quantity": 2, "selected_options": {...}},
            ...
        ]
        """
        try:
            subtotal = Decimal(0)
            order_items = []
            
            # Validar y procesar cada item
            for item in items:
                product_id = item["product_id"]
                quantity = int(item["quantity"])
                
                # Obtener producto
                stmt = select(Product).where(Product.id == product_id)
                result = await db.execute(stmt)
                product = result.scalar_one_or_none()
                
                if not product:
                    return {"error": f"Producto {product_id} no encontrado"}
                
                if product.stock < quantity:
                    return {"error": f"Stock insuficiente de {product.name}"}
                
                item_total = product.price * Decimal(quantity)
                subtotal += item_total
                
                order_item = {
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": float(product.price),
                    "total_price": float(item_total),
                    "selected_options": item.get("selected_options", {})
                }
                order_items.append(order_item)
            
            # Crear orden
            order = Order(
                tenant_id=tenant_id,
                client_ci=client_ci,
                subtotal=float(subtotal),
                tax=0,  # Calcular según configuración del tenant
                delivery_fee=0,  # Calcular según zona
                discount=0,
                total_amount=float(subtotal),
                status="pending",
                payment_status="pending",
                channel="whatsapp"
            )
            
            db.add(order)
            await db.flush()  # Obtener el ID generado
            
            # Agregar items a la orden
            for item_data in order_items:
                order_item_obj = OrderItem(
                    order_id=order.id,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    unit_price=Decimal(str(item_data["unit_price"])),
                    total_price=Decimal(str(item_data["total_price"])),
                    selected_options=item_data["selected_options"]
                )
                db.add(order_item_obj)
            
            await db.commit()
            await db.refresh(order)
            
            logger.info(f"✅ Orden creada: {order.id} - Total: ${order.total_amount}")
            
            return {
                "success": True,
                "order_id": order.id,
                "total": float(order.total_amount),
                "items_count": len(order_items)
            }
        
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creando orden: {str(e)}")
            return {"error": str(e)}
    
    async def get_order_total(self, db, tenant_id: str, items: List[Dict]) -> Dict:
        """Calcular total de una orden sin crearla (para preview)"""
        try:
            subtotal = Decimal(0)
            
            for item in items:
                stmt = select(Product).where(Product.id == item["product_id"])
                result = await db.execute(stmt)
                product = result.scalar_one_or_none()
                
                if product:
                    subtotal += product.price * Decimal(item["quantity"])
            
            return {
                "subtotal": float(subtotal),
                "tax": 0,
                "delivery_fee": 0,
                "total": float(subtotal)
            }
        except Exception as e:
            logger.error(f"Error calculando total: {str(e)}")
            return {"error": str(e)}


order_service = OrderService()
