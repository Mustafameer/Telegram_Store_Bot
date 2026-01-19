"""
🔥 Firebase Integration for Bot.py
أضف هذا الكود في بداية bot.py (بعد psycopg2 imports)
"""

# ======================== Firebase Initialization ========================

try:
    import firebase_admin
    from firebase_admin import storage, credentials
    
    # تهيئة Firebase إذا كان firebase-key.json موجوداً
    if os.path.exists('firebase-key.json'):
        try:
            # تحقق إذا كان Firebase مهيأ بالفعل
            firebase_admin.get_app()
            print("✅ Firebase is already initialized")
        except ValueError:
            # Firebase لم يكن مهيأ بعد
            cred = credentials.Certificate('firebase-key.json')
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'telegram-store-bot.appspot.com'
            })
            print("✅ Firebase initialized successfully")
        
        FIREBASE_ENABLED = True
    else:
        print("⚠️  firebase-key.json not found - Firebase disabled")
        FIREBASE_ENABLED = False

except ImportError:
    print("⚠️  firebase-admin not installed - Firebase disabled")
    print("   Install with: pip install firebase-admin")
    FIREBASE_ENABLED = False
except Exception as e:
    print(f"⚠️  Firebase initialization error: {e}")
    FIREBASE_ENABLED = False

# ======================== End Firebase Initialization ========================
