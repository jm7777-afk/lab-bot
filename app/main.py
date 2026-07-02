"""
BOT IA ENTERPRISE - FastAPI Main
Plataforma SaaS multi-tenant para WhatsApp
"""
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import webhook, admin, public
from app.database import engine, Base
from app.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bot IA Enterprise",
    description="Plataforma SaaS multi-tenant para automatizar WhatsApp",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/admin-ui", StaticFiles(directory="admin"), name="admin_ui")

# Routers
app.include_router(webhook.router, prefix="/webhook", tags=["whatsapp"])
app.include_router(admin.router)
app.include_router(public.router)

# Get base path for static files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Corporate routes
@app.get("/")
async def home():
    """Serve home page"""
    file_path = os.path.join(BASE_DIR, "static/corporate/index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    return {"message": "BotIA - Plataforma SaaS Multi-tenant"}

@app.get("/features")
async def features():
    """Serve features page"""
    file_path = os.path.join(BASE_DIR, "static/corporate/features.html")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    return {"message": "Características"}

@app.get("/pricing")
async def pricing():
    """Serve pricing page"""
    file_path = os.path.join(BASE_DIR, "static/corporate/pricing.html")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    return {"message": "Planes disponibles: Free, Startup, Business"}

@app.get("/about")
async def about():
    """Serve about page"""
    file_path = os.path.join(BASE_DIR, "static/corporate/about.html")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    return {"message": "Acerca de BotIA"}

@app.get("/contact")
async def contact():
    """Serve contact page"""
    file_path = os.path.join(BASE_DIR, "static/corporate/contact.html")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    return {"message": "Contacto"}

@app.get("/blog")
async def blog():
    """Serve blog page"""
    file_path = os.path.join(BASE_DIR, "static/corporate/blog.html")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    return {"message": "Blog de BotIA"}

@app.get("/login")
async def login():
    """Serve login page"""
    return FileResponse(os.path.join(BASE_DIR, "static/login.html"), media_type="text/html")

@app.on_event("startup")
async def startup():
    """Crear tablas en la base de datos al iniciar"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Base de datos inicializada - MySQL")
    except Exception as e:
        logger.error(f"❌ Error inicializando BD: {str(e)}")


@app.get("/api", tags=["general"])
async def api_info():
    return {
        "status": "online",
        "app": "Bot IA Enterprise",
        "version": "2.0.0",
        "database": config.MYSQL_DATABASE,
    }


@app.get("/health", tags=["general"])
async def health():
    return {"status": "healthy"}


@app.get("/admin-ui")
async def admin_index():
    return FileResponse("admin/index.html")


@app.get("/admin-ui/")
async def admin_index_slash():
    return FileResponse("admin/index.html")
