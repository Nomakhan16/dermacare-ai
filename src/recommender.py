import joblib
from sklearn.ensemble import RandomForestClassifier

class SkinRecommender:
    def __init__(self):
        self.model = RandomForestClassifier()
    
    def train(self, X, y):
        self.model.fit(X, y)
    
    def predict(self, features):
        return self.model.predict(features)