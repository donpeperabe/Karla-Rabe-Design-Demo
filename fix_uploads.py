# fix_uploads.py
import os
import shutil
from app import create_app

app = create_app()

with app.app_context():
    print("🔧 Reparando estructura de archivos...")
    
    # Crear carpeta uploads si no existe
    uploads_path = os.path.join('static', 'uploads')
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)
        print(f"✅ Carpeta creada: {uploads_path}")
    
    # Verificar imágenes en static/images
    images_path = os.path.join('static', 'images')
    if os.path.exists(images_path):
        print("📁 Archivos en static/images:")
        for file in os.listdir(images_path):
            print(f"   - {file}")
    
    print("🎯 Listo! Reinicia la aplicación.")
