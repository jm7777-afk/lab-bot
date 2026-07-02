from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from passlib.hash import bcrypt
from app.database import get_db
import uuid
import jwt
import os
from datetime import datetime, timedelta
from app.config import config

router = APIRouter(prefix="/api/public", tags=["public"])

SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str
    business_name: str
    password: str
    industry: str
    tone: str
    custom_instructions: str = ""
    schedule: str = "247"


class RegisterResponse(BaseModel):
    access_token: str
    tenant_id: str
    message: str


PROMPT_TEMPLATES = {
    "restaurante": {
        "formal": "Eres el asistente virtual de {business_name}, un restaurante profesional. Responde de manera formal, cordial y precisa. Ofrece el menú, toma pedidos y coordina entregas.",
        "amigable": "¡Hola! Soy el bot de {business_name}, tu restaurante amigo. Soy cálido, entusiasta y me encanta ayudar a los clientes a elegir sus platos favoritos. Hablo de manera cercana y uso emojis 😊",
        "divertido": "¡Qué onda! Soy el bot más divertido de {business_name} 🎉 Atiendo con chistes, buen humor y mucha energía. Ayudo a pedir comida de manera rápida y divertida.",
        "directo": "Soy el asistente de {business_name}. Respondo de manera rápida y eficiente. Voy al grano: te ayudo a pedir, pagar y recibir tu comida sin rodeos."
    },
    "tienda": {
        "amigable": "¡Bienvenido a {business_name}! Soy tu asistente de compras. Te ayudo a encontrar productos, revisar tallas y colores, y completar tu pedido. ¿En qué puedo ayudarte? 🛍️"
    },
    "servicios": {
        "amigable": "Hola, soy el asistente de {business_name}. Te ayudo a agendar citas, conocer nuestros servicios y resolver tus dudas. ¡Estoy para servirte! ✨"
    },
    "farmacia": {
        "formal": "Bienvenido a {business_name}. Soy el asistente virtual. Proporciono información de medicamentos, horarios y coordino pedidos. Recuerda que mis respuestas no sustituyen consulta médica."
    }
}


def generate_system_prompt(business_name: str, industry: str, tone: str, custom_instructions: str) -> str:
    templates = PROMPT_TEMPLATES.get(industry, PROMPT_TEMPLATES["restaurante"])
    base_prompt = templates.get(tone, templates.get("amigable", ""))
    base_prompt = base_prompt.format(business_name=business_name)

    business_rules = f"""
REGLAS DEL NEGOCIO:
{base_prompt}

INSTRUCCIONES ADICIONALES:
- Siempre saluda al cliente cuando llegue
- Si el cliente quiere comprar, solicita su CÉDULA DE IDENTIDAD (CI) primero
- NO inventes precios, usa SOLO los que están en la base de datos
- Si no sabes algo, deriva a un humano diciendo "Te conectaré con un asesor"
- Procesa pedidos paso a paso: producto → cantidad → confirmar → datos de pago
- Para pagos, proporciona los datos bancarios de la empresa
- Sé rápido y conciso, responde en menos de 200 palabras
- Responde SIEMPRE en español
"""

    if custom_instructions:
        business_rules += f"\nINSTRUCCIONES PERSONALIZADAS:\n{custom_instructions}\n"

    return business_rules


@router.post("/register", response_model=RegisterResponse)
async def register_tenant(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 1. Verificar email
    result = await db.execute(
        text("SELECT id FROM tenants WHERE email = :email"),
        {"email": request.email}
    )
    if result.first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    # 2. Verificar teléfono
    result = await db.execute(
        text("SELECT id FROM tenants WHERE phone_number = :phone"),
        {"phone": request.phone}
    )
    if result.first():
        raise HTTPException(status_code=400, detail="Número de WhatsApp ya registrado")

    # 3. Generar prompt
    system_prompt = generate_system_prompt(
        business_name=request.business_name,
        industry=request.industry,
        tone=request.tone,
        custom_instructions=request.custom_instructions
    )

    # 4. Crear tenant
    tenant_id = str(uuid.uuid4())
    password_hash = bcrypt.hash(request.password)

    await db.execute(
        text("""
            INSERT INTO tenants (id, business_name, phone_number, email, system_prompt, plan)
            VALUES (:id, :name, :phone, :email, :prompt, 'free')
        """),
        {
            "id": tenant_id,
            "name": request.business_name,
            "phone": request.phone,
            "email": request.email,
            "prompt": system_prompt
        }
    )

    # 5. Crear usuario admin
    user_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO tenant_users (id, tenant_id, email, password_hash, full_name, role)
            VALUES (:id, :tenant_id, :email, :password, :name, 'admin')
        """),
        {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": request.email,
            "password": password_hash,
            "name": request.business_name
        }
    )

    await db.commit()

    # 6. Generar token
    token_data = {
        "sub": request.email,
        "tenant_id": tenant_id,
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return RegisterResponse(
        access_token=access_token,
        tenant_id=tenant_id,
        message=f"Empresa {request.business_name} creada exitosamente"
    )


@router.get("/check-email/{email}")
async def check_email(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT id FROM tenants WHERE email = :email"), {"email": email})
    return {"available": result.first() is None}


@router.get("/check-phone/{phone}")
async def check_phone(phone: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT id FROM tenants WHERE phone_number = :phone"), {"phone": phone})
    return {"available": result.first() is None}
