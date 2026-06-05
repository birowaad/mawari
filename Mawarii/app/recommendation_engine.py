# في app/recommendation_engine.py (ملف جديد)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json

class RecommendationEngine:
    def __init__(self, models_data):
        self.models = models_data
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = None
        self.build_matrix()
    
    def build_matrix(self):
        """بناء مصفوفة TF-IDF من وسوم المجسمات"""
        tags_list = [model.get('tags', '') for model in self.models]
        self.tfidf_matrix = self.vectorizer.fit_transform(tags_list)
    
    def get_recommendations(self, user_tags, top_n=5):
        """الحصول على توصيات مخصصة للمستخدم"""
        user_vector = self.vectorizer.transform([user_tags])
        similarities = cosine_similarity(user_vector, self.tfidf_matrix).flatten()
        
        # ترتيب النتائج حسب التشابه
        indices = np.argsort(similarities)[::-1][:top_n]
        
        recommendations = []
        for idx in indices:
            if similarities[idx] > 0:
                recommendations.append({
                    'model': self.models[idx],
                    'similarity_score': round(float(similarities[idx]), 4)
                })
        return recommendations
