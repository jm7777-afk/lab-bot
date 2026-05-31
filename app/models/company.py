import json
import secrets

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(32), unique=True, nullable=False, default=lambda: secrets.token_hex(16))
    name = Column(String(255), nullable=False)
    plan = Column(String(50), default="free")
    is_active = Column(Boolean, default=True)
    settings = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())

    def get_settings(self):
        return json.loads(self.settings)

    def set_settings(self, settings_dict):
        self.settings = json.dumps(settings_dict)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    company_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
