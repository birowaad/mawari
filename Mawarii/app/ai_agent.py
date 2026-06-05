# app/ai_agent.py
import json
import random
from datetime import datetime
from collections import Counter
import numpy as np

class AIAgent:
    """وكيل ذكي لتحليل سلوك المستخدم وتقديم توصيات مخصصة"""
    
    def __init__(self, db_session, recommendation_engine):
        self.db = db_session
        self.recommendation_engine = recommendation_engine
        self.user_profiles = {}
        
    def analyze_user_behavior(self, user_id):
        """تحليل سلوك المستخدم بناءً على تفاعلاته السابقة"""
        from app.models import UserInteraction
        
        interactions = self.db.query(UserInteraction).filter_by(user_id=user_id).all()
        
        if not interactions:
            return None
        
        # تحليل أنماط التفاعل
        interaction_types = [i.interaction_type for i in interactions]
        model_ids = [i.model_id for i in interactions]
        total_duration = sum(i.duration_seconds or 0 for i in interactions)
        
        # حساب مقاييس السلوك
        behavior_analysis = {
            'user_id': user_id,
            'total_interactions': len(interactions),
            'most_viewed_type': Counter(interaction_types).most_common(1)[0][0] if interaction_types else 'unknown',
            'favorite_model': Counter(model_ids).most_common(1)[0][0] if model_ids else None,
            'total_time_spent': total_duration,
            'avg_interaction_duration': total_duration / len(interactions) if interactions else 0,
            'engagement_score': min(100, len(interactions) * 5 + (total_duration / 60)),
            'last_active': interactions[-1].created_at if interactions else None
        }
        
        # تحديث ملف المستخدم
        self.user_profiles[user_id] = behavior_analysis
        
        return behavior_analysis
    
    def predict_interest_evolution(self, user_id, days_ahead=7):
        """توقع تطور اهتمامات المستخدم مستقبلاً"""
        behavior = self.analyze_user_behavior(user_id)
        
        if not behavior:
            return None
        
        # نموذج بسيط لتوقع الاهتمامات
        base_interests = self.get_user_interests(user_id)
        
        if behavior['engagement_score'] > 70:
            # مستخدم متفاعل - إضافة اهتمامات متقدمة
            advanced_interests = ['architecture', 'history', 'archaeology']
            return list(set(base_interests + advanced_interests))
        elif behavior['engagement_score'] > 40:
            # مستخدم متوسط - اهتمامات متنوعة
            varied_interests = ['culture', 'heritage', 'artifacts']
            return list(set(base_interests + varied_interests))
        else:
            # مستخدم جديد - اهتمامات أساسية
            return base_interests
    
    def get_user_interests(self, user_id):
        """الحصول على اهتمامات المستخدم من قاعدة البيانات"""
        from app.models import User
        user = self.db.query(User).filter_by(id=user_id).first()
        if user and user.interests:
            return [i.strip() for i in user.interests.split(',') if i.strip()]
        return []
    
    def get_contextual_recommendations(self, user_id, current_model_id=None, time_of_day=None):
        """توصيات سياقية (حسب الوقت والموقع الحالي)"""
        if time_of_day is None:
            hour = datetime.now().hour
            if hour < 12:
                time_context = 'morning'
            elif hour < 18:
                time_context = 'afternoon'
            else:
                time_context = 'evening'
        else:
            time_context = time_of_day
        
        user_interests = self.get_user_interests(user_id)
        
        if not user_interests:
            return []
        
        # تعديل الاهتمامات حسب السياق الزمني
        contextual_interests = user_interests.copy()
        
        if time_context == 'morning':
            contextual_interests.append('educational')
        elif time_context == 'afternoon':
            contextual_interests.append('exploration')
        else:  # evening
            contextual_interests.append('relaxing')
        
        # استبعاد النموذج الحالي (إذا كان موجوداً)
        recommendations = self.recommendation_engine.get_recommendations(
            contextual_interests, 
            top_n=6
        )
        
        if current_model_id:
            recommendations = [r for r in recommendations if r['model'].get('id') != current_model_id]
        
        return recommendations[:4]
    
    def generate_learning_path(self, user_id, num_steps=5):
        """توليد مسار تعلم مخصص للمستخدم"""
        behavior = self.analyze_user_behavior(user_id)
        user_interests = self.get_user_interests(user_id)
        
        if not user_interests:
            return []
        
        # الحصول على جميع التوصيات
        all_recommendations = self.recommendation_engine.get_recommendations(
            user_interests, 
            top_n=20
        )
        
        # تقسيم المسار إلى مستويات
        learning_path = []
        
        # المستوى 1: أساسي (أعلى تشابه)
        basic = [r for r in all_recommendations if r['similarity_score'] > 70][:2]
        
        # المستوى 2: متوسط
        intermediate = [r for r in all_recommendations if 40 < r['similarity_score'] <= 70][:2]
        
        # المستوى 3: متقدم
        advanced = [r for r in all_recommendations if r['similarity_score'] <= 40][:1]
        
        learning_path = basic + intermediate + advanced
        
        return learning_path[:num_steps]
    
    def get_insights(self, user_id):
        """تقديم رؤى وتحليلات للمستخدم"""
        behavior = self.analyze_user_behavior(user_id)
        
        if not behavior:
            return {
                'message': 'Complete your first exploration to get insights!',
                'next_step': 'Explore your first heritage site'
            }
        
        insights = []
        
        # تحليل الاهتمامات السائدة
        if behavior['engagement_score'] > 80:
            insights.append("You're a heritage expert! 🎓")
        elif behavior['engagement_score'] > 50:
            insights.append("You're building great heritage knowledge! 📚")
        else:
            insights.append("Keep exploring to discover more heritage sites! 🌍")
        
        # نصائح مخصصة
        if behavior['most_viewed_type'] == 'listen':
            insights.append("You love audio stories - try the interactive hotspots too!")
        elif behavior['most_viewed_type'] == 'view':
            insights.append("You enjoy 3D models - don't miss the audio narrations!")
        
        # تقدير الوقت المستغرق
        hours = behavior['total_time_spent'] // 60
        if hours > 0:
            insights.append(f"You've spent {hours} hours exploring AlUla's heritage!")
        
        return {
            'insights': insights,
            'engagement_score': behavior['engagement_score'],
            'next_recommendation': self.generate_learning_path(user_id, num_steps=1)[0] if self.generate_learning_path(user_id, num_steps=1) else None
        }
