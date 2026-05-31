import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import config
from app.database import get_db
from app.models.company import Company
from app.models.conversation import Conversation, Message
from app.services.llm_service import llm_service
from app.services.rate_limiter import rate_limiter

router = APIRouter(prefix="/chat/web", tags=["web_chat"])


class ChatRequest(BaseModel):
    company_uuid: str
    session_id: str | None = None
    message: str
    channel: str = "web"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    model_used: str


def get_company_bot_config(company: Company) -> dict:
    try:
        settings = company.get_settings()
    except Exception:
        settings = {}
    return settings.get("bot_config", {})


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.uuid == request.company_uuid, Company.is_active.is_(True)).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada o inactiva")

    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    if len(message) > 10000:
        message = message[:10000] + "... [truncado]"

    bot_config = get_company_bot_config(company)
    if bot_config.get("is_running") is False:
        raise HTTPException(status_code=503, detail="El bot está desactivado para esta empresa")

    rate_limit_value = bot_config.get("rate_limit_per_user")
    try:
        rate_limit = int(rate_limit_value) if rate_limit_value is not None else None
    except (TypeError, ValueError):
        rate_limit = None

    user_id = request.session_id or "anonymous"
    if not rate_limiter.check_user_limit(company.id, user_id, limit=rate_limit):
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes. Espera un momento.")

    conversation = None
    if request.session_id:
        conversation = db.query(Conversation).filter(
            Conversation.session_id == request.session_id,
            Conversation.company_id == company.id,
        ).first()

    if conversation is None:
        conversation = Conversation(
            company_id=company.id,
            session_id=str(uuid.uuid4()),
            channel=request.channel,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    user_message = Message(conversation_id=conversation.id, role="user", content=message)
    db.add(user_message)
    db.commit()

    try:
        max_context = int(bot_config.get("max_context_messages") or config.MAX_CONTEXT_MESSAGES)
    except (TypeError, ValueError):
        max_context = config.MAX_CONTEXT_MESSAGES

    history = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(max_context)
        .all()
    )
    messages_for_llm = [{"role": msg.role, "content": msg.content} for msg in reversed(history)]

    llm_response = await llm_service.generate_response(company.id, messages_for_llm, company_config=bot_config)

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=llm_response["content"],
        model_used=llm_response["model"],
        tokens_used=llm_response.get("tokens_used", 0),
    )
    db.add(assistant_message)
    db.commit()

    return ChatResponse(
        response=llm_response["content"],
        session_id=conversation.session_id,
        model_used=llm_response["model"],
    )
