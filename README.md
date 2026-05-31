# Lab Bot

Proyecto de prueba con FastAPI, SQLAlchemy y una interfaz de administración estática.

Requisitos

- Python 3.11+
- pip
- opcional: Docker / Docker Compose

Instalación (virtualenv)

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Ejecutar (desarrollo)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Con Docker Compose (si Docker está disponible)

```powershell
docker compose build
docker compose up
```

Despliegue de prueba

Puedes desplegar en Railway, Render o Fly.io conectando este repo.

Notas

- No subas el archivo `.env` ni la base de datos local `data/*.db` al repositorio.
- Las páginas de administración están en `static/pages/` y se sirven desde `/static/`.
