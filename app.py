import os
from flask import Flask, render_template, request, redirect, url_for, flash, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Configuración
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
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

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    images = db.relationship('Image', backref='category', lazy=True, cascade='all, delete')

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

# Configuración Login
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# INICIALIZACIÓN DE BASE DE DATOS
def init_db():
    with app.app_context():
        db.create_all()
        # Crear usuario admin si no existe
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_user = User(username='admin', is_admin=True)
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Usuario admin creado: admin / admin123")

# LLAMAR INICIALIZACIÓN
init_db()

# Utilidades
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# Rutas Públicas
@app.route('/')
def home():
    categories = Category.query.all()
    return render_template('index.html', categories=categories)

@app.route('/category/<int:category_id>')
def category_detail(category_id):
    category = Category.query.get_or_404(category_id)
    return render_template('public/category.html', category=category)

# Rutas de Autenticación
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    return render_template('auth/login.html')

@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    categories = Category.query.all()
    return render_template('dashboard/panel.html', categories=categories)

@app.route('/dashboard/crear_categoria', methods=['POST'])
@login_required
def crear_categoria():
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('El nombre es obligatorio', 'error')
        return redirect(url_for('dashboard'))

    new_cat = Category(name=name, description=description)
    
    if 'cover_image' in request.files:
        file = request.files['cover_image']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_cat.cover_image = filename
    
    db.session.add(new_cat)
    db.session.commit()
    flash('Categoría creada exitosamente!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/subir_imagen/<int:category_id>', methods=['POST'])
@login_required
def subir_imagen(category_id):
    files = request.files.getlist('image')
    title = request.form.get('title')

    if not files or all(file.filename == '' for file in files):
        flash('Selecciona al menos una imagen', 'error')
        return redirect(url_for('dashboard'))

    uploaded_count = 0
    for file in files:
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            img = Image(filename=filename, category_id=category_id, title=title)
            db.session.add(img)
            uploaded_count += 1

    if uploaded_count > 0:
        db.session.commit()
        flash(f'✅ {uploaded_count} imagen(es) subida(s) exitosamente!', 'success')
    else:
        flash('❌ No se pudieron subir las imágenes', 'error')

    return redirect(url_for('dashboard'))

@app.route('/dashboard/eliminar_imagen/<int:image_id>', methods=['POST'])
@login_required
def eliminar_imagen(image_id):
    img = Image.query.get_or_404(image_id)
    db.session.delete(img)
    db.session.commit()
    flash('Imagen eliminada exitosamente!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Crear carpeta uploads si no existe
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    app.run(host='0.0.0.0', port=5000, debug=True)
