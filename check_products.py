from database import db

print("="*60)
print("DATABASE PRODUCTS CHECK")
print("="*60)

total = db.products.count_documents({})
print(f"\n📦 Total products in database: {total}")

if total == 0:
    print("\n❌ NO PRODUCTS FOUND!")
    print("\nYou need to load products from CSV. Run:")
    print("   python load_products.py")
else:
    print("\n📋 Sample products:")
    sample = list(db.products.find({}, {'_id': 0}).limit(5))
    for i, prod in enumerate(sample):
        print(f"\nProduct {i+1}:")
        for key, value in prod.items():
            if key != '_id':
                print(f"   {key}: {str(value)[:50]}")

print("\n" + "="*60)