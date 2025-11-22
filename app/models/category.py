from app import db

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)

    images = db.relationship("Image", backref="category", lazy=True, cascade="all, delete")

    def __repr__(self):
        return f"<Category {self.name}>"