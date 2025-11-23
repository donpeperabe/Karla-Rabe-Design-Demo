import os
from flask import Flask, render_template, request, redirect, url_for, flash, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Configuración
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')

# Usar SQLite con ruta absoluta en Render
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/app.db'  # /tmp es persistente en Render
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager(app)

# Modelos
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
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    images = db.relationship('Image', backref='proyecto', lazy=True, cascade='all, delete')

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)

class PDFFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)

    def __repr__(self):
        return f"<PDF {self.filename}>"


# Configuración Login
login_manager.login_view = 'auth_login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# INICIALIZACIÓN DE BASE DE DATOS MEJORADA
def init_db():
    with app.app_context():
        try:
            # Verificar si la base de datos existe
            db_path = '/tmp/app.db'
            db_exists = os.path.exists(db_path)
            
            db.create_all()
            
            if not db_exists:
                # Solo crear admin si la DB es nueva
                admin = User.query.filter_by(username='admin').first()
                if not admin:
                    admin_user = User(username='admin', is_admin=True)
                    admin_user.set_password('admin123')
                    db.session.add(admin_user)
                    db.session.commit()
                    print("✅ Usuario admin creado: admin / admin123")
                print("✅ Base de datos inicializada correctamente")
            else:
                print("✅ Base de datos existente cargada")
                
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")

init_db()

# Utilidades
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# Rutas Públicas
@app.route('/')
def home():
    try:
        proyectos = Proyecto.query.all()
        print(f"✅ Número de proyectos encontrados: {len(proyectos)}")
        return render_template('public/index.html', categories=proyectos)
    except Exception as e:
        print(f"❌ Error en home: {e}")
        return render_template('public/index.html', categories=[])

@app.route('/category/<int:category_id>')
def category_detail(category_id):
    try:
        proyecto = Proyecto.query.get_or_404(category_id)
        return render_template('public/category.html', category=proyecto)
    except Exception as e:
        flash(f'Error cargando el proyecto: {e}', 'error')
        return redirect(url_for('home'))

# Rutas de Autenticación
@app.route('/admin/login', methods=['GET', 'POST'])
def auth_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('dashboard_panel'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    return render_template('auth/login.html')

@app.route('/admin/logout')
@login_required
def auth_logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('home'))

# Dashboard Principal
@app.route('/dashboard')
@login_required
def dashboard_panel():
    try:
        proyectos = Proyecto.query.all()
        print(f"✅ Dashboard - Proyectos encontrados: {len(proyectos)}")
        return render_template('dashboard/panel.html', categories=proyectos)
    except Exception as e:
        print(f"❌ Error en dashboard: {e}")
        flash(f'Error cargando el dashboard: {e}', 'error')
        return render_template('dashboard/panel.html', categories=[])

# Crear Proyecto (desde panel)
@app.route('/dashboard/crear_proyecto', methods=['POST'])
@login_required
def crear_proyecto():
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        
        print(f"📝 Intentando crear proyecto: {name}")
        
        if not name or not name.strip():
            flash('El nombre es obligatorio', 'error')
            return redirect(url_for('dashboard_panel'))

        nuevo_proyecto = Proyecto(name=name.strip(), description=description)
        
        # Procesar imagen de portada
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Crear directorio si no existe
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                nuevo_proyecto.cover_image = filename
                print(f"📸 Imagen guardada: {filename}")
        
        db.session.add(nuevo_proyecto)
        db.session.commit()
        
        print(f"✅ Proyecto creado exitosamente: {name} (ID: {nuevo_proyecto.id})")
        flash('Proyecto creado exitosamente!', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al crear proyecto: {e}")
        flash(f'Error al crear proyecto: {str(e)}', 'error')
    
    return redirect(url_for('dashboard_panel'))

# Subir Imágenes
@app.route('/dashboard/subir_imagen/<int:proyecto_id>', methods=['POST'])
@login_required
def subir_imagen(proyecto_id):
    try:
        files = request.files.getlist('image')
        title = request.form.get('title')

        print(f"📸 Intentando subir imágenes para proyecto {proyecto_id}")

        if not files or all(file.filename == '' for file in files):
            flash('Selecciona al menos una imagen', 'error')
            return redirect(url_for('dashboard_panel'))

        uploaded_count = 0
        for file in files:
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Crear directorio si no existe
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)
                img = Image(filename=filename, proyecto_id=proyecto_id, title=title)
                db.session.add(img)
                uploaded_count += 1
                print(f"✅ Imagen subida: {filename}")

        if uploaded_count > 0:
            db.session.commit()
            flash(f'✅ {uploaded_count} imagen(es) subida(s) exitosamente!', 'success')
        else:
            flash('❌ No se pudieron subir las imágenes', 'error')
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al subir imágenes: {e}")
        flash(f'Error al subir imágenes: {str(e)}', 'error')
    
    return redirect(url_for('dashboard_panel'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.static_folder, 'uploads'), filename)


