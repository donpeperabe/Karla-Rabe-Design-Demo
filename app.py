import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config

# -------------------- APP --------------------
app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth_login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

# -------------------- CLOUDINARY CONFIG --------------------
CLOUDINARY_CONFIGURED = False

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    
    # REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES REALES
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'devlfxd7k'),
        api_key=os.environ.get('CLOUDINARY_API_KEY', '884811176721628'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET', '-xtYxEL5UqwePOM1370L3gImET0')
    )
    CLOUDINARY_CONFIGURED = True
    print("✅ Cloudinary configurado correctamente")
except ImportError:
    print("❌ Cloudinary no está instalado")
except Exception as e:
    print(f"❌ Error configurando Cloudinary: {e}")

# -------------------- MODELOS --------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Proyecto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    imagen = db.Column(db.String(255), nullable=True)

    images = db.relationship('Image', backref='proyecto', lazy=True, cascade="all,delete")
    pdffiles = db.relationship('PDFFile', backref='proyecto', lazy=True, cascade="all,delete")

    @property
    def name(self):
        return self.nombre
    
    @property
    def description(self):
        return self.descripcion
    
    @property
    def cover_image(self):
        return self.imagen
    
    @property
    def cover_image_url(self):
        return self.imagen


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200))
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    
    @property
    def image_url(self):
        return self.filename


class PDFFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200))
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    
    @property
    def pdf_url(self):
        return self.filename


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def init_db():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tablas creadas exitosamente")
            
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(username='admin', is_admin=True)
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Usuario admin creado: admin / admin123")
            else:
                print("✅ Usuario admin ya existe")
                
        except Exception as e:
            print(f"❌ Error al inicializar la base de datos: {e}")


init_db()

# -------------------- UTIL --------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def upload_to_cloudinary(file, folder="karla_rabe"):
    """Sube archivo a Cloudinary y retorna URL"""
    if not CLOUDINARY_CONFIGURED:
        print("❌ Cloudinary no está configurado")
        flash('Cloudinary no está configurado correctamente', 'error')
        return None
    
    try:
        print(f"☁️ Subiendo a Cloudinary: {file.filename}")
        
        # Asegurarnos de que el archivo esté en la posición inicial
        file.seek(0)
        
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="auto"
        )
        
        print(f"✅ Cloudinary upload exitoso: {result['secure_url']}")
        return result['secure_url']
        
    except Exception as e:
        print(f"❌ Error subiendo a Cloudinary: {e}")
        flash(f'Error subiendo archivo: {str(e)}', 'error')
        return None

def delete_from_cloudinary(url):
    """Elimina archivo de Cloudinary usando la URL"""
    if not CLOUDINARY_CONFIGURED:
        return False
    
    try:
        # Extraer public_id de la URL de Cloudinary
        public_id = url.split('/')[-1].split('.')[0]
        folder = "karla_rabe"
        full_public_id = f"{folder}/{public_id}"
        
        result = cloudinary.uploader.destroy(full_public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"❌ Error eliminando de Cloudinary: {e}")
        return False

# -------------------- RUTAS PARA ARCHIVOS --------------------

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    image = Image.query.filter_by(filename=filename).first()
    if image:
        return redirect(image.filename)
    return "Archivo no encontrado", 404

@app.route('/uploaded_pdf/<path:filename>')
def uploaded_pdf(filename):
    pdf = PDFFile.query.filter_by(filename=filename).first()
    if pdf:
        return redirect(pdf.filename)
    return "PDF no encontrado", 404

# -------------------- PÚBLICO --------------------

@app.route('/')
def home():
    proyectos = Proyecto.query.all()
    return render_template('public/index.html', categories=proyectos)

@app.route('/category/<int:category_id>')
def category_detail(category_id):
    proyecto = Proyecto.query.get_or_404(category_id)
    return render_template('public/category.html', category=proyecto)

