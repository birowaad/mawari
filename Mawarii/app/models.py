# app/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """نموذج المستخدم - يدعم الأدوار (Admin / User) والتخصيص"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ========== تخصيص المستخدم ==========
    interests = db.Column(db.String(500), default='')  # اهتمامات المستخدم (مفصولة بفواصل)
    experience_level = db.Column(db.String(50), default='beginner')  # beginner, intermediate, expert
    preferences = db.Column(db.Text, default='{}')  # تفضيلات إضافية بصيغة JSON
    
    # ========== العلاقات ==========
    interactions = db.relationship('UserInteraction', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """تشفير كلمة المرور"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """التحقق من كلمة المرور"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """التحقق من صلاحيات المدير"""
        return self.role == 'admin'
    
    def get_preferences(self):
        """الحصول على التفضيلات بصيغة قاموس"""
        try:
            return json.loads(self.preferences) if self.preferences else {}
        except:
            return {}
    
    def set_preferences(self, prefs_dict):
        """تخزين التفضيلات كـ JSON"""
        self.preferences = json.dumps(prefs_dict)
    
    def get_interests_list(self):
        """الحصول على اهتمامات المستخدم كقائمة"""
        return [i.strip() for i in self.interests.split(',') if i.strip()] if self.interests else []
    
    def get_total_time_spent(self):
        """حساب إجمالي وقت الاستكشاف"""
        total = sum(i.duration_seconds or 0 for i in self.interactions)
        return total // 60  # تحويل إلى دقائق
    
    def get_total_stories_listened(self):
        """حساب عدد القصص المستمعة"""
        return self.interactions.filter_by(interaction_type='listen').count()
    
    def get_explored_models_count(self):
        """حساب عدد المجسمات المستكشفة"""
        return self.interactions.filter_by(interaction_type='explore').distinct('model_id').count()
    
    def get_id(self):
        return str(self.id)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Model3D(db.Model):
    """نموذج المجسمات ثلاثية الأبعاد"""
    __tablename__ = 'models_3d'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)  # 'site', 'artifact', 'desert'
    file_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500))
    
    # ========== وسوم المحتوى للتوصيات ==========
    tags = db.Column(db.String(500), default='')  # وسوم مفصولة بفواصل
    
    # ========== القصص الصوتية والنصية ==========
    story_en = db.Column(db.Text)  # القصة بالإنجليزية
    story_ar = db.Column(db.Text)  # القصة بالعربية
    
    # ========== إعدادات العرض ==========
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    
    # ========== البيانات الزمنية ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ========== العلاقات ==========
    interactions = db.relationship('UserInteraction', back_populates='model', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_tags_list(self):
        """الحصول على الوسوم كقائمة"""
        return [t.strip() for t in self.tags.split(',') if t.strip()]
    
    def get_story(self, language='en'):
        """الحصول على القصة حسب اللغة"""
        return self.story_en if language == 'en' else self.story_ar
    
    def get_total_views(self):
        """حساب عدد المشاهدات"""
        return self.interactions.filter_by(interaction_type='view').count()
    
    def get_total_listens(self):
        """حساب عدد مرات الاستماع"""
        return self.interactions.filter_by(interaction_type='listen').count()
    
    def get_total_explores(self):
        """حساب عدد مرات الاستكشاف"""
        return self.interactions.filter_by(interaction_type='explore').count()
    
    def get_avg_time_spent(self):
        """حساب متوسط الوقت المستغرق"""
        avg = self.interactions.with_entities(db.func.avg(UserInteraction.duration_seconds)).scalar()
        return round(avg / 60, 1) if avg else 0
    
    def __repr__(self):
        return f'<Model3D {self.name}>'


class UserInteraction(db.Model):
    """تسجيل تفاعلات المستخدم مع المجسمات (للتحليلات والتوصيات)"""
    __tablename__ = 'user_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ========== المفاتيح الخارجية ==========
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('models_3d.id'), nullable=False)
    
    # ========== نوع التفاعل ==========
    interaction_type = db.Column(db.String(50), nullable=False)  
    # القيم الممكنة: 'view', 'listen', 'explore', 'share', 'hotspot_click'
    
    # ========== بيانات التفاعل ==========
    duration_seconds = db.Column(db.Integer, default=0)  # الوقت المستغرق بالثواني
    completion_percentage = db.Column(db.Float, default=0.0)  # نسبة الإكمال (0-100)
    
    # ========== بيانات إضافية ==========
    metadata = db.Column(db.Text, default='{}')  # بيانات إضافية بصيغة JSON
    
    # ========== البيانات الزمنية ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ========== العلاقات ==========
    user = db.relationship('User', back_populates='interactions')
    model = db.relationship('Model3D', back_populates='interactions')
    
    def get_metadata(self):
        """الحصول على البيانات الإضافية كقاموس"""
        try:
            return json.loads(self.metadata) if self.metadata else {}
        except:
            return {}
    
    def set_metadata(self, data_dict):
        """تخزين البيانات الإضافية كـ JSON"""
        self.metadata = json.dumps(data_dict)
    
    @classmethod
    def log_interaction(cls, db_session, user_id, model_id, interaction_type, duration=0, completion=0, **kwargs):
        """تسجيل تفاعل جديد (طريقة مساعدة)"""
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
    
    def __repr__(self):
        return f'<UserInteraction {self.user_id}:{self.model_id} - {self.interaction_type}>'


class Notification(db.Model):
    """نموذج الإشعارات للمستخدمين (اختياري - للمراحل المستقبلية)"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  # 'info', 'success', 'warning', 'achievement'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.title}>'


class Achievement(db.Model):
    """نموذج الإنجازات (لنظام Gamification - للمراحل المستقبلية)"""
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='🏆')
    points = db.Column(db.Integer, default=10)
    requirement_type = db.Column(db.String(50))  # 'explore_count', 'listen_count', 'time_spent'
    requirement_value = db.Column(db.Integer, default=1)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'


class UserAchievement(db.Model):
    """ربط الإنجازات بالمستخدمين"""
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='user_achievements')
    achievement = db.relationship('Achievement', backref='user_achievements')
    
    def __repr__(self):
        return f'<UserAchievement {self.user_id}:{self.achievement_id}>'
