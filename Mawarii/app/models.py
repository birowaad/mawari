from . import db

# ------------------------------
# User Model
# ------------------------------
class User(db.Model):
    __tablename__ = 'users'  # optional, makes table name explicit

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"
        # app/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # NEW: Store user preferences as JSON
    preferences = db.Column(db.Text, default='{}')  # JSON string
    interests = db.Column(db.String(500), default='')  # Comma-separated interests
    experience_level = db.Column(db.String(50), default='beginner')  # beginner, intermediate, expert
    
    def set_preferences(self, prefs_dict):
        """Store preferences as JSON string"""
        self.preferences = json.dumps(prefs_dict)
    
    def get_preferences(self):
        """Retrieve preferences as dictionary"""
        return json.loads(self.preferences) if self.preferences else {}
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'


class Model3D(db.Model):
    """3D Model for heritage sites and artifacts"""
    __tablename__ = 'models_3d'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)  # 'site', 'artifact', 'desert'
    file_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500))
    
    # NEW: Content tags for recommendations
    tags = db.Column(db.String(500), default='')  # Comma-separated tags like "architecture,history,nabataean"
    
    story_en = db.Column(db.Text)
    story_ar = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    def get_tags_list(self):
        """Return tags as list"""
        return [t.strip() for t in self.tags.split(',') if t.strip()]
    
    def __repr__(self):
        return f'<Model3D {self.name}>'
