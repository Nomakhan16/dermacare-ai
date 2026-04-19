from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import joblib
import pandas as pd
from datetime import datetime
import random
import cv2
import numpy as np
from sklearn.preprocessing import LabelEncoder
import re
from database import db
from groq import Groq
from dotenv import load_dotenv
from captcha.image import ImageCaptcha
import io
import base64

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'dermacare-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================
# IMAGE CAPTCHA SETUP
# ============================================
image_captcha = ImageCaptcha(width=250, height=80)

def generate_captcha():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    captcha_text = ''.join(random.choice(chars) for _ in range(5))
    pil_image = image_captcha.generate_image(captcha_text)
    buffered = io.BytesIO()
    pil_image.save(buffered, format='PNG')
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    session['captcha_text'] = captcha_text.upper()
    return img_base64, captcha_text


GROQ_API_KEY = os.getenv('GROQ_API_KEY')
groq_client = Groq(api_key=GROQ_API_KEY)

# ============================================
# LOAD AI MODELS
# ============================================
try:
    skin_model = joblib.load('models/skin_model.pkl')
    skin_le = joblib.load('models/skin_label_encoder.pkl')
    print("✅ Skin AI Model loaded!")
except:
    skin_model = None
    skin_le = None
    print("⚠️ Skin model not found")

try:
    hair_model = joblib.load('models/hair_model.pkl')
    hair_le = joblib.load('models/hair_label_encoder.pkl')
    print("✅ Hair AI Model loaded!")
except:
    hair_model = None
    hair_le = None
    print("⚠️ Hair model not found")

# ============================================
# LOAD PRODUCTS TO MONGODB
# ============================================
try:
    if db.products.count_documents({}) == 0:
        db.load_products_from_csv('data/dermacare_dataset.csv')
    print(f"✅ Products in MongoDB: {db.products.count_documents({})}")
except Exception as e:
    print(f"⚠️ Could not load products: {e}")

# ============================================
# DEMO PRODUCTS DATABASE (FALLBACK)
# ============================================
DEMO_SKIN_PRODUCTS = {
    'Acne': [
        {'name': 'Salicylic Acid Cleanser', 'brand': 'CeraVe', 'category': 'Cleanser', 
         'ingredients': 'Salicylic Acid, Niacinamide, Ceramides', 'for': 'Acne'},
        {'name': 'Benzoyl Peroxide Gel', 'brand': 'La Roche-Posay', 'category': 'Treatment', 
         'ingredients': 'Benzoyl Peroxide 5%', 'for': 'Acne'}
    ],
    'Dry Skin': [
        {'name': 'Hyaluronic Acid Serum', 'brand': 'The Ordinary', 'category': 'Serum', 
         'ingredients': 'Hyaluronic Acid, Vitamin B5', 'for': 'Dry Skin'},
        {'name': 'Moisturizing Cream', 'brand': 'CeraVe', 'category': 'Moisturizer', 
         'ingredients': 'Ceramides, Hyaluronic Acid', 'for': 'Dry Skin'}
    ],
    'Oily Skin': [
        {'name': 'Niacinamide Serum', 'brand': 'The Ordinary', 'category': 'Serum', 
         'ingredients': 'Niacinamide 10%, Zinc 1%', 'for': 'Oily Skin'},
        {'name': 'Oil-Free Moisturizer', 'brand': 'Neutrogena', 'category': 'Moisturizer', 
         'ingredients': 'Glycerin, Dimethicone', 'for': 'Oily Skin'}
    ],
    'Dark Spots': [
        {'name': 'Vitamin C Serum', 'brand': 'SkinCeuticals', 'category': 'Serum', 
         'ingredients': 'Vitamin C, Vitamin E', 'for': 'Dark Spots'},
        {'name': 'Retinol Cream', 'brand': 'RoC', 'category': 'Treatment', 
         'ingredients': 'Retinol, Shea Butter', 'for': 'Dark Spots'}
    ],
    'Wrinkles': [
        {'name': 'Retinol Serum', 'brand': 'The Ordinary', 'category': 'Serum', 
         'ingredients': 'Retinol 0.5%, Squalane', 'for': 'Wrinkles'},
        {'name': 'Peptide Cream', 'brand': 'Olay', 'category': 'Moisturizer', 
         'ingredients': 'Peptides, Niacinamide', 'for': 'Wrinkles'}
    ],
    'Redness': [
        {'name': 'Centella Asiatica Cream', 'brand': 'COSRX', 'category': 'Moisturizer', 
         'ingredients': 'Centella Asiatica, Madecassoside', 'for': 'Redness'},
        {'name': 'Azelaic Acid Suspension', 'brand': 'The Ordinary', 'category': 'Treatment', 
         'ingredients': 'Azelaic Acid 10%', 'for': 'Redness'}
    ]
}