# -------------------- AUTH --------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def auth_login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_panel'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor ingresa usuario y contraseña', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login exitoso!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            else:
                return redirect(url_for('dashboard_panel'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('auth/login.html')

@app.route('/admin/logout')
@login_required
def auth_logout():
    logout_user()
    flash('Has cerrado sesión', 'success')
    return redirect(url_for('home'))

# -------------------- DASHBOARD --------------------

@app.route('/dashboard')
@login_required
def dashboard_panel():
    proyectos = Proyecto.query.all()
    return render_template('dashboard/panel.html', proyectos=proyectos)

# -------- CREAR PROYECTO --------

@app.route('/dashboard/crear_proyecto', methods=['GET', 'POST'])
@login_required
def dashboard_proyecto_crear():
    if request.method == 'POST':
        nombre = request.form.get('name')
        descripcion = request.form.get('description')

        proyecto = Proyecto(nombre=nombre, descripcion=descripcion)

        file = request.files.get('cover_image')
        if file and allowed_file(file.filename):
            image_url = upload_to_cloudinary(file)
            if image_url:
                proyecto.imagen = image_url
                flash('Imagen de portada subida exitosamente a la nube', 'success')
            else:
                flash('Error subiendo la imagen', 'error')

        db.session.add(proyecto)
        db.session.commit()
        flash('Proyecto creado exitosamente', 'success')
        return redirect(url_for('dashboard_panel'))
    
    return render_template('dashboard/proyecto_crear.html')

# -------- EDITAR PROYECTO --------

@app.route('/dashboard/editar_proyecto/<int:proyecto_id>', methods=['GET', 'POST'])
@login_required
def dashboard_proyecto_editar(proyecto_id):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    if request.method == 'POST':
        proyecto.nombre = request.form.get('name')
        proyecto.descripcion = request.form.get('description')

        file = request.files.get('cover_image')
        if file and allowed_file(file.filename):
            # Eliminar imagen anterior de Cloudinary si existe
            if proyecto.imagen and CLOUDINARY_CONFIGURED:
                delete_from_cloudinary(proyecto.imagen)
            
            # Subir nueva imagen a Cloudinary
            image_url = upload_to_cloudinary(file)
            if image_url:
                proyecto.imagen = image_url
                flash('Imagen de portada actualizada exitosamente', 'success')
            else:
                flash('Error actualizando la imagen', 'error')

        db.session.commit()
        flash('Proyecto actualizado exitosamente', 'success')
        return redirect(url_for('dashboard_panel'))

    return render_template('dashboard/proyecto_editar.html', proyecto=proyecto)

# Alias para compatibilidad con panel.html
@app.route('/dashboard/editar_categoria/<int:id>')
@login_required
def editar_categoria(id):
    return redirect(url_for('dashboard_proyecto_editar', proyecto_id=id))

# -------- ELIMINAR PROYECTO --------

@app.route('/dashboard/eliminar_categoria/<int:id>')
@login_required
def eliminar_categoria(id):
    proyecto = Proyecto.query.get_or_404(id)
    
    # Eliminar archivos de Cloudinary
    if CLOUDINARY_CONFIGURED:
        if proyecto.imagen:
            delete_from_cloudinary(proyecto.imagen)
        for img in proyecto.images:
            delete_from_cloudinary(img.filename)
        for pdf in proyecto.pdffiles:
            delete_from_cloudinary(pdf.filename)

    db.session.delete(proyecto)
    db.session.commit()
    flash('Proyecto y todos sus archivos eliminados exitosamente', 'success')
    return redirect(url_for('dashboard_panel'))

# -------- SUBIR IMAGEN --------

@app.route('/dashboard/subir_imagen/<int:proyecto_id>', methods=['POST'])
@login_required
def subir_imagen(proyecto_id):
    files = request.files.getlist('image')
    title = request.form.get('title')

    print(f"📸 Intentando subir {len(files)} imágenes para proyecto {proyecto_id}")
    
    uploaded_count = 0
    for file in files:
        if file and file.filename != '' and allowed_file(file.filename):
            print(f"📁 Procesando archivo: {file.filename}")
            
            # Subir a Cloudinary
            image_url = upload_to_cloudinary(file)
            if image_url:
                print(f"✅ Imagen subida a Cloudinary: {image_url}")
                db.session.add(Image(filename=image_url, title=title, proyecto_id=proyecto_id))
                uploaded_count += 1
                flash(f'Imagen {file.filename} subida exitosamente', 'success')
            else:
                print(f"❌ Error subiendo {file.filename} a Cloudinary")
                flash(f'Error subiendo {file.filename}', 'error')
        else:
            print(f"⚠️ Archivo inválido o vacío: {file.filename if file else 'None'}")

    db.session.commit()
    
    if uploaded_count > 0:
        flash(f'{uploaded_count} imagen(es) subidas exitosamente', 'success')
    else:
        flash('No se pudieron subir las imágenes', 'error')
        
    return redirect(url_for('dashboard_proyecto_editar', proyecto_id=proyecto_id))

# -------- ELIMINAR IMAGEN --------

@app.route('/dashboard/eliminar_imagen/<int:image_id>', methods=['POST'])
@login_required
def eliminar_imagen(image_id):
    img = Image.query.get_or_404(image_id)
    proyecto_id = img.proyecto_id
    
    if CLOUDINARY_CONFIGURED:
        delete_from_cloudinary(img.filename)
    
    db.session.delete(img)
    db.session.commit()
    flash('Imagen eliminada exitosamente', 'success')
    return redirect(url_for('dashboard_proyecto_editar', proyecto_id=proyecto_id))

# -------- SUBIR PDF --------

@app.route('/dashboard/subir_pdf/<int:proyecto_id>', methods=['POST'])
@login_required
def subir_pdf(proyecto_id):
    file = request.files.get('pdf')
    title = request.form.get('title')

    print(f"📄 Intentando subir PDF para proyecto {proyecto_id}")
    
    if not file or file.filename == '':
        flash('No se seleccionó ningún archivo PDF', 'error')
        return redirect(url_for('dashboard_panel'))
        
    if not file.filename.lower().endswith('.pdf'):
        flash('Debes subir un archivo PDF válido', 'error')
        return redirect(url_for('dashboard_panel'))

    print(f"📁 Procesando PDF: {file.filename}")
    
    # Subir a Cloudinary
    pdf_url = upload_to_cloudinary(file)
    if pdf_url:
        print(f"✅ PDF subido a Cloudinary: {pdf_url}")
        db.session.add(PDFFile(filename=pdf_url, title=title, proyecto_id=proyecto_id))
        db.session.commit()
        flash('PDF subido exitosamente a la nube', 'success')
    else:
        print(f"❌ Error subiendo PDF a Cloudinary")
        flash('Error subiendo el PDF', 'error')
        
    return redirect(url_for('dashboard_panel'))

# -------- ELIMINAR PDF --------

@app.route('/dashboard/eliminar_pdf/<int:pdf_id>', methods=['POST'])
@login_required
def eliminar_pdf(pdf_id):
    pdf = PDFFile.query.get_or_404(pdf_id)
    
    if CLOUDINARY_CONFIGURED:
        delete_from_cloudinary(pdf.filename)
    
    db.session.delete(pdf)
    db.session.commit()
    flash('PDF eliminado exitosamente', 'success')
    return redirect(url_for('dashboard_panel'))

# -------------------- MANEJO DE ERRORES SIMPLIFICADO --------------------

@app.errorhandler(404)
def not_found_error(error):
    return "Página no encontrada", 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return "Error interno del servidor", 500

# -------------------- RUN --------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
