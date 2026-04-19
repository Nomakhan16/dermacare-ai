# database.py
import os
import ssl
from pymongo import MongoClient
from datetime import datetime

class Database:
    def __init__(self):
        # Get MongoDB URI from environment variable
        mongodb_uri = os.environ.get('MONGODB_URI')
        
        # If no environment variable, fall back to localhost (for development)
        if not mongodb_uri:
            print("⚠️ MONGODB_URI not set, using localhost (development mode)")
            mongodb_uri = 'mongodb://localhost:27017/'
            self.client = MongoClient(mongodb_uri)
        else:
            # For production (MongoDB Atlas), add SSL configuration
            print(f"✅ Connecting to MongoDB Atlas...")
            self.client = MongoClient(
                mongodb_uri,
                tls=True,
                tlsAllowInvalidCertificates=True  # Required for some Atlas setups
            )
        
        self.db = self.client['dermacare_db']
        self.users = self.db['users']
        self.products = self.db['products']
        
        # Create index on email for faster lookup
        self.users.create_index('email', unique=True)
        print("✅ Connected to MongoDB successfully")
    
    def get_user(self, email):
        return self.users.find_one({'email': email})
    
    def create_user(self, email, name, password, skin_type='Normal', hair_type='Normal'):
        user = {
            'email': email,
            'name': name,
            'password': password,
            'skin_type': skin_type,
            'hair_type': hair_type,
            'created': datetime.now().strftime('%Y-%m-%d'),
            'history': []
        }
        return self.users.insert_one(user)
    
    def update_user(self, email, updates):
        return self.users.update_one({'email': email}, {'$set': updates})
    
    def add_to_history(self, email, history_entry):
        return self.users.update_one(
            {'email': email},
            {'$push': {'history': {'$each': [history_entry], '$position': 0}}}
        )
    
    def clear_history(self, email):
        return self.users.update_one(
            {'email': email},
            {'$set': {'history': []}}
        )
    
    def user_exists(self, email):
        return self.users.find_one({'email': email}) is not None
    
    def load_products_from_csv(self, csv_path='data/dermacare_dataset.csv'):
        import pandas as pd
        df = pd.read_csv(csv_path)
        products = df.to_dict('records')
        self.products.delete_many({})
        self.products.insert_many(products)
        print(f"✅ Loaded {len(products)} products to MongoDB")
    
    def get_products_by_condition(self, condition, category='skin'):
        query = {}
        if category == 'skin':
            query = {
                '$or': [
                    {'target_hydration': {'$regex': condition, '$options': 'i'}},
                    {'skin_tone': {'$regex': condition, '$options': 'i'}},
                    {'concern': {'$regex': condition, '$options': 'i'}}
                ]
            }
        else:
            query = {
                '$or': [
                    {'hair_type': {'$regex': condition, '$options': 'i'}},
                    {'hair_scalp': {'$regex': condition, '$options': 'i'}},
                    {'hair_concern': {'$regex': condition, '$options': 'i'}}
                ]
            }
        return list(self.products.find(query, {'_id': 0}).limit(3))

# Create instance
db = Database()