DEMO_HAIR_PRODUCTS = {
    'Hair Fall': [
        {'name': 'Biotin Hair Serum', 'brand': 'The Ordinary', 'category': 'Hair Serum', 
         'ingredients': 'Biotin, Caffeine, Peptides', 'for': 'Hair Fall'},
        {'name': 'Hair Growth Oil', 'brand': 'Mamaearth', 'category': 'Hair Oil', 
         'ingredients': 'Onion Oil, Rosemary, Castor Oil', 'for': 'Hair Fall'}
    ],
    'Dandruff': [
        {'name': 'Anti-Dandruff Shampoo', 'brand': 'Head & Shoulders', 'category': 'Shampoo', 
         'ingredients': 'Zinc Pyrithione', 'for': 'Dandruff'},
        {'name': 'Scalp Scrub', 'brand': 'Anomaly', 'category': 'Scalp Treatment', 
         'ingredients': 'Glycolic Acid, Charcoal', 'for': 'Dandruff'}
    ],
    'Oily Scalp': [
        {'name': 'Clarifying Shampoo', 'brand': 'Neutrogena', 'category': 'Shampoo', 
         'ingredients': 'Tea Tree Oil, Salicylic Acid', 'for': 'Oily Scalp'},
        {'name': 'Dry Shampoo', 'brand': 'Batiste', 'category': 'Hair Care', 
         'ingredients': 'Rice Starch', 'for': 'Oily Scalp'}
    ],
    'Dry Scalp': [
        {'name': 'Scalp Moisturizer', 'brand': 'Aveeno', 'category': 'Scalp Treatment', 
         'ingredients': 'Oat Extract, Aloe Vera', 'for': 'Dry Scalp'},
        {'name': 'Hydrating Shampoo', 'brand': 'L\'Oreal', 'category': 'Shampoo', 
         'ingredients': 'Hyaluronic Acid, Glycerin', 'for': 'Dry Scalp'}
    ],
    'Thinning Hair': [
        {'name': 'Hair Growth Serum', 'brand': 'Minimalist', 'category': 'Hair Serum', 
         'ingredients': 'Redensyl, Procapil', 'for': 'Thinning Hair'},
        {'name': 'Biotin Tablets', 'brand': 'Carbamide Forte', 'category': 'Supplements', 
         'ingredients': 'Biotin 10000mcg', 'for': 'Thinning Hair'}
    ],
    'Split Ends': [
        {'name': 'Hair Mask', 'brand': 'L\'Oreal', 'category': 'Hair Mask', 
         'ingredients': 'Keratin, Amino Acids', 'for': 'Split Ends'},
        {'name': 'Leave-in Conditioner', 'brand': 'Olaplex', 'category': 'Hair Care', 
         'ingredients': 'Bond Repair Complex', 'for': 'Split Ends'}
    ]
}

# ============================================
# ROUTES
# ============================================

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        captcha_input = request.form.get('captcha_text')
        captcha_expected = session.get('captcha_text', '')
        
        if not captcha_input or captcha_input.upper() != captcha_expected.upper():
            img_base64, captcha_text = generate_captcha()
            return render_template('login.html', error='Invalid CAPTCHA. Please try again.', 
                                 captcha_image=img_base64, captcha_hash=captcha_text)
        
        user = db.get_user(email)
        
        if user and user['password'] == password:
            session['user'] = {
                'name': user['name'],
                'email': user['email'],
                'skin_type': user.get('skin_type', 'Normal'),
                'hair_type': user.get('hair_type', 'Normal')
            }
            session['history'] = user.get('history', [])
            return redirect(url_for('dashboard'))
        else:
            img_base64, captcha_text = generate_captcha()
            return render_template('login.html', error='Invalid email or password', 
                                 captcha_image=img_base64, captcha_hash=captcha_text)
    
    img_base64, captcha_text = generate_captcha()
    return render_template('login.html', captcha_image=img_base64, captcha_hash=captcha_text)

