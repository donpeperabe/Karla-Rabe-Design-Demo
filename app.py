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

# Asegurar que la carpeta de uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth_login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

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

    # Propiedades para compatibilidad
    @property
    def name(self):
        return self.nombre
    
    @property
    def description(self):
        return self.descripcion
    
    @property
    def cover_image(self):
        return self.imagen


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200))
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)


class PDFFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200))
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def init_db():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tablas creadas exitosamente")
            
            # Crear usuario admin si no existe
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


# Inicializar la base de datos
init_db()

# -------------------- UTIL --------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# -------------------- RUTAS PARA ARCHIVOS --------------------

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploaded_pdf/<path:filename>')
def uploaded_pdf(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            proyecto.imagen = filename

        db.session.add(proyecto)
        db.session.commit()
        flash('Proyecto creado exitosamente', 'success')
        return redirect(url_for('dashboard_panel'))
    
    return render_template('proyecto_crear.html')

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
            if proyecto.imagen:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], proyecto.imagen)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            proyecto.imagen = filename

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
    
    if proyecto.imagen:
        path = os.path.join(app.config['UPLOAD_FOLDER'], proyecto.imagen)
        if os.path.exists(path):
            os.remove(path)

    for img in proyecto.images:
        p = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
        if os.path.exists(p):
            os.remove(p)

    for pdf in proyecto.pdffiles:
        p = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
        if os.path.exists(p):
            os.remove(p)

    db.session.delete(proyecto)
    db.session.commit()
    flash('Proyecto eliminado exitosamente', 'success')
    return redirect(url_for('dashboard_panel'))

# -------- SUBIR IMAGEN --------

@app.route('/dashboard/subir_imagen/<int:proyecto_id>', methods=['POST'])
@login_required
def subir_imagen(proyecto_id):
    files = request.files.getlist('image')
    title = request.form.get('title')

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            db.session.add(Image(filename=filename, title=title, proyecto_id=proyecto_id))

    db.session.commit()
    flash('Imágenes subidas exitosamente', 'success')
    return redirect(url_for('dashboard_proyecto_editar', proyecto_id=proyecto_id))

# -------- ELIMINAR IMAGEN --------

@app.route('/dashboard/eliminar_imagen/<int:image_id>', methods=['POST'])
@login_required
def eliminar_imagen(image_id):
    img = Image.query.get_or_404(image_id)
    proyecto_id = img.proyecto_id
    path = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
    if os.path.exists(path):
        os.remove(path)
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

    if not file or not file.filename.endswith('.pdf'):
        flash('Debes subir un PDF válido', 'error')
        return redirect(url_for('dashboard_panel'))

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    db.session.add(PDFFile(filename=filename, title=title, proyecto_id=proyecto_id))
    db.session.commit()
    flash('PDF subido exitosamente', 'success')
    return redirect(url_for('dashboard_panel'))

# -------- ELIMINAR PDF --------

@app.route('/dashboard/eliminar_pdf/<int:pdf_id>', methods=['POST'])
@login_required
def eliminar_pdf(pdf_id):
    pdf = PDFFile.query.get_or_404(pdf_id)
    path = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(pdf)
    db.session.commit()
    flash('PDF eliminado exitosamente', 'success')
    return redirect(url_for('dashboard_panel'))

# -------------------- MANEJO DE ERRORES --------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# -------------------- RUN --------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
