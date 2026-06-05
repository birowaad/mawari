# app/recommendation_engine.py
import numpy as np
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import precision_score, recall_score, f1_score
import pickle
import os

class RecommendationEngine:
    """محرك التوصيات الذكي باستخدام TF-IDF و Cosine Similarity"""
    
    def __init__(self, models_data=None):
        self.models = models_data or []
        self.vectorizer = TfidfVectorizer(
            stop_words=['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at'],
            max_features=100,
            ngram_range=(1, 2)
        )
        self.tfidf_matrix = None
        self.model_vectors = {}
        
    def build_index(self):
        """بناء مصفوفة TF-IDF من وسوم ونصوص المجسمات"""
        if not self.models:
            return False
        
        # تجميع النصوص من جميع المجسمات
        documents = []
        for model in self.models:
            text = f"{model.get('tags', '')} {model.get('name', '')} {model.get('description', '')}"
            documents.append(text.lower())
        
        # بناء مصفوفة TF-IDF
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)
        
        # تخزين المتجهات لكل نموذج
        for idx, model in enumerate(self.models):
            self.model_vectors[model.get('id')] = self.tfidf_matrix[idx]
        
        return True
    
    def get_user_vector(self, user_interests, user_experience_level='beginner'):
        """تحويل اهتمامات المستخدم إلى متجه TF-IDF"""
        if not user_interests:
            return None
        
        # معالجة الاهتمامات حسب مستوى الخبرة
        if user_experience_level == 'expert':
            query = ' '.join([f"{interest} advanced deep detailed" for interest in user_interests])
        elif user_experience_level == 'intermediate':
            query = ' '.join([f"{interest} detailed" for interest in user_interests])
        else:  # beginner
            query = ' '.join(user_interests)
        
        return self.vectorizer.transform([query])
    
    def get_recommendations(self, user_interests, user_experience_level='beginner', top_n=5):
        """الحصول على توصيات مخصصة مع درجات التشابه"""
        user_vector = self.get_user_vector(user_interests, user_experience_level)
        
        if user_vector is None or self.tfidf_matrix is None:
            return []
        
        # حساب التشابه باستخدام Cosine Similarity
        similarities = cosine_similarity(user_vector, self.tfidf_matrix).flatten()
        
        # ترتيب النتائج تنازلياً
        indices = np.argsort(similarities)[::-1][:top_n]
        
        recommendations = []
        for idx in indices:
            if similarities[idx] > 0:
                recommendations.append({
                    'model': self.models[idx],
                    'similarity_score': round(float(similarities[idx]) * 100, 2),
                    'rank': len(recommendations) + 1
                })
        
        return recommendations
    
    def evaluate_recommendations(self, test_data):
        """تقييم دقة التوصيات باستخدام معايير علمية"""
        if not test_data:
            return {}
        
        y_true = []
        y_pred = []
        
        for test_item in test_data:
            user_interests = test_item.get('interests', [])
            expected_models = test_item.get('expected_models', [])
            
            recommendations = self.get_recommendations(user_interests, top_n=len(expected_models))
            recommended_ids = [rec['model'].get('id') for rec in recommendations]
            
            # إنشاء مصفوفات للمقارنة
            for model_id in expected_models:
                y_true.append(1)
                y_pred.append(1 if model_id in recommended_ids else 0)
        
        if not y_true:
            return {}
        
        # حساب مقاييس التقييم العلمي
        precision = precision_score(y_true, y_pred, zero_division=0) if len(set(y_pred)) > 1 else 0
        recall = recall_score(y_true, y_pred, zero_division=0) if len(set(y_pred)) > 1 else 0
        f1 = f1_score(y_true, y_pred, zero_division=0) if precision + recall > 0 else 0
        
        return {
            'precision': round(precision * 100, 2),
            'recall': round(recall * 100, 2),
            'f1_score': round(f1 * 100, 2),
            'sample_size': len(test_data)
        }
    
    def save_model(self, path='models/recommendation_engine.pkl'):
        """حفظ نموذج التوصيات للاستخدام لاحقاً"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'tfidf_matrix': self.tfidf_matrix,
                'model_vectors': self.model_vectors,
                'models': self.models
            }, f)
    
    def load_model(self, path='models/recommendation_engine.pkl'):
        """تحميل نموذج التوصيات المحفوظ"""
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.vectorizer = data['vectorizer']
                self.tfidf_matrix = data['tfidf_matrix']
                self.model_vectors = data['model_vectors']
                self.models = data['models']
            return True
        return False
