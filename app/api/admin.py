import json
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import AdminUser, Company
from app.models.conversation import Conversation, Message

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "mi_clave_secreta_123456")
ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class CompanyCreate(BaseModel):
    name: str
    plan: str = "free"
    settings: dict | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None
    is_active: bool | None = None
    settings: dict | None = None


class BotConfigUpdate(BaseModel):
    system_prompt: str | None = None
    temperature: float | None = None
    model: str | None = None
    max_context_messages: int | None = None
    rate_limit_per_user: int | None = None
    is_running: bool | None = None
    welcome_message: str | None = None


class CompanyItem(BaseModel):
    id: int
    uuid: str
    name: str
    plan: str
    is_active: bool
    settings: dict
    created_at: str | None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.verify(plain_password, hashed_password)


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=8))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


def safe_get_settings(company: Company) -> dict:
    try:
        return json.loads(company.settings or "{}")
    except Exception:
        return {}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return TokenResponse(access_token=access_token, role=user.role, name=user.email.split("@")[0])


@router.get("/me")
async def get_me(current_admin: AdminUser = Depends(get_current_admin)):
    return {"email": current_admin.email, "role": current_admin.role, "company_id": current_admin.company_id}


@router.get("/companies")
async def get_companies(page: int = 1, limit: int = 100, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    if current_admin.role == "super_admin":
        query = db.query(Company)
    else:
        query = db.query(Company).filter(Company.id == current_admin.company_id)

    total = query.count()
    companies = query.order_by(desc(Company.created_at)).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [
            {
                "id": company.id,
                "uuid": company.uuid,
                "name": company.name,
                "plan": company.plan,
                "is_active": company.is_active,
                "settings": safe_get_settings(company),
                "created_at": company.created_at.isoformat() if company.created_at else None,
            }
            for company in companies
        ],
    }


