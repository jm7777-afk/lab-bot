import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "1234")


@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    """Verifica el webhook de WhatsApp/Meta."""
    print(
        f"🔍 Verificación recibida - mode: {hub_mode}, challenge: {hub_challenge}, token: {hub_verify_token}"
    )

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print("✅ Webhook verificado correctamente")
        return PlainTextResponse(content=str(hub_challenge or ""))

    print(f"❌ Verificación fallida - Token esperado: {VERIFY_TOKEN}")
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("/whatsapp")
async def handle_whatsapp(request: Request):
    """Recibe eventos de WhatsApp y confirma recepción."""
    try:
        body = await request.json()
        print(f"📨 Mensaje recibido de WhatsApp: {body}")
        return JSONResponse(content={"status": "ok"})
    except Exception as exc:
        print(f"❌ Error al procesar webhook: {exc}")
        return JSONResponse(content={"error": str(exc)}, status_code=500)
