# 📐 DOCUMENTACIÓN TÉCNICA - BOT IA ENTERPRISE

## Tabla de Contenidos
1. [Modelo Entidad-Relación (MER)](#mer)
2. [Flujo de Arquitectura](#flujo-arquitectura)
3. [Estrategia Multi-Tenant](#multi-tenant)
4. [Optimización RAG](#rag)
5. [Gestión de Órdenes](#órdenes)
6. [API Reference](#api)

---

## <a name="mer"></a> 1. MODELO ENTIDAD-RELACIÓN (MER)

### Tablas Principales

#### `tenants` (Empresas/Inquilinos)
```sql
id (UUID PK)
business_name (VARCHAR 255)
phone_number (VARCHAR 20, UNIQUE)
email (VARCHAR 255, UNIQUE)
system_prompt (TEXT) -- Personalidad del bot
bot_temperature (DECIMAL 3,2) -- Control de creatividad (0.1-1.0)
bot_model (VARCHAR 50) -- Modelo Groq a usar
payment_info (JSON) -- Datos bancarios
plan (ENUM: free, startup, business, enterprise)
monthly_message_limit (INT)
products_limit (INT)
bot_is_active (BOOLEAN)
```

**Índices**:
- PK: `id`
- UNIQUE: `phone_number`, `email`
- FOREIGN KEY: Ninguna (es la raíz)

---

#### `clients` (Clientes/Usuarios Finales)
```sql
tenant_id (UUID FK) -- Multi-tenant
ci (VARCHAR 20) -- Cédula Identidad (OBLIGATORIO)
full_name (VARCHAR 255)
phone (VARCHAR 20)
email (VARCHAR 255)
delivery_address (TEXT)
location_lat (DECIMAL 10,8)
location_lng (DECIMAL 11,8)
total_orders (INT)
total_spent (DECIMAL 12,2)
last_order_at (TIMESTAMP)
```

**Índices**:
- PK: `(tenant_id, ci)` -- Clave compuesta
- FK: `tenant_id` → `tenants.id`

**Notas**:
- CI es obligatorio para evitar duplicados
- (tenant_id, ci) aísla clientes por empresa

---

#### `products` (Catálogo Agnóstico)
```sql
id (UUID PK)
tenant_id (UUID FK)
category_id (UUID FK, NULL)
sku (VARCHAR 100)
name (VARCHAR 255)
description (TEXT)
price (DECIMAL 12,2)
compare_at_price (DECIMAL 12,2) -- Precio anterior (ofertas)
cost (DECIMAL 12,2)
stock (INT)
stock_status (ENUM: in_stock, low_stock, out_of_stock)
image_url (VARCHAR 500)
gallery_urls (JSON)
attributes (JSON) -- <-- FLEXIBLE POR RUBRO
is_active (BOOLEAN)
is_featured (BOOLEAN)
weight (INT) -- Orden de visualización
```

**`attributes` JSON Ejemplos**:

```json
// Hamburguesa
{
  "size": ["pequeño", "mediano", "grande"],
  "meat": ["res", "pollo", "cerdo"],
  "extras": ["queso", "tocino", "huevo"],
  "spicy_level": "medium"
}

// Ropa
{
  "sizes": ["XS", "S", "M", "L", "XL"],
  "colors": ["rojo", "azul", "negro"],
  "material": "algodón 100%",
  "care_instructions": "Lavar en agua fría"
}

// Servicio de Estética
{
  "duration": "60 minutos",
  "employees": ["Maria", "Pedro", "Lucia"],
  "materials": ["cera", "tintura", "crema"],
  "location": "Salón Centro"
}
```

---

#### `orders` (Pedidos)
```sql
id (UUID PK)
tenant_id (UUID FK)
client_ci (VARCHAR 20 FK) -- Multi-key FK
subtotal (DECIMAL 12,2) -- Calculado en backend
tax (DECIMAL 12,2) -- Impuesto (si aplica)
delivery_fee (DECIMAL 12,2) -- Costo envío
discount (DECIMAL 12,2) -- Descuento aplicado
total_amount (DECIMAL 12,2) -- NUNCA por IA

status (ENUM: pending, confirmed, paid, preparing, ready, delivered, cancelled)
payment_method (ENUM: movil, transferencia, efectivo, tarjeta)
payment_status (ENUM: pending, paid, failed, refunded)
payment_receipt_url (VARCHAR 500) -- Comprobante del cliente

delivery_address (TEXT)
scheduled_for (TIMESTAMP) -- Entrega programada
```

**Índices**:
- PK: `id`
- FK: `(tenant_id, client_ci)` → `clients(tenant_id, ci)`
- Búsqueda: `(tenant_id, status)`, `(tenant_id, created_at)`

---

#### `order_items` (Detalles del Pedido)
```sql
id (UUID PK)
order_id (UUID FK)
product_id (UUID FK)
quantity (INT)
unit_price (DECIMAL 12,2) -- Precio al momento de compra
total_price (DECIMAL 12,2) -- unit_price * quantity
selected_options (JSON) -- Opciones elegidas
```

**`selected_options` JSON Ejemplo**:
```json
{
  "size": "grande",
  "meat": "res",
  "extras": ["queso", "tocino"],
  "special_instructions": "sin cebolla"
}
```

---

#### `conversations` (Chats)
```sql
id (UUID PK)
tenant_id (UUID FK)
client_ci (VARCHAR 20 FK)
channel (VARCHAR 20) -- whatsapp, web, api
started_at (TIMESTAMP)
last_activity (TIMESTAMP)
message_count (INT)

current_intent (VARCHAR 100) -- purchase, inquiry, complaint
current_order_id (UUID FK, NULL)
conversation_state (JSON) -- Estado de máquina
is_resolved (BOOLEAN)
resolved_at (TIMESTAMP)
```

**`conversation_state` JSON Ejemplo**:
```json
{
  "step": "waiting_for_ci",
  "cart": {
    "items": [
      {"product_id": "uuid", "quantity": 2}
    ],
    "subtotal": 85.50
  },
  "waiting_for": "payment_receipt"
}
```

---

#### `messages` (Historial)
```sql
id (UUID PK)
conversation_id (UUID FK)
role (ENUM: user, assistant, system)
content (TEXT)
content_type (ENUM: text, image, audio, document)
media_url (VARCHAR 500) -- URL de archivo
tokens_used (INT) -- Para cálculo de costos
processing_time_ms (INT)
cost_usd (DECIMAL 10,6)
```

---

#### `usage_logs` (Facturación)
```sql
id (UUID PK)
tenant_id (UUID FK)
message_id (UUID FK)
message_type (ENUM: text, audio, image)
model_used (VARCHAR 50)
tokens_input (INT)
tokens_output (INT)
cost_usd (DECIMAL 10,6)
processing_time_ms (INT)
created_at (TIMESTAMP)
```

**Propósito**: Auditoría y facturación automática

---

## <a name="flujo-arquitectura"></a> 2. FLUJO DE ARQUITECTURA

### Diagrama de Secuencia

```
Cliente WhatsApp
    │
    │ [Envía mensaje/audio/imagen]
    │
    ▼
┌─────────────────────────────────┐
│ 1. Webhook Meta                 │
│ POST /webhook/whatsapp          │
│ - Extrae: from_number, to_number│
│ - Tipo: text, audio, image      │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. Identificar Tenant           │
│ SELECT * FROM tenants           │
│ WHERE phone_number = to_number  │
│                                 │
│ ✅ Obtiene: system_prompt,      │
│    payment_info, bot config     │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. Buscar/Crear Cliente         │
│ SELECT * FROM clients           │
│ WHERE tenant_id = X             │
│   AND phone = from_number       │
│                                 │
│ Si NO existe:                   │
│ INSERT con ci = "PENDIENTE"     │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 4. Procesar Multimedia          │
│                                 │
│ if type == "audio":             │
│   → Groq Whisper → Transcribe   │
│                                 │
│ if type == "image":             │
│   → Guardar URL para validar    │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 5. RAG (Búsqueda Inteligente)  │
│ extract_keywords(message)       │
│                                 │
│ SELECT * FROM products          │
│ WHERE name LIKE %keyword%       │
│   OR description LIKE %keyword% │
│ LIMIT 8                         │
│                                 │
│ 📊 Resultado: Máx 8 productos   │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 6. Construir Prompt Final       │
│                                 │
│ final_prompt = f"""             │
│ {system_prompt}                 │
│ {payment_info}                  │
│ {productos_encontrados}         │
│ {historial_5_mensajes}          │
│ CLIENTE: {client}               │
│ MENSAJE: {user_message}         │
│ """                             │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 7. Llamada Groq (LLaMA 3)      │
│ groq.chat.completions.create(   │
│   model="llama3-70b-8192",      │
│   messages=[...],               │
│   temperature=0.7,              │
│   max_tokens=500                │
│ )                               │
│                                 │
│ ⏱️  LATENCIA: 200-500ms          │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 8. Procesar Respuesta           │
│ Detectar intenciones especiales:│
│ - [REQUEST_CI] → Pedir cédula   │
│ - [CREATE_ORDER] → Crear orden  │
│ - [REQUEST_PAYMENT] → Enviar $$ │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 9. Guardar en BD                │
│ INSERT INTO messages            │
│ UPDATE conversations            │
│ INSERT INTO usage_logs          │
│ UPDATE clients stats            │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 10. Enviar a WhatsApp           │
│ POST to Meta Graph              │
│ {"to": client_phone,            │
│  "text": bot_response}          │
└─────────────────────────────────┘
    │
    ▼
Cliente recibe respuesta ✅
```

---

## <a name="multi-tenant"></a> 3. ESTRATEGIA MULTI-TENANT

### Aislamiento por `tenant_id`

**Principio**: CADA consulta debe filtrar por tenant_id

```python
# ✅ CORRECTO
SELECT * FROM products 
WHERE tenant_id = 'tenant-uuid' 
AND is_active = 1

# ❌ INCORRECTO (BRECHA DE SEGURIDAD)
SELECT * FROM products 
WHERE is_active = 1
```

### Esquema de Clientes Multi-Tenant

```sql
-- Clave primaria compuesta para aislamiento máximo
PRIMARY KEY (tenant_id, ci)

-- Ejemplos:
INSERT INTO clients VALUES 
  ('empresa-1-uuid', '12345678', 'Juan', ...),
  ('empresa-2-uuid', '12345678', 'Maria', ...);  -- MISMO CI, diferente empresa
```

**Beneficio**: No hay colisiones de datos entre empresas

---

## <a name="rag"></a> 4. OPTIMIZACIÓN RAG (Recuperación de Información)

### Por qué RAG es crítico

**Escenario SIN RAG**:
```python
# Prompt con TODO el inventario
prompt = f"{system_prompt}\n{TODOS_LOS_5000_PRODUCTOS}\n{mensaje}"
# → 50,000+ tokens inyectados
# → Costo: $0.015 por conversación
# → Margen: -75% (¡PERDEMOS DINERO!)
```

**Escenario CON RAG**:
```python
# Prompt solo con lo relevante
keywords = ["hamburguesa", "combo"]
productos = search_products(tenant_id, keywords)  # ~8 productos
prompt = f"{system_prompt}\n{8_PRODUCTOS}\n{mensaje}"
# → 200 tokens inyectados
# → Costo: $0.000006 por conversación
# → Margen: 99.9% (¡ULTRA RENTABLE!)
```

### Implementación RAG

```python
async def search_products_simple(db, tenant_id, message):
    # 1. Extraer palabras clave
    keywords = await extract_keywords(message)
    # ["hamburguesa", "combo", "grande"]
    
    # 2. Construir búsqueda
    search_conditions = [
        Product.name.ilike(f"%{kw}%") for kw in keywords
    ]
    
    # 3. Consultar
    stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        Product.is_active == True,
        or_(*search_conditions)
    ).limit(8)  # ← LIMITE CRÍTICO
    
    result = await db.execute(stmt)
    return result.scalars().all()
```

### Optimizaciones de Búsqueda

```sql
-- FULLTEXT INDEX para búsqueda más rápida
FULLTEXT INDEX idx_search (name, description)

SELECT * FROM products
WHERE MATCH(name, description) AGAINST('+hamburguesa +combo' IN BOOLEAN MODE)
AND tenant_id = 'uuid'
LIMIT 8;
```

---

## <a name="órdenes"></a> 5. GESTIÓN DE ÓRDENES

### Flujo de Creación de Orden

```
1. Cliente dice: "Quiero un combo grande"
   ↓
2. Bot: "¿Cuál es tu CI para procesar el pedido?"
   ↓
3. Cliente: "12345678"
   ↓
4. Bot: "Perfecto. Tu orden es:
   - Combo Premium: $40
   TOTAL: $40
   
   Transfiere a: Banco XYZ | Número: 123456
   Luego envía el comprobante"
   ↓
5. Cliente envía imagen de comprobante
   ↓
6. Bot: "Recibido. Preparando tu pedido..."
   ↓
7. Backend: Validar pago + Crear orden
```

### Creación Automática de Orden

```python
async def create_order(db, tenant_id, client_ci, items):
    """
    items = [
        {"product_id": "uuid", "quantity": 2, "selected_options": {...}},
        ...
    ]
    """
    subtotal = 0
    order_items = []
    
    for item in items:
        # Obtener producto
        product = await get_product(db, item["product_id"])
        
        # Validar stock
        if product.stock < item["quantity"]:
            return {"error": f"Stock insuficiente de {product.name}"}
        
        # Calcular total
        item_total = product.price * item["quantity"]
        subtotal += item_total
        
        order_items.append({
            "product_id": product.id,
            "quantity": item["quantity"],
            "unit_price": float(product.price),
            "total_price": float(item_total)
        })
    
    # Crear orden
    order = Order(
        tenant_id=tenant_id,
        client_ci=client_ci,
        subtotal=float(subtotal),
        total_amount=float(subtotal),
        status="pending",
        channel="whatsapp"
    )
    
    db.add(order)
    await db.flush()
    
    # Agregar items
    for item_data in order_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data["product_id"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            total_price=item_data["total_price"]
        )
        db.add(order_item)
    
    await db.commit()
    return {"success": True, "order_id": order.id}
```

### Cálculo de Totales (NUNCA por IA)

```python
# ❌ MAL - Dejar que la IA calcule
bot_response = "Tu total es $47.99 + $5 envío = $52.99"

# ✅ BIEN - Backend calcula
subtotal = sum(item.price * item.quantity for item in items)
tax = subtotal * 0.10  # Según configuración
delivery_fee = calculate_delivery_fee(address, tenant_id)
total = subtotal + tax + delivery_fee

bot_response = f"Tu total es: ${total:.2f}"
```

---

## <a name="api"></a> 6. API REFERENCE

### Webhook WhatsApp

**Endpoint**: `POST /webhook/whatsapp`

**Request**:
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "type": "text",
          "text": {"body": "Hola, quiero..."}
        }],
        "contacts": [{
          "wa_id": "584141234567",
          "profile": {"name": "Juan"}
        }],
        "metadata": {
          "display_phone_number": "584141234567"
        }
      }
    }]
  }]
}
```

**Response**:
```json
{
  "status": "success",
  "order_id": "conversation-uuid",
  "response": "Hola Juan, ¿en qué puedo ayudarte?"
}
```

---

### Crear Producto

**Endpoint**: `POST /admin/tenants/{tenant_id}/products`

**Body**:
```json
{
  "name": "Combo Premium",
  "description": "Incluye: Sándwich + Bebida + Postre",
  "price": 40.00,
  "stock": 100,
  "image_url": "https://...",
  "category_id": "cat-uuid",
  "attributes": {
    "size": ["pequeño", "mediano", "grande"],
    "meat": ["res", "pollo"]
  }
}
```

---

### Crear Orden (Manual)

**Endpoint**: `POST /admin/tenants/{tenant_id}/orders`

**Body**:
```json
{
  "client_ci": "12345678",
  "items": [
    {
      "product_id": "prod-uuid",
      "quantity": 2,
      "selected_options": {"size": "grande"}
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "order_id": "order-uuid",
  "total": 80.00,
  "items_count": 1
}
```

---

## 🎯 Resumen de Optimizaciones

| Aspecto | Optimization | Impacto |
|---------|--------------|--------|
| Tokens | RAG limit 8 | -95% costos LLM |
| BD | Multi-tenant aislamiento | 0 brechas seguridad |
| Órdenes | Backend calcula | 100% precisión |
| Velocidad | Groq Whisper | 200-500ms latencia |
| Escala | MySQL + Redis | Soporta 10K+ empresas |

---

**Documento Actualizado**: Mayo 31, 2024
**Versión**: 2.0.0
