# init_admin.py
from app import create_app, db
from app.models.user import User

app = create_app()

with app.app_context():
    # Crear todas las tablas
    db.create_all()
    
    # Verificar si el usuario admin ya existe
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # Crear usuario admin
        admin_user = User(
            username='admin',
            is_admin=True  # ← Ahora este campo existe
        )
        admin_user.set_password('admin123')
        
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Usuario admin creado exitosamente!")
        print("👤 Usuario: admin")
        print("🔑 Contraseña: admin123")
        print("🎯 Accede en: http://localhost:5000/login")
    else:
        print("⚠️ El usuario admin ya existe")