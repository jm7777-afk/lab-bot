from app.database import SessionLocal
from app.models.company import AdminUser
from passlib.hash import bcrypt

def create_admin():
    email = input("Email: ")
    password = input("Contraseña: ")
    
    db = SessionLocal()
    
    if db.query(AdminUser).filter(AdminUser.email == email).first():
        print("❌ El usuario ya existe")
        db.close()
        return
    
    hashed = bcrypt.hash(password)
    admin = AdminUser(email=email, password_hash=hashed, role="super_admin")
    db.add(admin)
    db.commit()
    db.close()
    
    print(f"✅ Admin {email} creado correctamente")

if __name__ == "__main__":
    create_admin()