# Eliminar Imagen
@app.route('/dashboard/eliminar_imagen/<int:image_id>', methods=['POST'])
@login_required
def eliminar_imagen(image_id):
    try:
        img = Image.query.get_or_404(image_id)
        db.session.delete(img)
        db.session.commit()
        flash('Imagen eliminada exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar imagen: {str(e)}', 'error')
    
    return redirect(url_for('dashboard_panel'))

@app.route('/dashboard/subir_pdf/<int:proyecto_id>', methods=['POST'])
@login_required
def subir_pdf(proyecto_id):
    try:
        file = request.files.get('pdf')
        title = request.form.get('title')

        if not file or file.filename == '':
            flash('Selecciona un archivo PDF', 'error')
            return redirect(url_for('dashboard_panel'))

        if allowed_file(file.filename) and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)

            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)

            pdf = PDFFile(filename=filename, title=title, proyecto_id=proyecto_id)
            db.session.add(pdf)
            db.session.commit()

            flash('PDF subido exitosamente!', 'success')
        else:
            flash('Archivo no permitido. Debe ser PDF.', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir PDF: {str(e)}', 'error')

    return redirect(url_for('dashboard_panel'))

@app.route('/dashboard/eliminar_pdf/<int:pdf_id>', methods=['POST'])
@login_required
def eliminar_pdf(pdf_id):
    try:
        pdf = PDFFile.query.get_or_404(pdf_id)

        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        db.session.delete(pdf)
        db.session.commit()
        flash('PDF eliminado exitosamente!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar PDF: {str(e)}', 'error')

    return redirect(url_for('dashboard_panel'))

@app.route('/ver_pdf/<path:filename>')
def ver_pdf(filename):
    return send_from_directory(
        os.path.join(app.static_folder, 'uploads'),
        filename,
        mimetype="application/pdf",
        as_attachment=False
    )

# Editar Proyecto
@app.route('/dashboard/editar_proyecto/<int:proyecto_id>', methods=['GET', 'POST'])
@login_required
def editar_proyecto(proyecto_id):
    try:
        proyecto = Proyecto.query.get_or_404(proyecto_id)
        
        if request.method == 'POST':
            try:
                proyecto.name = request.form.get('name')
                proyecto.description = request.form.get('description')
                
                print(f"📝 Editando proyecto: {proyecto.name}")
                
                if 'cover_image' in request.files:
                    file = request.files['cover_image']
                    if file and file.filename != '' and allowed_file(file.filename):
                        # Eliminar imagen anterior si existe
                        if proyecto.cover_image:
                            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], proyecto.cover_image)
                            if os.path.exists(old_image_path):
                                os.remove(old_image_path)
                                print(f"🗑️ Imagen anterior eliminada: {proyecto.cover_image}")
                        
                        # Guardar nueva imagen
                        filename = secure_filename(file.filename)
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        proyecto.cover_image = filename
                        print(f"📸 Nueva imagen guardada: {filename}")
                
                db.session.commit()
                flash('Proyecto actualizado exitosamente!', 'success')
                return redirect(url_for('dashboard_panel'))
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error al actualizar proyecto: {e}")
                flash(f'Error al actualizar proyecto: {str(e)}', 'error')
        
        return render_template('dashboard/editar_proyecto.html', proyecto=proyecto)
        
    except Exception as e:
        print(f"❌ Error cargando página de edición: {e}")
        flash(f'Error cargando el proyecto: {str(e)}', 'error')
        return redirect(url_for('dashboard_panel'))

# Eliminar Proyecto
@app.route('/dashboard/eliminar_proyecto/<int:proyecto_id>', methods=['POST'])
@login_required
def eliminar_proyecto(proyecto_id):
    try:
        proyecto = Proyecto.query.get_or_404(proyecto_id)
        
        if proyecto.cover_image:
            cover_path = os.path.join(app.config['UPLOAD_FOLDER'], proyecto.cover_image)
            if os.path.exists(cover_path):
                os.remove(cover_path)
        
        for image in proyecto.images:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(proyecto)
        db.session.commit()
        flash('Proyecto eliminado exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar proyecto: {str(e)}', 'error')
    
    return redirect(url_for('dashboard_panel'))

if __name__ == '__main__':
    # Crear directorios necesarios
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)


