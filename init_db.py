import secrets

from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models.company import AdminUser, Company

print("📦 Creando tablas...")
Base.metadata.create_all(bind=engine)

session = Session(engine)

# Crear empresa demo
if not session.query(Company).first():
    demo = Company(name="Empresa Demo", is_active=True)
    session.add(demo)
    session.commit()
    print("\n✅ Empresa demo creada con éxito!")
    print(f"📋 UUID de la empresa: {demo.uuid}")
    print("\n📌 GUARDA ESTE UUID para probar el chat.")
else:
    company = session.query(Company).first()
    print(f"\n✅ Empresa ya existe. UUID: {company.uuid}")

# Crear usuario admin demo
if not session.query(AdminUser).filter(AdminUser.email == "admin@admin.com").first():
    session.add(
        AdminUser(
            email="admin@admin.com",
            password_hash=bcrypt.hash("admin123"),
            role="super_admin",
        )
    )
    session.commit()
    print("\n✅ Usuario admin demo creado: admin@admin.com / admin123")

session.close()
print("\n✅ Base de datos inicializada correctamente")