@app.route('/refresh-captcha')
def refresh_captcha():
    img_base64, captcha_text = generate_captcha()
    return jsonify({'image': img_base64, 'hash': captcha_text})

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not name or not email or not password:
            return render_template('signup.html', error='All fields are required')
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return render_template('signup.html', error='Please enter a valid email address')
        
        if len(password) < 6:
            return render_template('signup.html', error='Password must be at least 6 characters')
        
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        if db.user_exists(email):
            return render_template('signup.html', error='Email already registered. Please login.')
        
        db.create_user(email, name, password)
        print(f"✅ New user created: {email}")
        
        session['user'] = {
            'name': name,
            'email': email,
            'skin_type': 'Normal',
            'hair_type': 'Normal'
        }
        session['history'] = []
        
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = db.get_user(session['user']['email'])
    user_history = user.get('history', []) if user else []
    
    return render_template('dashboard.html', 
                         user=session['user'],
                         history=user_history)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ============================================
# ANALYSIS ROUTES
# ============================================

@app.route('/analyze')
def analyze():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('analyze.html', user=session['user'])

@app.route('/skin-analysis')
def skin_analysis_redirect():
    return redirect(url_for('analyze'))

@app.route('/analyze/upload', methods=['POST'])
def analyze_upload():
    if 'user' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    file = request.files.get('image')
    analysis_type = request.form.get('type', 'skin')
    
    if not file:
        return jsonify({'error': 'No image uploaded'}), 400
    
    filename = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    validation_result = validate_image(filepath, analysis_type)
    
    if not validation_result['valid']:
        os.remove(filepath)
        return jsonify({'error': validation_result['message'], 'invalid_image': True}), 400
    
    new_filename = f"{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    new_filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
    os.rename(filepath, new_filepath)
    
    if analysis_type == 'skin':
        detected_conditions = detect_skin_problems(new_filepath)
        recommended_products = get_products_for_skin(detected_conditions)
        category = 'skin'
    else:
        detected_conditions = detect_hair_problems(new_filepath)
        recommended_products = get_products_for_hair(detected_conditions)
        category = 'hair'
    
    severity = "moderate"
    if len(detected_conditions) >= 3:
        severity = "severe"
    elif len(detected_conditions) <= 1:
        severity = "mild"
    
    session['last_analysis'] = {
        'type': category,
        'conditions': detected_conditions,
        'products': recommended_products,
        'image': new_filename,
        'severity': severity,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    
    email = session['user']['email']
    
    history_entry = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'type': category,
        'conditions': detected_conditions,
        'severity': severity,
        'products': [p['name'] for p in recommended_products[:3]] if recommended_products else []
    }
    
    db.add_to_history(email, history_entry)
    
    user = db.get_user(email)
    session['history'] = user.get('history', []) if user else []
    
    return jsonify({
        'type': category,
        'conditions': detected_conditions,
        'products': recommended_products,
        'severity': severity,
        'success': True
    })

# ============================================
# STRICT IMAGE VALIDATION
# ============================================

def validate_image(image_path, analysis_type='skin'):
    img = cv2.imread(image_path)
    if img is None:
        return {'valid': False, 'message': 'Could not read image. Please try again.'}
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    
    if height < 100 or width < 100:
        return {'valid': False, 'message': 'Image too small. Please upload a larger photo.'}
    
    brightness = np.mean(gray) / 255.0
    if brightness < 0.1:
        return {'valid': False, 'message': 'Image is too dark. Please take a well-lit photo.'}
    if brightness > 0.95:
        return {'valid': False, 'message': 'Image is overexposed. Please take a clearer photo.'}
    
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 40:
        return {'valid': False, 'message': 'Image is blurry. Please take a clearer photo.'}
    
    texture_variation = np.std(gray) / 255.0
    if texture_variation < 0.03:
        return {'valid': False, 'message': 'Image lacks detail. Please upload a clear photo.'}
    
    # Face Detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.03, minNeighbors=3, minSize=(50, 50))
    if len(faces) == 0:
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.01, minNeighbors=2, minSize=(40, 40))
    
    has_eyes = False
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray, 1.05, 5)
        if len(eyes) >= 1:
            has_eyes = True
            break
    
    is_face = len(faces) >= 1 and has_eyes
    
    # Hair Detection
    edges = cv2.Canny(gray, 30, 150)
    edge_density = np.mean(edges) / 255.0
    scalp_region = gray[0:int(height*0.5), :]
    scalp_edges = cv2.Canny(scalp_region, 30, 150)
    scalp_density = np.mean(scalp_edges) / 255.0
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 40, minLineLength=15, maxLineGap=8)
    has_hair_strands = lines is not None and len(lines) > 5
    is_hair = (edge_density > 0.06 or scalp_density > 0.06 or has_hair_strands)
    
    if analysis_type == 'skin':
        if is_face:
            return {'valid': True, 'message': 'Valid face image'}
        else:
            return {'valid': False, 'message': '❌ SKIN ANALYSIS: No face detected. Please upload a CLEAR FACE PHOTO only.'}
    else:
        if is_face:
            return {'valid': False, 'message': '❌ HAIR ANALYSIS: Face detected. Please upload a CLEAR SCALP or HAIR photo only.'}
        if is_hair:
            return {'valid': True, 'message': 'Valid hair/scalp image'}
        return {'valid': False, 'message': '❌ HAIR ANALYSIS: No hair or scalp detected.'}

