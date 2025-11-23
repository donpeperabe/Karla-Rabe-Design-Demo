import os
from flask import Flask, render_template, request, redirect, url_for, flash, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Configuración
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')

# Usar PostgreSQL en Render, SQLite localmente
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///app.db'

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

# Configuración Login
login_manager.login_view = 'auth_login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# INICIALIZACIÓN DE BASE DE DATOS
def init_db():
    with app.app_context():
        try:
            db.create_all()
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin_user = User(username='admin', is_admin=True)
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Usuario admin creado: admin / admin123")
            print("✅ Base de datos inicializada correctamente")
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")

init_db()

# Utilidades
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

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
        
        if not name:
            flash('El nombre es obligatorio', 'error')
            return redirect(url_for('dashboard_panel'))

        nuevo_proyecto = Proyecto(name=name, description=description)
        
        # Procesar imagen de portada
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
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

# Editar Proyecto
@app.route('/dashboard/editar_proyecto/<int:proyecto_id>', methods=['GET', 'POST'])
@login_required
def editar_proyecto(proyecto_id):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    if request.method == 'POST':
        try:
            proyecto.name = request.form.get('name')
            proyecto.description = request.form.get('description')
            
            if 'cover_image' in request.files:
                file = request.files['cover_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    if proyecto.cover_image:
                        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], proyecto.cover_image)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    proyecto.cover_image = filename
            
            db.session.commit()
            flash('Proyecto actualizado exitosamente!', 'success')
            return redirect(url_for('dashboard_panel'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar proyecto: {str(e)}', 'error')
    
    return render_template('dashboard/editar_proyecto.html', proyecto=proyecto)

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
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', port=5000, debug=True)
