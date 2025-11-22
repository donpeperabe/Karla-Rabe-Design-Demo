# mover_uploads.py
import os
import shutil
from app import create_app

app = create_app()

with app.app_context():
    print("🔄 Moviendo archivos a la ubicación correcta...")
    
    # Ruta actual (raíz) y nueva ruta (static/uploads)
    uploads_viejo = 'uploads'
    uploads_nuevo = 'static/uploads'
    
    if os.path.exists(uploads_viejo):
        print(f"📁 Encontré carpeta en: {uploads_viejo}")
        
        # Mover cada archivo
        for filename in os.listdir(uploads_viejo):
            if filename != 'app.db':  # No mover la base de datos
                viejo_path = os.path.join(uploads_viejo, filename)
                nuevo_path = os.path.join(uploads_nuevo, filename)
                
                shutil.move(viejo_path, nuevo_path)
                print(f"✅ Movido: {filename}")
        
        print("🎯 Archivos movidos a static/uploads/")
    else:
        print("ℹ️ No hay carpeta uploads en la raíz")
    
    print("¡Listo! Las imágenes deberían verse ahora.")