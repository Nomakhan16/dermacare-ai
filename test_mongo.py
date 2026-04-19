from pymongo import MongoClient

try:
    client = MongoClient('mongodb://localhost:27017/')
    db = client['test_db']
    db.test_collection.insert_one({'test': 'Hello MongoDB!'})
    print("✅ MongoDB is working on Windows!")
    print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure MongoDB is installed and running")