# ============================================
# SKIN DETECTION
# ============================================

def detect_skin_problems(image_path):
    if skin_model is None:
        problems = ["Acne", "Dry Skin", "Oily Skin", "Dark Spots", "Wrinkles", "Redness"]
        return random.sample(problems, random.randint(2, 3))
    
    try:
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        redness = img[:, :, 0].mean() / 255.0
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        oiliness = np.std(gray) / 255.0
        edges = cv2.Canny(gray, 50, 150)
        wrinkles = np.mean(edges) / 255.0
        _, spots = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        dark_spots = np.mean(spots) / 255.0
        texture = np.var(gray) / (255.0 * 255.0)
        features = np.array([[redness, oiliness, wrinkles, dark_spots, texture]])
        prediction = skin_model.predict(features)[0]
        return [skin_le.inverse_transform([prediction])[0]]
    except:
        return ["Acne", "Dry Skin"]

# ============================================
# HAIR DETECTION
# ============================================

def detect_hair_problems(image_path):
    if hair_model is None:
        problems = ["Hair Fall", "Dandruff", "Oily Scalp", "Dry Scalp", "Thinning Hair", "Split Ends"]
        return random.sample(problems, random.randint(2, 3))
    
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        hair_density = np.mean(edges) / 255.0
        oiliness = np.std(gray) / 255.0
        _, white_specks = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        dandruff = np.mean(white_specks) / 255.0
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        redness = img_rgb[:, :, 0].mean() / 255.0
        features = np.array([[hair_density, oiliness, dandruff, redness]])
        prediction = hair_model.predict(features)[0]
        return [hair_le.inverse_transform([prediction])[0]]
    except:
        return ["Hair Fall", "Dandruff"]


def get_products_for_skin(conditions):
    """Get skin products - uses demo products if database has none"""
    products = []
    
    # Try to get from database first
    if db.products.count_documents({}) > 0:
        for condition in conditions:
            condition_lower = condition.lower()
            query = {
                '$or': [
                    {'name': {'$regex': condition_lower, '$options': 'i'}},
                    {'key_ingredients': {'$regex': condition_lower, '$options': 'i'}},
                    {'target_hydration': {'$regex': condition_lower, '$options': 'i'}},
                    {'category': {'$regex': condition_lower, '$options': 'i'}}
                ]
            }
            query['category'] = {'$not': {'$regex': 'hair', '$options': 'i'}}
            
            for prod in db.products.find(query, {'_id': 0}).limit(3):
                products.append({
                    'name': prod.get('name', 'Product'),
                    'brand': prod.get('brand', 'Brand'),
                    'category': prod.get('category', 'Skincare'),
                    'ingredients': prod.get('key_ingredients', 'Not specified'),
                    'for': condition
                })
    
    # If no products from database, use demo products
    if not products:
        for condition in conditions:
            if condition in DEMO_SKIN_PRODUCTS:
                for prod in DEMO_SKIN_PRODUCTS[condition]:
                    products.append(prod.copy())
    
    # Remove duplicates
    seen = set()
    unique = []
    for p in products:
        if p['name'] not in seen:
            seen.add(p['name'])
            unique.append(p)
    return unique[:6]

