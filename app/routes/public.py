from flask import Blueprint, render_template
from app.models.category import Category

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def home():
    categories = Category.query.all()
    return render_template("public/index.html", categories=categories)

# CAMBIA el nombre de la función para que coincida
@public_bp.route('/category/<int:category_id>')
def category_detail(category_id):  # ← Este nombre debe coincidir con url_for
    category = Category.query.get_or_404(category_id)
    return render_template("public/category.html", category=category)