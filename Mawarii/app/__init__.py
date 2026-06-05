# app/__init__.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import qrcode
from flask import send_file
import io
import os
import json
from datetime import datetime, timedelta
import csv
from io import StringIO

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()


# ===========================================================
# MODELS
# ===========================================================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')
    interests = db.Column(db.String(500), default='')
    experience_level = db.Column(db.String(50), default='beginner')
    preferences = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    
    def is_admin(self):
        return self.role == 'admin'
    
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

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # ========== CREATE DATABASE TABLES ==========
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Create default admin user if not exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                email='admin@mawari.com',
                role='admin',
                interests='',
                experience_level='expert'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Default admin created: username='admin', password='admin123'")

    # ===========================================================
    # Helper Functions
    # ===========================================================
    
    def admin_required(f):
        """Decorator to check if user is admin"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin():
                flash('Access denied. Admin privileges required.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function

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
    # Main Routes
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
            'alula_old_town': {'name': 'AlUla Old Town', 'model_file': 'alula_old_town.glb'}
        }
        info = heritage_data.get(heritage_id, heritage_data['hegra_tomb'])
        return render_template('heritage_detail.html', title=info['name'], heritage=info, heritage_id=heritage_id)

    @app.route('/heritage/ar/<model_name>')
    def heritage_ar_viewer(model_name):
        ar_models = {
            "ancient_tomb": "ancient_tomb.glb",
            "old_city_wall": "old_city_wall.glb",
            "hegra_tomb": "hegra_tomb.glb"
        }
        if model_name not in ar_models:
            return "AR model not found", 404
        return render_template('ar_model.html', title=f"AR View: {model_name.replace('_', ' ').title()}", model_file=ar_models[model_name])

    @app.route('/virtual-city-tour')
    def virtual_city_tour():
        """Virtual city tour page with gamification and AI recommendations"""
        return render_template('virtual_city_tour.html', title='Virtual City Tour | AlUla Heritage')

    # ===========================================================
    # Authentication Routes
    # ===========================================================

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
                user.last_login = datetime.utcnow()
                db.session.commit()
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
    # API Endpoints
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

    # ===========================================================
    # ADMIN DASHBOARD - ANALYTICS & EXPORTS
    # ===========================================================
    
    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        """Admin main dashboard"""
        return render_template('admin_dashboard.html', title='Admin Dashboard')
    
    @app.route('/admin/analytics')
    @login_required
    @admin_required
    def admin_analytics():
        """Admin analytics page with statistics"""
        total_users = User.query.count()
        total_interactions = UserInteraction.query.count()
        total_models = Model3D.query.count()
        admin_count = User.query.filter_by(role='admin').count()
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_last_week = User.query.filter(User.created_at >= week_ago).count()
        interactions_last_week = UserInteraction.query.filter(UserInteraction.created_at >= week_ago).count()
        
        top_models = db.session.query(
            Model3D.name,
            db.func.count(UserInteraction.id).label('count')
        ).join(UserInteraction, Model3D.id == UserInteraction.model_id).group_by(Model3D.id).order_by(db.desc('count')).limit(5).all()
        
        top_users = db.session.query(
            User.username,
            db.func.count(UserInteraction.id).label('count')
        ).join(UserInteraction, User.id == UserInteraction.user_id).group_by(User.id).order_by(db.desc('count')).limit(5).all()
        
        interaction_types = db.session.query(
            UserInteraction.interaction_type,
            db.func.count(UserInteraction.id).label('count')
        ).group_by(UserInteraction.interaction_type).all()
        
        avg_listen_time = db.session.query(db.func.avg(UserInteraction.duration_seconds)).filter_by(interaction_type='listen').scalar() or 0
        avg_completion = db.session.query(db.func.avg(UserInteraction.completion_percentage)).scalar() or 0
        
        daily_activity = db.session.query(
            db.func.date(UserInteraction.created_at).label('date'),
            db.func.count(UserInteraction.id).label('count')
        ).group_by(db.func.date(UserInteraction.created_at)).order_by(db.desc('date')).limit(14).all()
        
        users_with_interests = User.query.filter(User.interests != '').count()
        
        return render_template('admin_analytics.html',
                              total_users=total_users,
                              total_interactions=total_interactions,
                              total_models=total_models,
                              admin_count=admin_count,
                              new_users_last_week=new_users_last_week,
                              interactions_last_week=interactions_last_week,
                              top_models=top_models,
                              top_users=top_users,
                              interaction_types=interaction_types,
                              avg_listen_time=int(avg_listen_time),
                              avg_completion=round(avg_completion, 1),
                              daily_activity=daily_activity,
                              users_with_interests=users_with_interests)
    
    @app.route('/admin/users')
    @login_required
    @admin_required
    def admin_users():
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin_users.html', users=users)
    
    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def admin_delete_user(user_id):
        user = User.query.get(user_id)
        if user and user.id != current_user.id:
            db.session.delete(user)
            db.session.commit()
            flash(f'User {user.username} has been deleted.', 'success')
        else:
            flash('Cannot delete this user.', 'danger')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
    @login_required
    @admin_required
    def admin_toggle_admin(user_id):
        user = User.query.get(user_id)
        if user and user.id != current_user.id:
            user.role = 'user' if user.role == 'admin' else 'admin'
            db.session.commit()
            flash(f'User {user.username} role updated to {user.role}.', 'success')
        return redirect(url_for('admin_users'))
    
    # ===========================================================
    # EXPORT ROUTES
    # ===========================================================
    
    @app.route('/admin/export/users')
    @login_required
    @admin_required
    def export_users_csv():
        users = User.query.all()
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Username', 'Email', 'Role', 'Interests', 'Experience Level', 'Created At', 'Last Login'])
        
        for user in users:
            writer.writerow([
                user.id, user.username, user.email, user.role,
                user.interests, user.experience_level, user.created_at, user.last_login
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=users_export.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
    
    @app.route('/admin/export/interactions')
    @login_required
    @admin_required
    def export_interactions_csv():
        interactions = UserInteraction.query.all()
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'User ID', 'Model ID', 'Interaction Type', 'Duration (s)', 'Completion %', 'Created At'])
        
        for interaction in interactions:
            writer.writerow([
                interaction.id, interaction.user_id, interaction.model_id,
                interaction.interaction_type, interaction.duration_seconds,
                interaction.completion_percentage, interaction.created_at
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=interactions_export.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
    
    @app.route('/admin/export/metrics')
    @login_required
    @admin_required
    def export_metrics_csv():
        models = Model3D.query.filter_by(is_active=True).all()
        users = User.query.filter(User.interests != '').all()
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['User ID', 'Username', 'Interests', 'Recommendations Count'])
        
        for user in users:
            interests = user.get_interests_list()
            writer.writerow([user.id, user.username, user.interests, len(interests)])
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=metrics_export.csv'
        response.headers['Content-type'] = 'text/csv'
        return response

    return app
