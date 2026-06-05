# app/__init__.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import qrcode
from flask import send_file
import io
import os
import json
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()


# ===========================================================
# MODELS - ORDER MATTERS FOR FOREIGN KEYS
# ===========================================================

# 1. User model (must be first because UserInteraction references it)
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    interests = db.Column(db.String(500), default='')
    experience_level = db.Column(db.String(50), default='beginner')
    preferences = db.Column(db.Text, default='{}')
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def get_preferences(self):
        return json.loads(self.preferences) if self.preferences else {}
    
    def set_preferences(self, prefs_dict):
        self.preferences = json.dumps(prefs_dict)
    
    def get_interests_list(self):
        return [i.strip() for i in self.interests.split(',') if i.strip()] if self.interests else []
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)


# 2. Model3D model (must be before UserInteraction)
class Model3D(db.Model):
    __tablename__ = 'models_3d'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500))
    tags = db.Column(db.String(500), default='')
    story_en = db.Column(db.Text)
    story_ar = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_tags_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]


# 3. UserInteraction model (depends on User and Model3D)
class UserInteraction(db.Model):
    __tablename__ = 'user_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('models_3d.id'), nullable=False)
    interaction_type = db.Column(db.String(50), nullable=False)
    duration_seconds = db.Column(db.Integer, default=0)
    completion_percentage = db.Column(db.Float, default=0.0)
    interaction_data = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_metadata(self):
        try:
            return json.loads(self.interaction_data) if self.interaction_data else {}
        except:
            return {}
    
    def set_metadata(self, data_dict):
        self.interaction_data = json.dumps(data_dict)
    
    @classmethod
    def log_interaction(cls, db_session, user_id, model_id, interaction_type, duration=0, completion=0, **kwargs):
        interaction = cls(
            user_id=user_id,
            model_id=model_id,
            interaction_type=interaction_type,
            duration_seconds=duration,
            completion_percentage=completion
        )
        if kwargs:
            interaction.set_metadata(kwargs)
        db_session.add(interaction)
        db_session.commit()
        return interaction


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app():
    app = Flask(__name__)

    # App config
    app.config['SECRET_KEY'] = 'your-secret-key-change-this'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # ========== CREATE DATABASE TABLES ==========
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Verify tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {tables}")

    # ===========================================================
    # Helper Functions for Interaction Logging
    # ===========================================================
    
    def log_interaction(user_id, model_id, interaction_type, duration=0, completion=0, **kwargs):
        try:
            UserInteraction.log_interaction(
                db.session, user_id, model_id, interaction_type, duration, completion, **kwargs
            )
            print(f"✅ Logged: {interaction_type} | user:{user_id} | model:{model_id}")
            return True
        except Exception as e:
            print(f"❌ Error logging interaction: {e}")
            return False
    
    def log_view_interaction(user_id, model_id, duration=0):
        return log_interaction(user_id, model_id, 'view', duration)
    
    def log_listen_interaction(user_id, model_id, duration=0, completion=100):
        return log_interaction(user_id, model_id, 'listen', duration, completion)
    
    def log_explore_interaction(user_id, model_id, duration=0):
        return log_interaction(user_id, model_id, 'explore', duration)

    # ===========================================================
    # Language Settings
    # ===========================================================

    @app.route('/set_language/<lang>')
    def set_language(lang):
        if lang in ['en', 'ar']:
            session['language'] = lang
        return redirect(request.referrer or url_for('index'))

    @app.context_processor
    def inject_language():
        current_lang = session.get('language', 'en')
        return {
            'current_lang': current_lang,
            'is_rtl': current_lang == 'ar'
        }

    @app.before_request
    def set_default_language():
        if 'language' not in session:
            session['language'] = 'en'

    # ===========================================================
    # Routes
    # ===========================================================

    @app.route('/')
    def index():
        return render_template('index.html', title="AlUla Wonders")

    @app.route('/heritage')
    def heritage():
        return render_template('heritage.html', title="AlUla Heritage Sites")

    @app.route('/qrcode/<model_name>')
    def generate_qrcode(model_name):
        url = url_for('heritage_ar', heritage_id=model_name, _external=True)
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype='image/png')

    @app.route('/heritage/<heritage_id>')
    def heritage_ar(heritage_id):
        heritage_data = {
            'hegra_tomb': {'name': 'Hegra - Qasr al-Farid', 'model_file': 'hegra_tomb.glb'},
            'alula_old_town': {'name': 'AlUla Old Town', 'model_file': 'alula_old_town.glb'},
            'dadan_lion_tombs': {'name': 'Dadan Lion Tombs', 'model_file': 'dadan_lion_tombs.glb'},
            'jabal_ikmah': {'name': 'Jabal Ikmah', 'model_file': 'jabal_ikmah.glb'},
            'ancient_tomb': {'name': 'Ancient Tomb', 'model_file': 'ancient_tomb.glb'},
            'old_city_wall': {'name': 'Old City Wall', 'model_file': 'old_city_wall.glb'}
        }
        info = heritage_data.get(heritage_id, heritage_data['hegra_tomb'])
        return render_template('heritage_detail.html', title=info['name'], heritage=info, heritage_id=heritage_id)

    @app.route('/heritage/ar/<model_name>')
    def heritage_ar_viewer(model_name):
        ar_models = {
            "ancient_tomb": "ancient_tomb.glb",
            "old_city_wall": "old_city_wall.glb",
            "hegra_tomb": "hegra_tomb.glb",
            "alula_old_town": "alula_old_town.glb",
            "dadan_lion_tombs": "dadan_lion_tombs.glb",
            "jabal_ikmah": "jabal_ikmah.glb"
        }
        if model_name not in ar_models:
            return "AR model not found", 404
        return render_template('ar_model.html', title=f"AR View: {model_name.replace('_', ' ').title()}", model_file=ar_models[model_name])

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            if User.query.filter_by(email=email).first():
                flash("Email already exists", "danger")
                return redirect(url_for('register'))

            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))

        return render_template('register.html', title="Register")

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user)
                session['user_id'] = user.id
                session['username'] = user.username
                flash("Login successful!", "success")
                
                if not user.interests:
                    return redirect(url_for('preferences_page'))
                
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid credentials", "danger")
                return redirect(url_for('login'))

        return render_template('login.html', title="Login")

    @app.route('/logout')
    def logout():
        logout_user()
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for('login'))

    @app.route('/dashboard')
    def dashboard():
        if not current_user.is_authenticated:
            flash("Please log in to access the dashboard.", "warning")
            return redirect(url_for('login'))
        
        return render_template('dashboard.html', title="Dashboard", username=current_user.username)

    @app.route('/profile', methods=['GET', 'POST'])
    def profile():
        if not current_user.is_authenticated:
            flash("Please log in to access your profile.", "warning")
            return redirect(url_for('login'))

        user = current_user

        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form.get('password')

            existing_user = User.query.filter(User.email == email, User.id != user.id).first()
            if existing_user:
                flash("Email already in use by another account.", "danger")
                return redirect(url_for('profile'))

            user.username = username
            user.email = email
            if password:
                user.set_password(password)

            db.session.commit()
            session['username'] = user.username
            flash("Profile updated successfully!", "success")
            return redirect(url_for('dashboard'))

        return render_template('profile.html', title="Edit Profile", user=user)

    @app.route('/about')
    def about():
        about_info = {
            "title": "About Mawari",
            "description": "Mawari is a web app inspired by the heritage and landscapes of AlUla, Saudi Arabia.",
            "image": "12.jpg"
        }
        return render_template('about.html', title="About Mawari", about=about_info)

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        return render_template('contact.html', title="Contact Us")

    # PWA Routes
    @app.route('/service-worker.js')
    def service_worker():
        return send_file('static/service-worker.js', mimetype='application/javascript')

    @app.route('/manifest.json')
    def manifest():
        return send_file('static/manifest.json', mimetype='application/manifest+json')

    @app.route('/offline')
    def offline():
        return render_template('offline.html', title="Offline")

    # ===========================================================
    # AI Personalization Routes
    # ===========================================================
    
    @app.route('/preferences', methods=['GET'])
    @login_required
    def preferences_page():
        return render_template('preferences.html', title='Personalize Your Experience')

    @app.route('/save-preferences', methods=['POST'])
    @login_required
    def save_preferences():
        user = current_user
        
        interests = request.form.getlist('interests')
        user.interests = ','.join(interests)
        user.experience_level = request.form.get('experience_level', 'beginner')
        
        prefs = user.get_preferences()
        prefs['tour_duration'] = int(request.form.get('tour_duration', 30))
        user.set_preferences(prefs)
        
        db.session.commit()
        
        flash('Preferences saved successfully!', 'success')
        return redirect(url_for('heritage'))

    @app.route('/profile/preferences', methods=['GET'])
    @login_required
    def edit_preferences():
        return render_template('preferences.html', title='Edit Preferences')

    # ===========================================================
    # API Endpoints for Interaction Logging
    # ===========================================================
    
    @app.route('/api/log/interaction', methods=['POST'])
    @login_required
    def api_log_interaction():
        data = request.get_json()
        
        model_id = data.get('model_id')
        interaction_type = data.get('type')
        duration = data.get('duration', 0)
        completion = data.get('completion', 0)
        metadata = data.get('metadata', {})
        
        if not model_id or not interaction_type:
            return jsonify({'error': 'Missing required fields'}), 400
        
        success = log_interaction(
            current_user.id, model_id, interaction_type, 
            duration, completion, **metadata
        )
        
        if success:
            return jsonify({'status': 'success', 'message': 'Interaction logged'})
        return jsonify({'status': 'error', 'message': 'Failed to log interaction'}), 500
    
    @app.route('/api/log/view', methods=['POST'])
    @login_required
    def api_log_view():
        data = request.get_json()
        model_id = data.get('model_id')
        duration = data.get('duration', 0)
        
        if log_view_interaction(current_user.id, model_id, duration):
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error'}), 500
    
    @app.route('/api/log/listen', methods=['POST'])
    @login_required
    def api_log_listen():
        data = request.get_json()
        model_id = data.get('model_id')
        duration = data.get('duration', 0)
        completion = data.get('completion', 100)
        
        if log_listen_interaction(current_user.id, model_id, duration, completion):
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error'}), 500
    
    @app.route('/api/log/explore', methods=['POST'])
    @login_required
    def api_log_explore():
        data = request.get_json()
        model_id = data.get('model_id')
        
        if log_explore_interaction(current_user.id, model_id):
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error'}), 500

    # ===========================================================
    # User API Endpoints
    # ===========================================================
    
    @app.route('/api/user/preferences')
    @login_required
    def api_user_preferences():
        user = current_user
        return {
            'interests': user.get_interests_list(),
            'experience_level': user.experience_level,
            'preferences': user.get_preferences()
        }

    return app
