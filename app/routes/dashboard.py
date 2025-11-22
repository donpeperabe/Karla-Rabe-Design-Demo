import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from app import db
from app.models.category import Category
from app.models.image import Image
from app.utils.file_rules import allowed_file

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@dashboard_bp.route("/")
@login_required
def panel():
    categories = Category.query.all()
    return render_template("dashboard/panel.html", categories=categories)

@dashboard_bp.route("/crear_categoria", methods=["POST"])
@login_required
def crear_categoria():
    name = request.form.get("name")
    description = request.form.get("description")

    if not name:
        flash("El nombre es obligatorio", "error")
        return redirect(url_for("dashboard.panel"))

    new_cat = Category(name=name, description=description)
    
    if 'cover_image' in request.files:
        file = request.files['cover_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
            new_cat.cover_image = filename
    
    db.session.add(new_cat)
    db.session.commit()
    flash("Categoría creada exitosamente!", "success")

    return redirect(url_for("dashboard.panel"))

@dashboard_bp.route("/subir_imagen/<int:category_id>", methods=["POST"])
@login_required
def subir_imagen(category_id):
    files = request.files.getlist("image")
    title = request.form.get("title")

    if not files or all(file.filename == '' for file in files):
        flash("Selecciona al menos una imagen", "error")
        return redirect(url_for("dashboard.panel"))

    uploaded_count = 0
    for file in files:
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            
            try:
                file.save(upload_path)
                img = Image(filename=filename, category_id=category_id, title=title)
                db.session.add(img)
                uploaded_count += 1
            except Exception as e:
                flash(f"Error con {filename}", "error")

    if uploaded_count > 0:
        db.session.commit()
        flash(f"✅ {uploaded_count} imagen(es) subida(s) exitosamente!", "success")
    else:
        flash("❌ No se pudieron subir las imágenes. Verifica el formato.", "error")

    return redirect(url_for("dashboard.panel"))

@dashboard_bp.route("/eliminar_imagen/<int:image_id>", methods=["POST"])
@login_required
def eliminar_imagen(image_id):
    img = Image.query.get_or_404(image_id)

    img_path = os.path.join(current_app.config["UPLOAD_FOLDER"], img.filename)
    if os.path.exists(img_path):
        os.remove(img_path)

    db.session.delete(img)
    db.session.commit()
    flash("Imagen eliminada exitosamente!", "success")

    return redirect(url_for("dashboard.panel"))
@dashboard_bp.route("/editar_categoria/<int:category_id>", methods=["GET", "POST"])
@login_required
def editar_categoria(category_id):
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        # Actualizar datos de la categoría
        category.name = request.form.get("name")
        category.description = request.form.get("description")
        
        # Manejar nueva imagen de portada
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Eliminar imagen anterior si existe
                if category.cover_image:
                    old_image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], category.cover_image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Guardar nueva imagen
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
                category.cover_image = filename
        
        db.session.commit()
        flash("Categoría actualizada exitosamente!", "success")
        return redirect(url_for("dashboard.panel"))
    
    return render_template("dashboard/editar_categoria.html", category=category)

@dashboard_bp.route("/eliminar_categoria/<int:category_id>", methods=["POST"])
@login_required
def eliminar_categoria(category_id):
    category = Category.query.get_or_404(category_id)
    
    # Eliminar imagen de portada si existe
    if category.cover_image:
        cover_path = os.path.join(current_app.config["UPLOAD_FOLDER"], category.cover_image)
        if os.path.exists(cover_path):
            os.remove(cover_path)
    
    # Eliminar todas las imágenes de la categoría
    for image in category.images:
        image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], image.filename)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    # Eliminar la categoría (las imágenes se eliminarán por cascade)
    db.session.delete(category)
    db.session.commit()
    
    flash("Categoría eliminada exitosamente!", "success")
    return redirect(url_for("dashboard.panel"))