def get_products_for_hair(conditions):
    """Get hair products - uses demo products if database has none"""
    products = []
    
    # Try to get from database first
    if db.products.count_documents({}) > 0:
        for condition in conditions:
            condition_lower = condition.lower()
            query = {
                '$or': [
                    {'name': {'$regex': condition_lower, '$options': 'i'}},
                    {'hair_type': {'$regex': condition_lower, '$options': 'i'}},
                    {'scalp_condition': {'$regex': condition_lower, '$options': 'i'}},
                    {'hair_concerns': {'$regex': condition_lower, '$options': 'i'}}
                ]
            }
            
            for prod in db.products.find(query, {'_id': 0}).limit(3):
                category = prod.get('category', '')
                if 'skin' in category.lower() or 'face' in category.lower():
                    continue
                products.append({
                    'name': prod.get('name', 'Product'),
                    'brand': prod.get('brand', 'Brand'),
                    'category': category if category else 'Haircare',
                    'ingredients': prod.get('key_ingredients', 'Not specified'),
                    'for': condition
                })
    
    # If no products from database, use demo products
    if not products:
        for condition in conditions:
            if condition in DEMO_HAIR_PRODUCTS:
                for prod in DEMO_HAIR_PRODUCTS[condition]:
                    products.append(prod.copy())
    
    # Remove duplicates
    seen = set()
    unique = []
    for p in products:
        if p['name'] not in seen:
            seen.add(p['name'])
            unique.append(p)
    return unique[:6]

# ============================================
# OTHER ROUTES
# ============================================

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = db.get_user(session['user']['email'])
    return render_template('history.html', history=user.get('history', []), user=session['user'])

@app.route('/view-analysis', methods=['POST'])
def view_analysis():
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    index = request.json.get('index', 0)
    user = db.get_user(session['user']['email'])
    history = user.get('history', [])
    if index < len(history):
        selected = history[index]
        session['last_analysis'] = {
            'type': selected.get('type', 'skin'),
            'conditions': selected.get('conditions', []),
            'severity': selected.get('severity', 'moderate'),
            'date': selected.get('date', ''),
            'products': selected.get('products', [])
        }
        return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/clear-history', methods=['POST'])
def clear_history():
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    db.clear_history(session['user']['email'])
    session['history'] = []
    return jsonify({'success': True})

@app.route('/results')
def results():
    if 'user' not in session:
        return redirect(url_for('login'))
    if 'last_analysis' not in session:
        return redirect(url_for('analyze'))
    return render_template('results.html', results=session['last_analysis'], user=session['user'])

@app.route('/recommendations')
def recommendations():
    if 'user' not in session:
        return redirect(url_for('login'))
    last = session.get('last_analysis', {})
    return render_template('recommendations.html', user=session['user'], 
                         conditions=last.get('conditions', []), 
                         products=last.get('products', []), 
                         analysis_type=last.get('type', 'skin'))

@app.route('/chatbot')
def chatbot():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('chatbot.html', user=session['user'])

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    user_message = data.get('message', '')
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "You are Derma AI, a skincare and haircare expert. Give SHORT, SIMPLE answers. NO markdown, NO asterisks, NO bullet points. Use plain text only."}, {"role": "user", "content": user_message}],
            temperature=0.5,
            max_tokens=200
        )
        response = completion.choices[0].message.content
        response = response.replace('*', '').replace('#', '').replace('-', '').replace('**', '').replace('__', '')
        return jsonify({'response': response})
    except:
        return jsonify({'response': "Please try again."})


@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """Convert speech to text using Groq Whisper API"""
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    temp_path = f"temp_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
    audio_file.save(temp_path)
    
    try:
        with open(temp_path, 'rb') as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_path, file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="en",
                temperature=0.0
            )
        
        os.remove(temp_path)
        return jsonify({'success': True, 'text': transcription})
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Transcription error: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/progress')
def progress():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('progress.html', user=session['user'])

@app.route('/api/progress')
def get_progress():
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    user = db.get_user(session['user']['email'])
    history = user.get('history', [])
    severity_score = {'mild': 1, 'moderate': 2, 'severe': 3}
    progress_data = []
    for item in history:
        score = severity_score.get(item.get('severity', 'moderate'), 2)
        progress_data.append({'date': item['date'], 'severity': item['severity'], 'score': score, 'conditions': item['conditions']})
    improving = len(progress_data) >= 2 and progress_data[0]['score'] < progress_data[-1]['score']
    return jsonify({'progress': progress_data, 'improving': improving, 'total_analyses': len(history)})

