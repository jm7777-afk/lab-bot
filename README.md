# 🤖 BOT IA ENTERPRISE - Plataforma SaaS Multi-tenant

**Plataforma tecnológica altamente rentable, escalable y agnóstica para automatizar 90% de la atención al cliente mediante un bot configurable para WhatsApp.**

---

## 📋 Tabla de Contenidos

1. [Características](#características)
2. [Arquitectura](#arquitectura)
3. [Instalación](#instalación)
4. [Configuración](#configuración)
5. [API Endpoints](#api-endpoints)
6. [Monetización](#monetización)
7. [Flujo del Mensaje](#flujo-del-mensaje)

---

## ✨ Características

### 🏢 Multi-Tenant
- Aislamiento completo de datos por `tenant_id`
- Cada empresa tiene su propio bot, configuraciones y clientes
- Escalabilidad horizontal

### 🚀 Bajo Costo Marginal
- Onboarding 100% automático (Product-Led Growth)
- Mínimo soporte técnico requerido
- Infraestructura compartida

### 💰 Optimización de Tokens (RAG)
- Búsqueda inteligente de productos
- Solo inyecta información relevante al LLM
- Reducción de costos hasta 80% vs enviar todo el inventario

### 📱 Capacidades Multimedia
- **Entrada**: Recibe audios, imágenes, comprobantes de pago
- **Salida**: Envía imágenes de productos dinámicamente
- **Audio**: Transcripción ultra-rápida con Whisper (Groq)

### 🛒 Gestión de Órdenes
- Carrito de compras automático
- Cálculo de totales en backend (NO por IA)
- Validación obligatoria de CI
- Procesamiento de comprobantes de pago

---

## 🏗️ Arquitectura

### Tech Stack
- **Backend**: FastAPI (Python 3.11+) - Async/Await
- **Database**: MySQL 8.0+ (InnoDB, ACID)
- **IA**: Groq (LLaMA 3 + Whisper)
- **Cache**: Redis
- **Docker**: Docker Compose

### Estructura Base de Datos (MySQL)

```
Tenants (Empresas)
  ├─ Clients (Clientes con CI)
  ├─ Products (Catálogo agnóstico con JSON)
  ├─ Orders & Order_Items (Pedidos + Ítems)
  ├─ Conversations (Chats)
  ├─ Messages (Historial)
  ├─ RAG_Documents (Para búsqueda semántica)
  └─ Usage_Logs (Facturación)
```

### Flujo de Datos

```
[WhatsApp] 
  → Webhook (POST /webhook/whatsapp)
  → Identificar Tenant
  → Buscar/Crear Cliente
  → RAG (Búsqueda de productos)
  → Construir Prompt
  → Groq LLaMA 3
  → Procesar Respuesta
  → Actualizar BD
  → Enviar a WhatsApp
```

---

## 🚀 Instalación

### Opción 1: Docker Compose (Recomendado)

```bash
# 1. Clonar/crear proyecto
git clone <repo>
cd bot-enterprise

# 2. Configurar .env
cp .env.example .env
# Editar: GROQ_API_KEY, META_ACCESS_TOKEN, etc

# 3. Levantar servicios
docker-compose up -d

# 4. Verificar
curl http://localhost:8000/health
```

### Opción 2: Local Development

```bash
# 1. Instalar Python 3.11+
python --version

# 2. Crear virtual env
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar MySQL local
# - Crear BD: bot_enterprise
# - Ejecutar: schema.sql

# 5. Configurar .env
cp .env.example .env

# 6. Ejecutar
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ⚙️ Configuración

### Variables de Entorno (.env)

```env
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=botuser
MYSQL_PASSWORD=botpass
MYSQL_DATABASE=bot_enterprise

# Groq (LLaMA 3 + Whisper)
GROQ_API_KEY=gsk_xxxxx
GROQ_MODEL=llama3-70b-8192

# WhatsApp Meta
META_ACCESS_TOKEN=EAAV...
META_PHONE_NUMBER_ID=123456789
WHATSAPP_VERIFY_TOKEN=1234

# Security
SECRET_KEY=your-random-secret-key
ALGORITHM=HS256

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Crear Primer Tenant (Empresa)

```sql
INSERT INTO tenants (
  id, business_name, phone_number, email,
  system_prompt, payment_info, plan
) VALUES (
  UUID(),
  'Mi Tienda',
  '584141234567',
  'admin@mitienda.com',
  'Eres un asistente amable que vende productos...',
  JSON_OBJECT(
    'bank', 'Banco XYZ',
    'account_number', '12345678',
    'owner_name', 'Juan Pérez',
    'owner_ci', '12345678',
    'phone', '584141234567',
    'instructions', 'Pago Móvil o Transferencia'
  ),
  'business'
);
```

---

## 📡 API Endpoints

### Webhook WhatsApp

**POST** `/webhook/whatsapp`
- Recibe mensajes de WhatsApp
- Procesa: texto, audio, imágenes
- Retorna: JSON con estado

**GET** `/webhook/whatsapp`
- Verifica webhook con Meta

### Admin API

**GET** `/admin/tenants/{tenant_id}`
- Obtener detalles del tenant

**POST** `/admin/tenants/{tenant_id}/products`
- Crear producto

**GET** `/admin/tenants/{tenant_id}/products`
- Listar productos

**POST** `/admin/tenants/{tenant_id}/orders`
- Crear orden

**GET** `/admin/tenants/{tenant_id}/orders`
- Listar órdenes del tenant

**GET** `/admin/tenants/{tenant_id}/clients`
- Listar clientes

**GET** `/health`
- Health check

---

## 💰 Monetización

### Planes de Suscripción

| Plan | Mensual | Conversaciones/mes | Productos | Ideal para |
|------|---------|-------------------|-----------|-----------|
| **Free** | $0 | 100 | 20 | Pruebas |
| **Startup** | $49 | 1,000 | 200 | Negocios pequeños |
| **Business** | $199 | 5,000 | 1,000 | Crecimiento |
| **Enterprise** | $499+ | Ilimitado | Ilimitado | Grandes empresas |

### Economía de Costos

```
Costo por mensaje (Groq LLaMA 3): ~$0.0000003
Margen por conversación (plan Business): 88%

Ejemplo:
- Cliente paga: $0.04 por conversación (en $199/5000)
- Groq cuesta: $0.000005 por conversación
- Margen: 99.8%
```

---

## 🔄 Flujo del Mensaje (Detallado)

### 1️⃣ Webhook de WhatsApp Recibido

```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "type": "text",
          "text": {"body": "Hola, quiero un combo..."}
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

### 2️⃣ Identificar Tenant
```sql
SELECT * FROM tenants WHERE phone_number = '584141234567'
```

### 3️⃣ Buscar/Crear Cliente
```sql
SELECT * FROM clients 
WHERE tenant_id = 'uuid' AND phone = '584141234567'
```

### 4️⃣ RAG - Búsqueda de Productos

```python
keywords = extract_keywords("combo hamburguesa")
# ["combo", "hamburguesa"]

SELECT * FROM products 
WHERE tenant_id = 'uuid'
AND (name LIKE '%combo%' OR description LIKE '%hamburguesa%')
LIMIT 8
```

### 5️⃣ Construir Prompt

```python
prompt = f"""
{system_prompt}

DATOS DE PAGO:
- Banco: {payment_info['bank']}
- Número: {payment_info['account_number']}

PRODUCTOS DISPONIBLES:
• Combo Básico - $25 (✅ En stock)
• Combo Premium - $40 (✅ En stock)

HISTORIAL:
👤 Cliente: Hola, quiero un combo
🤖 Bot: Tenemos dos opciones...

CLIENTE: Juan (CI: Pendiente)
MENSAJE: Quiero el combo premium

RESPUESTA:
"""
```

### 6️⃣ Llamada a Groq (Ultra-rápida)

```python
response = groq.chat.completions.create(
    model="llama3-70b-8192",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    max_tokens=500
)
```

### 7️⃣ Procesar Respuesta

```
Bot dice: "Perfecto, te ofrezco el combo premium por $40. 
¿Cuál es tu Cédula de Identidad para procesar el pedido?"

Sistema detecta: [REQUEST_CI] - Estado = "waiting_for_ci"
```

### 8️⃣ Guardar BD + Enviar WhatsApp

```python
INSERT INTO messages (...) VALUES (...)
UPDATE conversations SET last_activity = NOW()
await whatsapp_service.send_text(to_number, bot_response)
```

---

## 📊 Casos de Uso

### 🍔 Hamburguesería
- **Productos**: Combos, sándwiches, bebidas
- **Atributos JSON**: `{"size": "grande", "meat": "res", "extras": ["queso"]}`

### 👕 Tienda de Ropa
- **Productos**: Prendas por categoría
- **Atributos JSON**: `{"size": "M", "color": "azul", "material": "algodón"}`

### 💇 Estética/Salón
- **Productos**: Servicios
- **Atributos JSON**: `{"duration": "60min", "employee": "Maria", "materials": ["cera"]}`

---

## 🛠️ Desarrollo

### Agregar Nuevo Endpoint

```python
# app/api/admin.py

@router.post("/tenants/{tenant_id}/invoices")
async def create_invoice(tenant_id: str, db: AsyncSession = Depends(get_db)):
    """Crear factura"""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404)
    
    # Tu lógica aquí
    return {"message": "Factura creada"}
```

### Logs

```bash
# Ver logs de contenedor
docker-compose logs -f app

# Ver logs de MySQL
docker-compose logs -f mysql
```

### Debugging

```bash
# Ejecutar sin Docker
uvicorn app.main:app --reload --log-level debug

# MySQL CLI
mysql -h localhost -u botuser -p bot_enterprise
```

---

## 📈 Escalabilidad

### Replicación MySQL
```sql
-- En servidor esclavo
CHANGE MASTER TO
  MASTER_HOST='primary.server',
  MASTER_USER='replication',
  MASTER_PASSWORD='password';
```

### Load Balancing
- Nginx / HAProxy en frente de múltiples instancias de app
- Redis Cluster para sesiones

### Particionamiento de BD
```sql
ALTER TABLE messages PARTITION BY RANGE (YEAR(created_at)) (
  PARTITION p2024 VALUES LESS THAN (2025),
  PARTITION p2025 VALUES LESS THAN (2026)
);
```

---

## 🚨 Seguridad

- ✅ Aislamiento multi-tenant por `tenant_id`
- ✅ JWT para autenticación
- ✅ HTTPS en producción
- ✅ Rate limiting por usuario
- ✅ Validación de CI para pedidos

---

## 📞 Soporte

Para soporte técnico o preguntas: support@botenterprise.com

---

## 📄 Licencia

Propietario - © 2024 Bot IA Enterprise

---

**Construido con ❤️ usando FastAPI, MySQL y Groq**
