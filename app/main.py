import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from passlib.hash import bcrypt

from app.api import admin as admin_api, web_chat, whatsapp_webhook
from app.database import Base, SessionLocal, engine
from app.models.company import AdminUser

Base.metadata.create_all(bind=engine)


def ensure_default_admin():
    db = SessionLocal()
    try:
        if db.query(AdminUser).filter(AdminUser.email == "admin@admin.com").first() is None:
            db.add(
                AdminUser(
                    email="admin@admin.com",
                    password_hash=bcrypt.hash("admin123"),
                    role="super_admin",
                )
            )
            db.commit()
    finally:
        db.close()


ensure_default_admin()

app = FastAPI(title="Bot Multitenente IA", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_chat.router)
app.include_router(whatsapp_webhook.router, prefix="/webhook", tags=["whatsapp"])
app.include_router(admin_api.router)

os.makedirs("static", exist_ok=True)
with open("app/templates/chat_widget.js", "r", encoding="utf-8") as source:
    with open("static/chat-widget.js", "w", encoding="utf-8") as target:
        target.write(source.read())

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/admin", StaticFiles(directory="admin", html=True), name="admin")


@app.get("/admin")
async def admin_index():
    return FileResponse("admin/index.html")


@app.get("/admin/")
async def admin_index_slash():
    return FileResponse("admin/index.html")


@app.on_event("startup")
def startup_seed():
    ensure_default_admin()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "Bot multitenente IA listo", "status": "online"}