@app.route('/clear-analysis', methods=['POST'])
def clear_analysis():
    if 'last_analysis' in session:
        session.pop('last_analysis')
    return jsonify({'success': True})

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = db.get_user(email)
        if user:
            return render_template('forgot-password.html', email=email, password=user['password'], found=True)
        else:
            return render_template('forgot-password.html', error='Email not found', found=False)
    return render_template('forgot-password.html', found=None)

@app.route('/skin-coach')
def skin_coach():
    if 'user' not in session:
        return redirect(url_for('login'))
    last_analysis = session.get('last_analysis', {})
    conditions = last_analysis.get('conditions', [])
    severity = last_analysis.get('severity', 'moderate')
    daily_plan = generate_personalized_plan(conditions, severity)
    
    return render_template('skin_coach.html', 
                         user=session['user'],
                         conditions=conditions,
                         daily_plan=daily_plan)

def generate_personalized_plan(conditions, severity):
    """Generate DIFFERENT plan for DIFFERENT skin types"""
    
    plan = {
        'morning': [],
        'afternoon': [],
        'evening': [],
        'tips': [],
        'products_to_use': [],
        'products_to_avoid': []
    }
    if 'Acne' in conditions:
        plan['morning'] = [
            'Cleanse with salicylic acid face wash',
            'Apply niacinamide serum (controls oil)',
            'Use oil-free moisturizer',
            'Apply SPF 50 (non-comedogenic)'
        ]
        plan['afternoon'] = [
            'Blot excess oil with blotting paper',
            'Reapply sunscreen if outdoors'
        ]
        plan['evening'] = [
            'Double cleanse (oil cleanser + gentle cleanser)',
            'Apply benzoyl peroxide (spot treatment)',
            'Use lightweight moisturizer',
            'Change pillowcase weekly'
        ]
        plan['tips'] = [
            'Do not pop pimples - causes scarring' ,
            'Wash makeup brushes weekly',
            'Avoid touching face throughout the day'
        ]
        plan['products_to_use'] = [
            'Salicylic acid cleanser',
            'Benzoyl peroxide gel',
            'Niacinamide serum',
            'Non-comedogenic sunscreen'
        ]
        plan['products_to_avoid'] = [
            'Heavy coconut oil',
            'Fragranced products',
            'Physical scrubs'
        ]
    elif 'Dry Skin' in conditions:
        plan['morning'] = [
            'Cleanse with cream-based gentle cleanser',
            'Apply hyaluronic acid serum (on damp skin)',
            'Use thick ceramide moisturizer',
            'Apply SPF 50 (hydrating formula)'
        ]
        plan['afternoon'] = [
            'Mist face with thermal water',
            'Reapply moisturizer if feeling tight'
        ]
        plan['evening'] = [
            'Oil cleanse (removes makeup without stripping)',
            'Apply hydrating serum',
            'Use overnight sleeping mask',
            'Use humidifier in bedroom'
        ]
        plan['tips'] = [
            'Avoid hot water while washing face',
            'Pat dry - do not rub',
            'Drink 8+ glasses of water daily'
        ]
        plan['products_to_use'] = [
            'Hyaluronic acid serum',
            'Ceramide moisturizer',
            'Gentle cream cleanser',
            'Facial oil (squalane)'
        ]
        plan['products_to_avoid'] = [
            'Foaming cleansers',
            'Alcohol-based toners',
            'Physical exfoliants'
        ]
    elif 'Oily Skin' in conditions:
        plan['morning'] = [
            'Cleanse with gel-based salicylic acid cleanser',
            'Apply niacinamide serum (controls sebum)',
            'Use gel moisturizer (oil-free)',
            'Apply mattifying SPF'
        ]
        plan['afternoon'] = [
            'Use blotting paper',
            'Mist with oil-control toner'
        ]
        plan['evening'] = [
            'Double cleanse',
            'Apply retinol (2-3x per week)',
            'Use lightweight gel moisturizer',
            'Use clay mask once a week'
        ]
        plan['tips'] = [
            'Do not over-wash (stimulates more oil)',
            'Use oil-free makeup',
            'Change pillowcase twice weekly'
        ]
        plan['products_to_use'] = [
            'Salicylic acid cleanser',
            'Niacinamide serum',
            'Clay mask',
            'Oil-free moisturizer'
        ]
        plan['products_to_avoid'] = [
            'Heavy creams',
            'Coconut oil',
            'Pore-clogging ingredients'
        ]
    elif 'Dark Spots' in conditions:
        plan['morning'] = [
            'Gentle cleanse',
            'Apply Vitamin C serum (brightening)',
            'Use moisturizer',
            'Apply SPF 50 (MUST - prevents darkening)'
        ]
        plan['afternoon'] = [
            'Reapply sunscreen without fail',
            'Wear hat if outdoors'
        ]
        plan['evening'] = [
            'Cleanse',
            'Apply retinol or azelaic acid',
            'Use niacinamide moisturizer'
        ]
        plan['tips'] = [
            'Sunscreen is NON-NEGOTIABLE',
            'Results take 8-12 weeks',
            'Avoid picking skin (causes more spots)'
        ]
        plan['products_to_use'] = [
            'Vitamin C serum',
            'Retinol cream',
            'Azelaic acid',
            'SPF 50 PA++++'
        ]
        plan['products_to_avoid'] = [
            'Sun exposure without protection',
            'Harsh physical scrubs'
        ]
    
    
    elif 'Wrinkles' in conditions:
        plan['morning'] = [
            'Gentle cleanse',
            'Apply Vitamin C serum',
            'Apply SPF 50'
        ]
        plan['afternoon'] = [
            'Reapply sunscreen',
            'Use hydrating mist'
        ]
        plan['evening'] = [
            'Cleanse',
            'Apply retinol (start 2x per week)',
            'Use rich night cream',
            'Sleep on silk pillowcase'
        ]
        plan['tips'] = [
            'Retinol causes sun sensitivity - MUST use SPF',
            'Expect 8-12 weeks for visible results',
            'Stay hydrated'
        ]
        plan['products_to_use'] = [
            'Retinol cream',
            'Vitamin C serum',
            'Peptide moisturizer',
            'Hyaluronic acid'
        ]
        plan['products_to_avoid'] = [
            'Harsh exfoliants',
            'Alcohol-based products'
        ]
    
    elif 'Redness' in conditions:
        plan['morning'] = [
            'Cleanse with gentle, fragrance-free cleanser',
            'Apply centella asiatica serum',
            'Use calming moisturizer',
            'Apply mineral sunscreen (zinc oxide)'
        ]
        plan['afternoon'] = [
            'Avoid direct sun exposure',
            'Use cool water to soothe if red'
        ]
        plan['evening'] = [
            'Gentle cleanse',
            'Apply calming serum',
            'Use ceramide moisturizer'
        ]
        plan['tips'] = [
            'Avoid hot water',
            'Patch test all new products',
            'Keep skincare routine SIMPLE'
        ]
        plan['products_to_use'] = [
            'Centella asiatica products',
            'Ceramide moisturizer',
            'Aloe vera gel',
            'Mineral sunscreen'
        ]
        plan['products_to_avoid'] = [
            'Fragrance',
            'Essential oils',
            'Alcohol',
            'Chemical exfoliants'
        ]
    else:
        plan['morning'] = [
            'Gentle cleanse',
            'Apply moisturizer',
            'Apply SPF 30+'
        ]
        plan['afternoon'] = [
            'Stay hydrated',
            'Reapply sunscreen if outdoors'
        ]
        plan['evening'] = [
            'Cleanse',
            'Apply moisturizer',
            'Use eye cream'
        ]
        plan['tips'] = [
            'Maintain consistent routine',
            'Drink water throughout day',
            'Get 7-8 hours sleep'
        ]
        plan['products_to_use'] = [
            'Gentle cleanser',
            'Hydrating moisturizer',
            'SPF 30+'
        ]
        plan['products_to_avoid'] = []
    
    # Add severity-based adjustments
    if severity == 'severe':
        plan['morning'].insert(0, '⚠️ SEVERE: Consult a dermatologist')
        plan['tips'].append('⚠️ Consider seeing a professional for your condition')
    
    return plan


if __name__ == '__main__':
    print("\n🚀 DERMACARE AI STARTED")
    print("🌐 Open: http://localhost:5000\n")
    app.run(debug=True, port=5000)