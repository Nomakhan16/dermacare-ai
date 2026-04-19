import pandas as pd
from datetime import datetime

class ProgressTracker:
    def __init__(self):
        self.progress_data = {}
    
    def log_progress(self, user_id, condition, improvement, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if user_id not in self.progress_data:
            self.progress_data[user_id] = []
        
        self.progress_data[user_id].append({
            'date': date,
            'condition': condition,
            'improvement': improvement
        })
    
    def get_progress(self, user_id):
        return self.progress_data.get(user_id, [])