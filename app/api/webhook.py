"""
Webhook de WhatsApp - Punto de entrada para todos los mensajes
"""
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Tenant, Client, Conversation, Message, Product
from app.services.groq_service import groq_service
from app.services.whatsapp_service import whatsapp_service
from app.services.rag_service import rag_service
from app.config import config
import json
import logging
import uuid
import re

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = None,
    hub_challenge: int = None,
    hub_verify_token: str = None
):
    """Verificación del webhook con Meta"""
    if hub_mode == "subscribe" and hub_verify_token == config.WHATSAPP_VERIFY_TOKEN:
        return Response(content=str(hub_challenge), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token inválido")


@router.post("/whatsapp")
async def handle_whatsapp(request: Request, db: AsyncSession = Depends(get_db)):
    """Endpoint principal para recibir mensajes de WhatsApp"""
    try:
        body = await request.json()
        logger.info(f"📨 Webhook recibido")
        
        # Extraer datos del payload
        entry = body.get("entry", [])[0] if body.get("entry") else {}
        changes = entry.get("changes", [])[0] if entry.get("changes") else {}
        value = changes.get("value", {})
        
        # Verificar si es un mensaje
        if not value.get("messages"):
            logger.warning("No hay mensajes en el webhook")
            return {"status": "ok"}
        
        message_obj = value["messages"][0]
        contact = value.get("contacts", [{}])[0]
        metadata = value.get("metadata", {})
        
        # Datos del cliente y bot
        client_phone = contact.get("wa_id")
        client_name = contact.get("profile", {}).get("name", "Cliente")
        bot_phone = metadata.get("display_phone_number")
        msg_type = message_obj.get("type")
        
        logger.info(f"📱 De: {client_phone}, Bot: {bot_phone}, Tipo: {msg_type}")
        
        # ===== 1. BUSCAR TENANT (Empresa) =====
        stmt = select(Tenant).where(
            Tenant.phone_number == bot_phone,
            Tenant.bot_is_active == True
        )
        result = await db.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning(f"❌ Tenant no encontrado: {bot_phone}")
            return {"status": "error", "message": "Tenant not found"}
        
        logger.info(f"✅ Tenant encontrado: {tenant.business_name}")
        
        # ===== 2. BUSCAR O CREAR CLIENTE =====
        stmt = select(Client).where(
            Client.tenant_id == tenant.id,
            Client.phone == client_phone
        )
        result = await db.execute(stmt)
        client = result.scalar_one_or_none()
        
        if not client:
            # Crear cliente sin CI (se pedirá después)
            client = Client(
                tenant_id=tenant.id,
                ci="PENDIENTE",
                full_name=client_name,
                phone=client_phone
            )
            db.add(client)
            await db.flush()
            logger.info(f"✅ Cliente creado: {client_name}")
        
        client_ci = client.ci
        
        # ===== 3. BUSCAR O CREAR CONVERSACIÓN =====
        stmt = select(Conversation).where(
            Conversation.tenant_id == tenant.id,
            Conversation.client_ci == client_ci,
            Conversation.is_resolved == False
        ).order_by(Conversation.last_activity.desc())
        
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            conversation = Conversation(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                client_ci=client_ci,
                channel="whatsapp"
            )
            db.add(conversation)
            await db.flush()
            logger.info(f"✅ Conversación creada: {conversation.id}")
        else:
            logger.info(f"✅ Conversación existente: {conversation.id}")
        
        # ===== 4. PROCESAR MENSAJE SEGÚN TIPO =====
        user_message = ""
        media_url = None
        
        if msg_type == "text":
            user_message = message_obj.get("text", {}).get("body", "")
        
        elif msg_type == "audio":
            # Transcribir audio con Whisper
            media_url = message_obj.get("audio", {}).get("url")
            logger.info(f"🎤 Procesando audio: {media_url[:50]}")
            user_message = await groq_service.transcribe_audio(media_url)
        
        elif msg_type == "image":
            media_url = message_obj.get("image", {}).get("url")
            user_message = "[Imagen recibida - Comprobante de pago]"
            logger.info(f"🖼️ Imagen recibida")
        
        else:
            user_message = f"[{msg_type.upper()} - No soportado aún]"
        
        logger.info(f"📝 Mensaje: {user_message[:100]}")
        
        # ===== 5. GUARDAR MENSAJE DEL USUARIO =====
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=user_message,
            content_type=msg_type,
            media_url=media_url
        )
        db.add(user_msg)
        await db.flush()
        
        # ===== 6. RAG - BÚSQUEDA INTELIGENTE DE PRODUCTOS =====
        relevant_products = await rag_service.search_products_simple(
            db, tenant.id, user_message
        )
        products_context = rag_service.format_products_for_prompt(relevant_products)
        logger.info(f"🔍 Productos encontrados: {len(relevant_products)}")
        
        # ===== 7. OBTENER HISTORIAL RECIENTE =====
        stmt = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc()).limit(8)
        
        result = await db.execute(stmt)
        history = list(result.scalars().all())
        history.reverse()
        
        chat_history = "\n".join([
            f"{'👤 Cliente' if m.role == 'user' else '🤖 Bot'}: {m.content[:100]}"
            for m in history[-6:]
        ])
        
        # ===== 8. CONSTRUIR PROMPT FINAL =====
        system_prompt = tenant.system_prompt
        
        # Formatear información de pago
        payment_info = tenant.payment_info or {}
        payment_text = f"""
DATOS DE PAGO:
- Banco: {payment_info.get('bank', 'No especificado')}
- Número: {payment_info.get('account_number', 'No especificado')}
- Titular: {payment_info.get('owner_name', 'No especificado')}
- CI: {payment_info.get('owner_ci', 'No especificado')}
- Teléfono: {payment_info.get('phone', 'No especificado')}
- Instrucciones: {payment_info.get('instructions', 'Pago Móvil o Transferencia')}
"""
        
        final_prompt = f"""{system_prompt}

{payment_text}

{products_context}

HISTORIAL RECIENTE:
{chat_history}

CLIENTE: {client.full_name} (CI: {client_ci})
MENSAJE ACTUAL: {user_message}

INSTRUCCIONES IMPORTANTES:
1. Si el cliente quiere comprar, solicita su CÉDULA DE IDENTIDAD (CI) si no la tienes.
2. Confirma productos y cantidades solicitadas.
3. NO calcules totales tú mismo - solo confirma con el cliente.
4. Para pagos, proporciona EXACTAMENTE los datos de pago de arriba.
5. Si el cliente envía imagen, confirma si es comprobante de pago.
6. Sé amable, profesional, rápido y responde en español.
7. NO inventes información que no está en el contexto.

RESPUESTA:"""
        
        # ===== 9. LLAMAR A GROQ (LLaMA 3) =====
        logger.info("🤖 Llamando a Groq...")
        groq_response = await groq_service.chat_completion(
            messages=[{"role": "user", "content": final_prompt}],
            temperature=float(tenant.bot_temperature),
            max_tokens=500
        )
        
        bot_response = groq_response["content"]
        tokens_used = groq_response.get("tokens", 0)
        
        logger.info(f"✅ Respuesta recibida: {bot_response[:100]}")
        
        # ===== 10. GUARDAR RESPUESTA DEL BOT =====
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="assistant",
            content=bot_response,
            content_type="text",
            tokens_used=tokens_used,
            cost_usd=0.001  # Aproximado
        )
        db.add(assistant_msg)
        
        # Actualizar conversación
        conversation.last_activity = func.now()
        conversation.message_count = conversation.message_count + 2
        
        await db.commit()
        
        # ===== 11. ENVIAR RESPUESTA A WHATSAPP =====
        logger.info(f"📤 Enviando respuesta a {client_phone}")
        await whatsapp_service.send_text(client_phone, bot_response)
        
        return {
            "status": "success",
            "order_id": conversation.id,
            "response": bot_response[:100]
        }
    
    except Exception as e:
        logger.error(f"❌ Error en webhook: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