@router.post("/companies")
async def create_company(request: CompanyCreate, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Solo super admin puede crear empresas")

    company = Company(name=request.name, plan=request.plan, settings=json.dumps(request.settings or {}))
    db.add(company)
    db.commit()
    db.refresh(company)

    return {"id": company.id, "uuid": company.uuid, "name": company.name}


@router.put("/companies/{company_id}")
async def update_company(company_id: int, request: CompanyUpdate, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if current_admin.role != "super_admin" and current_admin.company_id != company_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    if request.name is not None:
        company.name = request.name
    if request.plan is not None:
        company.plan = request.plan
    if request.is_active is not None:
        company.is_active = request.is_active
    if request.settings is not None:
        company.settings = json.dumps(request.settings)

    db.commit()
    return {"message": "Empresa actualizada"}


@router.get("/companies/{company_id}/bot-config")
async def get_bot_config(company_id: int, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if current_admin.role != "super_admin" and current_admin.company_id != company_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    settings = safe_get_settings(company)
    default_config = {
        "system_prompt": "Eres un asistente virtual útil y amigable. Responde de manera clara y concisa.",
        "temperature": 0.7,
        "model": "llama3-70b-8192",
        "max_context_messages": 10,
        "rate_limit_per_user": 10,
        "is_running": True,
        "welcome_message": "¡Hola! Soy tu asistente IA. ¿En qué puedo ayudarte?",
    }

    bot_config = settings.get("bot_config", {})
    return {**default_config, **bot_config}


@router.put("/companies/{company_id}/bot-config")
async def update_bot_config(company_id: int, request: BotConfigUpdate, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if current_admin.role != "super_admin" and current_admin.company_id != company_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    settings = safe_get_settings(company)
    bot_config = settings.get("bot_config", {})

    for field, value in request.dict(exclude_unset=True).items():
        bot_config[field] = value

    settings["bot_config"] = bot_config
    company.settings = json.dumps(settings)
    db.commit()

    return {"message": "Configuración actualizada"}


@router.get("/companies/{company_id}/conversations")
async def get_conversations(company_id: int, page: int = 1, limit: int = 50, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    if current_admin.role != "super_admin" and current_admin.company_id != company_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    query = db.query(Conversation).filter(Conversation.company_id == company_id)
    total = query.count()
    conversations = query.order_by(desc(Conversation.last_activity)).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "data": [
            {
                "id": conversation.id,
                "session_id": conversation.session_id,
                "channel": conversation.channel,
                "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
                "last_activity": conversation.last_activity.isoformat() if conversation.last_activity else None,
                "message_count": db.query(Message).filter(Message.conversation_id == conversation.id).count(),
            }
            for conversation in conversations
        ],
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: int, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    if current_admin.role != "super_admin" and current_admin.company_id != conversation.company_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at).all()
    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "model_used": message.model_used,
            "tokens_used": message.tokens_used,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
        for message in messages
    ]


@router.get("/stats/dashboard")
async def get_dashboard_stats(current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    if current_admin.role == "super_admin":
        company_ids = [company.id for company in db.query(Company).all()]
    else:
        company_ids = [current_admin.company_id] if current_admin.company_id else []

    conversations = db.query(Conversation).filter(Conversation.company_id.in_(company_ids)).all()
    messages = db.query(Message).filter(Message.conversation_id.in_([conversation.id for conversation in conversations])).all()

    return {
        "total_companies": len(company_ids),
        "active_companies": db.query(Company).filter(Company.id.in_(company_ids), Company.is_active.is_(True)).count(),
        "total_conversations": len(conversations),
        "total_messages": len(messages),
        "messages_by_channel": {
            "web": sum(1 for conversation in conversations if conversation.channel == "web"),
            "whatsapp": sum(1 for conversation in conversations if conversation.channel == "whatsapp"),
        },
    }


@router.get("/stats/companies/{company_id}")
async def get_company_stats(company_id: int, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    if current_admin.role != "super_admin" and current_admin.company_id != company_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    conversations = db.query(Conversation).filter(Conversation.company_id == company_id).all()
    messages = db.query(Message).filter(Message.conversation_id.in_([conversation.id for conversation in conversations])).all()
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_messages = [message for message in messages if message.created_at and message.created_at >= week_ago]

    return {
        "total_conversations": len(conversations),
        "total_messages": len(messages),
        "messages_last_7_days": len(recent_messages),
        "active_conversations": sum(1 for conversation in conversations if conversation.last_activity and conversation.last_activity >= week_ago),
    }


@router.get("/stats/activity")
async def get_activity_stats(
    days: int = 7,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Obtener estadísticas de actividad para gráficos"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, cast, Date

    start_date = datetime.utcnow() - timedelta(days=days)

    if current_admin.role == "super_admin":
        company_ids = [c.id for c in db.query(Company).all()]
    else:
        company_ids = [current_admin.company_id] if current_admin.company_id else []

    # Consultar mensajes por día
    results = (
        db.query(cast(Message.created_at, Date).label("date"), func.count(Message.id).label("count"))
        .filter(
            Message.conversation_id.in_(
                db.query(Conversation.id).filter(Conversation.company_id.in_(company_ids))
            ),
            Message.created_at >= start_date,
        )
        .group_by(cast(Message.created_at, Date))
        .order_by("date")
        .all()
    )

    from datetime import timedelta as _td
    dates = [(start_date + _td(days=i)).date() for i in range(days)]
    counts = {r.date: r.count for r in results}

    labels = [d.strftime('%a %d/%m') for d in dates]
    values = [counts.get(d, 0) for d in dates]

    return {"labels": labels, "values": values}


@router.get("/activity/recent")
async def get_recent_activity(
    limit: int = 10,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Obtener actividad reciente para el dashboard"""
    if current_admin.role == "super_admin":
        company_ids = [c.id for c in db.query(Company).all()]
    else:
        company_ids = [current_admin.company_id] if current_admin.company_id else []

    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id.in_(
                db.query(Conversation.id).filter(Conversation.company_id.in_(company_ids))
            ),
            Message.role == "user",
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )

    activities = []
    icons = {"web": "fa-globe", "whatsapp": "fa-whatsapp"}

    for msg in messages:
        conv = db.query(Conversation).filter(Conversation.id == msg.conversation_id).first()
        if conv:
            company = db.query(Company).filter(Company.id == conv.company_id).first()
            activities.append({
                "icon": icons.get(conv.channel, "fa-comment"),
                "title": f'Nuevo mensaje en {company.name if company else "Empresa"} - {conv.channel}',
                "time": msg.created_at.strftime('%H:%M - %d/%m/%Y'),
            })

    return activities
