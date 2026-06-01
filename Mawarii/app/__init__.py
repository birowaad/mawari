# app/__init__.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from flask import send_file
import io
import os

# Initialize SQLAlchemy
db = SQLAlchemy()


# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


def create_app():
    app = Flask(__name__)

    # App config
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # ===========================================================
    # إعدادات اللغة - Language Settings (بدون ملف خارجي)
    # ===========================================================

    @app.route('/set_language/<lang>')
    def set_language(lang):
        """تغيير اللغة"""
        if lang in ['en', 'ar']:
            session['language'] = lang
        return redirect(request.referrer or url_for('index'))

    @app.context_processor
    def inject_language():
        """إضافة متغيرات اللغة إلى جميع القوالب"""
        current_lang = session.get('language', 'en')
        return {
            'current_lang': current_lang,
            'is_rtl': current_lang == 'ar'
        }

    @app.before_request
    def set_default_language():
        """تعيين اللغة الافتراضية"""
        if 'language' not in session:
            session['language'] = 'en'

    # ===========================================================
    # المسارات - Routes
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
            'hegra_tomb': {
                'name': 'Hegra (Mada\'in Saleh) - Qasr al-Farid',
                'description': 'The largest and most famous tomb at Hegra.',
                'history': 'Built during the Nabataean Kingdom in the 1st century CE.',
                'location': 'Hegra Archaeological Site, AlUla',
                'coordinates': '26.8041° N, 37.9656° E',
                'model_file': 'hegra_tomb.glb'
            },
            'alula_old_town': {
                'name': 'AlUla Old Town',
                'description': 'A historic mud-brick village.',
                'history': 'Settled from the 12th century CE.',
                'location': 'AlUla Valley',
                'coordinates': '26.6367° N, 37.9240° E',
                'model_file': 'alula_old_town.glb'
            },
            'dadan_lion_tombs': {
                'name': 'Dadan (Al-Khuraybah)',
                'description': 'Lion tombs carved into red rock.',
                'history': 'Capital of the Dadan and Lihyan kingdoms.',
                'location': 'Dadan, AlUla',
                'coordinates': '26.6500° N, 37.9000° E',
                'model_file': 'dadan_lion_tombs.glb'
            },
            'jabal_ikmah': {
                'name': 'Jabal Ikmah',
                'description': 'Ancient library of inscriptions.',
                'history': 'Used as a ceremonial site for thousands of years.',
                'location': 'Desert area north of AlUla',
                'coordinates': '26.6800° N, 37.8500° E',
                'model_file': 'jabal_ikmah.glb'
            },
            'ancient_tomb': {
                'name': 'Ancient Tomb',
                'description': 'A reconstructed Nabatean tomb in AR.',
                'history': 'Nabataean burial site from the 1st century CE.',
                'location': 'Hegra, AlUla',
                'coordinates': '26.8041° N, 37.9656° E',
                'model_file': 'ancient_tomb.glb'
            },
            'old_city_wall': {
                'name': 'Old City Wall',
                'description': 'The ancient defensive walls of AlUla Old Town.',
                'history': 'Built during the 12th century CE.',
                'location': 'AlUla Old Town',
                'coordinates': '26.6367° N, 37.9240° E',
                'model_file': 'old_city_wall.glb'
            }
        }
        info = heritage_data.get(heritage_id, heritage_data['hegra_tomb'])
        return render_template('heritage_detail.html',
                               title=info['name'],
                               heritage=info,
                               heritage_id=heritage_id)

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
        return render_template('ar_model.html',
                               title=f"AR View: {model_name.replace('_', ' ').title()}",
                               model_file=ar_models[model_name])

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = generate_password_hash(request.form['password'])

            if User.query.filter_by(email=email).first():
                flash("Email already exists", "danger")
                return redirect(url_for('register'))

            new_user = User(username=username, email=email, password=password)
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
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['username'] = user.username
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid credentials", "danger")
                return redirect(url_for('login'))

        return render_template('login.html', title="Login")

    @app.route('/logout')
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for('login'))

    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            flash("Please log in to access the dashboard.", "warning")
            return redirect(url_for('login'))
        return render_template('dashboard.html', title="Dashboard", username=session['username'])

    @app.route('/profile', methods=['GET', 'POST'])
    def profile():
        if 'user_id' not in session:
            flash("Please log in to access your profile.", "warning")
            return redirect(url_for('login'))

        user = User.query.get(session['user_id'])

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
                user.password = generate_password_hash(password)

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

    return app