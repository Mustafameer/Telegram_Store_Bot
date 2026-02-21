import sys
import io

# Fix encoding for console output to handle Telegram messages properly
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import telebot
from telebot import types
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

import re
import sys
import time
import uuid
import traceback
from datetime import datetime
from utils.receipt_generator import generate_order_card
import base64
import json
import threading
from flask import Flask, request, jsonify
# Reverting to direct DB functions defined in bot.py
# from db_manager import get_seller_by_telegram, get_products, get_categories, get_product_by_id, get_category_by_id
# from integration_models import Product, Category, Seller

# ----------------- إعداد البوت وملفات -----------------
import os

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import IntegrityError
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    IntegrityError = None

# ======================== Firebase Initialization ========================
try:
    import firebase_admin
    from firebase_admin import storage, credentials
    
    if os.path.exists('firebase-key.json'):
        try:
            firebase_admin.get_app()
            print("✅ Firebase is already initialized")
        except ValueError:
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
    FIREBASE_ENABLED = False
except Exception as e:
    print(f"⚠️  Firebase initialization error: {e}")
    FIREBASE_ENABLED = False
# ========================================================================

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if TOKEN:
    TOKEN = TOKEN.strip()

if not TOKEN:
    print("❌ FATAL ERROR: TELEGRAM_BOT_TOKEN environment variable is NOT set!")
    sys.exit(1) # Fail fast
else:
    print(f"[OK] DEBUG: TELEGRAM_BOT_TOKEN found. Starts with: {TOKEN[:10]}... Ends with: ...{TOKEN[-5:]}")
    print(f"[OK] DEBUG: Token Length: {len(TOKEN)}")

# --- DEBUGGING BLOCK: PRINT ALL ENV VARS ---
# print("\n🔍 DEBUGGING ENVIRONMENT VARIABLES:")
# for key, value in os.environ.items():
#    if "TOKEN" in key or "TELEGRAM" in key:
#        print(f"   🔑 Found Key: '{key}' -> Value starts with: '{value[:5]}...'")
# print("---------------------------------------\n")
bot = telebot.TeleBot(TOKEN)
IS_POSTGRES = (os.environ.get('DATABASE_URL') is not None) and (psycopg2 is not None)

# إضافة معرف صاحب البوت (أدمن) - للتحكم التقني فقط
BOT_ADMIN_ID = 1041977029  # ضع هنا معرف التليجرام الخاص بأدمن البوت

# ====================== Flask App for API ======================
app = Flask(__name__)

# API endpoint للحصول على الإشعارات
@app.route('/api/notifications', methods=['GET'])
def api_get_notifications():
    """
    احصل على الإشعارات للعميل
    
    Parameters:
        customer_id (int): معرف التليجرام للعميل
        unread_only (bool): هل تحضر الإشعارات غير المقروءة فقط (default: true)
    
    Returns:
        JSON: قائمة الإشعارات
    """
    try:
        customer_id = request.args.get('customer_id', type=int)
        unread_only = request.args.get('unread_only', default='true').lower() == 'true'
        
        if not customer_id:
            return jsonify({'error': 'customer_id is required'}), 400
        
        notifications = get_customer_notifications(customer_id, unread_only)
        
        return jsonify({
            'success': True,
            'count': len(notifications),
            'notifications': notifications
        }), 200
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({'error': str(e)}), 500

# API endpoint لوضع علامة على إشعار كمقروء
@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def api_mark_as_read(notification_id):
    """
    وضع علامة على إشعار كمقروء
    
    Parameters:
        notification_id (int): معرف الإشعار
    
    Returns:
        JSON: النتيجة
    """
    try:
        success = mark_notification_as_read(notification_id)
        
        if success:
            return jsonify({'success': True, 'message': 'تم وضع علامة على الإشعار'}), 200
        else:
            return jsonify({'success': False, 'error': 'فشل تحديث الإشعار'}), 500
            
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({'error': str(e)}), 500

# API endpoint للفحص
@app.route('/api/health', methods=['GET'])
def api_health():
    """التحقق من أن الـ API يعمل"""
    return jsonify({'status': 'ok', 'service': 'telegram-store-bot'}), 200

# API endpoint لحذف الصور بعد الشراء من التطبيق
@app.route('/api/delete-purchased-images', methods=['POST'])
def api_delete_purchased_images():
    """
    حذف الصور بعد شراؤها من التطبيق الـ Flutter
    
    Parameters (JSON):
        - product_id: معرف المنتج
        - image_ids: قائمة معرفات الصور المراد حذفها
    
    Returns:
        JSON: عدد الصور المحذوفة
    """
    try:
        data = request.get_json()
        product_id = int(data.get('product_id', 0))
        image_ids = data.get('image_ids', [])
        
        if not product_id or not image_ids:
            return jsonify({'error': 'Missing product_id or image_ids'}), 400
        
        print(f"🗑️ API: Delete {len(image_ids)} images from product {product_id}")
        
        # حذف الصور من قاعدة البيانات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        deleted_count = 0
        for image_id in image_ids:
            try:
                if IS_POSTGRES:
                    # احصل على اسم الملف أولاً
                    cursor.execute('SELECT filename FROM imagestorage WHERE imageid = %s', (image_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        filename = result[0]
                        # حذف من قاعدة البيانات
                        cursor.execute('DELETE FROM imagestorage WHERE imageid = %s', (image_id,))
                        deleted_count += 1
                        print(f"   ✅ Deleted image ID {image_id}: {filename}")
                        
                        # حذف الملف من القرص
                        img_path = os.path.join(IMAGES_FOLDER, filename)
                        if os.path.exists(img_path):
                            try:
                                os.remove(img_path)
                                print(f"   📁 File deleted: {img_path}")
                            except Exception as e:
                                print(f"   ⚠️ Error deleting file: {e}")
                else:
                    cursor.execute('SELECT filename FROM imagestorage WHERE imageid = ?', (image_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        filename = result[0]
                        cursor.execute('DELETE FROM imagestorage WHERE imageid = ?', (image_id,))
                        deleted_count += 1
                        print(f"   ✅ Deleted image ID {image_id}: {filename}")
                        
                        img_path = os.path.join(IMAGES_FOLDER, filename)
                        if os.path.exists(img_path):
                            try:
                                os.remove(img_path)
                                print(f"   📁 File deleted: {img_path}")
                            except Exception as e:
                                print(f"   ⚠️ Error deleting file: {e}")
            except Exception as e:
                print(f"   ⚠️ Error deleting image {image_id}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Successfully deleted {deleted_count} images from product {product_id}")
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'تم حذف {deleted_count} صورة بنجاح'
        }), 200
    except Exception as e:
        print(f"❌ Error in api_delete_purchased_images: {e}")
        return jsonify({'error': str(e)}), 500

# API endpoint لشراء الصور من التطبيق
@app.route('/api/buy-images', methods=['POST'])
def api_buy_images():
    """
    شراء صور من التطبيق - نفس عملية شراء الصور من البوت
    
    Parameters (JSON):
        - product_id: معرف المنتج
        - quantity: عدد الصور المراد شراؤها
        - customer_id: معرف العميل (من قاعدة البيانات)
        - seller_id: معرف البائع
        - customer_telegram_id: معرف التليجرام للعميل (لحفظ الإشعار)
    
    Returns:
        JSON: نتائج العملية (إرسال الصور، حذف الصور، حفظ الإشعار)
    """
    try:
        data = request.get_json()
        
        # التحقق من البيانات المطلوبة
        required_fields = ['product_id', 'quantity', 'customer_id', 'seller_id', 'customer_telegram_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        product_id = int(data['product_id'])
        quantity = int(data['quantity'])
        customer_id = int(data['customer_id'])
        seller_id = int(data['seller_id'])
        customer_telegram_id = int(data['customer_telegram_id'])
        
        print(f"📱 API: Buying {quantity} images for product {product_id} by customer {customer_id}")
        
        # التحقق من المنتج
        product = get_product_by_id(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        product_name = product[3]
        price = product[5]
        available_qty = product[7]
        
        if quantity > available_qty:
            return jsonify({'error': f'Only {available_qty} images available'}), 400
        
        # الحصول على صور المنتج من جدول imagestorage
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                SELECT imageid, filename FROM imagestorage 
                WHERE productid = %s
                ORDER BY imageorder ASC
                LIMIT %s
            """, (product_id, quantity))
        else:
            cursor.execute("""
                SELECT imageid, filename FROM imagestorage 
                WHERE productid = ?
                ORDER BY imageorder
                LIMIT ?
            """, (product_id, quantity))
        
        images = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"📸 Found {len(images)} images to delete for product {product_id}")
        
        if not images or len(images) < quantity:
            print(f"⚠️ Not enough images: found {len(images)}, need {quantity}")
            return jsonify({'error': 'Not enough images available'}), 400
        
        # حساب المبلغ الإجمالي
        total_amount = price * quantity
        
        # إضافة المعاملة الائتمانية
        if not add_credit_transaction(customer_id, seller_id, total_amount, 
                                     f"شراء {quantity} صورة من منتج: {product_name}"):
            return jsonify({'error': 'Failed to add credit transaction'}), 500
        
        # تحديث كمية المنتج
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute(
                'UPDATE products SET quantity = GREATEST(0, quantity - %s) WHERE productid = %s',
                (quantity, product_id)
            )
        else:
            cursor.execute(
                'UPDATE Products SET Quantity = MAX(0, Quantity - ?) WHERE ProductID = ?',
                (quantity, product_id)
            )
        
        # حذف الصور المشتراة من قاعدة البيانات
        deleted_count = 0
        images_to_delete = images[:quantity]
        
        print(f"🗑️ Attempting to delete {len(images_to_delete)} images...")
        
        for image_id, filename in images_to_delete:
            # حذف من قاعدة البيانات
            try:
                if IS_POSTGRES:
                    cursor.execute('DELETE FROM imagestorage WHERE imageid = %s', (image_id,))
                else:
                    cursor.execute('DELETE FROM imagestorage WHERE imageid = ?', (image_id,))
                deleted_count += 1
                print(f"   ✅ Deleted image ID {image_id}: {filename}")
            except Exception as e:
                print(f"   ⚠️ Error deleting image {image_id}: {e}")
            
            # حذف الملف من القرص المحلي
            img_path = os.path.join(IMAGES_FOLDER, filename)
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
                    print(f"   📁 File deleted: {img_path}")
            except Exception as e:
                print(f"   ⚠️ Error deleting file {filename}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Successfully deleted {deleted_count} images")
        
        # حفظ إشعار للعميل
        conn = get_db_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=%s", (customer_id,))
        else:
            cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
        customer_result = cursor.fetchone()
        cursor.close()
        conn.close()
        customer_name = customer_result[0] if customer_result else "عميل"
        
        notification_saved = save_notification(
            customer_telegram_id=customer_telegram_id,
            notification_type='image_purchase',
            title='✅ تم شراء الصور',
            message=f'تم شراء {quantity} صورة من {product_name} بنجاح! المبلغ: {total_amount:,.0f} د.ع',
            product_names=product_name,
            total_amount=total_amount,
            seller_id=seller_id,
            data=None
        )
        
        print(f"✅ Image purchase completed: {quantity} images, {deleted_count} deleted, notification saved: {notification_saved}")
        
        return jsonify({
            'success': True,
            'message': f'تم شراء {quantity} صورة بنجاح',
            'total_amount': total_amount,
            'deleted_images': deleted_count,
            'notification_saved': notification_saved
        }), 200
        
    except Exception as e:
        print(f"❌ API Error in buy-images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Start Flask in a separate thread
def run_flask():
    """تشغيل Flask في thread منفصل"""
    port = int(os.environ.get('API_PORT', 5000))
    print(f"🌐 Starting Flask API on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ================================================================

@bot.message_handler(commands=['sys_info'])
def sys_info(message):
    try:
        import sys
        info = f"🤖 **System Diagnostics**\n\n"
        info += f"🐍 Python: {sys.version.split()[0]}\n"
        info += f"📦 IS_POSTGRES: `{IS_POSTGRES}`\n"
        info += f"🔑 DATABASE_URL: {'✅ Found' if os.environ.get('DATABASE_URL') else '❌ Missing'}\n"
        info += f"🐘 psycopg2: {'✅ Imported' if psycopg2 else '❌ Missing'}\n"
        
        # Check explicit import
        try:
            import psycopg2 as pg2_test
            info += "🐘 Import Test: OK\n"
        except ImportError as e:
            info += f"🐘 Import Test: ❌ {e}\n"
            
        bot.reply_to(message, info, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['update_auction_store'])
def update_auction_store_command(message):
    """أمر لتحديث متجر المزادات برقم تليجرام صحيح"""
    try:
        # الحصول على معرف المستخدم الحالي
        user_id = message.from_user.id
        
        # تحديث المتجر بمعرف المستخدم الحالي
        success = update_auction_store_owner(user_id)
        
        if success:
            bot.reply_to(message, 
                        f"✅ تم تحديث متجر المزادات بنجاح!\n\n"
                        f"معرفك: {user_id}\n"
                        f"الآن يمكنك تلقي الإشعارات بشكل صحيح")
        else:
            bot.reply_to(message, "❌ فشل التحديث")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['force_migration'])
def force_migration_command(message):
    """أمر لتطبيق Migration بشكل إجباري - للمشرفين فقط"""
    if not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط")
        return
    
    if not IS_POSTGRES:
        bot.reply_to(message, "⚠️ هذا الأمر يعمل فقط مع PostgreSQL (Cloud)")
        return
    
    try:
        bot.reply_to(message, "🔄 بدء تطبيق Migration...")
        
        # Use direct psycopg2 connection
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            bot.reply_to(message, "❌ DATABASE_URL not found")
            return
        
        result = urllib.parse.urlparse(database_url)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        conn = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port,
            sslmode='require'
        )
        cursor = conn.cursor()
        
        migrations = [
            ("Users", "TelegramID"),
            ("Sellers", "TelegramID"),
            ("CreditCustomers", "TelegramID"),
            ("Orders", "BuyerID"),
            ("Carts", "UserID"),
        ]
        
        results = []
        for table_name, column_name in migrations:
            try:
                cursor.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name=%s AND column_name=%s
                """, (table_name.lower(), column_name.lower()))
                result = cursor.fetchone()
                
                if result:
                    current_type = result[0].upper()
                    if current_type not in ('BIGINT', 'INT8'):
                        cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT")
                        conn.commit()
                        results.append(f"✅ {table_name}.{column_name}: {current_type} → BIGINT")
                    else:
                        results.append(f"✅ {table_name}.{column_name}: Already BIGINT")
                else:
                    results.append(f"⚠️ {table_name}.{column_name}: Column not found")
            except Exception as e:
                results.append(f"❌ {table_name}.{column_name}: {str(e)}")
                try:
                    conn.rollback()
                except:
                    pass
        
        cursor.close()
        conn.close()
        
        result_text = "🔄 **نتائج Migration:**\n\n" + "\n".join(results)
        bot.reply_to(message, result_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في تطبيق Migration: {str(e)}")
        import traceback
        traceback.print_exc()

@bot.message_handler(commands=['set_closed_store'])
def set_closed_store(message):
    """أمر لتحديث متجرك ليكون مغلق"""
    if not is_seller(message.from_user.id):
        bot.reply_to(message, "❌ يجب أن تكون بائعاً")
        return
    
    try:
        seller = get_seller_by_telegram(message.from_user.id)
        if not seller:
            bot.reply_to(message, "❌ لم يتم العثور على متجرك")
            return
        
        seller_id = seller[0]
        print(f"🔍 [DEBUG] set_closed_store: seller_id={seller_id}, seller={seller}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # التحقق من الحالة الحالية
        if IS_POSTGRES:
            cursor.execute('SELECT sellerid, storename, COALESCE(requirecustomerregistration, 0) FROM sellers WHERE sellerid=%s', (seller_id,))
        else:
            cursor.execute('SELECT SellerID, StoreName, COALESCE(RequireCustomerRegistration, 0) FROM Sellers WHERE SellerID=?', (seller_id,))
        
        result = cursor.fetchone()
        print(f"🔍 [DEBUG] Current value: {result}")
        
        if not result:
            bot.reply_to(message, "❌ لم يتم العثور على متجرك في قاعدة البيانات")
            cursor.close()
            conn.close()
            return
        
        current_seller_id, store_name, current_value = result
        print(f"🔍 [DEBUG] Store: {store_name}, Current RequireCustomerRegistration: {current_value}")
        
        # تحديث إلى مغلق
        if IS_POSTGRES:
            cursor.execute('UPDATE sellers SET requirecustomerregistration=1 WHERE sellerid=%s', (seller_id,))
        else:
            cursor.execute('UPDATE Sellers SET RequireCustomerRegistration=1 WHERE SellerID=?', (seller_id,))
        
        conn.commit()
        print(f"✅ [DEBUG] تم تحديث المتجر {seller_id}")
        
        cursor.close()
        conn.close()
        
        msg = f"""
✅ **تم تحديث متجرك!**

🏪 **متجرك:** {store_name}
🔒 **النوع:** مغلق (يتطلب تسجيل العملاء)

**التأثيرات:**
• عند إضافة منتج: لن يسأل عن الكمية
• ستتمكن من إضافة صور متعددة
• الكمية = عدد الصور المرفوعة

لتغيير هذا لاحقاً، استخدم: /set_open_store
"""
        bot.reply_to(message, msg, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ [ERROR] خطأ في set_closed_store: {e}")
        import traceback
        traceback.print_exc()
        bot.reply_to(message, f"❌ خطأ: {str(e)}")

@bot.message_handler(commands=['set_open_store'])
def set_open_store(message):
    """أمر لتحديث متجرك ليكون مفتوح"""
    if not is_seller(message.from_user.id):
        bot.reply_to(message, "❌ يجب أن تكون بائعاً")
        return
    
    try:
        seller = get_seller_by_telegram(message.from_user.id)
        if not seller:
            bot.reply_to(message, "❌ لم يتم العثور على متجرك")
            return
        
        seller_id = seller[0]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تحديث إلى مفتوح
        if IS_POSTGRES:
            cursor.execute('UPDATE sellers SET requirecustomerregistration=0 WHERE sellerid=%s', (seller_id,))
        else:
            cursor.execute('UPDATE Sellers SET RequireCustomerRegistration=0 WHERE SellerID=?', (seller_id,))
        
        conn.commit()
        conn.close()
        
        msg = f"""
✅ **تم تحديث متجرك!**

🔓 متجرك الآن: **مفتوح** (متاح للجميع)

**التأثيرات:**
• عند إضافة منتج: سيسأل عن الكمية
• يمكن إضافة صورة واحدة فقط
• الكمية كما تدخلها

لتغيير هذا لاحقاً، استخدم: /set_closed_store
"""
        bot.reply_to(message, msg, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")
        print(f"❌ خطأ في set_open_store: {e}")

# Use absolute path to ensure consistency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Use absolute path to ensure consistency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SEED_DIR = os.path.join(BASE_DIR, "seed_data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "store_local_new.db")
IMAGES_FOLDER = os.path.join(DATA_DIR, "Images")
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# ===================== نسخ الصور من seed_data عند بدء البوت =====================
def ensure_images_synced():
    """
    نسخ الصور من seed_data/Images إلى data/Images في كل مرة يبدأ البوت
    هذا يضمن أن الصور متوفرة حتى لو كانت قاعدة البيانات موجودة بالفعل
    """
    seed_images_dir = os.path.join(SEED_DIR, "Images")
    
    if os.path.exists(seed_images_dir):
        try:
            # نسخ جميع الصور من seed_data/Images إلى data/Images
            for image_file in os.listdir(seed_images_dir):
                src = os.path.join(seed_images_dir, image_file)
                dst = os.path.join(IMAGES_FOLDER, image_file)
                
                # نسخ الملف إذا لم يكن موجوداً أو إذا كان مختلفاً
                if os.path.isfile(src):
                    # نسخ بدون حذف الصور الموجودة الأخرى
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        print(f"[OK] Copied image: {image_file}")
            
            print(f"[OK] Images synced from seed_data/Images")
        except Exception as e:
            print(f"[WARN] Error syncing images: {e}")
    else:
        print(f"[WARN] seed_data/Images directory not found")

# تشغيل مزامنة الصور عند بدء البوت
ensure_images_synced()

# ----------------- استعادة البيانات عند إضافة Volume جديد -----------------
import shutil
import urllib.parse
from contextlib import contextmanager

# ===================== Database Wrapper =====================
class DBWrapper:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres

    def cursor(self):
        return CursorWrapper(self.conn.cursor(), self.is_postgres)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

class CursorWrapper:
    def __init__(self, cursor, is_postgres=False):
        self.cursor = cursor
        self.is_postgres = is_postgres
        self.lastrowid = None # Placeholder

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def execute(self, query, params=None):
        if self.is_postgres:
            # Replace ? with %s
            query = query.replace('?', '%s')
            # Handle AUTOINCREMENT replacement for Postgres compatibility
            query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            query = query.replace('DATETIME DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            query = query.replace('DATETIME', 'TIMESTAMP')
        
        try:
            if params is None:
                self.cursor.execute(query)
            else:
                self.cursor.execute(query, params)
                
            # Try to capture lastrowid if supported
            if not self.is_postgres:
                self.lastrowid = self.cursor.lastrowid
            else:
                # Psycopg2: lastrowid is often OID, not PK. 
                # If RETURNING was used, we need to fetchone to get it.
                if query.strip().upper().startswith("INSERT") and "RETURNING" in query.upper():
                    res = self.cursor.fetchone()
                    if res:
                        self.lastrowid = res[0]
        except Exception as e:
            raise e
            
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()
        
    def close(self):
        self.cursor.close()

def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        try:
            # NUCLEAR OPTION: If we are supposed to use Postgres, KILL the local DB to prevent confusion
            if os.path.exists(DB_FILE):
                print("⚠️ FOUND LOCAL DB IN CLOUD MODE - DELETING IT TO FORCE POSTGRES ⚠️")
                try:
                    os.remove(DB_FILE)
                except:
                    pass

            result = urllib.parse.urlparse(database_url)
            username = result.username
            password = result.password
            database = result.path[1:]
            hostname = result.hostname
            port = result.port
            conn = psycopg2.connect(
                database=database,
                user=username,
                password=password,
                host=hostname,
                port=port,
                sslmode='require'
            )
            print("\n" + "="*50)
            print(f"✅ BOT CONNECTED TO POSTGRES (Cloud)")
            print(f"   Host: {hostname}")
            print("="*50 + "\n")
            return DBWrapper(conn, is_postgres=True)
        except Exception as e:
            print(f"❌ CRITICAL ERROR connecting to Postgres: {e}")
            raise e
    else:
        # Local development mode (no DATABASE_URL)
        print("\n" + "="*50)
        print(f"⚠️ BOT CONNECTED TO LOCAL SQLITE (No DATABASE_URL)")
        print(f"   File: {DB_FILE}")
        print("="*50 + "\n")
        return DBWrapper(sqlite3.connect(DB_FILE), is_postgres=False)

# Remove the restore logic entirely or guard it carefully
if not os.path.exists(DB_FILE) and os.path.exists(os.path.join(SEED_DIR, "store.db")) and not os.environ.get('DATABASE_URL'):
    print("🔄 استعادة قاعدة البيانات من النسخة الاحتياطية (Seed)...")
    shutil.copy(os.path.join(SEED_DIR, "store.db"), DB_FILE)
    if os.path.exists(os.path.join(SEED_DIR, "Images")):
         if os.path.exists(IMAGES_FOLDER):
             shutil.rmtree(IMAGES_FOLDER)
         shutil.copytree(os.path.join(SEED_DIR, "Images"), IMAGES_FOLDER)
    print("[OK] Data restored successfully!")

# ===================== قاعدة البيانات =====================
# ===================== قاعدة البيانات =====================
def init_db():
    print("=" * 60)
    print("🛠️ INITIALIZING DATABASE...")
    print("=" * 60)
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    cursor = cursor_wrapper.cursor  # Get the underlying cursor for direct access if needed

    # 1. Users (Main table, no dependencies)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Users(
                UserID SERIAL PRIMARY KEY,
                TelegramID BIGINT UNIQUE,
                UserName TEXT,
                UserType TEXT,
                PhoneNumber TEXT,
                FullName TEXT,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Users(
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                TelegramID INTEGER UNIQUE,
                UserName TEXT,
                UserType TEXT,
                PhoneNumber TEXT,
                FullName TEXT,
                CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    # Migration: Change TelegramID from INTEGER to BIGINT in PostgreSQL if needed
    if IS_POSTGRES:
        try:
            print("🔍 Checking Users.TelegramID column type...")
            cursor_wrapper.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='telegramid'
            """)
            result = cursor_wrapper.fetchone()
            if result:
                current_type = result[0].upper()
                print(f"📊 Users.TelegramID current type: {current_type}")
                # Force migration if not already BIGINT
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"🔄 FORCE Migrating Users.TelegramID from {current_type} to BIGINT...")
                    cursor_wrapper.execute("ALTER TABLE Users ALTER COLUMN TelegramID TYPE BIGINT")
                    conn.commit()
                    print("✅ Users.TelegramID migrated to BIGINT successfully")
                else:
                    print(f"✅ Users.TelegramID is already BIGINT")
            else:
                print("⚠️ Users.TelegramID column not found!")
        except Exception as e:
            print(f"❌ Migration ERROR for Users.TelegramID: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass

    # 2. Sellers (Depends on Users for SuspendedBy)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Sellers(
                SellerID SERIAL PRIMARY KEY,
                TelegramID BIGINT UNIQUE,
                UserName TEXT,
                StoreName TEXT,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                Status TEXT DEFAULT 'active',
                SuspensionReason TEXT,
                SuspendedBy BIGINT,
                SuspendedAt TIMESTAMP,
                RequireCustomerRegistration INTEGER DEFAULT 0,
                FOREIGN KEY (SuspendedBy) REFERENCES Users(TelegramID)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Sellers(
                SellerID INTEGER PRIMARY KEY AUTOINCREMENT,
                TelegramID INTEGER UNIQUE,
                UserName TEXT,
                StoreName TEXT,
                CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                Status TEXT DEFAULT 'active',
                SuspensionReason TEXT,
                SuspendedBy INTEGER,
                SuspendedAt DATETIME,
                RequireCustomerRegistration INTEGER DEFAULT 0,
                FOREIGN KEY (SuspendedBy) REFERENCES Users(TelegramID)
            )
        """)
    
    # Migration: Change TelegramID from INTEGER to BIGINT in PostgreSQL if needed
    if IS_POSTGRES:
        try:
            print("🔍 Checking Sellers.TelegramID column type...")
            cursor_wrapper.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='sellers' AND column_name='telegramid'
            """)
            result = cursor_wrapper.fetchone()
            if result:
                current_type = result[0].upper()
                print(f"📊 Sellers.TelegramID current type: {current_type}")
                # Force migration if not already BIGINT
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"🔄 FORCE Migrating Sellers.TelegramID from {current_type} to BIGINT...")
                    cursor_wrapper.execute("ALTER TABLE Sellers ALTER COLUMN TelegramID TYPE BIGINT")
                    conn.commit()
                    print("✅ Sellers.TelegramID migrated to BIGINT successfully")
                else:
                    print(f"✅ Sellers.TelegramID is already BIGINT")
            else:
                print("⚠️ Sellers.TelegramID column not found!")
        except Exception as e:
            print(f"❌ Migration ERROR for Sellers.TelegramID: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass
    
    # Migration: Add RequireCustomerRegistration column if it doesn't exist
    try:
        if IS_POSTGRES:
            cursor_wrapper.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='sellers' AND column_name='requirecustomerregistration'
            """)
            if not cursor_wrapper.fetchone():
                print("🔄 Adding RequireCustomerRegistration column to Sellers table...")
                cursor_wrapper.execute("ALTER TABLE Sellers ADD COLUMN RequireCustomerRegistration INTEGER DEFAULT 0")
                conn.commit()
                print("✅ RequireCustomerRegistration column added successfully")
            # تأكد من أن جميع المتاجر لديها القيمة 0 (مفتوحة) افتراضياً
            cursor_wrapper.execute("UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE RequireCustomerRegistration IS NULL")
            conn.commit()
        else:
            try:
                cursor_wrapper.execute("SELECT RequireCustomerRegistration FROM Sellers LIMIT 1")
                # تأكد من أن جميع المتاجر لديها القيمة 0 (مفتوحة) افتراضياً
                cursor_wrapper.execute("UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE RequireCustomerRegistration IS NULL")
                conn.commit()
            except:
                print("🔄 Adding RequireCustomerRegistration column to Sellers table (SQLite)...")
                cursor_wrapper.execute("ALTER TABLE Sellers ADD COLUMN RequireCustomerRegistration INTEGER DEFAULT 0")
                cursor_wrapper.execute("UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE RequireCustomerRegistration IS NULL")
                conn.commit()
                print("✅ RequireCustomerRegistration column added successfully (SQLite)")
    except Exception as e:
        print(f"⚠️ Migration warning (non-critical): {e}")
        try:
            conn.rollback()
        except:
            pass

    # 3. CreditCustomers (Depends on Sellers)
    # Create table with nullable PhoneNumber first (for compatibility with existing data)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS CreditCustomers(
                CustomerID SERIAL PRIMARY KEY,
                SellerID INTEGER,
                FullName TEXT NOT NULL,
                PhoneNumber TEXT,
                TelegramID BIGINT,
                CustomerType TEXT DEFAULT 'CreditCustomer',
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(SellerID, PhoneNumber),
                FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS CreditCustomers(
                CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                SellerID INTEGER,
                FullName TEXT NOT NULL,
                PhoneNumber TEXT,
                TelegramID INTEGER,
                CustomerType TEXT DEFAULT 'CreditCustomer',
                CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(SellerID, PhoneNumber),
                FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
            )
        """)
    
    # Migration: Ensure both CustomerType and TelegramID exist and have correct types
    try:
        if IS_POSTGRES:
            # 1) Ensure CustomerType exists
            cursor_wrapper.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='creditcustomers' AND column_name='customertype'
            """)
            result = cursor_wrapper.fetchone()
            if not result:
                print("🔄 Adding CustomerType column to CreditCustomers table...")
                cursor_wrapper.execute("ALTER TABLE CreditCustomers ADD COLUMN CustomerType TEXT DEFAULT 'CreditCustomer'")
                cursor_wrapper.execute("UPDATE CreditCustomers SET CustomerType = 'CreditCustomer' WHERE CustomerType IS NULL")
                conn.commit()
                print("✅ CustomerType column added successfully")

            # 2) Ensure TelegramID exists and is BIGINT
            cursor_wrapper.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='creditcustomers' AND column_name='telegramid'
            """)
            result = cursor_wrapper.fetchone()
            if not result:
                print("🔄 Adding TelegramID column to CreditCustomers table...")
                cursor_wrapper.execute("ALTER TABLE CreditCustomers ADD COLUMN TelegramID BIGINT")
                conn.commit()
                print("✅ TelegramID column added successfully")
            else:
                cursor_wrapper.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name='creditcustomers' AND column_name='telegramid'
                """)
                type_result = cursor_wrapper.fetchone()
                if type_result:
                    current_type = type_result[0].upper()
                    print(f"📊 CreditCustomers.TelegramID current type: {current_type}")
                    if current_type not in ('BIGINT', 'INT8'):
                        print(f"🔄 FORCE Migrating CreditCustomers.TelegramID from {current_type} to BIGINT...")
                        cursor_wrapper.execute("ALTER TABLE CreditCustomers ALTER COLUMN TelegramID TYPE BIGINT")
                        conn.commit()
                        print("✅ CreditCustomers.TelegramID migrated to BIGINT successfully")
                    else:
                        print("✅ CreditCustomers.TelegramID is already BIGINT")
        else:
            # SQLite: check table columns and add missing ones
            cursor_wrapper.execute("PRAGMA table_info(CreditCustomers)")
            columns = [row[1] for row in cursor_wrapper.fetchall()]

            if 'TelegramID' not in columns:
                print("🔄 Adding TelegramID column to CreditCustomers table...")
                cursor_wrapper.execute("ALTER TABLE CreditCustomers ADD COLUMN TelegramID INTEGER")
                conn.commit()
                print("✅ TelegramID column added successfully")

            if 'CustomerType' not in columns:
                print("🔄 Adding CustomerType column to CreditCustomers table (SQLite)...")
                cursor_wrapper.execute("ALTER TABLE CreditCustomers ADD COLUMN CustomerType TEXT DEFAULT 'CreditCustomer'")
                cursor_wrapper.execute("UPDATE CreditCustomers SET CustomerType = 'CreditCustomer' WHERE CustomerType IS NULL")
                conn.commit()
                print("✅ CustomerType column added successfully (SQLite)")
    except Exception as e:
        print(f"⚠️ Migration warning (non-critical): {e}")
        try:
            conn.rollback()
        except:
            pass
        # Don't fail the entire init if migration fails

    # 4. CreditLimits (Depends on CreditCustomers, Sellers)
    # Using DEFAULT TRUE for Postgres compatibility
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS CreditLimits (
            LimitID INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerID INTEGER,
            SellerID INTEGER,
            MaxCreditAmount REAL DEFAULT 1000000,
            WarningThreshold REAL DEFAULT 0.8,
            CurrentUsedAmount REAL DEFAULT 0,
            IsActive BOOLEAN DEFAULT TRUE,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (CustomerID) REFERENCES CreditCustomers(CustomerID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID),
            UNIQUE(CustomerID, SellerID)
        )
    """)

    # 5. Categories (Depends on Sellers)
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS Categories(
            CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
            SellerID INTEGER,
            Name TEXT,
            OrderIndex INTEGER DEFAULT 0,
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # 6. Products (Depends on Sellers, Categories)
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS Products(
            ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
            SellerID INTEGER,
            CategoryID INTEGER,
            Name TEXT,
            Description TEXT,
            Price REAL,
            WholesalePrice REAL,
            Quantity INTEGER,
            ImagePath TEXT,
            Status TEXT DEFAULT 'active',
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID),
            FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
        )
    """)
    
    # 6.1. ProductImages (Depends on Products) - صور متعددة لكل منتج
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS ProductImages(
            ImageID INTEGER PRIMARY KEY AUTOINCREMENT,
            ProductID INTEGER,
            ImagePath TEXT NOT NULL,
            ImageOrder INTEGER DEFAULT 0,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE CASCADE
        )
    """)

    # 7. Carts (Depends on Users, Products)
    if IS_POSTGRES:
        # PostgreSQL: Use BIGINT for UserID to support large Telegram IDs
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Carts(
                CartID SERIAL PRIMARY KEY,
                UserID BIGINT,
                ProductID INTEGER,
                Quantity INTEGER,
                Price REAL,
                AddedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(UserID, ProductID),
                FOREIGN KEY (UserID) REFERENCES Users(TelegramID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            )
        """)
    else:
        # SQLite: INTEGER supports 64-bit values
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Carts(
                CartID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER,
                ProductID INTEGER,
                Quantity INTEGER,
                Price REAL,
                AddedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(UserID, ProductID),
                FOREIGN KEY (UserID) REFERENCES Users(TelegramID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            )
        """)
    
    # Migration: Change UserID from INTEGER to BIGINT in PostgreSQL if needed
    if IS_POSTGRES:
        try:
            print("🔍 Checking Carts.UserID column type...")
            cursor_wrapper.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='carts' AND column_name='userid'
            """)
            result = cursor_wrapper.fetchone()
            if result:
                current_type = result[0].upper()
                print(f"📊 Carts.UserID current type: {current_type}")
                # Force migration if not already BIGINT
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"🔄 FORCE Migrating Carts.UserID from {current_type} to BIGINT...")
                    cursor_wrapper.execute("ALTER TABLE Carts ALTER COLUMN UserID TYPE BIGINT")
                    conn.commit()
                    print("✅ Carts.UserID migrated to BIGINT successfully")
                else:
                    print(f"✅ Carts.UserID is already BIGINT")
            else:
                print("⚠️ Carts.UserID column not found!")
        except Exception as e:
            print(f"❌ Migration ERROR for Carts.UserID: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass

    # 8. Orders (Depends on Users, Sellers)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Orders(
                OrderID SERIAL PRIMARY KEY,
                BuyerID BIGINT,
                SellerID INTEGER,
                Total REAL,
                Status TEXT DEFAULT 'Pending',
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                DeliveryAddress TEXT,
                Notes TEXT,
                PaymentMethod TEXT DEFAULT 'cash',
                FullyPaid BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (BuyerID) REFERENCES Users(TelegramID),
                FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Orders(
                OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
                BuyerID INTEGER,
                SellerID INTEGER,
                Total REAL,
                Status TEXT DEFAULT 'Pending',
                CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                DeliveryAddress TEXT,
                Notes TEXT,
                PaymentMethod TEXT DEFAULT 'cash',
                FullyPaid BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (BuyerID) REFERENCES Users(TelegramID),
                FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
            )
        """)
    
    # Migration: Change BuyerID from INTEGER to BIGINT in PostgreSQL if needed
    if IS_POSTGRES:
        try:
            print("🔍 Checking Orders.BuyerID column type...")
            cursor_wrapper.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name='orders' AND column_name='buyerid'
            """)
            result = cursor_wrapper.fetchone()
            if result:
                current_type = result[0].upper()
                print(f"📊 Orders.BuyerID current type: {current_type}")
                # Force migration if not already BIGINT
                if current_type not in ('BIGINT', 'INT8'):
                    print(f"🔄 FORCE Migrating Orders.BuyerID from {current_type} to BIGINT...")
                    cursor_wrapper.execute("ALTER TABLE Orders ALTER COLUMN BuyerID TYPE BIGINT")
                    conn.commit()
                    print("✅ Orders.BuyerID migrated to BIGINT successfully")
                else:
                    print(f"✅ Orders.BuyerID is already BIGINT")
            else:
                print("⚠️ Orders.BuyerID column not found!")
        except Exception as e:
            print(f"❌ Migration ERROR for Orders.BuyerID: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass

    # 9. OrderItems (Depends on Orders, Products)
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS OrderItems(
            OrderItemID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER,
            ProductID INTEGER,
            Quantity INTEGER,
            Price REAL,
            ReturnedQuantity INTEGER DEFAULT 0,
            ReturnReason TEXT,
            ReturnDate DATETIME,
            FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
        )
    """)

    # 10. Returns (Depends on Orders, Products, Users)
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS Returns(
            ReturnID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER,
            ProductID INTEGER,
            Quantity INTEGER,
            Reason TEXT,
            Status TEXT DEFAULT 'Pending',
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            ProcessedBy INTEGER,
            ProcessedAt DATETIME,
            FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID),
            FOREIGN KEY (ProcessedBy) REFERENCES Users(TelegramID)
        )
    """)

    # 11. Messages (Depends on Orders, Sellers)
    # Using DEFAULT FALSE for Postgres compatibility
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS Messages(
            MessageID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER,
            SellerID INTEGER,
            MessageType TEXT,
            MessageText TEXT,
            IsRead BOOLEAN DEFAULT FALSE,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # 12. CustomerCredit (Transaction History) - Depends on CreditCustomers, Sellers
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS CustomerCredit(
            CreditID INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerID INTEGER,
            SellerID INTEGER,
            TransactionType TEXT,
            Amount REAL,
            Description TEXT,
            BalanceBefore REAL,
            BalanceAfter REAL,
            TransactionDate DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (CustomerID) REFERENCES CreditCustomers(CustomerID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # 13. CustomerCredit (Depends on CreditCustomers, Sellers)
    # Using DEFAULT FALSE for Postgres compatibility (though boolean not used here heavily)
    cursor_wrapper.execute("""
        CREATE TABLE IF NOT EXISTS CustomerCredit (
            CreditID INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerID INTEGER,
            SellerID INTEGER,
            TransactionType TEXT,
            Amount REAL,
            Description TEXT,
            BalanceBefore REAL,
            BalanceAfter REAL,
            TransactionDate DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (CustomerID) REFERENCES CreditCustomers(CustomerID),
            FOREIGN KEY (SellerID) REFERENCES Sellers(SellerID)
        )
    """)

    # 14. Image Storage (For Syncing Images from Desktop App)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS ImageStorage(
                FileName TEXT PRIMARY KEY,
                FileData BYTEA,
                UploadedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS ImageStorage(
                FileName TEXT PRIMARY KEY,
                FileData BLOB,
                UploadedAt DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    # 15. Auctions (نظام المزادات)
    # جدول المزادات يتحتوي على المنتجات المرفوعة للمزاد
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Auctions(
                AuctionID SERIAL PRIMARY KEY,
                ProductID INTEGER NOT NULL,
                OriginalSellerID INTEGER NOT NULL,
                AuctionStoreID INTEGER NOT NULL,
                StartPrice REAL NOT NULL,
                AuctionStartAt TIMESTAMP NOT NULL,
                AuctionEndAt TIMESTAMP NOT NULL,
                Status TEXT DEFAULT 'active',
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID),
                FOREIGN KEY (OriginalSellerID) REFERENCES Sellers(SellerID),
                FOREIGN KEY (AuctionStoreID) REFERENCES Sellers(SellerID)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS Auctions(
                AuctionID INTEGER PRIMARY KEY AUTOINCREMENT,
                ProductID INTEGER NOT NULL,
                OriginalSellerID INTEGER NOT NULL,
                AuctionStoreID INTEGER NOT NULL,
                StartPrice REAL NOT NULL,
                AuctionStartAt DATETIME NOT NULL,
                AuctionEndAt DATETIME NOT NULL,
                Status TEXT DEFAULT 'active',
                CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID),
                FOREIGN KEY (OriginalSellerID) REFERENCES Sellers(SellerID),
                FOREIGN KEY (AuctionStoreID) REFERENCES Sellers(SellerID)
            )
        """)
    
    # 16. AuctionBidders (جدول المشترين في المزاد)
    # لتسجيل بيانات المشترين الراغبين بالمزايدة
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS AuctionBidders(
                BidderID SERIAL PRIMARY KEY,
                AuctionID INTEGER NOT NULL,
                BidderName TEXT NOT NULL,
                BidderPhone TEXT NOT NULL,
                TelegramID BIGINT,
                RegistrationTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
                UNIQUE(AuctionID, BidderPhone)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS AuctionBidders(
                BidderID INTEGER PRIMARY KEY AUTOINCREMENT,
                AuctionID INTEGER NOT NULL,
                BidderName TEXT NOT NULL,
                BidderPhone TEXT NOT NULL,
                TelegramID INTEGER,
                RegistrationTime DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
                UNIQUE(AuctionID, BidderPhone)
            )
        """)
    
    # 17. AuctionBids (جدول العطاءات)
    # لتسجيل العطاءات المقدمة من المشترين
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS AuctionBids(
                BidID SERIAL PRIMARY KEY,
                AuctionID INTEGER NOT NULL,
                BidderID INTEGER NOT NULL,
                BidAmount REAL NOT NULL,
                BidTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
                FOREIGN KEY (BidderID) REFERENCES AuctionBidders(BidderID)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS AuctionBids(
                BidID INTEGER PRIMARY KEY AUTOINCREMENT,
                AuctionID INTEGER NOT NULL,
                BidderID INTEGER NOT NULL,
                BidAmount REAL NOT NULL,
                BidTime DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
                FOREIGN KEY (BidderID) REFERENCES AuctionBidders(BidderID)
            )
        """)
    
    # 18. AuctionResults (نتائج المزاد)
    # لتسجيل نتائج المزاد (الفائز والسعر النهائي)
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS AuctionResults(
                ResultID SERIAL PRIMARY KEY,
                AuctionID INTEGER NOT NULL UNIQUE,
                WinnerBidderID INTEGER,
                WinnerName TEXT,
                WinnerPhone TEXT,
                FinalPrice REAL,
                AuctionEndedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
                FOREIGN KEY (WinnerBidderID) REFERENCES AuctionBidders(BidderID)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS AuctionResults(
                ResultID INTEGER PRIMARY KEY AUTOINCREMENT,
                AuctionID INTEGER NOT NULL UNIQUE,
                WinnerBidderID INTEGER,
                WinnerName TEXT,
                WinnerPhone TEXT,
                FinalPrice REAL,
                AuctionEndedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
                FOREIGN KEY (WinnerBidderID) REFERENCES AuctionBidders(BidderID)
            )
        """)
    
    # 19. AuctionProducts (نسخة المنتج في متجر المزادات)
    # جدول يحتفظ بنسخة من المنتج في متجر المزادات
    if IS_POSTGRES:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS AuctionProducts(
                AuctionProductID SERIAL PRIMARY KEY,
                AuctionID INTEGER NOT NULL,
                ProductID INTEGER NOT NULL,
                AuctionStoreProductID INTEGER,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID),
                FOREIGN KEY (AuctionStoreProductID) REFERENCES Products(ProductID)
            )
        """)
    else:
        cursor_wrapper.execute("""
            CREATE TABLE IF NOT EXISTS AuctionProducts(
                AuctionProductID INTEGER PRIMARY KEY AUTOINCREMENT,
                AuctionID INTEGER NOT NULL,
                ProductID INTEGER NOT NULL,
                AuctionStoreProductID INTEGER,
                CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID),
                FOREIGN KEY (AuctionStoreProductID) REFERENCES Products(ProductID)
            )
        """)
    
    # ----------------- MIGRATIONS -----------------
    def ensure_column(table, column, definition):
        try:
            cursor_wrapper.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.commit()
            print(f"[OK] Migrated: Added {column} to {table}")
        except Exception as e:
            # Most likely column already exists
            pass
            
    # Explicitly ensure ImagePath exists for Sync
    ensure_column('Sellers', 'ImagePath', 'TEXT')
    ensure_column('Categories', 'ImagePath', 'TEXT')
    ensure_column('Products', 'ImagePath', 'TEXT')
    
    # Ensure Suspension columns exist
    ensure_column('Sellers', 'SuspensionReason', 'TEXT')
    ensure_column('Sellers', 'SuspendedBy', 'INTEGER')
    ensure_column('Sellers', 'SuspendedAt', 'DATETIME')
    
    conn.commit()
    cursor_wrapper.close()
    conn.close()
    
    # Force apply BIGINT migrations after all tables are created
    if IS_POSTGRES:
        print("\n" + "=" * 60)
        print("🔄 APPLYING BIGINT MIGRATIONS (FORCE)...")
        print("=" * 60)
        try:
            force_apply_bigint_migrations()
        except Exception as e:
            print(f"❌ Error in force_apply_bigint_migrations: {e}")
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print("✅ DATABASE INITIALIZATION COMPLETE")
    print("=" * 60)

# Note: init_db() is called in if __name__ == "__main__" block, not here

def force_apply_bigint_migrations():
    """تطبيق Migration بشكل إجباري لجميع الأعمدة"""
    if not IS_POSTGRES:
        print("⚠️ Not PostgreSQL, skipping BIGINT migration")
        return
    
    # Get the actual connection (not DBWrapper) for direct SQL execution
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    try:
        result = urllib.parse.urlparse(database_url)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        # Connect directly using psycopg2
        conn = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port,
            sslmode='require'
        )
        cursor = conn.cursor()
        
        migrations = [
            ("Users", "TelegramID"),
            ("Sellers", "TelegramID"),
            ("CreditCustomers", "TelegramID"),
            ("Orders", "BuyerID"),
            ("Carts", "UserID"),
        ]
        
        for table_name, column_name in migrations:
            try:
                # Check current type
                cursor.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name=%s AND column_name=%s
                """, (table_name.lower(), column_name.lower()))
                result = cursor.fetchone()
                
                if result:
                    current_type = result[0].upper()
                    print(f"📊 {table_name}.{column_name}: {current_type}")
                    
                    if current_type not in ('BIGINT', 'INT8'):
                        print(f"   🔄 FORCE Migrating {table_name}.{column_name} from {current_type} to BIGINT...")
                        # Use direct SQL execution for ALTER TABLE
                        cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT")
                        conn.commit()
                        print(f"   ✅ Successfully migrated to BIGINT")
                    else:
                        print(f"   ✅ Already BIGINT")
                else:
                    print(f"⚠️ {table_name}.{column_name}: Column not found!")
            except Exception as e:
                print(f"❌ Error migrating {table_name}.{column_name}: {e}")
                import traceback
                traceback.print_exc()
                try:
                    conn.rollback()
                except:
                    pass
        
        cursor.close()
        conn.close()
        print("✅ Migration completed successfully")
    except Exception as e:
        print(f"❌ Error connecting to database for migration: {e}")
        import traceback
        traceback.print_exc()

def check_and_fix_db():
    # ... logic skipped ...
    pass

# check_and_fix_db()

# ===================== نظام المزادات - تهيئة متجر المزادات =====================

def initialize_auction_store():
    """
    تهيئة متجر المزادات الخاص (متجر نظام).
    يتم استدعاء هذه الدالة عند بدء البوت.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # التحقق إذا كان متجر المزادات موجوداً بالفعل
        cursor.execute("SELECT SellerID FROM Sellers WHERE StoreName = 'المزادات'")
        result = cursor.fetchone()
        
        if not result:
            # إنشاء حساب نظام خاص لمتجر المزادات
            # استخدام Telegram ID وهمي يكون محفوظاً للنظام
            AUCTION_STORE_TELEGRAM_ID = 1  # معرف النظام
            
            cursor.execute("""
                INSERT INTO Sellers (TelegramID, UserName, StoreName, Status, RequireCustomerRegistration)
                VALUES (?, ?, ?, ?, ?)
            """, (AUCTION_STORE_TELEGRAM_ID, 'System_Auction', 'المزادات', 'active', 0))
            
            conn.commit()
            print("✅ تم إنشاء متجر المزادات بنجاح")
        else:
            print("✅ متجر المزادات موجود بالفعل")
            
    except Exception as e:
        print(f"❌ خطأ في إنشاء متجر المزادات: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_auction_store_id():
    """الحصول على معرف متجر المزادات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT SellerID FROM Sellers WHERE StoreName = 'المزادات' LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"❌ خطأ في الحصول على معرف متجر المزادات: {e}")
        return None
    finally:
        conn.close()

def update_auction_store_owner(admin_telegram_id):
    """
    تحديث معرف الآدمن لمتجر المزادات
    استخدم هذه الدالة إذا كنت تريد تصحيح معرف التليجرام
    
    المعامل:
        admin_telegram_id: معرف التليجرام الحقيقي للآدمن
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # أولاً: جلب معرف متجر المزادات الحالي
        cursor.execute("SELECT SellerID, TelegramID FROM Sellers WHERE StoreName = 'المزادات' LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ متجر المزادات غير موجود")
            return False
        
        seller_id, current_telegram_id = result
        
        # إذا كان المعرف هو نفسه، لا حاجة للتحديث
        if current_telegram_id == admin_telegram_id:
            print(f"✅ معرف المزادات بالفعل محدث: {admin_telegram_id}")
            return True
        
        # تحديث المتجر الموجود
        # نستخدم SetNull للتخلص من القيمة القديمة أولاً، ثم نضع القيمة الجديدة
        cursor.execute("""
            UPDATE Sellers 
            SET TelegramID = ? 
            WHERE SellerID = ?
        """, (admin_telegram_id, seller_id))
        
        conn.commit()
        print(f"✅ تم تحديث معرف المزادات إلى: {admin_telegram_id}")
        return True
    except Exception as e:
        print(f"❌ خطأ: {e}")
        # إذا كان الخطأ عن تضارب المفتاح، نحاول حذف السجل القديم أولاً
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            try:
                print("🔧 محاولة إزالة الدخول المتضارب...")
                cursor.execute("""
                    UPDATE Sellers 
                    SET TelegramID = NULL 
                    WHERE TelegramID = ? AND StoreName != 'المزادات'
                """, (admin_telegram_id,))
                conn.commit()
                
                # محاولة التحديث مجدداً
                cursor.execute("""
                    UPDATE Sellers 
                    SET TelegramID = ? 
                    WHERE StoreName = 'المزادات'
                """, (admin_telegram_id,))
                conn.commit()
                print(f"✅ تم تحديث معرف المزادات بعد إزالة التضارب: {admin_telegram_id}")
                return True
            except Exception as e2:
                print(f"❌ فشل حتى بعد إزالة التضارب: {e2}")
                conn.rollback()
                return False
        
        conn.rollback()
        return False
    finally:
        conn.close()

def create_auction_for_product(original_seller_id, product_id, start_price, auction_start, auction_end):
    """
    إنشاء مزاد جديد لمنتج.
    1. ينسخ المنتج إلى متجر المزادات
    2. ينشئ سجل المزاد
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # الحصول على معرف متجر المزادات
        auction_store_id = get_auction_store_id()
        if not auction_store_id:
            return False, "❌ متجر المزادات غير متوفر"
        
        # الحصول على بيانات المنتج الأصلي
        cursor.execute("""
            SELECT ProductID, SellerID, CategoryID, Name, Description, Price, 
                   WholesalePrice, Quantity, ImagePath, Status
            FROM Products
            WHERE ProductID = ?
        """, (product_id,))
        
        product = cursor.fetchone()
        if not product:
            return False, "❌ المنتج غير موجود"
        
        # إنشاء نسخة من المنتج في متجر المزادات
        cursor.execute("""
            INSERT INTO Products 
            (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (auction_store_id, product[2], product[3], product[4], start_price, 
              product[6], product[7], product[8], 'active'))
        
        auction_product_id = cursor.lastrowid
        
        # إنشاء سجل المزاد
        cursor.execute("""
            INSERT INTO Auctions 
            (ProductID, OriginalSellerID, AuctionStoreID, StartPrice, AuctionStartAt, AuctionEndAt, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (auction_product_id, original_seller_id, auction_store_id, start_price, 
              auction_start, auction_end, 'active'))
        
        auction_id = cursor.lastrowid
        
        # إنشاء سجل في AuctionProducts
        cursor.execute("""
            INSERT INTO AuctionProducts (AuctionID, ProductID, AuctionStoreProductID)
            VALUES (?, ?, ?)
        """, (auction_id, product_id, auction_product_id))
        
        conn.commit()
        return True, f"✅ تم إنشاء المزاد برقم {auction_id}", auction_id
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء المزاد: {e}")
        conn.rollback()
        return False, f"❌ خطأ في إنشاء المزاد: {e}", None
    finally:
        conn.close()

def register_auction_bidder(auction_id, bidder_name, bidder_phone, telegram_id=None):
    """
    تسجيل مشتري جديد في المزاد
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO AuctionBidders (AuctionID, BidderName, BidderPhone, TelegramID)
            VALUES (?, ?, ?, ?)
        """, (auction_id, bidder_name, bidder_phone, telegram_id))
        
        bidder_id = cursor.lastrowid
        conn.commit()
        return True, "✅ تم تسجيل البيانات بنجاح", bidder_id
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ خطأ في التسجيل: {e}", None
    finally:
        conn.close()

def place_auction_bid(auction_id, bidder_id, bid_amount):
    """
    تسجيل عطاء جديد من المشتري
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # التحقق من وجود المشتري والمزاد
        cursor.execute("""
            SELECT BidderID FROM AuctionBidders 
            WHERE BidderID = ? AND AuctionID = ?
        """, (bidder_id, auction_id))
        
        if not cursor.fetchone():
            return False, "❌ المشتري أو المزاد غير موجود", None
        
        # إدراج العطاء
        cursor.execute("""
            INSERT INTO AuctionBids (AuctionID, BidderID, BidAmount)
            VALUES (?, ?, ?)
        """, (auction_id, bidder_id, bid_amount))
        
        bid_id = cursor.lastrowid
        conn.commit()
        return True, "✅ تم تسجيل العطاء بنجاح", bid_id
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ خطأ في تسجيل العطاء: {e}", None
    finally:
        conn.close()

def get_auction_bids(auction_id):
    """
    الحصول على قائمة العطاءات لمزاد معين مرتبة تصاعدياً
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT ab.BidderName, ab.BidderPhone, MAX(bid.BidAmount) as HighestBid, COUNT(bid.BidID) as BidCount
            FROM AuctionBidders ab
            LEFT JOIN AuctionBids bid ON ab.BidderID = bid.BidderID
            WHERE ab.AuctionID = ?
            GROUP BY ab.BidderID, ab.BidderName, ab.BidderPhone
            ORDER BY HighestBid ASC
        """, (auction_id,))
        
        bids = cursor.fetchall()
        return bids
        
    except Exception as e:
        print(f"❌ خطأ في جلب العطاءات: {e}")
        return []
    finally:
        conn.close()

def get_auction_winner(auction_id):
    """
    الحصول على الفائز بالمزاد (أعلى عطاء)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT ab.BidderID, ab.BidderName, ab.BidderPhone, MAX(b.BidAmount) as FinalPrice
            FROM AuctionBidders ab
            LEFT JOIN AuctionBids b ON ab.BidderID = b.BidderID
            WHERE ab.AuctionID = ?
            GROUP BY ab.BidderID, ab.BidderName, ab.BidderPhone
            ORDER BY FinalPrice DESC
            LIMIT 1
        """, (auction_id,))
        
        result = cursor.fetchone()
        return result
        
    except Exception as e:
        print(f"❌ خطأ في جلب الفائز: {e}")
        return None
    finally:
        conn.close()

def close_auction(auction_id):
    """
    إغلاق المزاد وتسجيل النتيجة
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # الحصول على الفائز
        winner = get_auction_winner(auction_id)
        
        if winner:
            bidder_id, bidder_name, bidder_phone, final_price = winner
        else:
            bidder_id, bidder_name, bidder_phone, final_price = None, None, None, None
        
        # تحديث حالة المزاد
        cursor.execute("""
            UPDATE Auctions SET Status = 'closed' WHERE AuctionID = ?
        """, (auction_id,))
        
        # تسجيل النتيجة
        cursor.execute("""
            INSERT INTO AuctionResults (AuctionID, WinnerBidderID, WinnerName, WinnerPhone, FinalPrice)
            VALUES (?, ?, ?, ?, ?)
        """, (auction_id, bidder_id, bidder_name, bidder_phone, final_price))
        
        conn.commit()
        return True, winner
        
    except Exception as e:
        print(f"❌ خطأ في إغلاق المزاد: {e}")
        conn.rollback()
        return False, None
    finally:
        conn.close()

# Note: download_image_from_cloud is defined later in the file (after line 1342)

# ===================== نظام حدود الائتمان =====================

def check_credit_limit(customer_id, seller_id, new_amount):
    """التحقق إذا كان يمكن للزبون تحمل مبلغ جديد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على الحد الحالي
    cursor.execute("""
        SELECT MaxCreditAmount, CurrentUsedAmount 
        FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
    """, (customer_id, seller_id))
    
    limit_data = cursor.fetchone()
    
    if not limit_data:
        # إذا لم يكن للزبون حد محدد، نعود لقيمة افتراضية كبيرة
        conn.close()
        return True, "لا يوجد حد ائتماني محدد", 0, 0, 0
    
    max_limit, current_used = limit_data
    
    # حساب المبلغ الجديد الكلي
    new_total = current_used + new_amount
    
    if new_total > max_limit:
        remaining = max_limit - current_used
        conn.close()
        return False, f"❌ تجاوز الحد الائتماني! الحد الأقصى: {max_limit:,.0f} دينار، المستخدم: {current_used:,.0f} دينار، المتبقي: {remaining:,.0f} دينار", max_limit, current_used, remaining
    
    # التحقق من عتبة التحذير
    warning_percentage = current_used / max_limit if max_limit > 0 else 0
    
    if warning_percentage >= 0.8:
        conn.close()
        return True, f"⚠️ تحذير: وصلت إلى {warning_percentage*100:.0f}% من حدك الائتماني", max_limit, current_used, max_limit - current_used
    
    conn.close()
    return True, f"✅ الحد الائتماني مناسب. المتبقي: {max_limit - current_used:,.0f} دينار", max_limit, current_used, max_limit - current_used

def update_credit_usage(customer_id, seller_id, amount, transaction_type):
    """تحديث المبلغ المستخدم من الحد الائتماني"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على الحد الحالي أو إنشاء واحد جديد
    cursor.execute("""
        SELECT CurrentUsedAmount FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
    """, (customer_id, seller_id))
    
    result = cursor.fetchone()
    
    if result:
        current_used = result[0]
        
        if transaction_type == 'purchase':
            new_used = current_used + amount
        elif transaction_type == 'payment':
            new_used = current_used - amount
            if new_used < 0:
                new_used = 0
        else:
            new_used = current_used
        
        cursor.execute("""
            UPDATE CreditLimits 
            SET CurrentUsedAmount=?, UpdatedAt=CURRENT_TIMESTAMP
            WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
        """, (new_used, customer_id, seller_id))
    else:
        # إنشاء سجل جديد
        if transaction_type == 'purchase':
            current_used = amount
        else:
            current_used = 0
        
        cursor.execute("""
            INSERT INTO CreditLimits 
            (CustomerID, SellerID, MaxCreditAmount, CurrentUsedAmount, IsActive)
            VALUES (?, ?, 1000000, ?, TRUE)
        """, (customer_id, seller_id, current_used))
    
    conn.commit()
    conn.close()
    return True

def set_credit_limit(customer_id, seller_id, max_amount, warning_percentage=0.8):
    """تعيين حد ائتماني للزبون"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على المبلغ المستخدم الحالي
    cursor.execute("""
        SELECT CurrentUsedAmount FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=?
    """, (customer_id, seller_id))
    
    result = cursor.fetchone()
    current_used = result[0] if result else 0
    
    if IS_POSTGRES:
        cursor.execute("""
            INSERT INTO CreditLimits (CustomerID, SellerID, MaxCreditAmount, WarningThreshold, CurrentUsedAmount, IsActive)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (CustomerID, SellerID) DO UPDATE SET
                MaxCreditAmount = EXCLUDED.MaxCreditAmount,
                WarningThreshold = EXCLUDED.WarningThreshold,
                IsActive = TRUE
        """, (customer_id, seller_id, max_amount, warning_percentage, current_used))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO CreditLimits 
            (CustomerID, SellerID, MaxCreditAmount, WarningThreshold, CurrentUsedAmount, IsActive)
            VALUES (?, ?, ?, ?, ?, TRUE)
        """, (customer_id, seller_id, max_amount, warning_percentage, current_used))
    
    conn.commit()
    conn.close()
    return True

def get_credit_limit_info(customer_id, seller_id):
    """الحصول على معلومات الحد الائتماني"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT MaxCreditAmount, CurrentUsedAmount, WarningThreshold,
               CASE 
                   WHEN CurrentUsedAmount >= MaxCreditAmount THEN '❌ ممتلئ'
                   WHEN CurrentUsedAmount >= MaxCreditAmount * WarningThreshold THEN '⚠️ تحذير'
                   ELSE '✅ متاح'
               END as Status,
               MaxCreditAmount - CurrentUsedAmount as Available
        FROM CreditLimits 
        WHERE CustomerID=? AND SellerID=? AND IsActive IS TRUE
    """, (customer_id, seller_id))
    
    info = cursor.fetchone()
    conn.close()
    
    if info:
        return {
            'max_limit': info[0],
            'current_used': info[1],
            'warning_threshold': info[2],
            'status': info[3],
            'available': info[4]
        }
    else:
        return {
            'max_limit': 1000000,
            'current_used': 0,
            'warning_threshold': 0.8,
            'status': '✅ غير محدد',
            'available': 1000000
        }

def reset_credit_usage(customer_id, seller_id):
    """إعادة تعيين المبلغ المستخدم للصفر"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE CreditLimits 
        SET CurrentUsedAmount=0, UpdatedAt=CURRENT_TIMESTAMP
        WHERE CustomerID=? AND SellerID=?
    """, (customer_id, seller_id))
    
    conn.commit()
    conn.close()
    return True

def deactivate_credit_limit(customer_id, seller_id):
    """تعطيل الحد الائتماني للزبون"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE CreditLimits 
        SET IsActive=0, UpdatedAt=CURRENT_TIMESTAMP
        WHERE CustomerID=? AND SellerID=?
    """, (customer_id, seller_id))
    
    conn.commit()
    conn.close()
    return True

# ===================== دوال إدارة الحسابات =====================
def suspend_seller(seller_id, suspended_by, reason=None):
    """تعليق حساب بائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE Sellers 
        SET Status = 'suspended',
            SuspensionReason = ?,
            SuspendedBy = ?,
            SuspendedAt = CURRENT_TIMESTAMP
        WHERE SellerID = ?
    """, (reason, suspended_by, seller_id))
    
    conn.commit()
    conn.close()
    
    # إرسال إشعار للبائع
    seller = get_seller_by_id(seller_id)
    if seller:
        try:
            bot.send_message(seller[1],
                           f"⚠️ **تم تعليق حسابك**\n\n"
                           f"🏪 المتجر: {seller[3]}\n"
                           f"📋 السبب: {reason if reason else 'غير محدد'}\n"
                           f"⏰ التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                           f"للمزيد من المعلومات، يرجى التواصل مع الإدارة.")
        except:
            pass
    
    return True

def activate_seller(seller_id, activated_by):
    """تنشيط حساب بائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE Sellers 
        SET Status = 'active',
            SuspensionReason = NULL,
            SuspendedBy = NULL,
            SuspendedAt = NULL
        WHERE SellerID = ?
    """, (seller_id,))
    
    conn.commit()
    conn.close()
    
    # إرسال إشعار للبائع
    seller = get_seller_by_id(seller_id)
    if seller:
        try:
            bot.send_message(seller[1],
                           f"✅ **تم تنشيط حسابك**\n\n"
                           f"🏪 المتجر: {seller[3]}\n"
                           f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                           f"يمكنك الآن استخدام حسابك بشكل طبيعي.")
        except:
            pass
    
    return True

def is_seller_active(seller_telegram_id):
    """التحقق من نشاط حساب البائع"""
    seller = get_seller_by_telegram(seller_telegram_id)
    return seller and seller[5] == 'active'

def get_seller_status(seller_id):
    """الحصول على حالة البائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Status, SuspensionReason, SuspendedAt FROM Sellers WHERE SellerID=?", (seller_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_suspended_sellers():
    """الحصول على قائمة الحسابات المعلقة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, u.UserName as SuspenderName
        FROM Sellers s
        LEFT JOIN Users u ON s.SuspendedBy = u.TelegramID
        WHERE s.Status = 'suspended'
        ORDER BY s.SuspendedAt DESC
    """)
    sellers = cursor.fetchall()
    conn.close()
    return sellers

# ===================== نظام الزبائن الآجل =====================

def get_image_from_cloud(filename):
    """
    جلب صورة من السحابة مباشرة دون الحاجة لحفظها محلياً
    Returns bytes إذا وُجدت، None إذا لم تُوجد
    """
    if not IS_POSTGRES:
        return None
        
    try:
        filename = os.path.basename(filename) if filename else None
        
        if not filename:
            return None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Try exact match first
        cursor.execute('SELECT filedata FROM imagestorage WHERE filename = %s', (filename,))
        result = cursor.fetchone()
        
        # If exact match fails, try case-insensitive
        if not result:
            cursor.execute('SELECT filedata FROM imagestorage WHERE LOWER(filename) = LOWER(%s) LIMIT 1', (filename,))
            result = cursor.fetchone()
        
        # If still not found, try partial match
        if not result:
            base_without_ext = os.path.splitext(filename)[0]
            cursor.execute("""
                SELECT "filedata" 
                FROM "imagestorage" 
                WHERE "filename" LIKE %s 
                ORDER BY "uploadedat" DESC 
                LIMIT 1
            """, (f"%{base_without_ext}%",))
            result = cursor.fetchone()
        
        conn.close()
        
        if result and result[0]:
            file_data = result[0]
            
            # Handle different data types
            if isinstance(file_data, memoryview):
                return file_data.tobytes()
            elif isinstance(file_data, bytes):
                return file_data
            elif isinstance(file_data, str):
                return file_data.encode('latin1')
            
            return file_data
        
        return None
        
    except Exception as e:
        print(f"❌ Error getting image from cloud: {e}")
        return None


def download_image_from_cloud(filename):
    """
    تحميل صورة من السحابة وحفظها محلياً.
    مع دعم البحث الذكي عن الصور
    """
    if not IS_POSTGRES:
        return False
        
    try:
        # Sanitize filename
        filename = os.path.basename(filename) if filename else None
        
        if not filename:
            print(f"❌ No filename provided")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Try exact match first
        cursor.execute('SELECT filedata FROM imagestorage WHERE filename = %s', (filename,))
        result = cursor.fetchone()
        found_filename = filename
        
        # If exact match fails, try case-insensitive match
        if not result:
            print(f"⚠️ Exact match failed for: {filename}, trying case-insensitive match...")
            cursor.execute('SELECT filename, filedata FROM imagestorage WHERE LOWER(filename) = LOWER(%s) LIMIT 1', (filename,))
            row = cursor.fetchone()
            
            if row:
                found_filename = row[0]
                result = (row[1],)
                print(f"✅ Found case-insensitive match: {found_filename}")
        
        # If still not found, try partial match
        if not result:
            print(f"⚠️ Case-insensitive match failed, trying partial match...")
            # Extract just the basename without extension for matching
            base_without_ext = os.path.splitext(filename)[0]
            cursor.execute("""
                SELECT "filename", "filedata" 
                FROM "imagestorage" 
                WHERE "filename" LIKE %s 
                ORDER BY "uploadedat" DESC 
                LIMIT 1
            """, (f"%{base_without_ext}%",))
            row = cursor.fetchone()
            
            if row:
                found_filename = row[0]
                result = (row[1],)
                print(f"✅ Found partial match: {found_filename}")
        
        if result and result[0]:
            file_data = result[0]
            
            # Handle different data types
            if isinstance(file_data, memoryview):
                file_data = file_data.tobytes()
            elif isinstance(file_data, str):
                file_data = file_data.encode('latin1')
                
            # Ensure IMAGES_FOLDER exists
            os.makedirs(IMAGES_FOLDER, exist_ok=True)
            
            # Save with the found filename
            local_path = os.path.join(IMAGES_FOLDER, found_filename)
            with open(local_path, 'wb') as f:
                f.write(file_data)
            
            print(f"✅ Downloaded {found_filename} ({len(file_data):,} bytes) to {local_path}")
            conn.close()
            return True
            
        print(f"❌ Image not found in ImageStorage: {filename}")
        conn.close()
        return False
        
    except Exception as e:
        print(f"❌ Error downloading image {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False

def add_credit_customer(seller_id, full_name, phone_number=None, customer_type='CreditCustomer', telegram_id=None):
    """إضافة زبون آجل أو نقطة بيع - فقط باستخدام الاسم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # التحقق من أن الاسم موجود
        if not full_name or not full_name.strip():
            conn.close()
            return None
        
        full_name = full_name.strip()
        
        # تحقق أولاً إذا كان الاسم موجود بالفعل
        if IS_POSTGRES:
            cursor.execute(
                "SELECT CustomerID FROM CreditCustomers WHERE SellerID=%s AND FullName=%s",
                (seller_id, full_name)
            )
        else:
            cursor.execute(
                "SELECT CustomerID FROM CreditCustomers WHERE SellerID=? AND FullName=?",
                (seller_id, full_name)
            )
        
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return existing[0]
        
        # إضافة الزبون الجديد
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO CreditCustomers (SellerID, FullName, PhoneNumber, CustomerType, TelegramID)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING CustomerID
            """, (seller_id, full_name, phone_number, customer_type, telegram_id))
            result = cursor.fetchone()
            customer_id = result[0] if result else None
        else:
            cursor.execute("""
                INSERT INTO CreditCustomers (SellerID, FullName, PhoneNumber, CustomerType, TelegramID)
                VALUES (?, ?, ?, ?, ?)
            """, (seller_id, full_name, phone_number, customer_type, telegram_id))
            customer_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return customer_id
            
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        return None

def update_credit_customer(customer_id, seller_id, full_name=None, phone_number=None):
    """تحديث بيانات زبون آجل"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        updates = []
        params = []
        
        if full_name:
            updates.append("FullName = ?" if not IS_POSTGRES else "FullName = %s")
            params.append(full_name)
        
        if phone_number is not None:
            updates.append("PhoneNumber = ?" if not IS_POSTGRES else "PhoneNumber = %s")
            params.append(phone_number)
        
        if not updates:
            conn.close()
            return False
        
        params.append(customer_id)
        params.append(seller_id)
        
        if IS_POSTGRES:
            query = f"UPDATE CreditCustomers SET {', '.join(updates)} WHERE CustomerID = %s AND SellerID = %s"
        else:
            query = f"UPDATE CreditCustomers SET {', '.join(updates)} WHERE CustomerID = ? AND SellerID = ?"
        
        cursor.execute(query, params)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        print(f"Error updating credit customer: {e}")
        conn.close()
        return False

def get_credit_customer(seller_id, phone_number=None, full_name=None):
    """الحصول على زبون آجل بالهاتف أو الاسم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if phone_number:
        if IS_POSTGRES:
            cursor.execute("""
                SELECT * FROM CreditCustomers 
                WHERE SellerID=%s AND PhoneNumber=%s
            """, (seller_id, phone_number))
        else:
            cursor.execute("""
                SELECT * FROM CreditCustomers 
                WHERE SellerID=? AND PhoneNumber=?
            """, (seller_id, phone_number))
    elif full_name:
        if IS_POSTGRES:
            cursor.execute("""
                SELECT * FROM CreditCustomers 
                WHERE SellerID=%s AND FullName LIKE %s
            """, (seller_id, f"%{full_name}%"))
        else:
            cursor.execute("""
                SELECT * FROM CreditCustomers 
                WHERE SellerID=? AND FullName LIKE ?
            """, (seller_id, f"%{full_name}%"))
    else:
        conn.close()
        return None
    
    customer = cursor.fetchone()
    conn.close()
    return customer

def is_customer_registered_for_store_by_telegram_id(telegram_id, seller_id):
    """التحقق من أن Telegram ID مسجل في CreditCustomers لهذا المتجر"""
    try:
        if not telegram_id:
            print(f"⚠️ TelegramID فارغ")
            return False
        
        conn = get_db_connection()
        cursor_wrapper = conn.cursor()
        
        print(f"\n{'='*60}")
        print(f"🔍 البحث عن: SellerID={seller_id}, TelegramID={telegram_id}")
        print(f"   نوع TelegramID: {type(telegram_id)}")
        print(f"   طول TelegramID: {len(str(telegram_id))}")
        print(f"{'='*60}")
        
        cursor_wrapper.execute("""
            SELECT CustomerID FROM CreditCustomers 
            WHERE SellerID=? AND TelegramID=?
        """, (seller_id, telegram_id))
        
        result = cursor_wrapper.fetchone()
        
        if result:
            print(f"✅ وجدنا الزبون! CustomerID={result[0]}")
        else:
            print(f"❌ لم نجد الزبون بهذا التوليفة (SellerID={seller_id} + TelegramID={telegram_id})")
            
            # جرب البحث عن نفس TelegramID في بائعين آخرين
            print(f"\n🔎 جاري البحث عن TelegramID={telegram_id} في جميع البائعين...")
            cursor_wrapper.execute("""
                SELECT CustomerID, SellerID, FullName FROM CreditCustomers 
                WHERE TelegramID=?
            """, (telegram_id,))
            all_results = cursor_wrapper.fetchall()
            
            if all_results:
                print(f"⚠️ وجدنا TelegramID في بائعين آخرين:")
                for cust_id, sel_id, name in all_results:
                    print(f"   - CustomerID={cust_id}, SellerID={sel_id}, الاسم='{name}'")
            else:
                print(f"❌ TelegramID={telegram_id} غير موجود في أي متجر!")
            
            # جرب البحث عن جميع الزبائن لهذا البائع
            print(f"\n🔎 جميع الزبائن للبائع SellerID={seller_id}:")
            cursor_wrapper.execute("""
                SELECT CustomerID, FullName, TelegramID FROM CreditCustomers 
                WHERE SellerID=?
            """, (seller_id,))
            all_customers = cursor_wrapper.fetchall()
            
            if all_customers:
                for cust_id, name, tele_id in all_customers:
                    match = "✅ تطابق" if tele_id == telegram_id else "❌"
                    print(f"   {match} - CustomerID={cust_id}, الاسم='{name}', TelegramID={tele_id}")
            else:
                print(f"   ⚠️ لا يوجد زبائن لهذا البائع!")
        
        cursor_wrapper.close()
        conn.close()
        
        return result is not None
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من تسجيل الزبون بـ Telegram ID: {e}")
        import traceback
        traceback.print_exc()
        return False

def is_customer_registered_for_store_by_phone(phone_number, seller_id):
    """التحقق من أن رقم الهاتف مسجل في CreditCustomers لهذا المتجر (deprecated - use Telegram ID)"""
    try:
        if not phone_number or not phone_number.strip():
            return False
        
        # تنظيف رقم الهاتف (إزالة المسافات والرموز)
        phone_number = phone_number.strip().replace(" ", "").replace("-", "").replace("+", "")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                SELECT CustomerID FROM CreditCustomers 
                WHERE SellerID=%s AND PhoneNumber=%s
            """, (seller_id, phone_number))
        else:
            cursor.execute("""
                SELECT CustomerID FROM CreditCustomers 
                WHERE SellerID=? AND PhoneNumber=?
            """, (seller_id, phone_number))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من تسجيل الزبون بالهاتف: {e}")
        return False

def has_previous_orders_for_store(telegram_id, seller_id):
    """التحقق من وجود طلبات سابقة للعميل من متجر معين (للمتاجر المغلقة)"""
    try:
        if not telegram_id:
            return False
        
        conn = get_db_connection()
        cursor_wrapper = conn.cursor()
        
        # البحث عن أي طلبات سابقة مؤكدة للعميل من هذا البائع
        # البحث في جدول Orders حيث BuyerID = TelegramID للمشتري
        cursor_wrapper.execute("""
            SELECT OrderID FROM Orders 
            WHERE BuyerID=? AND SellerID=? AND Status IN ('confirmed', 'delivered', 'completed')
            LIMIT 1
        """, (telegram_id, seller_id))
        
        result = cursor_wrapper.fetchone()
        cursor_wrapper.close()
        conn.close()
        
        return result is not None
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من الطلبات السابقة: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_all_credit_customers(seller_id):
    """الحصول على جميع الزبائن الآجلين ونقاط البيع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if IS_POSTGRES:
            cursor.execute("""
                SELECT cc.CustomerID, cc.SellerID, cc.FullName, cc.PhoneNumber, cc.TelegramID,
                       COALESCE(cc.CustomerType, 'CreditCustomer') as CustomerType, cc.CreatedAt,
                       COALESCE(cl.MaxCreditAmount, 1000000) as MaxCredit,
                       COALESCE(cl.CurrentUsedAmount, 0) as CurrentUsed,
                       COALESCE(cl.IsActive, TRUE) as LimitActive
                FROM CreditCustomers cc
                LEFT JOIN CreditLimits cl ON cc.CustomerID = cl.CustomerID AND cc.SellerID = cl.SellerID
                WHERE cc.SellerID=%s 
                ORDER BY cc.FullName
            """, (seller_id,))
        else:
            cursor.execute("""
                SELECT cc.CustomerID, cc.SellerID, cc.FullName, cc.PhoneNumber, cc.TelegramID,
                       COALESCE(cc.CustomerType, 'CreditCustomer') as CustomerType, cc.CreatedAt,
                       COALESCE(cl.MaxCreditAmount, 1000000) as MaxCredit,
                       COALESCE(cl.CurrentUsedAmount, 0) as CurrentUsed,
                       COALESCE(cl.IsActive, 1) as LimitActive
                FROM CreditCustomers cc
                LEFT JOIN CreditLimits cl ON cc.CustomerID = cl.CustomerID AND cc.SellerID = cl.SellerID
                WHERE cc.SellerID=? 
                ORDER BY cc.FullName
            """, (seller_id,))
        
        customers = cursor.fetchall()
        return customers if customers else []
    except Exception as e:
        print(f"ERROR in get_all_credit_customers: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def is_credit_customer(seller_id, phone_number, full_name):
    """التحقق إذا كان زبون آجل"""
    customer = get_credit_customer(seller_id, phone_number, full_name)
    return customer is not None

# ===================== نظام كشف حساب الزبائن الآجل =====================
def add_credit_transaction(customer_id, seller_id, transaction_type, amount, description=""):
    """إضافة معاملة ائتمانية للزبون"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على الرصيد الحالي
    cursor.execute("""
        SELECT BalanceAfter 
        FROM CustomerCredit 
        WHERE CustomerID=? AND SellerID=?
        ORDER BY TransactionDate DESC LIMIT 1
    """, (customer_id, seller_id))
    
    result = cursor.fetchone()
    balance_before = result[0] if result else 0
    
    if transaction_type == 'purchase':
        balance_after = balance_before + amount
    elif transaction_type == 'payment':
        balance_after = balance_before - amount
    elif transaction_type == 'adjustment':
        balance_after = amount
    else:
        balance_after = balance_before
    
    # إضافة المعاملة
    query = """
        INSERT INTO CustomerCredit 
        (CustomerID, SellerID, TransactionType, Amount, Description, BalanceBefore, BalanceAfter)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    if IS_POSTGRES:
        query += " RETURNING CreditID"
    
    cursor.execute(query, (customer_id, seller_id, transaction_type, amount, description, balance_before, balance_after))
    
    # تحديث الحد الائتماني
    if transaction_type in ['purchase', 'payment']:
        update_credit_usage(customer_id, seller_id, amount, transaction_type)
    
    conn.commit()
    conn.close()
    
    return True

def get_customer_balance(customer_id, seller_id):
    """الحصول على رصيد الزبون لدى بائع معين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT BalanceAfter 
        FROM CustomerCredit 
        WHERE CustomerID=? AND SellerID=?
        ORDER BY TransactionDate DESC LIMIT 1
    """, (customer_id, seller_id))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 0

def get_customer_statement(customer_id, seller_id, limit=10):
    """الحصول على كشف حساب الزبون"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            TransactionType,
            Amount,
            Description,
            BalanceBefore,
            BalanceAfter,
            TransactionDate
        FROM CustomerCredit 
        WHERE CustomerID=? AND SellerID=?
        ORDER BY TransactionDate DESC
        LIMIT ?
    """, (customer_id, seller_id, limit))
    
    transactions = cursor.fetchall()
    conn.close()
    
    return transactions

def get_all_customers_with_balance(seller_id):
    """الحصول على جميع الزبائن الذين لهم رصيد لدى البائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cc.CustomerID,
            cc.FullName,
            cc.PhoneNumber,
            cc.CreatedAt,
            COALESCE((
                SELECT BalanceAfter 
                FROM CustomerCredit 
                WHERE CustomerID = cc.CustomerID AND SellerID = cc.SellerID
                ORDER BY TransactionDate DESC LIMIT 1
            ), 0) as Balance,
            COALESCE(cl.MaxCreditAmount, 1000000) as MaxCredit,
            COALESCE(cl.CurrentUsedAmount, 0) as CurrentUsed,
            COALESCE(cl.IsActive, TRUE) as LimitActive
        FROM CreditCustomers cc
        LEFT JOIN CreditLimits cl ON cc.CustomerID = cl.CustomerID AND cc.SellerID = cl.SellerID
        WHERE cc.SellerID = ?
        ORDER BY Balance DESC
    """, (seller_id,))
    
    customers = cursor.fetchall()
    conn.close()
    
    return customers

# ===================== دوال النظام =====================
def add_user(telegram_id, username, usertype, phone_number=None, full_name=None):
    """إضافة مستخدم جديد أو تحديث المستخدم الموجود"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        if IS_POSTGRES:
            # PostgreSQL syntax
            cursor_wrapper.execute("""
                INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) 
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (TelegramID) 
                DO UPDATE SET 
                    UserName = EXCLUDED.UserName, 
                    UserType = EXCLUDED.UserType, 
                    PhoneNumber = COALESCE(EXCLUDED.PhoneNumber, Users.PhoneNumber), 
                    FullName = COALESCE(EXCLUDED.FullName, Users.FullName)
            """, (telegram_id, username, usertype, phone_number, full_name))
        else:
            # SQLite syntax
            cursor_wrapper.execute("""
                INSERT OR REPLACE INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) 
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, username, usertype, phone_number, full_name))
        conn.commit()
        print(f"[SUCCESS] User {telegram_id} added/updated successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Error in add_user for {telegram_id}: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

def get_user(telegram_id):
    """الحصول على معلومات المستخدم من TelegramID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        cursor_wrapper.execute("SELECT * FROM Users WHERE TelegramID=?", (telegram_id,))
        user = cursor_wrapper.fetchone()
        return user
    except Exception as e:
        print(f"[ERROR] Error in get_user for {telegram_id}: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor.close()
        conn.close()

def update_user_info(telegram_id, phone_number=None, full_name=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if phone_number is not None:
        updates.append("PhoneNumber = ?")
        params.append(phone_number)
    
    if full_name is not None:
        updates.append("FullName = ?")
        params.append(full_name)
    
    if updates:
        params.append(telegram_id)
        query = f"UPDATE Users SET {', '.join(updates)} WHERE TelegramID = ?"
        cursor.execute(query, params)
    
    conn.commit()
    conn.close()

def is_bot_admin(telegram_id):
    result = telegram_id == BOT_ADMIN_ID
    print(f"[DEBUG] is_bot_admin({telegram_id}): checking {telegram_id} == {BOT_ADMIN_ID} = {result}")
    return result

def add_seller(telegram_id, username, store_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        if IS_POSTGRES:
            cursor_wrapper.execute("""
                INSERT INTO Sellers (TelegramID, UserName, StoreName)
                VALUES (?, ?, ?)
                ON CONFLICT (TelegramID) DO NOTHING
            """, (telegram_id, username, store_name))
        else:
            cursor_wrapper.execute("""
                INSERT OR IGNORE INTO Sellers (TelegramID, UserName, StoreName)
                VALUES (?, ?, ?)
            """, (telegram_id, username, store_name))
        
        cursor_wrapper.execute("""
            UPDATE Sellers SET StoreName=?, UserName=?
            WHERE TelegramID=?
        """, (store_name, username, telegram_id))
        conn.commit()
    except Exception as e:
        print(f"Error in add_seller: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
    finally:
        cursor.close()
        conn.close()

def get_seller_by_telegram(telegram_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        if IS_POSTGRES:
            cursor_wrapper.execute('SELECT * FROM sellers WHERE telegramid=%s', (telegram_id,))
        else:
            cursor_wrapper.execute("SELECT * FROM Sellers WHERE TelegramID=?", (telegram_id,))
        seller = cursor_wrapper.fetchone()
        
        # إذا لم يتم العثور على البائع، حاول البحث في جدول Users
        if not seller:
            user = get_user(telegram_id)
            if user and user[3] == 'seller':
                # إذا كان المستخدم مسجلاً كبائع ولكن ليس في جدول البائعين
                # أضفه إلى جدول البائعين باسم افتراضي
                username = user[2] or user[5] or "بائع"
                store_name = f"متجر {username}"
                add_seller(telegram_id, username, store_name)
                try:
                    conn2 = get_db_connection()
                    cursor_wrapper2 = conn2.cursor()  # This returns CursorWrapper
                    if IS_POSTGRES:
                        cursor_wrapper2.execute('SELECT * FROM sellers WHERE telegramid=%s', (telegram_id,))
                    else:
                        cursor_wrapper2.execute("SELECT * FROM Sellers WHERE TelegramID=?", (telegram_id,))
                    seller = cursor_wrapper2.fetchone()
                except Exception as e:
                    print(f"Error fetching newly added seller: {e}")
        
        return seller
    except Exception as e:
        print(f"Error in get_seller_by_telegram: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        try:
            cursor_wrapper.close()
            conn.close()
        except:
            pass

def get_seller_by_id(seller_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        cursor_wrapper.execute("SELECT * FROM Sellers WHERE SellerID=?", (seller_id,))
        seller = cursor_wrapper.fetchone()
        return seller
    except Exception as e:
        print(f"Error in get_seller_by_id: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor_wrapper.close()
        conn.close()

def is_main_store(telegram_id):
    seller = get_seller_by_telegram(telegram_id)
    return seller is not None

def is_seller(telegram_id):
    seller = get_seller_by_telegram(telegram_id)
    return seller is not None

def get_user_type(telegram_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()
    try:
        if IS_POSTGRES:
            cursor_wrapper.execute("SELECT usertype FROM users WHERE telegramid=%s", (telegram_id,))
        else:
            cursor_wrapper.execute("SELECT UserType FROM Users WHERE TelegramID=?", (telegram_id,))
        result = cursor_wrapper.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error in get_user_type: {e}")
        return None
    finally:
        cursor_wrapper.close()
        conn.close()

def add_category(seller_id, name):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        print(f"🔍 جاري إضافة فئة:")
        print(f"   - البائع ID: {seller_id}")
        print(f"   - اسم الفئة: {name}")
        print(f"   - قاعدة البيانات: {'PostgreSQL' if cursor_wrapper.is_postgres else 'SQLite'}")
        
        # أولاً حدّث الـ sequence في PostgreSQL إلى أكبر ID موجود
        if cursor_wrapper.is_postgres:
            cursor_wrapper.execute("SELECT SETVAL('categories_categoryid_seq', (SELECT MAX(\"CategoryID\") FROM \"Categories\"))")
        
        if cursor_wrapper.is_postgres:
            cursor_wrapper.execute(
                "INSERT INTO \"Categories\" (\"SellerID\", \"Name\") VALUES (%s, %s)",
                (seller_id, name)
            )
        else:
            cursor_wrapper.execute(
                "INSERT INTO \"Categories\" (\"SellerID\", \"Name\") VALUES (?, ?)",
                (seller_id, name)
            )
        conn.commit()
        print(f"✅ تم إضافة الفئة '{name}' للبائع {seller_id} بنجاح")
    except Exception as e:
        print(f"❌ خطأ في إضافة الفئة: {e}")
        print(f"   النوع: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

def update_category(category_id, name):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        if cursor_wrapper.is_postgres:
            cursor_wrapper.execute(
                "UPDATE \"Categories\" SET \"Name\" = %s WHERE \"CategoryID\" = %s",
                (name, category_id)
            )
        else:
            cursor_wrapper.execute(
                "UPDATE \"Categories\" SET \"Name\" = ? WHERE \"CategoryID\" = ?",
                (name, category_id)
            )
        conn.commit()
        print(f"✅ تم تحديث الفئة {category_id} بنجاح")
    except Exception as e:
        print(f"❌ خطأ في تحديث الفئة: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_categories(seller_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        print(f"\n📁 [get_categories] Getting categories for seller {seller_id}")
        print(f"   Is PostgreSQL: {cursor_wrapper.is_postgres}")
        
        if cursor_wrapper.is_postgres:
            # PostgreSQL: use %s for parameters
            query = "SELECT \"CategoryID\", \"Name\" FROM \"Categories\" WHERE \"SellerID\"=%s ORDER BY \"OrderIndex\""
            print(f"   Query: {query}")
            print(f"   Params: ({seller_id},)")
            cursor_wrapper.execute(query, (seller_id,))
        else:
            # SQLite: use ? for parameters
            query = "SELECT \"CategoryID\", \"Name\" FROM \"Categories\" WHERE \"SellerID\"=? ORDER BY \"OrderIndex\""
            print(f"   Query: {query}")
            print(f"   Params: ({seller_id},)")
            cursor_wrapper.execute(query, (seller_id,))
        
        categories = cursor_wrapper.fetchall()
        print(f"   ✅ Got {len(categories) if categories else 0} categories")
        return categories
    except Exception as e:
        print(f"   ❌ Error in get_categories: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor_wrapper.close()
        conn.close()

def get_category_by_id(category_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()
    try:
        if cursor_wrapper.is_postgres:
            cursor_wrapper.execute("SELECT \"CategoryID\", \"SellerID\", \"Name\" FROM \"Categories\" WHERE \"CategoryID\"=%s", (category_id,))
        else:
            cursor_wrapper.execute("SELECT \"CategoryID\", \"SellerID\", \"Name\" FROM \"Categories\" WHERE \"CategoryID\"=?", (category_id,))
        category = cursor_wrapper.fetchone()
        return category
    except Exception as e:
        print(f"Error in get_category_by_id: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor_wrapper.close()
        conn.close()
        conn.close()

def add_product_db(seller_id, category_id, name, description, price, wholesale_price, quantity, image_path=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (seller_id, category_id, name, description, price, wholesale_price, quantity, image_path))
    conn.commit()
    conn.close()

def update_product(product_id, name=None, description=None, price=None, wholesale_price=None, quantity=None, category_id=None, image_path=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if name is not None:
        updates.append("Name = ?")
        params.append(name)
    
    if description is not None:
        updates.append("Description = ?")
        params.append(description)
    
    if price is not None:
        updates.append("Price = ?")
        params.append(price)
    
    if wholesale_price is not None:
        updates.append("WholesalePrice = ?")
        params.append(wholesale_price)
    
    if quantity is not None:
        updates.append("Quantity = ?")
        params.append(quantity)
    
    if category_id is not None:
        updates.append("CategoryID = ?")
        params.append(category_id)
    
    if image_path is not None:
        updates.append("ImagePath = ?")
        params.append(image_path)
    
    if updates:
        params.append(product_id)
        query = f"UPDATE Products SET {', '.join(updates)} WHERE ProductID = ?"
        cursor.execute(query, params)
    
    conn.commit()
    conn.close()

def get_products(seller_id=None, category_id=None):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        # Debug: Check database type
        is_postgres = conn.is_postgres if hasattr(conn, 'is_postgres') else IS_POSTGRES
        print(f"🔍 get_products: IS_POSTGRES={is_postgres}, seller_id={seller_id}, category_id={category_id}")
        
        if seller_id and category_id:
            cursor_wrapper.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND SellerID=? AND CategoryID=? AND Status='active'", 
                          (seller_id, category_id))
        elif seller_id:
            cursor_wrapper.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND SellerID=? AND Status='active'", (seller_id,))
        elif category_id:
            cursor_wrapper.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND CategoryID=? AND Status='active'", (category_id,))
        else:
            cursor_wrapper.execute("SELECT ProductID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE Quantity > 0 AND Status='active'")
        products = cursor_wrapper.fetchall()
        
        print(f"📊 get_products: Found {len(products)} products")
        if len(products) == 0:
            # Debug: Check if there are any products at all (even with Quantity = 0)
            cursor_wrapper.execute("SELECT COUNT(*) FROM Products WHERE Status='active'")
            count_result = cursor_wrapper.fetchone()
            total_count = count_result[0] if count_result else 0
            print(f"⚠️ No products found with Quantity > 0. Total active products: {total_count}")
        
        return products
    except Exception as e:
        print(f"Error in get_products: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor_wrapper.close()
        conn.close()

def get_product_images(product_id):
    """الحصول على جميع صور المنتج من imagestorage"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("""
            SELECT imageid, filename, imageorder 
            FROM imagestorage 
            WHERE productid=%s 
            ORDER BY imageorder, imageid
        """, (product_id,))
    else:
        cursor.execute("""
            SELECT imageid, filename, imageorder 
            FROM imagestorage 
            WHERE productid=? 
            ORDER BY imageorder, imageid
        """, (product_id,))
    images = cursor.fetchall()
    conn.close()
    return images

def delete_n_images_from_product(product_id, quantity):
    """
    حذف N صورة من أول الصور في المنتج (بناءً على ImageOrder)
    
    Returns:
        tuple: (deleted_count, deleted_images_list)
    """
    try:
        # الحصول على أول N صورة
        images = get_product_images(product_id)
        
        if not images or len(images) < quantity:
            print(f"⚠️ لا توجد صور كافية: المتاح {len(images)}, المطلوب {quantity}")
            return 0, []
        
        # أخذ أول quantity صورة
        images_to_delete = images[:quantity]
        deleted_count = 0
        deleted_images = []
        
        print(f"🗑️ حذف {quantity} صورة من المنتج {product_id}")
        
        for image_id, filename, imageorder in images_to_delete:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # حذف من قاعدة البيانات
                if IS_POSTGRES:
                    cursor.execute('DELETE FROM imagestorage WHERE imageid = %s', (image_id,))
                else:
                    cursor.execute('DELETE FROM imagestorage WHERE imageid = ?', (image_id,))
                
                conn.commit()
                conn.close()
                
                # حذف الملف من القرص
                img_path = os.path.join(IMAGES_FOLDER, filename)
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                        print(f"   ✅ حذفت الصورة ID {image_id}: {filename}")
                    except Exception as e:
                        print(f"   ⚠️ خطأ في حذف الملف {filename}: {e}")
                
                deleted_count += 1
                deleted_images.append({'image_id': image_id, 'filename': filename})
                
            except Exception as e:
                print(f"   ❌ خطأ في حذف الصورة {image_id}: {e}")
        
        print(f"✅ تم حذف {deleted_count} صورة بنجاح من المنتج {product_id}")
        return deleted_count, deleted_images
        
    except Exception as e:
        print(f"❌ خطأ في delete_n_images_from_product: {e}")
        return 0, []

def get_customer_by_phone_for_seller(phone_number, seller_id):
    """الحصول على معلومات الزبون من رقم الهاتف والبائع"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # تنظيف رقم الهاتف
    phone_number = phone_number.strip().replace(" ", "").replace("-", "").replace("+", "")
    
    if IS_POSTGRES:
        cursor.execute("""
            SELECT CustomerID, FullName, PhoneNumber 
            FROM CreditCustomers 
            WHERE SellerID=%s AND PhoneNumber=%s
        """, (seller_id, phone_number))
    else:
        cursor.execute("""
            SELECT CustomerID, FullName, PhoneNumber 
            FROM CreditCustomers 
            WHERE SellerID=? AND PhoneNumber=?
        """, (seller_id, phone_number))
    
    customer = cursor.fetchone()
    conn.close()
    return customer

def add_credit_transaction(customer_id, seller_id, amount, description):
    """إضافة معاملة ائتمانية للزبون"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على الرصيد الحالي
        current_balance = get_customer_balance(customer_id, seller_id)
        new_balance = current_balance + amount
        
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO CustomerCredit (CustomerID, SellerID, TransactionType, Amount, Description, BalanceBefore, BalanceAfter)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (customer_id, seller_id, 'Purchase', amount, description, current_balance, new_balance))
        else:
            cursor.execute("""
                INSERT INTO CustomerCredit (CustomerID, SellerID, TransactionType, Amount, Description, BalanceBefore, BalanceAfter)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (customer_id, seller_id, 'Purchase', amount, description, current_balance, new_balance))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding credit transaction: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def get_product_by_id(pid):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        if IS_POSTGRES:
            cursor_wrapper.execute('SELECT productid, sellerid, categoryid, name, description, price, wholesaleprice, quantity, imagepath FROM products WHERE productid=%s', (pid,))
        else:
            cursor_wrapper.execute("SELECT ProductID, SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath FROM Products WHERE ProductID=?", (pid,))
        product = cursor_wrapper.fetchone()
        return product
    except Exception as e:
        print(f"Error in get_product_by_id: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor_wrapper.close()
        conn.close()

def get_product_price_for_customer(product_id, seller_id, phone_number=None, full_name=None):
    """الحصول على سعر المنتج للزبون
    - زبون آجل (CreditCustomer): سعر المفرد
    - نقطة بيع (PointOfSale): سعر الجملة
    """
    product = get_product_by_id(product_id)
    if not product:
        return None
    
    # التحقق إذا كان الزبون مسجلاً
    if phone_number or full_name:
        customer = get_credit_customer(seller_id, phone_number, full_name)
        if customer:
            customer_type = customer[4] if len(customer) > 4 else 'CreditCustomer'
            # نقطة بيع: سعر الجملة
            if customer_type == 'PointOfSale':
                return product[6] if product[6] is not None and product[6] > 0 else product[5]
            # زبون آجل: سعر المفرد
            else:
                return product[5]
    
    # إرجاع سعر البيع العادي
    return product[5]

def get_customer_type(seller_id, phone_number=None, full_name=None):
    """الحصول على نوع الزبون"""
    customer = get_credit_customer(seller_id, phone_number, full_name)
    if customer:
        return customer[4] if len(customer) > 4 else 'CreditCustomer'
    return None

def add_to_cart_db(user_id, product_id, quantity=1, price=None):
    """إضافة منتج إلى السلة مع التحقق من وجود المستخدم والمنتج"""
    print(f"[DEBUG] add_to_cart_db called: user_id={user_id}, product_id={product_id}, quantity={quantity}, price={price}")
    
    # Validate inputs
    if not user_id or user_id == 0:
        print(f"[ERROR] Invalid user_id: {user_id}")
        return False
    
    if not product_id or product_id == 0:
        print(f"[ERROR] Invalid product_id: {product_id}")
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        # Ensure user exists in Users table before adding to cart (Foreign Key constraint)
        print(f"[DEBUG] Checking if user {user_id} exists...")
        user = get_user(user_id)
        if not user:
            # User doesn't exist, create a basic user entry
            print(f"[INFO] User {user_id} not found in Users table. Creating user entry...")
            user_created = add_user(user_id, None, 'buyer', None, None)
            if not user_created:
                print(f"[ERROR] Failed to create user {user_id}. Cannot add to cart.")
                cursor.close()
                conn.close()
                return False
            
            # Close current connection and reopen to ensure fresh state
            cursor.close()
            conn.close()
            
            # Small delay to ensure database commit is complete
            import time
            time.sleep(0.2)  # Increased delay
            
            # Reopen connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
            
            # Verify user was created
            user = get_user(user_id)
            if not user:
                print(f"[ERROR] User {user_id} still not found after creation attempt.")
                cursor.close()
                conn.close()
                return False
            print(f"[SUCCESS] User {user_id} created and verified")
        else:
            print(f"[OK] User {user_id} exists: TelegramID={user[1]}, UserType={user[3]}")
        
        # Verify product exists
        print(f"[DEBUG] Checking if product {product_id} exists...")
        if price is None:
            product = get_product_by_id(product_id)
            if not product:
                print(f"[ERROR] Product {product_id} not found")
                cursor.close()
                conn.close()
                return False
            price = product[5]
            print(f"[OK] Product {product_id} exists: Name={product[3]}, Price={price}")
        else:
            # Still verify product exists even if price is provided
            product = get_product_by_id(product_id)
            if not product:
                print(f"[ERROR] Product {product_id} not found")
                cursor.close()
                conn.close()
                return False
            print(f"[OK] Product {product_id} exists: Name={product[3]}")
        
        # Ensure referenced user exists (upsert) — prevents FK violations
        print(f"[DEBUG] Ensuring user row exists for TelegramID={user_id}...")
        try:
            if IS_POSTGRES:
                cursor_wrapper.execute(
                    """
                    INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (TelegramID) DO NOTHING
                    """,
                    (user_id, None, 'buyer', None, None)
                )
            else:
                cursor_wrapper.execute(
                    "INSERT OR IGNORE INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) VALUES (?, ?, ?, ?, ?)",
                    (user_id, None, 'buyer', None, None)
                )
        except Exception as e:
            print(f"[WARN] Failed to ensure user existence before cart insert: {e}")

        # Use CursorWrapper to handle PostgreSQL parameter conversion
        print(f"[DEBUG] Checking existing cart entry...")
        cursor_wrapper.execute("SELECT Quantity FROM Carts WHERE UserID=? AND ProductID=?", (user_id, product_id))
        existing = cursor_wrapper.fetchone()
        
        if existing:
            new_quantity = existing[0] + quantity
            print(f"[DEBUG] Updating cart: UserID={user_id}, ProductID={product_id}, OldQuantity={existing[0]}, NewQuantity={new_quantity}")
            cursor_wrapper.execute("UPDATE Carts SET Quantity=?, Price=? WHERE UserID=? AND ProductID=?", 
                          (new_quantity, price, user_id, product_id))
            print(f"[SUCCESS] Updated cart: UserID={user_id}, ProductID={product_id}, Quantity={new_quantity}")
        else:
            print(f"[DEBUG] Inserting new cart entry: UserID={user_id}, ProductID={product_id}, Quantity={quantity}, Price={price}")
            cursor_wrapper.execute("INSERT INTO Carts (UserID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                          (user_id, product_id, quantity, price))
            print(f"[SUCCESS] Added to cart: UserID={user_id}, ProductID={product_id}, Quantity={quantity}")
        
        conn.commit()
        print(f"[SUCCESS] Cart operation completed successfully for UserID={user_id}, ProductID={product_id}")
        return True
    except Exception as e:
        # Check if it's an IntegrityError (Foreign Key constraint violation)
        error_str = str(e).lower()
        if 'foreign key' in error_str or 'violates' in error_str or (psycopg2 and isinstance(e, psycopg2.IntegrityError)):
            print(f"[ERROR] Foreign Key Constraint Violation in add_to_cart_db:")
            print(f"  UserID: {user_id}")
            print(f"  ProductID: {product_id}")
            print(f"  Error: {e}")
            # Additional debugging
            try:
                # Check if user exists
                user_check = get_user(user_id)
                print(f"  User exists: {user_check is not None}")
                if user_check:
                    print(f"  User TelegramID: {user_check[1]}")
                # Check if product exists
                product_check = get_product_by_id(product_id)
                print(f"  Product exists: {product_check is not None}")
                if product_check:
                    print(f"  Product ProductID: {product_check[0]}")
            except Exception as debug_error:
                print(f"  Debug error: {debug_error}")
                import traceback
                traceback.print_exc()
            # Try to collect more DB state and attempt a safe repair: ensure Users row exists and retry once
            try:
                repair_conn = get_db_connection()
                repair_cur = repair_conn.cursor()
                repair_w = CursorWrapper(repair_cur, is_postgres=IS_POSTGRES)

                try:
                    # Show matching Users row(s)
                    repair_w.execute("SELECT UserID, TelegramID, UserName, UserType, CreatedAt FROM Users WHERE TelegramID=?", (user_id,))
                    rows = repair_w.fetchall()
                    print(f"  Users rows for TelegramID={user_id}: {rows}")

                    # If no user row, create one
                    if not rows:
                        print(f"  Attempting to insert missing Users row for TelegramID={user_id}")
                        if IS_POSTGRES:
                            repair_w.execute(
                                """
                                INSERT INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT (TelegramID) DO NOTHING
                                """,
                                (user_id, None, 'buyer', None, None)
                            )
                        else:
                            repair_w.execute(
                                "INSERT OR IGNORE INTO Users (TelegramID, UserName, UserType, PhoneNumber, FullName) VALUES (?, ?, ?, ?, ?)",
                                (user_id, None, 'buyer', None, None)
                            )
                        try:
                            repair_conn.commit()
                        except:
                            pass

                    # Show recent Carts rows for visibility
                    repair_w.execute("SELECT CartID, UserID, ProductID, Quantity, AddedAt FROM Carts ORDER BY CartID DESC LIMIT 10")
                    carts = repair_w.fetchall()
                    print(f"  Recent Carts: {carts}")

                    # For SQLite, show PRAGMA foreign_keys state
                    if not IS_POSTGRES:
                        try:
                            repair_w.execute("PRAGMA foreign_keys")
                            fk_state = repair_w.fetchall()
                            print(f"  PRAGMA foreign_keys: {fk_state}")
                        except Exception:
                            pass

                    # Attempt one safe retry of the insert into Carts
                    try:
                        print(f"  Retrying cart insert once for UserID={user_id}, ProductID={product_id}")
                        # Use a fresh cursor wrapper for the insert
                        repair_w.execute("SELECT Quantity FROM Carts WHERE UserID=? AND ProductID=?", (user_id, product_id))
                        ex = repair_w.fetchone()
                        if ex:
                            new_q = ex[0] + quantity
                            repair_w.execute("UPDATE Carts SET Quantity=?, Price=? WHERE UserID=? AND ProductID=?", (new_q, price, user_id, product_id))
                        else:
                            repair_w.execute("INSERT INTO Carts (UserID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)", (user_id, product_id, quantity, price))
                        repair_conn.commit()
                        print("  Retry succeeded: cart insert/update completed")
                        try:
                            repair_cur.close()
                        except:
                            pass
                        try:
                            repair_conn.close()
                        except:
                            pass
                        return True
                    except Exception as retry_e:
                        print(f"  Retry failed: {retry_e}")

                except Exception as rr:
                    print(f"  Repair debug failed: {rr}")
                finally:
                    try:
                        repair_cur.close()
                    except:
                        pass
                    try:
                        repair_conn.close()
                    except:
                        pass
            except Exception as outer_repair_err:
                print(f"  Outer repair error: {outer_repair_err}")

            try:
                conn.rollback()
            except:
                pass
            return False

        # Other exceptions
        print(f"[ERROR] Error in add_to_cart_db: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

def update_cart_quantity_db(user_id, product_id, new_quantity):
    """Update the quantity of a product in the cart (Set, not Add)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        cursor_wrapper.execute("UPDATE Carts SET Quantity=? WHERE UserID=? AND ProductID=?", 
                      (new_quantity, user_id, product_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in update_cart_quantity_db: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

def get_cart_items_db(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor_wrapper = CursorWrapper(cursor, is_postgres=IS_POSTGRES)
    
    try:
        cursor_wrapper.execute("""
            SELECT C.ProductID, C.Quantity, C.Price, P.Name, P.Description, P.ImagePath, 
                   P.Quantity as AvailableQty, P.SellerID, S.StoreName
            FROM Carts C
            JOIN Products P ON C.ProductID = P.ProductID
            JOIN Sellers S ON P.SellerID = S.SellerID
            WHERE C.UserID = ?
            ORDER BY C.AddedAt DESC
        """, (user_id,))
        
        items = cursor_wrapper.fetchall()
        return items
    except Exception as e:
        print(f"Error in get_cart_items_db: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor.close()
        conn.close()

def create_order(buyer_id, seller_id, cart_items, delivery_address=None, notes=None, payment_method='cash', fully_paid=False):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    total = 0
    
    try:
        for pid, qty, price in cart_items:
            total += price * qty

        query = """
            INSERT INTO Orders (BuyerID, SellerID, Total, DeliveryAddress, Notes, PaymentMethod, FullyPaid) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        if IS_POSTGRES:
            query += " RETURNING OrderID"
        
        cursor_wrapper.execute(query, (buyer_id, seller_id, total, delivery_address, notes, payment_method, fully_paid))
        order_id = cursor_wrapper.lastrowid
        
        # 🛡️ Safe Fallback for Postgres: If CursorWrapper didn't capture ID, try manually
        if IS_POSTGRES and not order_id:
            try:
                res = cursor_wrapper.fetchone()
                if res:
                    order_id = res[0]
                    print(f"DEBUG: Retrieved OrderID via fallback fetchone for User {buyer_id}")
            except Exception as e:
                print(f"DEBUG: Error in fallback fetchone: {e}")

        # Optimize: Fetch product data using valid transaction cursor to avoid locking/visibility issues
        # Pre-fetch check or inline check
        for pid, qty, price in cart_items:
            # Inline lookup using SAME cursor_wrapper
            cursor_wrapper.execute("SELECT Quantity FROM Products WHERE ProductID = ?", (pid,))
            res = cursor_wrapper.fetchone()
            
            if not res:
                print(f"⚠️ Warning: Product {pid} not found during Order {order_id} creation. Skipping Item.")
                continue
                
            current_qty_in_db = res[0]
            
            cursor_wrapper.execute("INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                           (order_id, pid, qty, price))
                           
            new_qty = current_qty_in_db - qty
            if new_qty < 0:
                new_qty = 0
            cursor_wrapper.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (new_qty, pid))
            
            # 🗑️ حذف الصور من imagestorage (الصور ترسل للمشتري ثم تُحذف من قاعدة البيانات)
            if IS_POSTGRES:
                # حذف صور هذا المنتج من imagestorage
                cursor_wrapper.execute("""
                    SELECT filename FROM imagestorage WHERE productid=%s
                """, (pid,))
            else:
                cursor_wrapper.execute("""
                    SELECT filename FROM imagestorage WHERE productid=?
                """, (pid,))
            
            image_paths = cursor_wrapper.fetchall()
            for (filename,) in image_paths:
                if filename:
                    try:
                        if IS_POSTGRES:
                            cursor_wrapper.execute("DELETE FROM imagestorage WHERE filename = %s", (filename,))
                        else:
                            cursor_wrapper.execute("DELETE FROM imagestorage WHERE filename = ?", (filename,))
                        print(f"🗑️ حذفت صورة {filename} من imagestorage بعد البيع")
                    except Exception as del_err:
                        print(f"⚠️ خطأ في حذف الصورة {filename}: {del_err}")
            
            # 📢 إشعار عندما تصبح الكمية صفر
            if new_qty == 0:
                try:
                    # احصل على بيانات المنتج والبائع للإشعار
                    cursor_wrapper.execute("SELECT ProductID, Name FROM Products WHERE ProductID = ?", (pid,))
                    prod_info = cursor_wrapper.fetchone()
                    
                    cursor_wrapper.execute("SELECT StoreName, TelegramID FROM Sellers WHERE SellerID = ?", (seller_id,))
                    seller_info = cursor_wrapper.fetchone()
                    
                    if prod_info and seller_info:
                        product_name = prod_info[1]
                        store_name = seller_info[0]
                        seller_telegram = seller_info[1]
                        
                        # إشعار للبائع
                        try:
                            msg = f"⚠️ **تنبيه: انتهت الكمية!**\n\n"
                            msg += f"🏪 المتجر: {store_name}\n"
                            msg += f"📦 المنتج: {product_name}\n"
                            msg += f"⏰ التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            msg += f"الكمية أصبحت صفر - يرجى إضافة منتجات جديدة"
                            bot.send_message(seller_telegram, msg, parse_mode='Markdown')
                        except Exception as msg_err:
                            print(f"⚠️ خطأ في إرسال إشعار البائع: {msg_err}")
                        
                        # إشعار للمشتري (اختياري)
                        try:
                            buyer_msg = f"✅ شكراً لشرائك!\n\n"
                            buyer_msg += f"📦 المنتج: {product_name}\n"
                            buyer_msg += f"🏪 المتجر: {store_name}\n\n"
                            buyer_msg += f"⚠️ **ملاحظة:** المنتج انتهى من المخزون.\n"
                            buyer_msg += f"سيتمكن صاحب المتجر من إضافة كمية جديدة قريباً."
                            bot.send_message(buyer_id, buyer_msg, parse_mode='Markdown')
                        except Exception as buyer_msg_err:
                            print(f"⚠️ خطأ في إرسال إشعار المشتري: {buyer_msg_err}")
                except Exception as notif_err:
                    print(f"⚠️ خطأ في إرسال الإشعارات: {notif_err}")
    
        # تسجيل المعاملة في كشف الحساب حسب نوع الزبون وطريقة الدفع
        buyer_info = get_user(buyer_id)
        if buyer_info:
            phone = buyer_info[4]
            full_name = buyer_info[5]
            customer = get_credit_customer(seller_id, phone, full_name)
            if customer:
                customer_type = customer[4] if len(customer) > 4 else 'CreditCustomer'
                
                # تحديد متى نسجل المعاملة:
                # - زبون آجل: دائماً نسجل إذا كان الدفع آجل
                # - نقطة بيع: نسجل فقط إذا كان الدفع آجل (لا نسجل إذا كان نقدي)
                should_record = False
                if customer_type == 'CreditCustomer':
                    # زبون آجل: نسجل إذا كان الدفع آجل
                    should_record = (payment_method == 'credit' and not fully_paid)
                elif customer_type == 'PointOfSale':
                    # نقطة بيع: نسجل فقط إذا كان الدفع آجل
                    should_record = (payment_method == 'credit' and not fully_paid)
                
                if should_record:
                    # التحقق من الحد الائتماني قبل إتمام الشراء
                    can_purchase, message, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, total)
                    if not can_purchase:
                        # إرجاع الطلب
                        conn.rollback()
                        cursor_wrapper.close()
                        conn.close()
                        return None, message
                    
                    add_credit_transaction(customer[0], seller_id, 'purchase', total, f"شراء طلب #{order_id}")

        conn.commit()
        notify_seller_of_order(order_id, buyer_id, seller_id)
        return order_id, total
    except Exception as e:
        print(f"Error in create_order: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return None, f"حدث خطأ أثناء إنشاء الطلب: {str(e)}"
    finally:
        cursor_wrapper.close()
        conn.close()

# This function is a duplicate - removed, using the one above

def get_orders_by_seller(seller_id, status=None):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        query = """
            SELECT O.OrderID, O.BuyerID, O.Total, O.Status, O.CreatedAt, 
                   O.DeliveryAddress, O.Notes, O.PaymentMethod, O.FullyPaid, 
                   U.FullName, U.PhoneNumber
            FROM Orders O
            LEFT JOIN Users U ON O.BuyerID = U.TelegramID
            WHERE O.SellerID = ?
        """
        
        params = [seller_id]
        
        if status:
            query += " AND O.Status = ?"
            params.append(status)
        
        query += " ORDER BY O.CreatedAt DESC"
        
        cursor_wrapper.execute(query, params)
        orders = cursor_wrapper.fetchall()
        return orders
    except Exception as e:
        print(f"Error in get_orders_by_seller: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor_wrapper.close()
        conn.close()

def update_order_status(order_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Orders SET Status=? WHERE OrderID=?", (new_status, order_id))
    conn.commit()
    conn.close()

def get_order_details(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.*, u.FullName, u.PhoneNumber, u.UserName, s.StoreName
        FROM Orders o
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        LEFT JOIN Sellers s ON o.SellerID = s.SellerID
        WHERE o.OrderID = ?
    """, (order_id,))
    order = cursor.fetchone()
    
    cursor.execute("""
        SELECT oi.*, p.Name, p.Description, p.ImagePath
        FROM OrderItems oi
        LEFT JOIN Products p ON oi.ProductID = p.ProductID
        WHERE oi.OrderID = ?
    """, (order_id,))
    items = cursor.fetchall()
    
    conn.close()
    return order, items

def clear_cart_db(user_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        cursor_wrapper.execute("DELETE FROM Carts WHERE UserID=?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in clear_cart_db: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor_wrapper.close()
        conn.close()

def delete_product(product_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        print(f"🔍 جاري حذف المنتج ID: {product_id}")
        
        # Delete in order of foreign key dependencies
        # Critical: Delete child records BEFORE parent records
        
        # 1. Delete OrderItems (references Products)
        print(f"   📋 جاري حذف OrderItems المرتبطة...")
        cursor_wrapper.execute("DELETE FROM orderitems WHERE productid = ?", (product_id,))
        deleted_count = cursor_wrapper.rowcount
        print(f"      ✅ تم حذف {deleted_count} عنصر طلب")
        
        # 2. Delete Cart items (references Products)
        print(f"   🛒 جاري حذف عناصر السلة المرتبطة...")
        cursor_wrapper.execute("DELETE FROM carts WHERE productid = ?", (product_id,))
        deleted_count = cursor_wrapper.rowcount
        print(f"      ✅ تم حذف {deleted_count} عنصر سلة")
        
        # 3. Delete image storage records (references Products)
        print(f"   🖼️ جاري حذف الصور المرتبطة...")
        cursor_wrapper.execute("DELETE FROM imagestorage WHERE productid = ?", (product_id,))
        deleted_count = cursor_wrapper.rowcount
        print(f"      ✅ تم حذف {deleted_count} صورة")
        
        # 4. Delete auction products (references Products)
        print(f"   🏆 جاري حذف المنتجات في المزادات...")
        cursor_wrapper.execute("DELETE FROM auctionproducts WHERE productid = ?", (product_id,))
        deleted_count = cursor_wrapper.rowcount
        print(f"      ✅ تم حذف {deleted_count} منتج مزاد")
        
        # 5. Delete auctions (if this product is in an auction)
        print(f"   🏆 جاري حذف المزادات المرتبطة...")
        cursor_wrapper.execute("DELETE FROM auctions WHERE productid = ?", (product_id,))
        deleted_count = cursor_wrapper.rowcount
        print(f"      ✅ تم حذف {deleted_count} مزاد")
        
        # 6. Delete returns (references Products)
        print(f"   📦 جاري حذف المرتجعات المرتبطة...")
        cursor_wrapper.execute("DELETE FROM returns WHERE productid = ?", (product_id,))
        deleted_count = cursor_wrapper.rowcount
        print(f"      ✅ تم حذف {deleted_count} مرتجع")
        
        # 7. Finally, delete the Product itself
        print(f"   🗑️ جاري حذف المنتج...")
        cursor_wrapper.execute("DELETE FROM products WHERE productid = ?", (product_id,))
        deleted_count = cursor_wrapper.rowcount
        
        conn.commit()
        print(f"✅ تم حذف المنتج {product_id} بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في حذف المنتج: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_category(category_id):
    conn = get_db_connection()
    cursor_wrapper = conn.cursor()  # This returns CursorWrapper
    
    try:
        print(f"🔍 جاري حذف الفئة ID: {category_id}")
        
        # 1. First, get all products in this category
        print(f"   📦 جاري جلب المنتجات في الفئة...")
        cursor_wrapper.execute("SELECT productid FROM products WHERE categoryid = ?", (category_id,))
        products = cursor_wrapper.fetchall()
        product_ids = [p[0] for p in products]
        print(f"      وجدنا {len(product_ids)} منتج في الفئة")
        
        # 2. Delete all dependent records for each product using cascading logic
        if product_ids:
            print(f"   🔄 جاري حذف جميع المرتبطات للمنتجات...")
            
            for product_id in product_ids:
                # Delete OrderItems
                cursor_wrapper.execute("DELETE FROM orderitems WHERE productid = ?", (product_id,))
                # Delete Cart items
                cursor_wrapper.execute("DELETE FROM carts WHERE productid = ?", (product_id,))
                # Delete image storage
                cursor_wrapper.execute("DELETE FROM imagestorage WHERE productid = ?", (product_id,))
                # Delete auction products
                cursor_wrapper.execute("DELETE FROM auctionproducts WHERE productid = ?", (product_id,))
                # Delete auctions
                cursor_wrapper.execute("DELETE FROM auctions WHERE productid = ?", (product_id,))
                # Delete returns
                cursor_wrapper.execute("DELETE FROM returns WHERE productid = ?", (product_id,))
        
        # 3. Now delete all Products in this category
        print(f"   📦 جاري حذف المنتجات في الفئة...")
        cursor_wrapper.execute("DELETE FROM \"Products\" WHERE \"CategoryID\" = ?", (category_id,))
        deleted_products = cursor_wrapper.rowcount
        print(f"      ✅ تم حذف {deleted_products} منتج")
        
        # 4. Finally, delete the Category itself
        print(f"   🗑️ جاري حذف الفئة...")
        cursor_wrapper.execute("DELETE FROM \"Categories\" WHERE \"CategoryID\" = ?", (category_id,))
        deleted_categories = cursor_wrapper.rowcount
        
        conn.commit()
        print(f"✅ تم حذف الفئة {category_id} بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في حذف الفئة: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_product_count_in_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Products WHERE CategoryID = ?", (category_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def create_message(order_id, seller_id, message_type, message_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Messages (OrderID, SellerID, MessageType, MessageText) 
        VALUES (?, ?, ?, ?)
    """, (order_id, seller_id, message_type, message_text))
    conn.commit()
    conn.close()

def save_notification(customer_telegram_id, notification_type, title, message, product_names=None, total_amount=None, seller_id=None, data=None):
    """
    حفظ إشعار في جدول Notifications
    
    Args:
        customer_telegram_id: معرف التليجرام للعميل
        notification_type: نوع الإشعار (مثل 'closed_store_purchase')
        title: عنوان الإشعار
        message: محتوى الإشعار
        product_names: أسماء المنتجات (اختياري)
        total_amount: المبلغ الإجمالي (اختياري)
        seller_id: معرف البائع (اختياري)
        data: بيانات إضافية JSON (اختياري)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO "Notifications" 
                ("CustomerTelegramID", "SellerID", "Type", "Title", "Message", "ProductNames", "TotalAmount", "Data")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (customer_telegram_id, seller_id, notification_type, title, message, product_names, total_amount, data))
        else:
            cursor.execute("""
                INSERT INTO Notifications 
                (CustomerTelegramID, SellerID, Type, Title, Message, ProductNames, TotalAmount, Data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_telegram_id, seller_id, notification_type, title, message, product_names, total_amount, data))
        
        conn.commit()
        conn.close()
        print(f"✅ تم حفظ إشعار للعميل {customer_telegram_id}")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في حفظ الإشعار: {e}")
        return False

def get_customer_notifications(customer_telegram_id, unread_only=True):
    """
    الحصول على الإشعارات للعميل
    
    Args:
        customer_telegram_id: معرف التليجرام للعميل
        unread_only: هل تحضر الإشعارات غير المقروءة فقط (default: True)
    
    Returns:
        قائمة الإشعارات مع معلوماتها
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            if unread_only:
                query = """
                    SELECT "NotificationID", "CustomerTelegramID", "SellerID", "Type", "Title", "Message", 
                           "ProductNames", "TotalAmount", "IsRead", "CreatedAt", "ReadAt", "Data"
                    FROM "Notifications"
                    WHERE "CustomerTelegramID" = %s AND "IsRead" = FALSE
                    ORDER BY "CreatedAt" DESC
                    LIMIT 50
                """
            else:
                query = """
                    SELECT "NotificationID", "CustomerTelegramID", "SellerID", "Type", "Title", "Message", 
                           "ProductNames", "TotalAmount", "IsRead", "CreatedAt", "ReadAt", "Data"
                    FROM "Notifications"
                    WHERE "CustomerTelegramID" = %s
                    ORDER BY "CreatedAt" DESC
                    LIMIT 50
                """
            cursor.execute(query, (customer_telegram_id,))
        else:
            if unread_only:
                query = """
                    SELECT NotificationID, CustomerTelegramID, SellerID, Type, Title, Message, 
                           ProductNames, TotalAmount, IsRead, CreatedAt, ReadAt, Data
                    FROM Notifications
                    WHERE CustomerTelegramID = ? AND IsRead = 0
                    ORDER BY CreatedAt DESC
                    LIMIT 50
                """
            else:
                query = """
                    SELECT NotificationID, CustomerTelegramID, SellerID, Type, Title, Message, 
                           ProductNames, TotalAmount, IsRead, CreatedAt, ReadAt, Data
                    FROM Notifications
                    WHERE CustomerTelegramID = ?
                    ORDER BY CreatedAt DESC
                    LIMIT 50
                """
            cursor.execute(query, (customer_telegram_id,))
        
        notifications = cursor.fetchall()
        conn.close()
        
        # تحويل النتائج إلى قاموس
        result = []
        for notif in notifications:
            if IS_POSTGRES:
                result.append({
                    'notificationId': notif['NotificationID'],
                    'customerTelegramId': notif['CustomerTelegramID'],
                    'sellerId': notif['SellerID'],
                    'type': notif['Type'],
                    'title': notif['Title'],
                    'message': notif['Message'],
                    'productNames': notif['ProductNames'],
                    'totalAmount': float(notif['TotalAmount']) if notif['TotalAmount'] else 0,
                    'isRead': notif['IsRead'],
                    'createdAt': notif['CreatedAt'].isoformat() if notif['CreatedAt'] else None,
                    'readAt': notif['ReadAt'].isoformat() if notif['ReadAt'] else None,
                    'data': json.loads(notif['Data']) if notif['Data'] else None
                })
            else:
                result.append({
                    'notificationId': notif[0],
                    'customerTelegramId': notif[1],
                    'sellerId': notif[2],
                    'type': notif[3],
                    'title': notif[4],
                    'message': notif[5],
                    'productNames': notif[6],
                    'totalAmount': float(notif[7]) if notif[7] else 0,
                    'isRead': bool(notif[8]),
                    'createdAt': notif[9],
                    'readAt': notif[10],
                    'data': json.loads(notif[11]) if notif[11] else None
                })
        
        return result
        
    except Exception as e:
        print(f"❌ خطأ في الحصول على الإشعارات: {e}")
        traceback.print_exc()
        return []

def mark_notification_as_read(notification_id):
    """
    وضع علامة على الإشعار كمقروء
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                UPDATE "Notifications"
                SET "IsRead" = TRUE, "ReadAt" = NOW()
                WHERE "NotificationID" = %s
            """, (notification_id,))
        else:
            cursor.execute("""
                UPDATE Notifications
                SET IsRead = 1, ReadAt = datetime('now')
                WHERE NotificationID = ?
            """, (notification_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ خطأ في تحديث الإشعار: {e}")
        return False

def get_unread_messages(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, o.OrderID, o.BuyerID, o.Status, o.CreatedAt,
               u.FullName, u.PhoneNumber
        FROM Messages m
        JOIN Orders o ON m.OrderID = o.OrderID
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        WHERE m.SellerID = ? AND m.IsRead IS FALSE
        ORDER BY m.CreatedAt DESC
    """, (seller_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def mark_message_as_read(message_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    conn.commit()
    conn.close()

def mark_messages_read_by_order(order_id):
    """Marks all messages related to a specific order as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Messages SET IsRead = TRUE WHERE OrderID = ?", (order_id,))
    conn.commit()
    conn.close()

def create_return_request(order_id, product_id, quantity, reason, buyer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT oi.Quantity, oi.ReturnedQuantity 
        FROM OrderItems oi 
        WHERE oi.OrderID = ? AND oi.ProductID = ?
    """, (order_id, product_id))
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        return False, "المنتج غير موجود في الطلب"
    
    total_quantity = item[0]
    returned_quantity = item[1] or 0
    
    if quantity > (total_quantity - returned_quantity):
        conn.close()
        return False, f"الكمية المطلوبة للإرجاع ({quantity}) أكبر من الكمية المتبقية ({total_quantity - returned_quantity})"
    
    query = """
        INSERT INTO Returns (OrderID, ProductID, Quantity, Reason, Status) 
        VALUES (?, ?, ?, ?, 'Pending')
    """
    if IS_POSTGRES:
        query += " RETURNING ReturnID"
    
    cursor.execute(query, (order_id, product_id, quantity, reason))
    
    return_id = cursor.lastrowid
    
    product = get_product_by_id(product_id)
    if product:
        seller_id = product[1]
        message_text = f"طلب إرجاع جديد للطلب #{order_id}\nالمنتج: {product[3]}\nالكمية: {quantity}\nالسبب: {reason}"
        create_message(order_id, seller_id, 'return_request', message_text)
    
    conn.commit()
    conn.close()
    return True, return_id

def process_return_request(return_id, status, processed_by, notes=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT OrderID, ProductID, Quantity FROM Returns WHERE ReturnID = ?", (return_id,))
    return_request = cursor.fetchone()
    
    if not return_request:
        conn.close()
        return False, "طلب الإرجاع غير موجود"
    
    order_id, product_id, quantity = return_request
    
    if status == 'Approved':
        cursor.execute("""
            UPDATE OrderItems 
            SET ReturnedQuantity = ReturnedQuantity + ?, 
                ReturnReason = ?,
                ReturnDate = CURRENT_TIMESTAMP
            WHERE OrderID = ? AND ProductID = ?
        """, (quantity, notes, order_id, product_id))
        
        cursor.execute("UPDATE Products SET Quantity = Quantity + ? WHERE ProductID = ?", (quantity, product_id))
        
        cursor.execute("""
            UPDATE Returns 
            SET Status = 'Approved', ProcessedBy = ?, ProcessedAt = CURRENT_TIMESTAMP 
            WHERE ReturnID = ?
        """, (processed_by, return_id))
        
        product = get_product_by_id(product_id)
        product_name = product[3] if product else "المنتج"
        message = f"✅ تمت الموافقة على إرجاع {quantity} من {product_name}\nملاحظات: {notes if notes else 'لا توجد ملاحظات'}"
        
    elif status == 'Rejected':
        cursor.execute("""
            UPDATE Returns 
            SET Status = 'Rejected', ProcessedBy = ?, ProcessedAt = CURRENT_TIMESTAMP 
            WHERE ReturnID = ?
        """, (processed_by, return_id))
        
        message = f"❌ تم رفض طلب الإرجاع\nملاحظات: {notes if notes else 'لا توجد ملاحظات'}"
    
    else:
        cursor.execute("""
            UPDATE Returns 
            SET Status = ?, ProcessedBy = ?, ProcessedAt = CURRENT_TIMESTAMP 
            WHERE ReturnID = ?
        """, (status, processed_by, return_id))
        
        message = f"📝 تم تحديث حالة الإرجاع إلى {status}"
    
    conn.commit()
    conn.close()
    
    order_details = get_order_details(order_id)
    if order_details[0]:
        buyer_id = order_details[0][1]
        try:
            bot.send_message(buyer_id, f"📦 **تحديث حالة الإرجاع**\n\n{message}")
        except:
            pass
    
    return True, "تم تحديث حالة الإرجاع بنجاح"

def get_pending_returns(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, p.Name as ProductName, o.OrderID, o.BuyerID, 
               u.FullName, u.PhoneNumber
        FROM Returns r
        JOIN Products p ON r.ProductID = p.ProductID
        JOIN Orders o ON r.OrderID = o.OrderID
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        WHERE p.SellerID = ? AND r.Status = 'Pending'
        ORDER BY r.CreatedAt DESC
    """, (seller_id,))
    
    returns = cursor.fetchall()
    conn.close()
    return returns


def send_privacy_instructions(message, user_id):
    """إرسال تعليمات إعدادات الخصوصية للمستخدم"""
    instructions = """
🔧 **إعدادات الخصوصية المطلوبة:**

للتأكد من استلامك لجميع رسائل البوت، يرجى اتباع الخطوات التالية:

1. **فتح إعدادات تليجرام:**
   - اضغط على ☰ (القائمة)
   - اختر Settings / الإعدادات
   - اختر Privacy and Security / الخصوصية والأمان

2. **إعدادات المجموعات والقنوات:**
   - اضغط على Groups and Channels / المجموعات والقنوات
   - اختر Everybody / الجميع

3. **رسائل البوتات:**
   - تأكد من أن إعدادات الخصوصية تسمح برسائل البوتات

4. **إضافة البوت كجهة اتصال:**
   - ابحث عن البوت: @{}
   - اضغط على Start / بدء المحادثة
   - اضغط على /start

5. **إذا كنت تستخدم تليجرام X أو إصدارات معدلة:**
   - تأكد من أن إعدادات الخصوصية تسمح برسائل البوتات
   - أضف البوت إلى قائمة الجهات المسموح بها

📌 **ملاحظة:** إذا كنت لا تستلم الرسائل، حاول حذف المحادثة مع البوت وإعادة الضغط على /start
    """.format(bot.get_me().username if hasattr(bot, 'get_me') else "اسم_البوت")
    
    try:
        bot.send_message(message.chat.id, instructions, parse_mode='Markdown')
    except:
        # إذا لم نستطع إرسالها للمستخدم، نرسلها للأدمن
        try:
            bot.send_message(BOT_ADMIN_ID, f"تعليمات الخصوصية للمستخدم {user_id}:\n\n{instructions}", parse_mode='Markdown')
        except:
            pass

def notify_seller_of_order(order_id, buyer_id, seller_id):
    """إرسال إشعار للبائع عن الطلب الجديد"""
    order_details, items = get_order_details(order_id)
    
    if not order_details:
        return
    
    seller_info = get_seller_by_id(seller_id)
    if not seller_info or seller_info[5] != 'active':
        return
    
    seller_telegram_id = seller_info[1]
    store_name = seller_info[3]
    
    buyer_info = get_user(buyer_id)
    buyer_name = buyer_info[5] if buyer_info and buyer_info[5] else buyer_info[2] if buyer_info else "مشتري"
    buyer_phone = buyer_info[4] if buyer_info and buyer_info[4] else "غير متوفر"
    
    notification = f"🛎️ **طلب جديد!**\n\n"
    notification += f"🏪 المتجر: {store_name}\n"
    # بناء النص التفصيلي (للرسايل الداخلية والاحتياط)
    full_notification = f"🛎️ **طلب جديد!**\n\n"
    full_notification += f"🏪 المتجر: {store_name}\n"
    full_notification += f"🆔 رقم الطلب: {order_id}\n"
    full_notification += f"👤 المشتري: {buyer_name}\n"
    full_notification += f"📞 رقم الهاتف: {buyer_phone}\n"
    full_notification += f"💰 الإجمالي: {order_details[3]} IQD\n"
    full_notification += f"💳 طريقة الدفع: {'نقداً' if order_details[8] == 'cash' else 'على الحساب'}\n"
    full_notification += f"💵 حالة الدفع: {'مدفوع بالكامل' if order_details[9] == 1 else 'غير مدفوع بالكامل'}\n"
    # تنسيق التاريخ (بدون وقت)
    order_date = str(order_details[5]).split()[0]
    full_notification += f"📅 تاريخ الطلب: {order_date}\n"
    
    if order_details[6]:
        full_notification += f"📍 العنوان: {order_details[6]}\n"
    
    full_notification += f"\n📦 **المنتجات:**\n"
    
    # تفاصيل المنتجات للنص الاحتياطي
    for item in items:
        item_id, order_id_val, product_id, quantity, price, returned_qty, return_reason, return_date = item[:8]
        product_name = item[8] if len(item) > 8 else "منتج"
        full_notification += f"• {product_name} × {quantity} = {quantity * price} IQD\n"

    # Minimal caption for the image
    short_caption = f"🛎️ **طلب جديد #{order_id}**\n💰 الإجمالي: {order_details[3]} IQD"


    # Buttons for Order Management
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("تفاصيل 📄", callback_data=f"order_details_{order_id}"),
               types.InlineKeyboardButton("تأكيد ✅", callback_data=f"confirm_order_{order_id}")) # Matches user request
    markup.add(types.InlineKeyboardButton("شحن 🚚", callback_data=f"ship_order_{order_id}"),
               types.InlineKeyboardButton("حذف 🗑️", callback_data=f"delete_order_{order_id}"))
    markup.add(types.InlineKeyboardButton("الرئيسية 🏠", callback_data="seller_main_menu"))
    
    # Save full details to Messages table (for history)
    create_message(order_id, seller_id, 'new_order', full_notification)
    
    try:
        # 🎨 Try to generate Receipt Image
        try:
            # Force Reload to ensure latest changes (Development Mode)
            import importlib
            import utils.receipt_generator
            importlib.reload(utils.receipt_generator)
            from utils.receipt_generator import generate_order_card
            
            receipt_img = generate_order_card(order_details, items, buyer_name, buyer_phone, store_name)
            
            if receipt_img:
                receipt_img.name = f"receipt_{order_id}.png"
                # Use Short Caption with Image AND Buttons
                bot.send_photo(seller_telegram_id, receipt_img, caption=short_caption, reply_markup=markup, parse_mode='Markdown')
                print(f"✅ Sent Visual Receipt for Order #{order_id}")
                return # Stop here if image sent successfully
        except ImportError:
            pass # Pillow not installed
        except Exception as img_err:
            print(f"⚠️ Failed to generate/send receipt image: {img_err}")
            
        # Fallback to Full Text if image fails
        bot.send_message(seller_telegram_id, full_notification, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للبائع {seller_telegram_id}: {e}")

        
# ===================== بوت التليجرام ====================
user_states = {}
carts = {}

def save_photo_from_message(message):
    """
    يحفظ الصورة المرسلة - يرفعها إلى Firebase بدلاً من PostgreSQL
    """
    try:
        if not message.photo:
            return None
        
        # تحميل الصورة الأصلية
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        original_size = len(downloaded) / 1024
        
        # ✅ ضغط الصورة (توفير ~80% مساحة)
        from image_compression import ImageCompressor
        downloaded_compressed = ImageCompressor.compress_image(downloaded)
        compressed_size = len(downloaded_compressed) / 1024
        
        ext = os.path.splitext(file_info.file_path)[1]
        if not ext:
            ext = ".jpg"
        
        # ✅ نفس صيغة اسم الملف من Flutter: {timestamp}_{32-char-uuid}{ext}
        timestamp = int(time.time())
        uuid_hex = uuid.uuid4().hex  # 32 حرف hex بدون شرطات
        filename = f"{timestamp}_{uuid_hex}{ext}"
        
        path = os.path.join(IMAGES_FOLDER, filename)
        
        # ✅ Save to Disk (محلي) - مع الصورة المضغوطة
        with open(path, "wb") as f:
            f.write(downloaded_compressed)
        
        print(f"🖼️  ضغط الصورة: {original_size:.1f} KB → {compressed_size:.1f} KB (توفير {(1-compressed_size/original_size)*100:.1f}%)")
        
        # ✅ Upload to Firebase Storage - إذا كان مفعل
        firebase_url = None
        if FIREBASE_ENABLED:
            try:
                print(f"🔥 [Firebase] Uploading image {filename}...")
                bucket = storage.bucket()
                blob = bucket.blob(f'telegram-images/{filename}')
                blob.upload_from_string(downloaded_compressed, content_type='image/jpeg')
                
                # جعل الملف عام
                blob.make_public()
                firebase_url = blob.public_url
                
                print(f"✅ [Firebase] Uploaded: {firebase_url}")
            except Exception as fb_e:
                print(f"⚠️  [Firebase] Upload failed: {fb_e}")
                firebase_url = None
        
        # ✅ Upload to PostgreSQL ImageStorage (كـ fallback)
        if IS_POSTGRES:
            try:
                print(f"🔄 [Cloud] Attempting to upload image {filename} to PostgreSQL...")
                conn_pg = get_db_connection()
                cursor_pg = conn_pg.cursor()
                
                # إذا لدينا رابط Firebase، احفظه مباشرة
                if firebase_url:
                    cursor_pg.execute(
                        '''INSERT INTO imagestorage (filename, url, firebase_filename) 
                           VALUES (%s, %s, %s) 
                           ON CONFLICT (filename) DO UPDATE 
                           SET url = EXCLUDED.url, firebase_filename = EXCLUDED.firebase_filename''',
                        (filename, firebase_url, filename)
                    )
                else:
                    # بدون Firebase - احفظ البيانات الثنائية كـ fallback
                    import psycopg2
                    cursor_pg.execute(
                        '''INSERT INTO imagestorage (filename, filedata, url) 
                           VALUES (%s, %s, %s) 
                           ON CONFLICT (filename) DO UPDATE 
                           SET filedata = EXCLUDED.filedata''',
                        (filename, psycopg2.Binary(downloaded_compressed), firebase_url)
                    )
                
                conn_pg.commit()
                conn_pg.close()
                print(f"✅ [Cloud] Saved image {filename} to PostgreSQL")
                
            except Exception as pg_e:
                print(f"❌ [Cloud] Upload Failed: {type(pg_e).__name__}: {pg_e}")
                import traceback
                traceback.print_exc()
                if 'conn_pg' in locals():
                    try:
                        conn_pg.close()
                    except: pass
        else:
            print("⚠️ [Local] IS_POSTGRES is False. Using SQLite only.")
        
        return filename  # ارجع اسم الملف
        
    except Exception as e:
        print(f"⚠️ خطأ في حفظ الصورة: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_bot_info():
    """الحصول على معلومات البوت"""
    try:
        me = bot.get_me()
        return {
            'id': me.id,
            'username': me.username,
            'first_name': me.first_name,
            'last_name': me.last_name if hasattr(me, 'last_name') else ''
        }
    except Exception as e:
        print(f"⚠️ خطأ في الحصول على معلومات البوت: {e}")
        return {'id': None, 'username': None, 'first_name': 'Bot'}

def escape_markdown_v1(text):
    """Escape special characters for legacy Markdown."""
    if not text:
        return ""
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")

def format_seller_mention(username, seller_telegram_id):
    """Return a safe display for seller username. Do not prefix @ for admin store."""
    try:
        if not username:
            return ''
        if seller_telegram_id == BOT_ADMIN_ID:
            return escape_markdown_v1(username)
        return f"@{escape_markdown_v1(username)}"
    except:
        return escape_markdown_v1(username) or ''

def generate_store_link(telegram_id):
    """توليد رابط المتجر"""
    bot_info = get_bot_info()
    if bot_info['username']:
        return f"https://t.me/{bot_info['username']}?start=store_{telegram_id}"
    return None

# ====== دالة لعرض المنتجات مع صورها ======
def send_product_with_image(chat_id, product, markup=None, seller_name=""):
    """إرسال منتج مع صورته"""
    try:
        pid, name, desc, price, wholesale_price, qty, img_path = product
        print(f"DEBUG: send_product_with_image called for product {pid}")
        
        # Build caption first
        caption = f"🛒 **{name}**\n💰 السعر: {price} IQD"
        if wholesale_price and wholesale_price > 0:
            caption += f"\n💰 سعر الجملة: {wholesale_price} IQD"
        caption += f"\n📦 متاح: {qty}"
        if seller_name:
            caption += f"\n🏪 {seller_name}"
        if desc:
            caption += f"\n📝 {desc[:100]}{'...' if len(desc) > 100 else ''}"
        
        # 🆕 Get image from ProductImages table (most reliable source)
        product_images = get_product_images(pid)
        
        if product_images:
            # Get first image (primary image)
            image_id, image_path, image_order = product_images[0]
            print(f"🔍 DEBUG: Got image from ProductImages: {image_path}")
            
            # Try 1: Get from cloud directly (if PostgreSQL)
            if IS_POSTGRES and image_path:
                print(f"🔄 Attempting to get image from cloud: {image_path}")
                try:
                    cloud_image = get_image_from_cloud(image_path)
                    if cloud_image:
                        print(f"✅ Got image from cloud ({len(cloud_image):,} bytes)")
                        from io import BytesIO
                        image_file = BytesIO(cloud_image)
                        image_file.seek(0)  # Reset position to beginning
                        image_file.name = image_path
                        bot.send_photo(chat_id, image_file, caption=caption, reply_markup=markup, parse_mode='Markdown')
                        print(f"✅ Photo sent successfully!")
                        return
                    else:
                        print(f"⚠️ get_image_from_cloud returned None")
                except Exception as e:
                    print(f"⚠️ Error getting image from cloud: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Try 2: Download from cloud and send
            if IS_POSTGRES and image_path:
                print(f"🔄 Attempting to download image from cloud: {image_path}")
                try:
                    if download_image_from_cloud(image_path):
                        print(f"✅ Downloaded image, trying to send...")
                        alt_path = os.path.join(IMAGES_FOLDER, image_path)
                        if os.path.exists(alt_path):
                            with open(alt_path, 'rb') as photo:
                                bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                            return
                except Exception as e:
                    print(f"⚠️ Error downloading from cloud: {e}")
        
        # Fallback: Try original img_path if ProductImages wasn't found
        if img_path:
            print(f"🔍 DEBUG: Looking for image from Products table: {img_path}")
            
            # Try 1: Direct path
            if os.path.exists(img_path):
                try:
                    print(f"✅ Found image at direct path: {img_path}")
                    with open(img_path, 'rb') as photo:
                        bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                    return
                except Exception as e:
                    print(f"⚠️ Error sending from direct path: {e}")
            
            # Try 2: Basename in IMAGES_FOLDER
            base_name = os.path.basename(img_path)
            alt_path = os.path.join(IMAGES_FOLDER, base_name)
            if os.path.exists(alt_path):
                try:
                    print(f"✅ Found image at alt path: {alt_path}")
                    with open(alt_path, 'rb') as photo:
                        bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                    return
                except Exception as e:
                    print(f"⚠️ Error sending from alt path: {e}")
        
        print(f"⚠️ Could not find image for product {pid}, sending text only")
        
        # Fallback: Send message without image
        if markup:
            bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, caption, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ Error in send_product_with_image: {e}")
        import traceback
        traceback.print_exc()

# ====== دالة مساعدة لإنشاء أزرار الكمية ======
def create_product_markup_with_qty(product_id, current_qty=1, is_admin_store=False):
    markup = types.InlineKeyboardMarkup()
    # Removed check: if not is_admin_store:
    # Always allow buying
    
    # Quantity Control Row
    markup.row(
        types.InlineKeyboardButton("➖", callback_data=f"qty_dec_{product_id}_{current_qty}"),
        types.InlineKeyboardButton(f"{current_qty}", callback_data="noop"),
        types.InlineKeyboardButton("➕", callback_data=f"qty_inc_{product_id}_{current_qty}")
    )
    # Add to Cart Button with Quantity
    markup.add(types.InlineKeyboardButton(f"🛒 أضف {current_qty} للسلة", callback_data=f"addtocart_{product_id}_{current_qty}"))
    print(f"DEBUG: Created Markup for PID {product_id}, Qty {current_qty}. Encoded: {markup.to_json()}")
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("qty_"))
def handle_qty_update(call):
    try:
        parts = call.data.split("_")
        action = parts[1] # inc or dec
        product_id = int(parts[2])
        current_qty = int(parts[3])
        
        new_qty = current_qty
        if action == "inc":
            new_qty += 1
        elif action == "dec":
            if current_qty > 1:
                new_qty -= 1
        
        if new_qty != current_qty:
            # Re-generate markup with new quantity
            # We need to check if it's admin store, but usually this button only appears if not admin.
            # However, for safety we can assume False or check product owner.
            # For UI speed, we assume False here as these buttons are only added if !is_admin_store
            markup = create_product_markup_with_qty(product_id, new_qty, is_admin_store=False)
            
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_qty_update: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ")

# ====== دالة لعرض عناصر السلة مع الصور ======
def send_cart_item_with_image(chat_id, cart_item, markup=None):
    """إرسال عنصر في السلة مع صورته"""
    try:
        product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = cart_item
        caption = f"🛒 **{name}**\n💰 السعر: {price} IQD\n📦 الكمية: {quantity}\n💰 المجموع: {price * quantity} IQD"
        caption += f"\n🏪 {seller_name}"
        
        if desc:
            caption += f"\n📝 {desc[:50]}{'...' if len(desc) > 50 else ''}"
        
        if img_path and os.path.exists(img_path):
            try:
                with open(img_path, 'rb') as photo:
                    if markup:
                        bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                    else:
                        bot.send_photo(chat_id, photo, caption=caption, parse_mode='Markdown')
            except Exception as e:
                print(f"⚠️ خطأ في إرسال صورة السلة: {e}")
                if markup:
                    bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
                else:
                    bot.send_message(chat_id, caption, parse_mode='Markdown')
        else:
            if markup:
                bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
            else:
                bot.send_message(chat_id, caption, parse_mode='Markdown')
    except Exception as e:
        print(f"⚠️ خطأ في send_cart_item_with_image: {e}")
        traceback.print_exc()

# ====== /start ======
@bot.message_handler(func=lambda message: message.text == "تسجيل حساب جديد 📝")
def register_new_user(message):
    msg = bot.send_message(message.chat.id, 
                          "👋 **مرحباً بك في تسجيل حساب جديد!**\n\n"
                          "يرجى إدخال اسمك الكامل:")
    bot.register_next_step_handler(msg, get_user_full_name_register, message.from_user.id, message.from_user.username)

def get_user_full_name_register(message, telegram_id, username):
    full_name = message.text.strip()
    
    if not full_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
        return start(message)
    
    msg = bot.send_message(message.chat.id, 
                          f"شكراً {full_name}!\n\n"
                          "يرجى إدخال رقم هاتفك للتواصل (اختياري):")
    bot.register_next_step_handler(msg, get_user_phone_register, telegram_id, username, full_name)

def get_user_phone_register(message, telegram_id, username, full_name):
    phone_number = message.text.strip() if message.text else None
    
    add_user(telegram_id, username, "buyer", phone_number, full_name)
    
    bot.send_message(message.chat.id, 
                    f"✅ **تم تسجيل معلوماتك بنجاح!**\n\n"
                    f"👤 الاسم: {full_name}\n"
                    f"📞 الهاتف: {phone_number if phone_number else 'غير محدد'}\n\n"
                    "يمكنك الآن البدء في التسوق 🛍️")
    
    show_buyer_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "تصفح بدون تسجيل 👀")
def browse_without_registration(message):
    telegram_id = message.from_user.id
    
    # تخزين حالة المستخدم كزائر
    user_states[telegram_id] = {
        'is_guest': True,
        'name': message.from_user.first_name,
        'username': message.from_user.username
    }
    # Reuse the unified buyer menu so guests see the same cart/edit-profile keyboard
    show_buyer_main_menu(message)

# ====== القوائم الرئيسية ======
def show_bot_admin_menu(message):
    telegram_id = message.from_user.id
    
    # التحقق إذا كان أدمن البوت لديه متجر
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🏪 إنشاء متجر خاص بي", callback_data="create_admin_store"),
            types.InlineKeyboardButton("👑 الوضع الإداري فقط", callback_data="admin_mode_only")
        )
        bot.send_message(message.chat.id, 
                        "👑 **مرحباً بأدمن البوت!**\n\n"
                        "يمكنك الاختيار بين:\n"
                        "1. إنشاء متجر خاص بك وإدارته\n"
                        "2. البقاء في الوضع الإداري فقط",
                        reply_markup=markup)
        return
    
    # إذا كان لديه متجر
    store_name = seller[3] if seller else "المتجر الإداري"
    
    unread_count = len(get_unread_messages(seller[0])) if seller else 0
    messages_badge = f" 📨({unread_count})" if unread_count > 0 else ""
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    # Row 1
    markup.row("👑 لوحة التحكم الإدارية", "🏪 منتجاتي", "📁 الأقسام")
    # Row 2
    markup.row("📦 الطلبات", "📊 كشف حساب الزبائن", "🏪 إدارة الزبائن الآجلين")
    # Row 3
    markup.row(f"📩 الرسائل{messages_badge}", "🔗 رابط المتجر", "📊 إحصائيات النظام")
    # Row 4
    markup.row("🗑️ حذف متجر", "➕ إضافة متجر", "📋 قائمة المتاجر")
    # Row 5
    markup.row("👑 إدارة الحسابات", "🛍️ وضع المشتري", "🏠 الرئيسية")
    # Row 6
    markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒")
    
    welcome_msg = f"👑🏪 **مرحباً بأدمن البوت وصاحب المتجر!**\n\n"
    welcome_msg += f"🏪 متجرك: {store_name}\n"
    welcome_msg += f"👑 صلاحياتك: إدارة النظام الكاملة"
    
    if unread_count > 0:
        welcome_msg += f"\n\nلديك {unread_count} رسالة غير مقروءة!"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='Markdown')

def show_admin_dashboard(message):
    """لوحة التحكم الإدارية فقط"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    markup.row("👑 إدارة الحسابات", "📊 إحصائيات النظام", "🗑️ حذف متجر")
    markup.row("➕ إضافة متجر", "📋 قائمة المتاجر", "🛍️ وضع المشتري")
    markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "🏠 الرئيسية")
    
    bot.send_message(
        message.chat.id,
        "👑 **لوحة التحكم الإدارية**\n\n"
        "يمكنك إدارة النظام من هنا:\n\n"
        "• 👑 إدارة الحسابات - تعليق/تنشيط المتاجر\n"
        "• 📊 إحصائيات النظام - إحصائيات النظام\n"
        "• ➕ إضافة متجر - إضافة متجر جديد\n"
        "• 📋 قائمة المتاجر - عرض جميع المتاجر\n"
        "• 🛍️ وضع المشتري - التبديل لوضع المشتري",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ====== عرض قائمة البائع ======
def show_seller_menu(message):
    telegram_id = message.from_user.id
    
    # التحقق أولاً إذا كان المستخدم مسجل كبائع
    seller = get_seller_by_telegram(telegram_id)
    # print(f"DEBUG: show_seller_menu - User: {telegram_id}, Seller: {seller}")
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست صاحب متجر مسجل!")
        return
    
    if not is_seller_active(telegram_id):
        bot.send_message(message.chat.id,
                        "⛔ **حسابك معطل**\n\n"
                        "لا يمكنك الوصول إلى هذه الصفحة لأن حسابك معطل.\n"
                        "يرجى التواصل مع الإدارة.")
        return
    
    store_name = seller[3] if seller else "متجرك"
    
    # تحديث الشارة لتظهر عدد الطلبات المعلقة
    conn = get_db_connection()
    cursor = conn.cursor()
    # اعرض فقط الطلبات المفتوحة (Pending, Shipped) - لا تعرض المغلقة (Confirmed)
    cursor.execute("SELECT COUNT(*) FROM Orders WHERE SellerID = ? AND Status IN ('Pending', 'Shipped')", (seller[0],))
    pending_count = cursor.fetchone()[0]
    
    # Self-Cleaning: Mark messages as read for processed orders (Shipped/Delivered/Rejected)
    # This fixes "stuck" counters for orders processed before the previous fix or outside the flow.
    if IS_POSTGRES:
        cursor.execute("""
            UPDATE Messages 
            SET IsRead = TRUE 
            WHERE SellerID = %s 
              AND IsRead = FALSE 
              AND OrderID IN (SELECT OrderID FROM Orders WHERE Status IN ('Shipped', 'Delivered', 'Rejected'))
        """, (seller[0],))
    else:
        cursor.execute("""
            UPDATE Messages 
            SET IsRead = 1 
            WHERE SellerID = ? 
              AND IsRead = 0 
              AND OrderID IN (SELECT OrderID FROM Orders WHERE Status IN ('Shipped', 'Delivered', 'Rejected'))
        """, (seller[0],))
    if cursor.rowcount > 0:
        conn.commit()
    
    if IS_POSTGRES:
        cursor.execute("SELECT COUNT(*) FROM Messages WHERE SellerID = %s AND IsRead = FALSE", (seller[0],))
    else:
        cursor.execute("SELECT COUNT(*) FROM Messages WHERE SellerID = ? AND IsRead = 0", (seller[0],))
    unread_messages = cursor.fetchone()[0]
    conn.close()
    
    # Red Circle Badges 🔴
    messages_badge = f" 🔴 {unread_messages}" if unread_messages > 0 else ""
    orders_badge = f" 🔴 {pending_count}" if pending_count > 0 else ""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    # Row 1 - الأزرار الأساسية للمشتري
    markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒")
    # Row 2 - أزرار المتجر
    markup.row("🏪 منتجاتي", "📁 الأقسام", f"📦 الطلبات{orders_badge}")
    # Row 3
    markup.row(f"📩 الرسائل{messages_badge}", "📊 كشف حساب الزبائن", "🏪 إدارة الزبائن الآجلين")
    # Row 4 - أضفنا زر المزادات
    markup.row("🔨 رفع منتج للمزاد", "🏠 الرئيسية")
    # Row 5
    markup.row("🔗 رابط المتجر", "🛍️ وضع المشتري")
    
    welcome_msg = f"🏪 مرحباً بصاحب المتجر!\n"
    welcome_msg += f"🏪 متجرك: {store_name}"
    
    if pending_count > 0:
        welcome_msg += f"\n\nلديك {pending_count} طلبات جديدة!"
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

# ... (Existing code) ...



# ====== عرض الطلبات للبائع ======
@bot.message_handler(func=lambda message: "📦 الطلبات" in message.text and is_seller(message.from_user.id))
def handle_seller_orders_menu(message):
    try:
        print("DEBUG: handle_seller_orders_menu triggered") # DEBUG
        telegram_id = message.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        print(f"DEBUG: Seller info: {seller}") # DEBUG
        
        if not seller:
            bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب آخر 10 طلبات مع التفاصيل الكاملة (مشابه لـ seller_messages)
        # اعرض فقط الطلبات المفتوحة (Pending, Shipped) - لا تعرض المغلقة (Confirmed)
        query = """
            SELECT o.OrderID, o.Total, o.Status, o.CreatedAt, 
                   COALESCE(u.FullName, 'زائر') as BuyerName,
                   COALESCE(u.PhoneNumber, 'غير متوفر') as BuyerPhone,
                   o.PaymentMethod, o.DeliveryAddress, o.Notes
            FROM Orders o
            LEFT JOIN Users u ON o.BuyerID = u.TelegramID
            WHERE o.SellerID = ? AND o.Status IN ('Pending', 'Shipped')
            ORDER BY 
                CASE WHEN o.Status = 'Pending' THEN 0 ELSE 1 END,
                o.CreatedAt DESC
            LIMIT 10
        """
        
        cursor.execute(query, (seller[0],))
        orders = cursor.fetchall()
        print(f"DEBUG: Retrieved {len(orders)} orders: {orders}") # DEBUG
        
        if not orders:
            bot.send_message(message.chat.id, "📭 لا توجد طلبات حالياً.")
            conn.close()
            return
            
        bot.send_message(message.chat.id, f"📦 **قائمة الطلبات**\n🏪 {seller[3]}\nيتم عرض آخر 10 طلبات:", parse_mode='Markdown')
        
        for order in orders:
            oid, total, status, date, buyer, phone, pay_method, address, notes = order
            
            # جلب المنتجات
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.Price, p.ImagePath 
                FROM OrderItems oi 
                LEFT JOIN Products p ON oi.ProductID = p.ProductID 
                WHERE oi.OrderID = ?
            """, (oid,))
            items = cursor.fetchall()
            
            # تنسيق المنتجات
            items_text = ""
            first_image_path = None
            
            # Check cloud images (Previous Logic)
            if items:
                 for i in items:
                    p_name = i[0] if i[0] else "منتج"
                    qty = i[1]
                    price = i[2]
                    img = i[3]
                    
                    if not first_image_path and img: 
                        first_image_path = img
                        
                    # 🟢 SYNC SUPPORT: Download image if missing locally (Check EVERY item)
                    if img and IS_POSTGRES:
                        if not os.path.exists(img):
                            try:
                                filename = os.path.basename(img)
                                alt_path = os.path.join(IMAGES_FOLDER, filename)
                                if not os.path.exists(alt_path):
                                     if download_image_from_cloud(filename):
                                         print(f"DEBUG: Downloaded {filename} from Cloud ImageStorage for Order {oid}")
                            except Exception as e:
                                print(f"DEBUG: Failed to download cloud image {img}: {e}")
                    
                    row_total = qty * price
                    items_text += f"\n🛍️ *{p_name}*\n"
                    items_text += f"   {qty} x {price:,.0f} = {row_total:,.0f}\n" 

            if not items_text:
                items_text = ""

            # ... Button Logic ... (Omitted to keep it simple, I target the mock tuple creation specifically if possible. No, need surrounding for context if replacing huge chunk)
            # Actually, I can allow replace to match the 'query' part and the 'mock_order' part separately if I use multi?
            # No, 'replace_file_content' is single block.
            # I will Replace the query block first (Fix Indent).
            
            # Wait, I can target just the mock_order_details line if the query block is fixed? 
            # The query block WAS replaced in the LAST step and broke indentation. I MUST fix it.
            # So I will replace the query block again with correct indentation.
            
            # AND I need to update 'mock_order_details'. That is further down.
            # If I select the whole block from 2277 to 2458 it's too big.
            # I will use multi_replace_file_content this time.

            
            # جلب المنتجات
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.Price, p.ImagePath 
                FROM OrderItems oi 
                LEFT JOIN Products p ON oi.ProductID = p.ProductID 
                WHERE oi.OrderID = ?
            """, (oid,))
            items = cursor.fetchall()
            
            # تنسيق المنتجات
            items_text = ""
            first_image_path = None
            
            # ... (Image handling loop code remains same, skipping for brevity in search replacement if possible? No, need to be contiguous)
            # Actually I can't skip lines easily with replace_file_content if I'm replacing a huge block unless I include them.
            # I will just replace the top part and the packing part.
            
            # Wait, replace_file_content checks for exact match.
            # I'll just Replace the Query block and the Unpacking line.
            
            # But there is code in between?
            # No.
            # Query is lines 2277-2289.
            # Execute 2291.
            # Loop start 2302.
            # Unpack 2303.
            
            # I will target lines 2277 to 2303.


            
            # جلب المنتجات
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.Price, p.ImagePath 
                FROM OrderItems oi 
                LEFT JOIN Products p ON oi.ProductID = p.ProductID 
                WHERE oi.OrderID = ?
            """, (oid,))
            items = cursor.fetchall()
            
            # تنسيق المنتجات
            items_text = ""
            first_image_path = None
            
            if not items:
                items_text = "" # User requested to remove the warning line
            else:
                for i in items:
                    p_name = i[0] if i[0] else "منتج محذوف"
                    qty = i[1]
                    price = i[2]
                    img = i[3]
                    
                    if not first_image_path and img:
                        first_image_path = img
                        
                    items_text += f"• {qty}x {p_name} ({price:,.0f})\n"
                    
            # تنسيق الحالة والتاريخ
            status_map = {
                'Pending': '⏳ قيد الانتظار',
                'Confirmed': '✅ تم التأكيد',
                'Shipped': '🚚 تم الشحن',
                'Delivered': '🎉 تم التسليم',
                'Rejected': '❌ مرفوض'
            }
            status_text = status_map.get(status, status)
            
            # تحويل التاريخ
            try:
                date_obj = datetime.strptime(str(date).split('.')[0], '%Y-%m-%d %H:%M:%S')
                date_fmt = date_obj.strftime('%Y-%m-%d')
            except:
                date_fmt = str(date)
                
            # تنسيق المنتجات
            items_text = ""
            if items:
                 for i in items:
                    p_name = i[0] if i[0] else "منتج"
                    qty = i[1]
                    price = i[2]
                    img = i[3]
                    
                    if not first_image_path and img: 
                        first_image_path = img
                        
                    # 🟢 SYNC SUPPORT: Download image if missing locally (Check EVERY item)
                    if img and IS_POSTGRES:
                        if not os.path.exists(img):
                            try:
                                filename = os.path.basename(img)
                                # Check if it exists in IMAGES_FOLDER first (alt path) before downloading
                                alt_path = os.path.join(IMAGES_FOLDER, filename)
                                if not os.path.exists(alt_path):
                                     if download_image_from_cloud(filename):
                                         print(f"DEBUG: Downloaded {filename} from Cloud ImageStorage for Order {oid}")
                            except Exception as e:
                                print(f"DEBUG: Failed to download cloud image {img}: {e}")
                    
                    row_total = qty * price
                    # تنسيق المنتج: اسم المنتج (غامق) وتحته التفاصيل
                    items_text += f"\n🛍️ *{p_name}*\n"
                    items_text += f"   {qty} x {price:,.0f} = {row_total:,.0f}\n" 

            if not items_text:
                items_text = ""

            # ================= تصميم البطاقة =================
            # بدلاً من النص العادي، سنقوم بتوليد صورة البطاقة
            
            # استعادة الأزرار
            markup = types.InlineKeyboardMarkup()
            
            # الصف الأول: أزرار الإجراءات الرئيسية (تأكيد / شحن)
            actions_row = []
            if status == 'Pending':
                 actions_row.append(types.InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_order_{oid}"))
            elif status == 'Confirmed':
                 actions_row.append(types.InlineKeyboardButton("🚚 شحن", callback_data=f"ship_order_{oid}"))
            
            # الصف الثاني: زر الحذف (أيقونة سلة المهملات)
            btns = []
            btns.append(types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_order_{oid}"))
            
            if actions_row:
                btns.insert(0, actions_row[0]) 
                
            markup.row(*btns)
            
            # 🎨 Generate Visual Card using the new REV 11 logic
            try:
                # Force Reload for Dev
                import importlib
                import utils.receipt_generator
                importlib.reload(utils.receipt_generator)
                from utils.receipt_generator import generate_order_card

                # Generator expects: (order_details, items, buyer_name, buyer_phone, store_name)
                # handle_seller_orders_menu has: oid, total, status, date, buyer, phone, pay_method, address
                # store_name comes from 'seller' tuple index 3
                
                # Construct Mock Order Details Tuple to match expectations:
                # [0] OrderID
                # [1] BuyerID (Not used in visual, pass 0)
                # [2] SellerID (Not used in visual, pass 0)
                # [3] TotalAmount (Used)
                # [4] Status (Used)
                # [5] CreatedAt (Used)
                # [6] DeliveryAddress (Used)
                # [6] DeliveryAddress (Used)
                mock_order_details = (oid, 0, 0, total, status, date, address, notes)
                
                # RESTRUCTURE ITEMS to match Generator Expectations
                # Generator expects: item[3]=Qty, item[4]=Price, item[8]=Name, item[10]=Image, item[13]=Image
                # Current 'items' from DB query (line 2307): (Name, Qty, Price, ImagePath)
                
                gen_items = []
                for db_item in items:
                    # db_item: (Name, Qty, Price, ImagePath)
                    d_name = db_item[0]
                    d_qty = db_item[1]
                    d_price = db_item[2]
                    d_img = db_item[3]
                    
                    # Create Mock Tuple (Length 15)
                    # Indices: 0,1,2, QTY(3), PRICE(4), 5,6,7, NAME(8), 9, IMG(10), 11,12, IMG(13), 14
                    mock_item = [None]*15
                    mock_item[3] = d_qty
                    mock_item[4] = d_price
                    mock_item[8] = d_name
                    mock_item[10] = d_img
                    mock_item[13] = d_img
                    gen_items.append(tuple(mock_item))
                
                # Generate
                card_img = generate_order_card(mock_order_details, gen_items, buyer, phone, seller[3])
                
                if card_img:
                    card_img.name = f"card_{oid}.png"
                    # Send Image Card
                    bot.send_photo(message.chat.id, card_img, reply_markup=markup)
                else:
                    # Fallback to text if generation fails
                    raise Exception("Image generation returned None")

            except Exception as e:
                print(f"Card generation error for Order list: {e}")
                # Fallback to Text
                card_text = f"{status_text} | طلب #{oid}\n"
                card_text += f"📅 {date_fmt}\n"
                card_text += f"👤 {buyer}\n"
                card_text += f"💰 **الإجمالي: {total:,.0f} د.ع**"
                
                if first_image_path and os.path.exists(first_image_path):
                    with open(first_image_path, 'rb') as photo:
                        bot.send_photo(message.chat.id, photo, caption=card_text, reply_markup=markup, parse_mode='Markdown')
                else:
                    bot.send_message(message.chat.id, card_text, reply_markup=markup, parse_mode='Markdown')
                
        conn.close()

    except Exception as e:
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض الطلبات:\n{str(e)}")

def show_buyer_main_menu(message=None, chat_id=None, user_id=None):
    """عرض قائمة المشتري - يمكن استدعاؤها مع message أو chat_id و user_id"""
    if message:
        telegram_id = message.from_user.id
        chat_id = message.chat.id
    elif chat_id and user_id:
        telegram_id = user_id
    else:
        return
    
    user = get_user(telegram_id)
    
    # Show buyer menu with original buttons
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, row_width=3)
    # الأزرار الأصلية
    markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "👤 تعديل بياناتي")

    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    if telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest'):
        welcome_msg = "👀 **مرحباً بك كزائر!**\n\nيمكنك تصفح المتاجر وإضافة المنتجات للسلة.\nعند إنهاء الطلب، سيُطلب منك إدخال معلوماتك."
    else:
        welcome_msg = "👋 **مرحباً بك كـ مشتري!**"
        
        if user and (user[4] or user[5]):
            welcome_msg += f"\n\n👤 الاسم: {user[5] if user[5] else 'غير محدد'}"
            welcome_msg += f"\n📞 الهاتف: {user[4] if user[4] else 'غير محدد'}"
    
    bot.send_message(chat_id, welcome_msg, reply_markup=markup)

# ====== معالجة اختيارات أدمن البوت ======
@bot.callback_query_handler(func=lambda call: call.data == "create_admin_store")
def handle_create_admin_store(call):
    user_states[call.from_user.id] = {
        "step": "create_admin_store_name"
    }
    
    bot.send_message(call.message.chat.id,
                    "🏪 **إنشاء متجر خاص بأدمن البوت**\n\n"
                    "يرجى إدخال اسم المتجر:")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_mode_only")
def handle_admin_mode_only(call):
    show_admin_dashboard(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "create_admin_store_name")
def process_admin_store_name(message):
    user_id = message.from_user.id
    store_name = message.text.strip()
    
    if not store_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للمتجر.")
        return
    
    # إنشاء متجر لأدمن البوت
    username = message.from_user.username or message.from_user.first_name
    add_seller(user_id, username, store_name)
    add_user(user_id, username, "bot_admin")
    
    bot.send_message(message.chat.id,
                    f"✅ **تم إنشاء متجرك بنجاح!**\n\n"
                    f"🏪 اسم المتجر: {store_name}\n"
                    f"👤 المالك: {format_seller_mention(username, user_id)}\n"
                    f"👑 الصلاحية: أدمن البوت وصاحب المتجر\n\n"
                    f"يمكنك الآن:\n"
                    f"1. إدارة متجرك\n"
                    f"2. الوصول للوظائف الإدارية الكاملة\n"
                    f"3. التبديل بين وضع المشتري والإدارة")
    
    del user_states[user_id]
    show_bot_admin_menu(message)

# ====== معالجة إنشاء متجر للمستخدمين ======
@bot.message_handler(func=lambda message: message.text == "🏪 إنشاء متجر جديد")
def handle_create_user_store(message):
    telegram_id = message.from_user.id
    
    # التحقق من أن المستخدم ليس بائعاً بالفعل
    seller = get_seller_by_telegram(telegram_id)
    if seller:
        bot.send_message(message.chat.id, "⛔ لديك متجر بالفعل!")
        return

    user_states[telegram_id] = {
        "step": "create_user_store_name"
    }
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🏠 الرئيسية")
    
    bot.send_message(message.chat.id,
                    "🏪 **إنشاء متجر جديد**\n\n"
                    "يرجى إدخال اسم المتجر الذي ترغب بإنشائه:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "create_user_store_name")
def process_user_store_name(message):
    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[user_id]
        if message.text == "🔙 رجوع":
            # Check user type to decide where to go, or just main menu
            handle_main_menu(message)
        else:
            handle_main_menu(message)
        return
        
    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم المتجر كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية'.")
        return
    user_id = message.from_user.id
    store_name = message.text.strip()
    
    if not store_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للمتجر.")
        return
    
    # إنشاء متجر للمستخدم
    username = message.from_user.username or message.from_user.first_name
    add_seller(user_id, username, store_name)
    
    # تحديث نوع المستخدم إلى بائع
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("UPDATE Users SET UserType = 'seller' WHERE TelegramID = %s", (user_id,))
    else:
        cursor.execute("UPDATE Users SET UserType = 'seller' WHERE TelegramID = ?", (user_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id,
                    f"✅ **تم إنشاء متجرك بنجاح!**\n\n"
                    f"🏪 اسم المتجر: {store_name}\n"
                    f"👤 المالك: {format_seller_mention(username, user_id)}\n\n"
                    f"يمكنك الآن البدء بإضافة المنتجات وإدارة متجرك.")
    
    # --- Notify Admin ---
    try:
        # Generate link if possible
        store_link = generate_store_link(user_id)
        links_text = f"\n🔗 **رابط المتجر:**\n`{store_link}`" if store_link else ""
        
        bot.send_message(BOT_ADMIN_ID, 
                f"🆕 **تم تسجيل متجر جديد!**\n\n"
                f"🏪 المتجر: {store_name}\n"
                f"👤 المالك: {format_seller_mention(username, user_id)}\n"
                f"🆔 المعرف: {user_id}\n"
                f"{links_text}\n\n"
                f"يرجى مراجعة المتجر وتفعيله (إذا كان التفعيل اليدوي مطلوباً).",
                parse_mode='Markdown')
    except Exception as e:
        print(f"Failed to notify admin about new store: {e}")
    # --------------------
    
    del user_states[user_id]
    show_seller_menu(message)

# ====== معالجة قائمة أدمن البوت ======
@bot.message_handler(func=lambda message: message.text == "👑 لوحة التحكم الإدارية" and is_bot_admin(message.from_user.id))
def admin_dashboard_menu(message):
    show_admin_dashboard(message)

@bot.message_handler(func=lambda message: message.text == "👑 إدارة الحسابات" and is_bot_admin(message.from_user.id))
def manage_accounts(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 قائمة المتاجر النشطة", callback_data="list_active_stores"),
        types.InlineKeyboardButton("⚠️ قائمة المتاجر المعلقة", callback_data="list_suspended_stores"),
        types.InlineKeyboardButton("⏸️ تعليق متجر", callback_data="suspend_store_menu"),
        types.InlineKeyboardButton("▶️ تنشيط متجر", callback_data="activate_store_menu")
    )
    
    bot.send_message(message.chat.id, "👑 **إدارة حسابات المتاجر**", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📊 إحصائيات النظام" and is_bot_admin(message.from_user.id))
def system_stats(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # إحصائيات المستخدمين
    cursor.execute("SELECT COUNT(*) FROM Users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Users WHERE UserType = 'buyer'")
    total_buyers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Users WHERE UserType = 'seller'")
    total_sellers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Users WHERE UserType = 'bot_admin'")
    total_bot_admins = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Sellers WHERE Status = 'active'")
    active_sellers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Sellers WHERE Status = 'suspended'")
    suspended_sellers = cursor.fetchone()[0]
    
    # إحصائيات المنتجات
    cursor.execute("SELECT COUNT(*) FROM Products")
    total_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Products WHERE Quantity > 0")
    available_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(Quantity) FROM Products")
    total_quantity = cursor.fetchone()[0] or 0
    
    # إحصائيات الطلبات
    cursor.execute("SELECT COUNT(*) FROM Orders")
    total_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Orders WHERE Status = 'Pending'")
    pending_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Orders WHERE Status = 'Delivered'")
    delivered_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(Total) FROM Orders WHERE Status = 'Delivered'")
    total_sales = cursor.fetchone()[0] or 0
    
    # إحصائيات الائتمان
    cursor.execute("SELECT SUM(BalanceAfter) FROM CustomerCredit")
    total_credit = cursor.fetchone()[0] or 0
    
    # إحصائيات الزبائن الآجلين
    cursor.execute("SELECT COUNT(*) FROM CreditCustomers")
    total_credit_customers = cursor.fetchone()[0]
    
    # إحصائيات الحدود الائتمانية
    cursor.execute("SELECT COUNT(*) FROM CreditLimits WHERE IsActive IS TRUE")
    active_credit_limits = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(MaxCreditAmount), SUM(CurrentUsedAmount) FROM CreditLimits WHERE IsActive IS TRUE")
    limits = cursor.fetchone()
    total_max_credit = limits[0] or 0
    total_used_credit = limits[1] or 0
    
    conn.close()
    
    text = "📊 **إحصائيات النظام**\n\n"
    text += "👥 **المستخدمين:**\n"
    text += f"• إجمالي المستخدمين: {total_users}\n"
    text += f"• المشترين: {total_buyers}\n"
    text += f"• البائعين: {total_sellers}\n"
    text += f"• أدمن البوت: {total_bot_admins}\n\n"
    
    text += "🏪 **المتاجر:**\n"
    text += f"• النشطة: {active_sellers}\n"
    text += f"• المعلقة: {suspended_sellers}\n\n"
    
    text += "🛒 **المنتجات:**\n"
    text += f"• إجمالي المنتجات: {total_products}\n"
    text += f"• المنتجات المتاحة: {available_products}\n"
    text += f"• إجمالي الكمية: {total_quantity}\n\n"
    
    text += "📦 **الطلبات:**\n"
    text += f"• إجمالي الطلبات: {total_orders}\n"
    text += f"• قيد الانتظار: {pending_orders}\n"
    text += f"• تم التسليم: {delivered_orders}\n"
    text += f"• إجمالي المبيعات: {total_sales} IQD\n\n"
    
    text += "💰 **الائتمان:**\n"
    text += f"• إجمالي الديون: {total_credit} IQD\n"
    text += f"• عدد الزبائن الآجلين: {total_credit_customers}\n"
    text += f"• عدد الحدود النشطة: {active_credit_limits}\n"
    text += f"• إجمالي الحدود المسموحة: {total_max_credit:,.0f} IQD\n"
    text += f"• إجمالي المبالغ المستخدمة: {total_used_credit:,.0f} IQD\n"
    text += f"• النسبة المستخدمة: {(total_used_credit/total_max_credit*100 if total_max_credit > 0 else 0):.1f}%\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ====== إضافة متجر جديد (للأدمن فقط) ======
@bot.message_handler(func=lambda message: message.text == "➕ إضافة متجر" and is_bot_admin(message.from_user.id))
def add_main_store_step1(message):
    msg = bot.send_message(message.chat.id, "أرسل معرف التليجرام الخاص بصاحب المتجر الجديد:")
    bot.register_next_step_handler(msg, add_main_store_step2)

def add_main_store_step2(message):
    try:
        telegram_id = int(message.text)
        msg = bot.send_message(message.chat.id, "أرسل اسم المتجر الجديد:")
        bot.register_next_step_handler(msg, add_main_store_step3, telegram_id)
    except:
        bot.send_message(message.chat.id, "معرّف غير صالح. الرجاء إدخال رقم.")
        if is_bot_admin(message.from_user.id):
            show_bot_admin_menu(message)
        else:
            show_admin_dashboard(message)

def add_main_store_step3(message, telegram_id):
    store_name = message.text
    
    try:
        # محاولة الحصول على معلومات المستخدم
        chat_member = bot.get_chat(telegram_id)
        username = chat_member.username if hasattr(chat_member, 'username') and chat_member.username else chat_member.first_name
    except Exception as e:
        print(f"⚠️ خطأ في الحصول على معلومات المستخدم {telegram_id}: {e}")
        username = "مستخدم"
    
    # إضافة المتجر
    add_seller(telegram_id, username, store_name)
    add_user(telegram_id, username, "seller")
    
    # توليد رابط المتجر
    store_link = generate_store_link(telegram_id)
    
    links_text = ""
    markup = types.InlineKeyboardMarkup()
    
    if store_link:
        links_text += f"🔗 **رابط المتجر:**\n`{store_link}`\n\n"
        markup.add(types.InlineKeyboardButton("📋 نسخ رابط المتجر", callback_data=f"copy_store_link_{telegram_id}"))
    
    # إرسال الرسالة للأدمن
    bot.send_message(message.chat.id, 
                    f"✅ **تم إضافة المتجر بنجاح!**\n\n"
                    f"🏪 اسم المتجر: {store_name}\n"
                    f"👤 المالك: {format_seller_mention(username, telegram_id)}\n"
                    f"🆔 المعرف: {telegram_id}\n\n"
                    f"{links_text}", 
                    reply_markup=markup,
                    parse_mode='Markdown')
    
    # محاولة إرسال رسالة لصاحب المتجر الجديد
    try:
        bot.send_message(telegram_id, 
                        f"🎉 **تهانينا!**\n\n"
                        f"تمت إضافتك كصاحب متجر!\n"
                        f"🏪 متجرك: {store_name}\n\n"
                        f"يمكنك الآن:\n"
                        f"1. إضافة منتجات للمتجر\n"
                        f"2. إدارة طلبات العملاء\n"
                        f"3. متابعة كشف حساب الزبائن\n\n"
                        f"🔗 رابط متجرك:\n{store_link if store_link else 'سيتم إرساله لاحقاً'}\n\n"
                        f"📝 **لبدء استخدام المتجر:**\n"
                        f"1. اضغط /start لبدء الاستخدام\n"
                        f"2. اختر '🏪 إضافة منتج' لإضافة منتجات\n"
                        f"3. شارك رابط متجرك مع عملائك")
        
        # إرسال قائمة البائع
        show_seller_menu_for_new_seller(telegram_id, store_name)
    except Exception as e:
        print(f"⚠️ تعذر إرسال رسالة لصاحب المتجر {telegram_id}: {e}")
        bot.send_message(message.chat.id, 
                        f"⚠️ **ملاحظة:** تعذر إرسال رسالة لصاحب المتجر الجديد.\n"
                        f"يرجى إبلاغه بأنه تمت إضافته كصاحب متجر وتزويده برابط المتجر:\n{store_link if store_link else 'سيتم توليد الرابط لاحقاً'}")
    
    if is_bot_admin(message.from_user.id):
        show_bot_admin_menu(message)
    else:
        show_admin_dashboard(message)

def show_seller_menu_for_new_seller(telegram_id, store_name):
    """إظهار قائمة البائع للمستخدم الجديد"""
    try:
        # التحقق أولاً إذا كان المستخدم مسجلاً كبائع
        seller = get_seller_by_telegram(telegram_id)
        if not seller:
            return
        
        if not is_seller_active(telegram_id):
            bot.send_message(telegram_id,
                            "⛔ **حسابك معطل**\n\n"
                            "لا يمكنك الوصول إلى هذه الصفحة لأن حسابك معطل.\n"
                            "يرجى التواصل مع الإدارة.")
            return
        
        store_name = seller[3] if seller else "متجرك"
        
        # تحديث الشارة لتظهر عدد الطلبات المعلقة
        conn = get_db_connection()
        cursor_wrapper = conn.cursor()  # This returns CursorWrapper
        try:
            cursor_wrapper.execute("SELECT COUNT(*) FROM Orders WHERE SellerID = ? AND Status IN ('Pending', 'Confirmed')", (seller[0],))
            result = cursor_wrapper.fetchone()
            pending_count = result[0] if result else 0
        except Exception as e:
            print(f"Error getting pending orders count: {e}")
            pending_count = 0
        finally:
            cursor_wrapper.close()
            conn.close()
        
        messages_badge = f" 📩({pending_count})" if pending_count > 0 else ""
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        # Row 1
        markup.row("🏪 منتجاتي", "📁 الأقسام", "📊 كشف حساب الزبائن")
        # Row 2
        markup.row("🏪 إدارة الزبائن الآجلين", f"📩 الرسائل{messages_badge}", "🔗 رابط المتجر")
        # Row 3
        markup.row("🛍️ وضع المشتري", "🏠 الرئيسية")
        
        welcome_msg = f"🏪 **مرحباً بصاحب المتجر!**\n"
        welcome_msg += f"🏪 متجرك: {store_name}"
        if pending_count > 0:
            welcome_msg += f"\n\nلديك {pending_count} طلبات جديدة!"
        
        bot.send_message(telegram_id, welcome_msg, reply_markup=markup)
    except Exception as e:
        print(f"⚠️ خطأ في إظهار قائمة البائع لـ {telegram_id}: {e}")

# ====== دالة handle_copy_store_link محسنة ======
def handle_copy_store_link(call):
    try:
        telegram_id = int(call.data.split("_")[3])
        store_link = generate_store_link(telegram_id)
        
        if store_link:
            # نسخ الرابط إلى الحافظة (محاكاة)
            bot.answer_callback_query(call.id, f"✅ تم نسخ رابط المتجر\n\n{store_link}", show_alert=False)
            
            # إرسال رسالة تأكيد
            try:
                seller = get_seller_by_telegram(telegram_id)
                store_name = seller[3] if seller else "المتجر"
                
                bot.send_message(call.message.chat.id,
                               f"✅ **تم نسخ رابط متجرك**\n\n"
                               f"🏪 {store_name}\n"
                               f"🔗 **الرابط:** `{store_link}`\n\n"
                               f"يمكنك الآن مشاركة الرابط مع عملائك.")
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "⚠️ تعذر توليد رابط المتجر")
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {str(e)}")

# ====== إصلاح مشكلة /start للمتاجر ======
@bot.message_handler(func=lambda message: message.text == "📋 قائمة المتاجر" and is_bot_admin(message.from_user.id))
def list_stores(message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Explicitly select columns to avoid index errors if schema changes
        if IS_POSTGRES:
            cursor.execute("""
                SELECT SellerID, TelegramID, UserName, StoreName, CreatedAt, Status, 
                       COALESCE(RequireCustomerRegistration, 0) as RequireCustomerRegistration
                FROM Sellers
                ORDER BY CreatedAt DESC
            """)
        else:
            cursor.execute("""
                SELECT SellerID, TelegramID, UserName, StoreName, CreatedAt, Status, 
                       COALESCE(RequireCustomerRegistration, 0) as RequireCustomerRegistration
                FROM Sellers
                ORDER BY CreatedAt DESC
            """)
        stores = cursor.fetchall()
        conn.close()
        
        if not stores:
            bot.send_message(message.chat.id, "لا توجد متاجر مسجلة بعد.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        text = "📋 **قائمة جميع المتاجر:**\n\n"
        
        for store in stores:
            seller_id, telegram_id, username, store_name, created_at, status = store[:6]
            require_reg = store[6] if len(store) > 6 else 0
            status_icon = "✅" if status == 'active' else "⏸️"
            reg_icon = "🔒" if require_reg == 1 else "🔓"
            
            # Escape store name to prevent markdown errors
            safe_store_name = escape_markdown_v1(store_name)
            
            text += f"{status_icon} {reg_icon} **المتجر:** {safe_store_name}\n"
            text += f"👤 المالك: {format_seller_mention(username, telegram_id)}\n"
            text += f"🆔 المعرف: {telegram_id}\n"
            text += f"📅 تاريخ الإنشاء: {created_at}\n"
            text += f"📊 الحالة: {'نشط' if status == 'active' else 'معلق'}\n"
            text += f"🔐 قيد الدخول: {'مفعل (يتطلب تسجيل)' if require_reg == 1 else 'معطل (مفتوح للجميع)'}\n"
            text += "────\n\n"
            
            # إضافة زر لإدارة إعدادات المتجر
            label = f"{safe_store_name[:30]} - {'🔒' if require_reg == 1 else '🔓'}"
            markup.add(types.InlineKeyboardButton(
                label,
                callback_data=f"manage_store_reg_{seller_id}"
            ))
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض القائمة:\n{e}")

@bot.message_handler(func=lambda message: message.text == "🛍️ وضع المشتري")
def admin_switch_to_buyer_mode(message):
    show_buyer_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "🏠 الرئيسية" and is_bot_admin(message.from_user.id))
def admin_main_menu(message):
    show_bot_admin_menu(message)

# ====== وظائف إضافة وتعديل القسم ======
@bot.message_handler(func=lambda message: message.text == "➕ إضافة قسم" and is_seller(message.from_user.id))
def add_category_step1(message):
    telegram_id = message.from_user.id
    
    print(f"🔍 add_category_step1 تم استدعاؤه")
    print(f"   User ID: {telegram_id}")
    print(f"   is_mock: {getattr(message, 'is_mock', False)}")
    
    # تم حذف الـ safeguard - جعل الدالة تعمل دائماً
    
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        # Debugging "Not a seller" issue
        bot.send_message(message.chat.id, f"⛔ أنت لست بائعاً مسجلاً! (Debug ID: {telegram_id})")
        return
    
    print(f"✅ البائع موجود: {seller}")
    
    user_states[telegram_id] = {
        "step": "add_category",
        "seller_id": seller[0]
    }
    
    print(f"📝 تم تعيين الـ state: {user_states[telegram_id]}")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🏠 الرئيسية")
    
    bot.send_message(message.chat.id, "📁 **إضافة قسم جديد**\n\nيرجى إدخال اسم القسم:", reply_markup=markup)

@bot.message_handler(func=lambda message: (message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "add_category"))
def add_category_step2(message):
    telegram_id = message.from_user.id
    
    print(f"\n{'='*60}")
    print(f"🔵 add_category_step2 تم استدعاؤه")
    print(f"   User ID: {telegram_id}")
    print(f"   Text: {message.text}")
    print(f"   User States: {user_states.get(telegram_id, {})}")
    print(f"{'='*60}")
    
    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        if telegram_id in user_states:
            del user_states[telegram_id]
        if message.text == "🔙 رجوع":
            show_seller_menu(message)
        else:
            handle_main_menu(message)
        return

    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم القسم كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية' أو '🔙 رجوع'.")
        return
    
    state = user_states[telegram_id]
    
    category_name = message.text.strip()
    
    if not category_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للقسم.")
        return
    
    print(f"✅ إدخال صحيح: '{category_name}'")
    print(f"📁 جاري إضافة فئة للبائع {state['seller_id']}")
    
    # إضافة القسم إلى قاعدة البيانات
    add_category(state["seller_id"], category_name)
    
    bot.send_message(message.chat.id, f"✅ **تم إضافة القسم بنجاح!**\n\n📁 القسم: {category_name}")
    
    if telegram_id in user_states:
        del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.text == "✏️ تعديل قسم" and is_seller(message.from_user.id))
def edit_category_step1(message):
    telegram_id = message.from_user.id
    
    # تم حذف الـ safeguard - جعل الدالة تعمل دائماً
    
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام لتعديلها.\n\nيمكنك إضافة قسم جديد أولاً.")
        return
    
    # Hide menu first
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=menu_markup)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for category_id, category_name in categories:
        markup.add(types.InlineKeyboardButton(category_name, callback_data=f"edit_cat_{category_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "📁 **تعديل قسم**\n\n"
                    "اختر القسم الذي تريد تعديله:",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_cat_"))
def handle_edit_category(call):
    try:
        category_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        category = get_category_by_id(category_id)
        if not category:
            bot.answer_callback_query(call.id, "القسم غير موجود")
            return
        
        user_states[telegram_id] = {
            "step": "edit_category_name",
            "category_id": category_id
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🏠 الرئيسية")
        
        bot.send_message(call.message.chat.id,
                        f"📁 **تعديل قسم**\n\n"
                        f"القسم الحالي: {category[2]}\n\n"
                        f"يرجى إدخال الاسم الجديد للقسم:", reply_markup=markup)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

# دالة جديدة لعرض قائمة الأقسام للتعديل (بدلاً من تعديل قسم محدد مباشرة)
def view_edit_category_menu(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return

    categories = get_categories(seller[0])
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام لتعديلها.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for cat in categories:
        # Revert to Tuple Access
        cid, name = cat[0], cat[1]
        markup.add(types.InlineKeyboardButton(f"📁 {name}", callback_data=f"view_cat_{cid}"))
    
    markup.add(types.InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="dashboard_add_cat"))
    markup.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, "📁 **أقسام متجرك**\n\nاضغط على القسم للتحكم به.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_cat_"))
def handle_view_category_detail(call):
    try:
        category_id = int(call.data.split("_")[2])
        category = get_category_by_id(category_id)
        
        if not category:
            bot.answer_callback_query(call.id, "القسم غير موجود")
            return
            
        cid = category[0]
        name = category[2]
        
        text = f"📁 **{name}**\n\n"
        text += "يمكنك التحكم في هذا القسم من هنا."
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة", callback_data="dashboard_add_cat"),
            types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_cat_{cid}"),
            types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_cat_{cid}") # Need to ensure delete_cat handler exists
        )
        markup.add(types.InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="back_to_cat_list"))
        
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
        bot.answer_callback_query(call.id)
    except Exception as e:
         bot.answer_callback_query(call.id, f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_cat_list")
def back_to_cat_list(call):
    call.message.from_user.id = call.from_user.id
    view_categories(call.message)
    bot.answer_callback_query(call.id)
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    markup_hidden = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_hidden.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=markup_hidden)
    
    bot.send_message(message.chat.id, "📁 **تعديل قسم**\n\nاختر القسم الذي تريد تعديله:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_category_name")
def edit_category_step2(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    new_name = message.text.strip()

    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[telegram_id]
        if message.text == "🔙 رجوع":
            show_seller_menu(message)
        else:
            handle_main_menu(message)
        return

    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم القسم كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية'.")
        return
    
    if not new_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للقسم.")
        return
    
    # تحديث اسم القسم
    update_category(state["category_id"], new_name)
    
    bot.send_message(message.chat.id, f"✅ **تم تعديل القسم بنجاح!**\n\n📁 الاسم الجديد: {new_name}")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def handle_back_to_menu(call):
    telegram_id = call.from_user.id
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(call.message)
    elif is_seller(telegram_id):
        show_seller_menu(call.message)
    else:
        show_buyer_main_menu(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def handle_main_menu_callback(call):
    """معالج زر العودة للرئيسية"""
    telegram_id = call.from_user.id
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(call.message)
    elif is_seller(telegram_id):
        show_seller_menu(call.message)
    else:
        show_buyer_main_menu(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == "📁 الأقسام" and is_seller(message.from_user.id))
def view_categories(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    # Hide menu first
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=menu_markup)
    
    text = "📁 **إدارة الأقسام**\n\n"
    text += "هنا يمكنك إدارة أقسام متجرك (إضافة، تعديل، حذف، وعرض).\n\n"
    text += "**الأقسام الحالية:**\n"
    
    if categories:
        for i, category in enumerate(categories, 1):
            category_id, category_name = category
            text += f"{i}. **{category_name}**\n"
            text += f"   🆔 معرف القسم: {category_id}\n"
            text += "────\n"
    else:
        text += "📭 لا توجد أقسام حالياً.\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ إضافة قسم", callback_data="dashboard_add_cat"),
        types.InlineKeyboardButton("✏️ تعديل قسم", callback_data="dashboard_edit_cat"),
        types.InlineKeyboardButton("🗑️ حذف قسم", callback_data="delete_category_menu"),
        types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "add_new_category")
def handle_add_new_category(call):
    mock_msg = MockMessage(call.message.chat, call.from_user, "➕ إضافة قسم")
    add_category_step1(mock_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "go_to_edit_category")
def handle_go_to_edit_category(call):
    mock_msg = MockMessage(call.message.chat, call.from_user, "✏️ تعديل قسم")
    edit_category_step1(mock_msg)
    bot.answer_callback_query(call.id)

# ====== معالجة أزرار الحذف النصية (القائمة الرئيسية) ======
@bot.message_handler(func=lambda message: message.text == "🗑️ حذف منتج" and is_seller(message.from_user.id))
def handle_delete_product_text(message):
    bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.text == "🗑️ حذف قسم" and is_seller(message.from_user.id))
def handle_delete_category_text(message):
    bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
    show_seller_menu(message)

# ====== حذف متجر (للأدمن) ======
@bot.message_handler(func=lambda message: message.text == "🗑️ حذف متجر" and is_bot_admin(message.from_user.id))
def handle_delete_store_text(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SellerID, StoreName, Status FROM Sellers ORDER BY CreatedAt DESC")
    stores = cursor.fetchall()
    conn.close()
    
    if not stores:
        bot.send_message(message.chat.id, "📭 لا توجد متاجر لحذفها.")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    for store in stores:
        sid, name, status = store
        status_icon = "✅" if status == 'active' else "⏸️"
        markup.add(types.InlineKeyboardButton(f"🗑️ {name} {status_icon}", callback_data=f"confirm_delete_store_{sid}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "🗑️ **حذف متجر**\n\nاضغط على المتجر لحذفه نهائياً:",
                    reply_markup=markup,
                    parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_store_"))
def handle_confirm_delete_store(call):
    store_id = int(call.data.split("_")[3])
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ نعم، احذف نهائياً", callback_data=f"do_delete_store_{store_id}"))
    markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        f"⚠️ **تحذير: حذف المتجر**\n\nهل أنت متأكد من حذف المتجر رقم {store_id}؟\nسيؤدي هذا إلى حذف جميع المنتجات والأقسام والطلبات المرتبطة به.\n\n⚠️ **لا يمكن التراجع عن هذا الإجراء!**",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_delete_store_"))
def handle_do_delete_store(call):
    store_id = int(call.data.split("_")[3])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete related data first (cascade manually if needed, or rely on FK cascade if configured)
    # Since we didn't specify ON DELETE CASCADE in init_db, we should delete manually or update schema.
    # For safety, let's delete manually.
    try:
        cursor.execute("DELETE FROM \"OrderItems\" WHERE \"OrderID\" IN (SELECT \"OrderID\" FROM \"Orders\" WHERE \"SellerID\" = ?)", (store_id,))
        cursor.execute("DELETE FROM \"Orders\" WHERE \"SellerID\" = ?", (store_id,))
        cursor.execute("DELETE FROM \"Carts\" WHERE \"ProductID\" IN (SELECT \"ProductID\" FROM \"Products\" WHERE \"SellerID\" = ?)", (store_id,))
        cursor.execute("DELETE FROM \"Products\" WHERE \"SellerID\" = ?", (store_id,))
        cursor.execute("DELETE FROM \"Categories\" WHERE \"SellerID\" = ?", (store_id,))
        cursor.execute("DELETE FROM \"CreditLimits\" WHERE \"SellerID\" = ?", (store_id,))
        cursor.execute("DELETE FROM \"CreditCustomers\" WHERE \"SellerID\" = ?", (store_id,))
        cursor.execute("DELETE FROM \"Sellers\" WHERE \"SellerID\" = ?", (store_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ تم حذف المتجر بنجاح")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **تم حذف المتجر وجميع بياناته بنجاح.**")
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ أثناء الحذف")
        print(f"Delete Store Error: {e}")
    finally:
        conn.close()

# ====== لوحة التحكم والحذف ======
@bot.message_handler(func=lambda message: message.text == "📊 لوحة التحكم" and is_seller(message.from_user.id))
def handle_seller_control_panel(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🗑️ حذف منتج", callback_data="delete_product_menu"))
    markup.add(types.InlineKeyboardButton("🗑️ حذف قسم", callback_data="delete_category_menu"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "📊 **لوحة التحكم**\n\n"
                    "اختر الإجراء المطلوب:",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "delete_product_menu")
def handle_delete_product_menu(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "أنت لست بائعاً مسجلاً!")
        return
        
    products = get_products(seller_id=seller[0])
    
    if not products:
        bot.answer_callback_query(call.id, "لا توجد منتجات لحذفها", show_alert=True)
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    for product in products: # Show allow products
        pid, name = product[0], product[1]
        markup.add(types.InlineKeyboardButton(f"🗑️ {name}", callback_data=f"confirm_delete_prod_{pid}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        "🗑️ **حذف منتج**\n\nاضغط على المنتج لحذفه:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_prod_"))
def handle_confirm_delete_product(call):
    product_id = int(call.data.split("_")[3])
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ نعم، احذف", callback_data=f"do_delete_prod_{product_id}"))
    markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="delete_product_menu"))
    
    product = get_product_by_id(product_id)
    if product:
        name = product[3]
        bot.edit_message_text(
            f"⚠️ **هل أنت متأكد من حذف المنتج؟**\n\n🛒 المنتج: {name}\n\n⚠️ لا يمكن التراجع عن هذا الإجراء.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "المنتج غير موجود")

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_delete_prod_"))
def handle_do_delete_product(call):
    product_id = int(call.data.split("_")[3])
    
    # 1. Fetch product to get image path BEFORE deletion
    product = get_product_by_id(product_id)
    image_path = None
    if product:
        # Structure: ProductID(0), ..., ImagePath(8)
        image_path = product[8]

    # 2. Delete from Database
    delete_product(product_id)
    
    # 3. Delete Image File if exists
    if image_path:
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"🗑️ Deleted image file: {image_path}")
        except Exception as e:
            print(f"⚠️ Failed to delete image file {image_path}: {e}")

    bot.answer_callback_query(call.id, "✅ تم حذف المنتج والصورة")
    handle_delete_product_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "delete_category_menu")
def handle_delete_category_menu(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "أنت لست بائعاً مسجلاً!")
        return
        
    categories = get_categories(seller[0])
    
    if not categories:
        bot.answer_callback_query(call.id, "لا توجد أقسام لحذفها", show_alert=True)
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        cid, name = cat[0], cat[1]
        markup.add(types.InlineKeyboardButton(f"🗑️ {name}", callback_data=f"try_delete_cat_{cid}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        "🗑️ **حذف قسم**\n\nاضغط على القسم لحذفه:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("try_delete_cat_"))
def handle_try_delete_category(call):
    category_id = int(call.data.split("_")[3])
    
    # Check if category has products
    count = get_product_count_in_category(category_id)
    if count > 0:
        bot.answer_callback_query(call.id, f"⛔ لا يمكن حذف القسم!\nيحتوي على {count} منتج.", show_alert=True)
        return
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ نعم، احذف", callback_data=f"do_delete_cat_{category_id}"))
    markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="delete_category_menu"))
    
    category = get_category_by_id(category_id)
    if category:
        name = category[2]
        bot.edit_message_text(
            f"⚠️ **هل أنت متأكد من حذف القسم؟**\n\n📁 القسم: {name}\n\n⚠️ لا يمكن التراجع عن هذا الإجراء.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "القسم غير موجود")

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_delete_cat_"))
def handle_do_delete_category(call):
    category_id = int(call.data.split("_")[3])
    delete_category(category_id)
    bot.answer_callback_query(call.id, "✅ تم حذف القسم")
    handle_delete_category_menu(call)

# ====== وظائف إضافة وتعديل المنتج ======
@bot.message_handler(func=lambda message: message.text == "➕ إضافة منتج" and is_seller(message.from_user.id))
def add_product_step1(message):
    telegram_id = message.from_user.id
    
    # safeguard: IF NOT MOCK (Real user click on old button), Redirect to new menu
    if not getattr(message, 'is_mock', False):
        bot.send_message(message.chat.id, "🔄 تحديث القائمة...")
        show_seller_menu(message)
        return

    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, "📭 لا توجد أقسام بعد.\n\nيرجى إضافة قسم أولاً قبل إضافة المنتجات.")
        return
    
    # Hide menu first
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=menu_markup)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for category_id, category_name in categories:
        markup.add(types.InlineKeyboardButton(category_name, callback_data=f"select_category_{category_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "🛒 **إضافة منتج جديد**\n\n"
                    "اختر القسم الذي ترغب بإضافة المنتج إليه:",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_category_"))
def handle_select_category_for_product(call):
    try:
        category_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        seller = get_seller_by_telegram(telegram_id)
        if not seller:
            bot.answer_callback_query(call.id, "أنت لست بائعاً مسجلاً!")
            return
        
        user_states[telegram_id] = {
            "step": "add_product_name",
            "category_id": category_id,
            "seller_id": seller[0]
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🏠 الرئيسية")
        
        bot.send_message(call.message.chat.id, 
                        "🛒 **إضافة منتج جديد**\n\n"
                        "الآن، يرجى إدخال اسم المنتج:", reply_markup=markup)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_name")
def add_product_step2(message):
    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[telegram_id]
        if message.text == "🔙 رجوع":
            show_seller_menu(message)
        else:
            handle_main_menu(message)
        return

    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم المنتج كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية' أو '🔙 رجوع'.")
        return
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    product_name = message.text.strip()
    
    if not product_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للمنتج.")
        return
    
    user_states[telegram_id]["product_name"] = product_name
    user_states[telegram_id]["step"] = "add_product_description"
    
    bot.send_message(message.chat.id, 
                    "📝 **وصف المنتج**\n\n"
                    "الآن، يرجى إدخال وصف للمنتج (اختياري):\n\n"
                    "يمكنك كتابة وصف تفصيلي أو كتابة 'تخطي' للاستمرار.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_description")
def add_product_step3(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    description = message.text.strip()
    if description.lower() == "تخطي":
        description = ""
    
    user_states[telegram_id]["description"] = description
    user_states[telegram_id]["step"] = "add_product_price"
    
    bot.send_message(message.chat.id, 
                    "💰 **سعر المنتج**\n\n"
                    "الآن، يرجى إدخال سعر المنتج (بالدينار العراقي):")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_price")
def add_product_step4(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    try:
        price = float(message.text)
        if price <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للسعر.")
        return
    
    user_states[telegram_id]["price"] = price
    user_states[telegram_id]["step"] = "add_product_wholesale_price"
    
    bot.send_message(message.chat.id, 
                    "💰 **سعر الجملة**\n\n"
                    "الآن، يرجى إدخال سعر الجملة (بالدينار العراقي):\n"
                    "يمكنك كتابة 'تخطي' إذا لم يكن هناك سعر جملة.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_wholesale_price")
def add_product_step4b(message):
    """معالج سعر الجملة - والفحص التلقائي لنوع المتجر"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    wholesale_price_text = message.text.strip()
    
    if wholesale_price_text.lower() == "تخطي":
        wholesale_price = None
    else:
        try:
            wholesale_price = float(wholesale_price_text)
            if wholesale_price <= 0:
                bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح أكبر من صفر.")
                return
        except:
            bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للسعر.")
            return
    
    user_states[telegram_id]["wholesale_price"] = wholesale_price
    
    # ✅ فحص نوع المتجر الآن
    seller_id = state.get("seller_id")
    is_closed_store = False
    
    print(f"\n{'='*60}")
    print(f"🔍 [DEBUG] فحص نوع المتجر")
    print(f"  - seller_id={seller_id}")
    print(f"  - telegram_id={telegram_id}")
    print(f"  - state keys={list(state.keys())}")
    print(f"{'='*60}")
    
    if not seller_id:
        print(f"⚠️ [DEBUG] لا يوجد seller_id في state!")
        print(f"  State contents: {state}")
        # محاولة الحصول على seller_id من البيانات الحالية
        seller = get_seller_by_telegram(telegram_id)
        if seller:
            seller_id = seller[0]
            user_states[telegram_id]["seller_id"] = seller_id
            print(f"✅ تم الحصول على seller_id من الـ database: {seller_id}")
        else:
            print(f"❌ فشل الحصول على seller_id!")
            bot.send_message(message.chat.id, "❌ حدث خطأ في تحديد هويتك. الرجاء المحاولة مرة أخرى.")
            return
    
    if seller_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            if IS_POSTGRES:
                # جرب مع lowercase لأن PostgreSQL قد يخزنه lowercase
                cursor.execute('SELECT sellerid, COALESCE(requirecustomerregistration, 0) FROM sellers WHERE sellerid=%s', (seller_id,))
            else:
                cursor.execute('SELECT SellerID, COALESCE(RequireCustomerRegistration, 0) FROM Sellers WHERE SellerID=?', (seller_id,))
            result = cursor.fetchone()
            
            print(f"🔍 [DEBUG] نتيجة الـ query: {result}")
            
            if result:
                require_registration = result[1]
                print(f"  - RequireCustomerRegistration value: {require_registration}")
                print(f"  - Type: {type(require_registration)}")
                
                # تحويل إلى int في حالة كونه string أو boolean
                if isinstance(require_registration, str):
                    is_closed_store = (require_registration == '1' or require_registration.lower() == 'true')
                elif isinstance(require_registration, bool):
                    is_closed_store = require_registration
                else:
                    is_closed_store = (int(require_registration) == 1)
                
                print(f"✅ [DEBUG] is_closed_store={is_closed_store}")
            else:
                print(f"⚠️ [DEBUG] لم يتم العثور على المتجر!")
            
            conn.close()
        except Exception as e:
            print(f"❌ [DEBUG] خطأ في الـ query: {e}")
            import traceback
            traceback.print_exc()
            is_closed_store = False
    
    print(f"📊 [FINAL] is_closed_store={is_closed_store}")
    print(f"{'='*60}\n")
    
    # للمتاجر المغلقة: تخطي الكمية والانتقال مباشرة لمعرض الصور
    if is_closed_store:
        print("🔒 [DEBUG] متجر مغلق - الانتقال لمعرض الصور المتعددة")
        user_states[telegram_id]["quantity"] = 1  # الكمية = 1 (سيتم تحديثها حسب عدد الصور)
        user_states[telegram_id]["step"] = "waiting_for_product_images_closed_store"
        
        bot.send_message(message.chat.id, 
                        "📸 **صور المنتج (متعددة)**\n\n"
                        "🎨 المتجر المغلق يتطلب صور متعددة\n"
                        "اختر من الخيارات أدناه:",
                        reply_markup=types.InlineKeyboardMarkup(row_width=2).add(
                            types.InlineKeyboardButton("📷 صور متعددة", callback_data="closed_store_multiple_images"),
                            types.InlineKeyboardButton("💾 حفظ المنتج", callback_data="closed_store_save_product")
                        ))
    else:
        # للمتاجر المفتوحة: طلب الكمية كالمعتاد
        print("🔓 [DEBUG] متجر مفتوح - طلب الكمية")
        user_states[telegram_id]["step"] = "add_product_quantity"
        
        bot.send_message(message.chat.id, 
                        "📦 **كمية المنتج**\n\n"
                        "الآن، يرجى إدخال كمية المنتج المتاحة:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_product_quantity")
def add_product_step5(message):
    """طلب الكمية - المتاجر المفتوحة فقط"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        quantity = int(message.text)
        if quantity < 0:
            bot.send_message(message.chat.id, "❌ الرجاء إدخال كمية صحيحة (صفر أو أكبر).")
            return
    except:
        bot.send_message(message.chat.id, "❌ الرجاء إدخال رقم صحيح للكمية.")
        return
    
    user_states[telegram_id]["quantity"] = quantity
    user_states[telegram_id]["step"] = "waiting_for_product_image"
    
    bot.send_message(message.chat.id, 
                    "📸 **صورة المنتج**\n\n"
                    "الآن يمكنك إرسال صورة للمنتج (اختياري).",
                    reply_markup=types.ForceReply(selective=False))

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "waiting_for_product_image")
def add_product_step6(message):
    """استقبال صورة المنتج - المتاجر المفتوحة فقط"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.content_type == 'photo':
        # استقبال الصورة
        filename = save_photo_from_message(message)
        if filename:
            state["image_path"] = filename
            bot.send_message(message.chat.id, f"✅ تم حفظ الصورة: {filename}")
        else:
            bot.send_message(message.chat.id, "⚠️ فشل حفظ الصورة، سيتم حفظ المنتج بدون صورة.")
            state["image_path"] = ""
    elif message.content_type == 'text' and message.text.lower() in ['تخطي', 'skip', 'الغاء']:
        state["image_path"] = ""
        bot.send_message(message.chat.id, "✅ تم تخطي الصورة.")
    else:
        bot.send_message(message.chat.id, "⚠️ الرجاء إرسال صورة أو كتابة 'تخطي' للمتابعة.")
        return
    
    # انتقل إلى حفظ المنتج
    finish_adding_product(message)


@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "waiting_for_product_image")
def handle_product_image_photo(message):
    """معالج الصور للمتاجر المفتوحة فقط"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        # ✅ حفظ الصورة في ImageStorage
        filename = save_photo_from_message(message)
        if not filename:
            bot.send_message(message.chat.id, "⚠️ فشل حفظ الصورة.")
            return
        
        state["image_path"] = filename
        print(f"✅ تم حفظ صورة المنتج: {filename}")
        bot.send_message(message.chat.id, f"✅ تم حفظ الصورة")
        
        # انتقل إلى حفظ المنتج
        finish_adding_product(message)
        
    except Exception as e:
        print(f"⚠️ خطأ في معالجة الصورة: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ: {str(e)}")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "waiting_for_product_image" and 
                     message.content_type == 'text')
def handle_product_image_text(message):
    """معالج النص - تخطي الصورة"""
    telegram_id = message.from_user.id
    if message.text.lower() in ['تخطي', 'تخطي بدون صورة', 'skip', 'الغاء']:
        state = user_states[telegram_id]
        state["image_path"] = ""
        finish_adding_product(message)
    else:
        bot.send_message(message.chat.id, "⚠️ الرجاء إرسال صورة أو كتابة 'تخطي' للمتابعة بدون صورة.")

def finish_adding_product(message):
    """حفظ المنتج النهائي - المتاجر المفتوحة فقط"""
    telegram_id = message.from_user.id
    if telegram_id not in user_states:
        bot.send_message(message.chat.id, "❌ انتهت الجلسة، ابدأ من جديد.")
        return
    
    state = user_states[telegram_id]
    
    # التحقق من البيانات المطلوبة
    required = ["seller_id", "category_id", "product_name", "price", "quantity"]
    for field in required:
        if field not in state:
            bot.send_message(message.chat.id, f"❌ بيانات غير مكتملة: {field}")
            del user_states[telegram_id]
            return
    
    seller_id = state["seller_id"]
    category_id = state["category_id"]
    product_name = state["product_name"]
    price = state["price"]
    quantity = state["quantity"]
    description = state.get("description", "")
    wholesale_price = state.get("wholesale_price", None)  # قد تكون None إذا لم يدخل المستخدم قيمة
    image_path = state.get("image_path", "")
    
    print(f"🔄 حفظ المنتج: {product_name} | السعر: {price} | سعر الجملة: {wholesale_price} | الكمية: {quantity} | الصورة: {image_path}")
    
    try:
        # إنشاء اتصال بقاعدة البيانات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إدراج المنتج
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath, Status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')
            """, (seller_id, category_id, product_name, description, price, wholesale_price, quantity, image_path))
        else:
            cursor.execute("""
                INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath, Status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (seller_id, category_id, product_name, description, price, wholesale_price, quantity, image_path))
        
        conn.commit()
        
        # استرجاع ProductID
        if IS_POSTGRES:
            cursor.execute("""
                SELECT ProductID FROM Products 
                WHERE SellerID=%s AND CategoryID=%s AND Name=%s 
                ORDER BY ProductID DESC LIMIT 1
            """, (seller_id, category_id, product_name))
        else:
            cursor.execute("""
                SELECT ProductID FROM Products 
                WHERE SellerID=? AND CategoryID=? AND Name=? 
                ORDER BY ProductID DESC LIMIT 1
            """, (seller_id, category_id, product_name))
        
        result = cursor.fetchone()
        if not result:
            print("❌ فشل إنشاء المنتج!")
            bot.send_message(message.chat.id, "❌ حدث خطأ في إنشاء المنتج.")
            conn.close()
            return
        
        product_id = result[0] if isinstance(result, tuple) else result['productid']
        print(f"✅ تم إنشاء المنتج: ProductID={product_id}")
        
        # إدراج الصورة في ProductImages إذا كانت موجودة
        if image_path:
            try:
                print(f"📝 [ProductImages] Inserting image_path='{image_path}' for ProductID={product_id}")
                if IS_POSTGRES:
                    cursor.execute("""
                        INSERT INTO productimages (productid, imagepath, imageorder)
                        VALUES (%s, %s, 0)
                    """, (product_id, image_path))
                else:
                    cursor.execute("""
                        INSERT INTO ProductImages (ProductID, ImagePath, ImageOrder)
                        VALUES (?, ?, 0)
                    """, (product_id, image_path))
                conn.commit()
                print(f"✅ [ProductImages] Saved: ProductID={product_id}, ImagePath='{image_path}'")
            except Exception as e:
                print(f"⚠️ خطأ في إدراج الصورة: {e}")
        
        conn.close()
        
        # رسالة النجاح
        success_msg = f"""
✅ **تم حفظ المنتج بنجاح!**

📦 **اسم المنتج:** {product_name}
💰 **السعر:** {price}
📊 **الكمية:** {quantity}
"""
        
        if image_path:
            success_msg += f"📸 **الصورة:** تم رفعها\n"
        
        if description:
            success_msg += f"📝 **الوصف:** {description}\n"
        
        bot.send_message(message.chat.id, success_msg)
        
        # حذف الحالة
        del user_states[telegram_id]
        
        # إظهار القائمة الرئيسية
        show_seller_menu(message)
        
    except Exception as e:
        print(f"❌ خطأ في حفظ المنتج: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")
        if telegram_id in user_states:
            del user_states[telegram_id]

# ====== معالج أزرار المتاجر المغلقة ======
@bot.callback_query_handler(func=lambda call: call.data == "closed_store_multiple_images")
def handle_closed_store_multiple_images(call):
    """معالج زر 'صور متعددة' للمتاجر المغلقة"""
    telegram_id = call.from_user.id
    
    print(f"\n🔔 [CALLBACK] Received closed_store_multiple_images")
    print(f"   - telegram_id={telegram_id}")
    print(f"   - in user_states: {telegram_id in user_states}")
    
    if telegram_id in user_states:
        print(f"   - current step: {user_states[telegram_id].get('step')}")
    
    if telegram_id not in user_states or user_states[telegram_id]["step"] != "waiting_for_product_images_closed_store":
        print(f"❌ Invalid state: {user_states.get(telegram_id, {}).get('step')}")
        bot.answer_callback_query(call.id, "❌ الجلسة انتهت، ابدأ من جديد")
        return
    
    # إنشاء قائمة لتخزين الصور
    user_states[telegram_id]["images"] = []
    user_states[telegram_id]["step"] = "uploading_closed_store_images"
    
    print(f"✅ تم تعيين step إلى uploading_closed_store_images")
    
    bot.answer_callback_query(call.id, "📸 جاهز لاستقبال الصور")
    bot.send_message(call.message.chat.id,
                    "📸 **إرسال الصور**\n\n"
                    "يمكنك الآن إرسال الصور واحدة تلو الأخرى.\n"
                    "عند الانتهاء، اضغط على 'حفظ المنتج'",
                    reply_markup=types.InlineKeyboardMarkup(row_width=1).add(
                        types.InlineKeyboardButton("✅ حفظ المنتج", callback_data="closed_store_save_product")
                    ))

@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "uploading_closed_store_images")
def handle_closed_store_image_upload(message):
    """استقبال صور المنتج للمتاجر المغلقة"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    try:
        # ✅ حفظ الصورة في ImageStorage
        filename = save_photo_from_message(message)
        if not filename:
            bot.send_message(message.chat.id, "⚠️ فشل حفظ الصورة، حاول مرة أخرى.")
            return
        
        # إضافة الصورة إلى القائمة
        if "images" not in state:
            state["images"] = []
        state["images"].append(filename)
        
        # عرض عدد الصور المرفوعة
        image_count = len(state["images"])
        bot.send_message(message.chat.id, 
                        f"✅ تم حفظ الصورة ({image_count})\n\n"
                        f"📸 عدد الصور المرفوعة: {image_count}\n"
                        f"(يمكنك إرسال المزيد أو الضغط على 'حفظ المنتج')",
                        reply_markup=types.InlineKeyboardMarkup(row_width=1).add(
                            types.InlineKeyboardButton("✅ حفظ المنتج", callback_data="closed_store_save_product")
                        ))
        
    except Exception as e:
        print(f"⚠️ خطأ في معالجة الصورة: {e}")
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ: {str(e)}")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "uploading_closed_store_images" and 
                     message.content_type == 'text')
def handle_closed_store_image_text(message):
    """معالج النص - تخطي الصور أو إلغاء"""
    telegram_id = message.from_user.id
    
    if message.text.lower() in ['إلغاء', 'الغاء', 'cancel']:
        bot.send_message(message.chat.id, "❌ تم إلغاء العملية")
        del user_states[telegram_id]
        show_seller_menu(message)
    else:
        bot.send_message(message.chat.id, "⚠️ الرجاء إرسال صورة أو اضغط على 'حفظ المنتج'")

@bot.callback_query_handler(func=lambda call: call.data == "closed_store_save_product")
def handle_closed_store_save_product(call):
    """معالج حفظ منتج المتجر المغلق مع تحديث الكمية"""
    telegram_id = call.from_user.id
    
    if telegram_id not in user_states:
        bot.answer_callback_query(call.id, "❌ الجلسة انتهت")
        return
    
    state = user_states[telegram_id]
    images = state.get("images", [])
    
    # للمتاجر المغلقة: الكمية = عدد الصور
    quantity = len(images) if images else 0
    
    if quantity == 0:
        bot.answer_callback_query(call.id, "⚠️ يجب إرسال صورة واحدة على الأقل")
        return
    
    # تحديث الكمية
    user_states[telegram_id]["quantity"] = quantity
    
    # إنشاء message object مزيف للتعامل مع finish_adding_product
    class MockMessage:
        def __init__(self, chat_id, from_user_id):
            self.chat = type('obj', (object,), {'id': chat_id})()
            self.from_user = type('obj', (object,), {'id': from_user_id})()
    
    mock_msg = MockMessage(call.message.chat.id, telegram_id)
    
    try:
        # حفظ المنتج الأساسي
        required = ["seller_id", "category_id", "product_name", "price"]
        for field in required:
            if field not in state:
                bot.answer_callback_query(call.id, f"❌ بيانات غير مكتملة: {field}")
                return
        
        seller_id = state["seller_id"]
        category_id = state["category_id"]
        product_name = state["product_name"]
        price = state["price"]
        description = state.get("description", "")
        wholesale_price = state.get("wholesale_price", None)
        
        # إنشاء اتصال بقاعدة البيانات وحفظ المنتج
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إدراج المنتج مع الكمية المحدثة (عدد الصور)
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath, Status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')
            """, (seller_id, category_id, product_name, description, price, wholesale_price, quantity, ""))
        else:
            cursor.execute("""
                INSERT INTO Products (SellerID, CategoryID, Name, Description, Price, WholesalePrice, Quantity, ImagePath, Status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (seller_id, category_id, product_name, description, price, wholesale_price, quantity, ""))
        
        conn.commit()
        
        # استرجاع ProductID
        if IS_POSTGRES:
            cursor.execute("""
                SELECT ProductID FROM Products 
                WHERE SellerID=%s AND CategoryID=%s AND Name=%s 
                ORDER BY ProductID DESC LIMIT 1
            """, (seller_id, category_id, product_name))
        else:
            cursor.execute("""
                SELECT ProductID FROM Products 
                WHERE SellerID=? AND CategoryID=? AND Name=? 
                ORDER BY ProductID DESC LIMIT 1
            """, (seller_id, category_id, product_name))
        
        result = cursor.fetchone()
        if not result:
            bot.answer_callback_query(call.id, "❌ فشل إنشاء المنتج")
            conn.close()
            return
        
        product_id = result[0] if isinstance(result, tuple) else result['productid']
        
        # إدراج جميع الصور في ProductImages
        for idx, image_filename in enumerate(images):
            try:
                if IS_POSTGRES:
                    cursor.execute("""
                        INSERT INTO productimages (productid, imagepath, imageorder)
                        VALUES (%s, %s, %s)
                    """, (product_id, image_filename, idx))
                else:
                    cursor.execute("""
                        INSERT INTO ProductImages (ProductID, ImagePath, ImageOrder)
                        VALUES (?, ?, ?)
                    """, (product_id, image_filename, idx))
            except Exception as e:
                print(f"⚠️ خطأ في إدراج الصورة {idx+1}: {e}")
        
        conn.commit()
        conn.close()
        
        # رسالة النجاح
        success_msg = f"""
✅ **تم حفظ المنتج بنجاح!**

📦 **اسم المنتج:** {product_name}
💰 **السعر:** {price}
📊 **الكمية:** {quantity} (عدد الصور)
📸 **عدد الصور:** {len(images)}
"""
        
        if description:
            success_msg += f"📝 **الوصف:** {description}\n"
        
        bot.send_message(call.message.chat.id, success_msg)
        bot.answer_callback_query(call.id, "✅ تم الحفظ بنجاح")
        
        # حذف الحالة
        del user_states[telegram_id]
        
        # إظهار القائمة الرئيسية
        show_seller_menu(mock_msg)
        
    except Exception as e:
        print(f"❌ خطأ في حفظ المنتج: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(call.message.chat.id, f"❌ خطأ: {str(e)}")
        bot.answer_callback_query(call.id, f"❌ خطأ: {str(e)}")
        if telegram_id in user_states:
            del user_states[telegram_id]

# ====== تعديل المنتج ======
@bot.message_handler(func=lambda message: message.text == "✏️ تعديل منتج" and is_seller(message.from_user.id))
def edit_product_step1(message):
    telegram_id = message.from_user.id
    
    # تم حذف الـ safeguard - جعل الدالة تعمل دائماً

    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    products = get_products(seller_id=seller[0])
    
    if not products:
        bot.send_message(message.chat.id, "📭 لا توجد منتجات لتعديلها.\n\nيمكنك إضافة منتجات أولاً.")
        return
    
    # Hide menu first
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري التحميل...**", reply_markup=menu_markup)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for product in products[:10]:
        pid = product[0]
        name = product[1]
        markup.add(types.InlineKeyboardButton(f"{name[:15]}...", callback_data=f"edit_product_{pid}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, 
                    "🛒 **تعديل منتج**\n\n"
                    "اختر المنتج الذي تريد تعديله:",
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_product_"))
def handle_select_product_to_edit(call):
    try:
        product_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "المنتج غير موجود")
            return
        
        user_states[telegram_id] = {
            "step": "edit_product_select_field",
            "product_id": product_id,
            "product_data": product
        }
        
        # جميع المتاجر مفتوحة - عرض جميع خيارات التعديل
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ تعديل الاسم", callback_data="edit_prod_name"),
            types.InlineKeyboardButton("📝 تعديل الوصف", callback_data="edit_prod_desc"),
            types.InlineKeyboardButton("💰 تعديل السعر", callback_data="edit_prod_price"),
            types.InlineKeyboardButton("💰 تعديل سعر الجملة", callback_data="edit_prod_wholesale"),
            types.InlineKeyboardButton("📦 تعديل الكمية", callback_data="edit_prod_qty"),
            types.InlineKeyboardButton("📁 تغيير القسم", callback_data="edit_prod_cat"),
            types.InlineKeyboardButton("📸 تغيير الصورة", callback_data="edit_prod_img"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_edit_product")
        )
        
        pid, seller_id, category_id, name, desc, price, wholesale_price, qty, img_path = product
        
        category = get_category_by_id(category_id)
        category_name = category[2] if category else "غير محدد"
        
        text = f"🛒 **تعديل المنتج**\n\n"
        text += f"**المنتج:** {name}\n"
        text += f"**القسم:** {category_name}\n"
        text += f"**الوصف:** {desc[:50] if desc else 'لا يوجد وصف'}...\n"
        text += f"**السعر:** {price} IQD\n"
        if wholesale_price:
            text += f"**سعر الجملة:** {wholesale_price} IQD\n"
        text += f"**الكمية:** {qty}\n\n"
        text += "اختر ما تريد تعديله:"
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_edit_product")
def handle_back_to_edit_product(call):
    mock_msg = MockMessage(call.message.chat, call.from_user, "✏️ تعديل منتج")
    edit_product_step1(mock_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_prod_"))
def handle_edit_product_field(call):
    telegram_id = call.from_user.id
    if telegram_id not in user_states:
        bot.answer_callback_query(call.id, "انتهت الجلسة، ابدأ من جديد.")
        return
    
    state = user_states[telegram_id]
    product_id = state["product_id"]
    product = state["product_data"]
    
    field = call.data.split("_")[2]
    
    if field == "name":
        user_states[telegram_id]["step"] = "edit_product_name"
        bot.send_message(call.message.chat.id,
                        f"✏️ **تعديل اسم المنتج**\n\n"
                        f"الاسم الحالي: {product[3]}\n\n"
                        f"يرجى إدخال الاسم الجديد:")
    
    elif field == "desc":
        user_states[telegram_id]["step"] = "edit_product_description"
        current_desc = product[4] if product[4] else "لا يوجد وصف"
        bot.send_message(call.message.chat.id,
                        f"📝 **تعديل وصف المنتج**\n\n"
                        f"الوصف الحالي: {current_desc}\n\n"
                        f"يرجى إدخال الوصف الجديد (أو 'حذف' لحذف الوصف):")
    
    elif field == "price":
        user_states[telegram_id]["step"] = "edit_product_price"
        bot.send_message(call.message.chat.id,
                        f"💰 **تعديل سعر المنتج**\n\n"
                        f"السعر الحالي: {product[5]} IQD\n\n"
                        f"يرجى إدخال السعر الجديد (بالدينار العراقي):")
    
    elif field == "wholesale":
        user_states[telegram_id]["step"] = "edit_product_wholesale"
        current_wholesale = product[6] if product[6] else "لا يوجد"
        bot.send_message(call.message.chat.id,
                        f"💰 **تعديل سعر الجملة**\n\n"
                        f"سعر الجملة الحالي: {current_wholesale if current_wholesale != 'لا يوجد' else current_wholesale} IQD\n\n"
                        f"يرجى إدخال سعر الجملة الجديد (بالدينار العراقي):\n"
                        f"أو اكتب 'حذف' لحذف سعر الجملة.")
    
    elif field == "qty":
        user_states[telegram_id]["step"] = "edit_product_quantity"
        bot.send_message(call.message.chat.id,
                        f"📦 **تعديل كمية المنتج**\n\n"
                        f"الكمية الحالية: {product[7]}\n\n"
                        f"يرجى إدخال الكمية الجديدة:")
    
    elif field == "cat":
        user_states[telegram_id]["step"] = "edit_product_category"
        seller = get_seller_by_telegram(telegram_id)
        categories = get_categories(seller[0])
        
        if not categories:
            bot.send_message(call.message.chat.id, "📭 لا توجد أقسام متاحة.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cat_id, cat_name in categories:
            markup.add(types.InlineKeyboardButton(cat_name, callback_data=f"select_new_cat_{cat_id}"))
        
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_edit_product"))
        
        current_category = get_category_by_id(product[2])
        current_cat_name = current_category[2] if current_category else "غير محدد"
        
        bot.send_message(call.message.chat.id,
                        f"📁 **تغيير قسم المنتج**\n\n"
                        f"القسم الحالي: {current_cat_name}\n\n"
                        f"اختر القسم الجديد:",
                        reply_markup=markup)
    
    elif field == "img":
        # عرض رسالة توجيه بدلاً من طلب صورة مباشرة
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📷 معرض الصور", callback_data=f"manage_product_images_{product_id}"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_edit_product")
        )
        
        bot.send_message(call.message.chat.id,
                        f"📸 **إدارة صور المنتج**\n\n"
                        f"اضغط على آيقونة معرض الصور لإضافة الصور\n\n"
                        f"💡 **ملاحظة:** الصور ترسل للمشتري فقط ثم تُحذف من النظام",
                        reply_markup=markup)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_new_cat_"))
def handle_select_new_category(call):
    telegram_id = call.from_user.id
    if telegram_id not in user_states:
        bot.answer_callback_query(call.id, "انتهت الجلسة، ابدأ من جديد.")
        return
    
    try:
        category_id = int(call.data.split("_")[3])
        state = user_states[telegram_id]
        
        update_product(state["product_id"], category_id=category_id)
        
        category = get_category_by_id(category_id)
        category_name = category[2] if category else "غير محدد"
        
        bot.send_message(call.message.chat.id,
                        f"✅ **تم تغيير قسم المنتج بنجاح!**\n\n"
                        f"القسم الجديد: {category_name}")
        
        del user_states[telegram_id]
        handle_select_product_to_edit(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"حدث خطأ: {e}")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_name")
def process_edit_product_name(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    new_name = message.text.strip()
    
    # Validation: Handle menu buttons
    if message.text in ["🔙 رجوع", "🏠 الرئيسية"]:
        del user_states[telegram_id]
        if message.text == "🔙 رجوع":
            show_seller_menu(message)
        else:
            handle_main_menu(message)
        return

    if message.text in ["🏪 إنشاء متجر جديد", "➕ إضافة قسم", "➕ إضافة منتج", "✏️ تعديل قسم", "✏️ تعديل منتج", "تصفح المتاجر 🛍️", "سلة المشتريات 🛒", "📦 طلباتي", "📞 تواصل معنا"]:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم المنتج كتابةً.\nلإلغاء العملية، اضغط على '🏠 الرئيسية'.")
        return
    
    if not new_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح للمنتج.")
        return
    
    update_product(state["product_id"], name=new_name)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تعديل اسم المنتج بنجاح!**\n\n"
                    f"الاسم الجديد: {new_name}")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_description")
def process_edit_product_description(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    new_description = message.text.strip()
    
    if new_description.lower() == "حذف":
        new_description = ""
    
    update_product(state["product_id"], description=new_description)
    
    if new_description:
        bot.send_message(message.chat.id,
                        f"✅ **تم تعديل وصف المنتج بنجاح!**\n\n"
                        f"الوصف الجديد: {new_description[:100]}...")
    else:
        bot.send_message(message.chat.id,
                        "✅ **تم حذف وصف المنتج بنجاح!**")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_price")
def process_edit_product_price(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    try:
        new_price = float(message.text)
        if new_price <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للسعر.")
        return
    
    update_product(state["product_id"], price=new_price)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تعديل سعر المنتج بنجاح!**\n\n"
                    f"السعر الجديد: {new_price} IQD")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_wholesale")
def process_edit_product_wholesale(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    wholesale_text = message.text.strip()
    
    if wholesale_text.lower() == "حذف":
        new_wholesale_price = None
    else:
        try:
            new_wholesale_price = float(wholesale_text)
            if new_wholesale_price <= 0:
                bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح أكبر من صفر.")
                return
        except:
            bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للسعر.")
            return
    
    update_product(state["product_id"], wholesale_price=new_wholesale_price)
    
    if new_wholesale_price is None:
        bot.send_message(message.chat.id,
                        "✅ **تم حذف سعر الجملة بنجاح!**")
    else:
        bot.send_message(message.chat.id,
                        f"✅ **تم تعديل سعر الجملة بنجاح!**\n\n"
                        f"سعر الجملة الجديد: {new_wholesale_price} IQD")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_quantity")
def process_edit_product_quantity(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    product_id = state["product_id"]
    product = state["product_data"]
    
    # جميع المتاجر مفتوحة - يمكن تعديل الكمية مباشرة
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    try:
        new_quantity = int(message.text)
        if new_quantity < 0:
            bot.send_message(message.chat.id, "الرجاء إدخال كمية صحيحة (صفر أو أكبر).")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للكمية.")
        return
    
    update_product(state["product_id"], quantity=new_quantity)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تعديل كمية المنتج بنجاح!**\n\n"
                    f"الكمية الجديدة: {new_quantity}")
    
    del user_states[telegram_id]
    show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_image")
@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_product_image")
def process_edit_product_image(message):
    """معالجة تحديث الصورة مع خيارات واضحة"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    if message.text == "📸 إرسال صورة جديدة":
        user_states[telegram_id]["step"] = "waiting_for_new_product_image"
        bot.send_message(message.chat.id, "📤 الرجاء إرسال الصورة الجديدة الآن:")
        return
    
    elif message.text == "🗑️ حذف الصورة الحالية":
        try:
            product_id = state["product_id"]
            
            # حذف من imagestorage
            conn = get_db_connection()
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute('DELETE FROM imagestorage WHERE productid=%s', (product_id,))
            else:
                cursor.execute("DELETE FROM imagestorage WHERE ProductID=?", (product_id,))
            conn.commit()
            conn.close()
            print(f"✅ تم حذف الصور من imagestorage للمنتج {product_id}")
            
            # تحديث Products (للتوافق)
            update_product(product_id, image_path="")
            
        except Exception as e:
            print(f"⚠️ خطأ في حذف الصورة: {e}")
        
        bot.send_message(message.chat.id,
                        "✅ **تم حذف صورة المنتج بنجاح!**")
        
        del user_states[telegram_id]
        show_seller_menu(message)
        return
    
    elif message.text == "⏭️ إلغاء":
        bot.send_message(message.chat.id,
                        "❌ **تم إلغاء تغيير الصورة**")
        
        del user_states[telegram_id]
        show_seller_menu(message)
        return

@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "waiting_for_new_product_image")
def handle_new_product_image_photo(message):
    """معالج تحديث صورة المنتج - نفس منطق Flutter"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    product_id = state["product_id"]
    
    try:
        # ✅ حفظ الصورة في ImageStorage والحصول على اسم الملف
        filename = save_photo_from_message(message)
        if not filename:
            bot.send_message(message.chat.id, "⚠️ حدث خطأ في حفظ الصورة، لم يتم تغيير الصورة.")
            del user_states[telegram_id]
            show_seller_menu(message)
            return
        
        # ✅ حذف الصور القديمة للمنتج (إن وجدت)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # حذف الروابط القديمة من imagestorage
            if IS_POSTGRES:
                cursor.execute('DELETE FROM imagestorage WHERE productid=%s', (product_id,))
            else:
                cursor.execute("DELETE FROM imagestorage WHERE ProductID=?", (product_id,))
            
            conn.commit()
            conn.close()
            print(f"✅ تم حذف الصور القديمة للمنتج {product_id}")
        except Exception as e:
            print(f"⚠️ خطأ في حذف الصور القديمة: {e}")
        
        # ✅ إضافة الصورة الجديدة في ProductImages
        try:
            image_id = add_product_image_db(product_id, filename, 0)
            print(f"✅ [ProductImages] تم إضافة صورة جديدة: ImageID={image_id}, Filename={filename}")
        except Exception as e:
            print(f"⚠️ خطأ في إضافة الصورة في ProductImages: {e}")
        
        # ✅ تحديث Products لم يعد ضروري (الصور الآن في ProductImages)
        # لكن نحتفظ بـ ImagePath للتوافق مع الأنظمة القديمة
        update_product(product_id, image_path=filename)
        
        bot.send_message(message.chat.id,
                        "✅ **تم تغيير صورة المنتج بنجاح!**\n\n"
                        f"📁 {filename}\n"
                        "الصورة الجديدة ستظهر الآن في عرض المنتج.")
        
    except Exception as e:
        print(f"❌ خطأ في معالجة الصورة الجديدة: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, "⚠️ حدث خطأ في معالجة الصورة.")
    
    finally:
        if telegram_id in user_states:
            del user_states[telegram_id]
        show_seller_menu(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "waiting_for_new_product_image" and 
                     message.content_type == 'text')
def handle_new_product_image_text(message):
    telegram_id = message.from_user.id
    if message.text == "🏠 الرئيسية":
        if telegram_id in user_states:
            del user_states[telegram_id]
        handle_main_menu(message)
        return

    if message.text.lower() in ['إلغاء', 'الغاء', 'cancel']:
        bot.send_message(message.chat.id, "❌ **تم إلغاء تغيير الصورة**")
        telegram_id = message.from_user.id
        del user_states[telegram_id]
        show_seller_menu(message)
    else:
        bot.send_message(message.chat.id, "⚠️ الرجاء إرسال صورة أو كتابة 'إلغاء'.")

# ====== عرض منتجات المتجر ======
@bot.message_handler(func=lambda message: message.text == "🏪 منتجاتي" and is_seller(message.from_user.id))
def view_my_products(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    categories = get_categories(seller[0])
    
    if not categories:
        bot.send_message(message.chat.id, 
                        "📭 **لا توجد أقسام بعد**\n\nيجب إنشاء قسم واحد على الأقل قبل إضافة المنتجات.",
                        reply_markup=types.InlineKeyboardMarkup().add(
                            types.InlineKeyboardButton("➕ إضافة قسم", callback_data="dashboard_add_cat"),
                            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")
                        ))
        return
    
    all_products = []
    
    for category_id, category_name in categories:
        products = get_products(seller_id=seller[0], category_id=category_id)
        if products:
            all_products.append((category_name, products))
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_products:
        text = "📭 **لا توجد منتجات حالياً**\n\nيمكنك إضافة منتجات جديدة باستخدام الأزرار أدناه."
    else:
        text = "🏪 **قائمة منتجاتك**\n\nاضغط على المنتج لعرض التفاصيل والتحكم به:\n"
        for category_name, products in all_products:
            # Optional: Add category header
            # markup.add(types.InlineKeyboardButton(f"--- {category_name} ---", callback_data="ignore"))
            
            for product in products:
                # Product tuple: (ProductID, Name, Description, Price, ...)
                pid = product[0]
                name = product[1]
                price = product[3]
                markup.add(types.InlineKeyboardButton(f"📦 {name} - {price}", callback_data=f"view_prod_{pid}"))
    
    # Add Control Buttons (Always Visible)
    markup.add(types.InlineKeyboardButton("➕ إضافة منتج", callback_data="dashboard_add_prod"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="back_to_menu"))
    
    # Hide menu first (ensure we are in a clean state)
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.row("🏠 الرئيسية")
    bot.send_message(message.chat.id, "🔄 **جاري الحصول على المنتجات...**", reply_markup=menu_markup)
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_prod_"))
def handle_view_product_detail(call):
    try:
        product_id = int(call.data.split("_")[2])
        # Direct DB Call (Tuple)
        product = get_product_by_id(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, "المنتج غير موجود")
            return
            
        print(f"DEBUG PRODUCT DATA: {product}") # Debugging

            
        # Structure: ProductID(0), SellerID(1), CategoryID(2), Name(3), Description(4), Price(5), WholesalePrice(6), Quantity(7), ImagePath(8)
        
        pid = product[0]
        name = product[3]
        desc = product[4]
        price = product[5]
        wholesale_price = product[6]
        qty = product[7]
        img_path = product[8]
        
        text = f"📦 **{name}**\n\n"
        text += f"💰 السعر: {price} IQD\n"
        if wholesale_price:
            text += f"💰 سعر الجملة: {wholesale_price} IQD\n"
        text += f"📦 الكمية: {qty}\n"
        if desc: text += f"📝 الوصف: {desc}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        
        # Check if viewer is the seller/admin (Owner)
        # We need seller_id of the product.
        seller = get_seller_by_id(product[1]) # product[1] is SellerID
        is_owner = False
        
        if seller and seller[1] == call.from_user.id:
             is_owner = True
        elif str(call.from_user.id) == str(BOT_ADMIN_ID): # Global Admin can edit everything? Maybe.
             # For now, stick to seller ownership
             if seller and seller[1] == call.from_user.id:
                 is_owner = True

        if is_owner:
            # Owner View: Edit/Delete
            markup.add(
                types.InlineKeyboardButton("➕ إضافة جديد", callback_data="dashboard_add_prod"),
                types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_product_{pid}"),
                types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_product_{pid}")
            )
        else:
            # Buyer View: Add to Cart
            # Always allow buying, even from Admin store
            # Reuse logic from create_product_markup_with_qty
            markup.row(
                types.InlineKeyboardButton("➖", callback_data=f"qty_dec_{pid}_1"),
                types.InlineKeyboardButton("1", callback_data="noop"),
                types.InlineKeyboardButton("➕", callback_data=f"qty_inc_{pid}_1")
            )
            markup.add(types.InlineKeyboardButton(f"🛒 أضف 1 للسلة", callback_data=f"addtocart_{pid}_1"))

        markup.add(types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_prod_list"))

        # Try to resolve valid image path
        final_img_data = None  # Changed from final_img_path to handle binary data
        
        if img_path:
            # 1. Try to get image from cloud (ImageStorage table)
            if IS_POSTGRES:
                filename = os.path.basename(img_path)
                cloud_data = get_image_from_cloud(filename)
                if cloud_data:
                    final_img_data = cloud_data
                    print(f"✅ Got image from cloud: {filename} ({len(cloud_data)} bytes)")
            
            # 2. If not found in cloud, check local file
            if not final_img_data:
                if os.path.exists(img_path):
                    final_img_path = img_path
                else:
                    # Check local Images folder (Fix for OS path mismatch)
                    filename = os.path.basename(img_path)
                    local_path = os.path.join(IMAGES_FOLDER, filename)
                    if os.path.exists(local_path):
                        final_img_path = local_path
                    else:
                        # Lazy Download from Cloud if missing
                        print(f"⚠️ Image found in DB but missing locally: {filename}. Attempting download...")
                        if download_image_from_cloud(filename):
                            if os.path.exists(local_path):
                                final_img_path = local_path
                                print(f"✅ Successfully downloaded {filename}")
                            else:
                                print(f"❌ Download reported success but file still missing: {local_path}")
                        else:
                            print(f"❌ Failed to download {filename} from cloud.")
                
                # Load local file as binary if exists
                if 'final_img_path' in locals() and final_img_path:
                    try:
                        with open(final_img_path, 'rb') as f:
                            final_img_data = f.read()
                    except Exception as e:
                        print(f"❌ Error reading local image: {e}")

        if final_img_data:
            try:
                from io import BytesIO
                photo = BytesIO(final_img_data)
                bot.send_photo(call.message.chat.id, photo, caption=text, parse_mode='Markdown', reply_markup=markup)
            except Exception as img_error:
                print(f"⚠️ Error sending photo for product {pid}: {img_error}")
                bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
            
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in view_prod: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ أثناء عرض المنتج")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_prod_list")
def back_to_product_list(call):
    # Call view_my_products but passing the message correctly
    call.message.from_user.id = call.from_user.id
    view_my_products(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_product_"))
def handle_delete_product_direct(call):
    try:
        product_id = int(call.data.split("_")[2])
        # Confirm deletion
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_delete_prod_{product_id}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data=f"view_prod_{product_id}")
        )
        # Handle different message types (Photo vs Text)
        if call.message.content_type == 'photo':
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                "⚠️ **هل أنت متأكد من حذف هذا المنتج؟**\nسيتم حذفه من القائمة نهائياً.",
                parse_mode='Markdown',
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ **هل أنت متأكد من حذف هذا المنتج؟**\nسيتم حذفه من القائمة نهائياً.",
                parse_mode='Markdown',
                reply_markup=markup
            )
            
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in delete product direct: {e}")
        # Show actual error to user for debugging
        bot.answer_callback_query(call.id, f"حدث خطأ: {str(e)[:50]}", show_alert=True)

# ====== ربط أزرار لوحة التحكم بالوظائف الموجودة ======
class MockMessage:
    def __init__(self, chat, from_user, text):
        self.chat = chat
        self.from_user = from_user
        self.text = text
        self.content_type = 'text'
        self.is_mock = True

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_add_prod")
def bridge_add_product(call):
    # استخدام MockMessage لضمان تمرير كائن المستخدم الصحيح (الذي ضغط الزر)
    # بدلاً من كائن البوت الموجود في call.message original
    mock_msg = MockMessage(call.message.chat, call.from_user, "➕ إضافة منتج")
    add_product_step1(mock_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_del_prod")
def bridge_delete_product(call):
    # دالة الحذف تستخدم call مباشرة، لذا يجب أن تعمل إذا كان الـ id صحيحاً
    # سنتأكد من تمرير الـ call كما هو
    handle_delete_product_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_add_cat")
def bridge_add_category(call):
    print(f"\n{'='*60}")
    print(f"🔵 bridge_add_category تم استدعاؤه")
    print(f"   User: {call.from_user.id}")
    print(f"   Chat ID: {call.message.chat.id}")
    print(f"{'='*60}")
    mock_msg = MockMessage(call.message.chat, call.from_user, "➕ إضافة قسم")
    print(f"📝 MockMessage تم إنشاؤه: is_mock={mock_msg.is_mock}")
    add_category_step1(mock_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "dashboard_edit_cat")
def bridge_edit_category(call):
    # Fix: Call the list menu, not the specific handler
    mock_msg = MockMessage(call.message.chat, call.from_user, "✏️ تعديل قسم")
    view_edit_category_menu(mock_msg)
    bot.answer_callback_query(call.id)


# ====== زر نسخ رابط المتجر ======
@bot.message_handler(func=lambda message: message.text == "🔗 رابط المتجر" and (is_seller(message.from_user.id) or is_bot_admin(message.from_user.id)))
def get_store_link(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "لم يتم العثور على معلومات المتجر.")
        return
    
    store_name = seller[3]
    store_link = generate_store_link(telegram_id)
    
    if not store_link:
        bot.send_message(message.chat.id, "⚠️ تعذر توليد رابط المتجر.")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 نسخ رابط المتجر", callback_data=f"copy_store_link_{telegram_id}"))
    
    bot.send_message(message.chat.id,
                    f"🔗 **رابط متجرك**\n\n"
                    f"🏪 المتجر: {store_name}\n\n"
                    f"**الرابط:**\n`{store_link}`\n\n"
                    f"يمكنك مشاركة هذا الرابط مع عملائك لزيارة متجرك.",
                    reply_markup=markup,
                    parse_mode='Markdown')

# ====== نظام كشف حساب الزبائن الآجل مع الحدود ======
@bot.message_handler(func=lambda message: message.text == "📊 كشف حساب الزبائن" and is_seller(message.from_user.id))
def customer_credit_dashboard(message):
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    customers = get_all_customers_with_balance(seller[0])
    
    if not customers:
        bot.send_message(message.chat.id, "📭 لا يوجد زبائن لهم رصيد آجل حالياً.")
        return
    
    text = f"💰 **كشف حساب الزبائن الآجل**\n🏪 المتجر: {seller[3]}\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    total_balance = 0
    total_max_credit = 0
    total_used_credit = 0
    
    for customer in customers:
        customer_id, full_name, phone, created_at, balance, max_credit, current_used, limit_active = customer
        total_balance += balance
        total_max_credit += max_credit
        total_used_credit += current_used
        
        text += f"👤 **{full_name}**\n"
        text += f"📞 {phone if phone else 'لا يوجد'}\n"
        text += f"💰 الرصيد: {balance} IQD\n"
        
        if limit_active == 1:
            percentage_used = (current_used / max_credit * 100) if max_credit > 0 else 0
            if percentage_used >= 100:
                status = "❌ ممتلئ"
            elif percentage_used >= 80:
                status = "⚠️ تحذير"
            else:
                status = "✅ جيد"
            
            text += f"💳 الحد الائتماني: {max_credit:,.0f} دينار\n"
            text += f"📊 المستخدم: {current_used:,.0f} دينار ({percentage_used:.1f}%) {status}\n"
        
        text += "────\n\n"
        
        markup.add(types.InlineKeyboardButton(f"👤 {full_name[:10]}", callback_data=f"view_customer_statement_{customer_id}"))
    
    text += f"\n💰 **إجمالي المديونيات:** {total_balance} IQD"
    text += f"\n💳 **إجمالي الحدود:** {total_max_credit:,.0f} دينار"
    text += f"\n📊 **إجمالي المستخدم:** {total_used_credit:,.0f} دينار"
    
    percentage_total = (total_used_credit / total_max_credit * 100) if total_max_credit > 0 else 0
    text += f"\n📈 **نسبة الاستخدام:** {percentage_total:.1f}%"
    
    markup.add(types.InlineKeyboardButton("➕ تسجيل دفعة", callback_data="record_payment"))
    markup.add(types.InlineKeyboardButton("💳 إدارة الحدود", callback_data="manage_credit_limits"))
    markup.add(types.InlineKeyboardButton("📊 الإحصائيات", callback_data="credit_stats"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🏪 إدارة الزبائن الآجلين" and is_seller(message.from_user.id))
def manage_credit_customers_new(message):
    try:
        print(f"\n[MANAGE_CREDIT_CUSTOMERS] Received message from {message.from_user.id}: {message.text}")
        
        telegram_id = message.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        
        print(f"[MANAGE_CREDIT_CUSTOMERS] Seller lookup: {seller}")
        
        if not seller:
            print(f"[MANAGE_CREDIT_CUSTOMERS] No seller found for telegram_id={telegram_id}")
            bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        print(f"[MANAGE_CREDIT_CUSTOMERS] Seller found: SellerID={seller[0]}")
        customers = get_all_credit_customers(seller[0])
        print(f"[MANAGE_CREDIT_CUSTOMERS] Got {len(customers) if customers else 0} customers")
        
        if not customers:
            print(f"[MANAGE_CREDIT_CUSTOMERS] No customers found, showing empty message")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("➕ إضافة زبون آجل", callback_data="add_credit_customer"))
            bot.send_message(message.chat.id, "📭 لا يوجد زبائن آجلين مسجلين.\n\nيمكنك إضافة زبون آجل جديد:", reply_markup=markup)
            return
        
        # إرسال رسالة الترحيب
        bot.send_message(message.chat.id, "🏪 الزبائن الآجلين\n\n" + "=" * 30)
        
        # إرسال كل زبون مع أزراره في رسالة منفصلة
        for customer in customers:
            if len(customer) >= 10:
                customer_id, seller_id, full_name, phone, telegram_id_cust, customer_type, created_at, max_credit, current_used, limit_active = customer[:10]
            else:
                # Fallback for old format (without TelegramID)
                customer_id, seller_id, full_name, phone, customer_type, created_at, max_credit, current_used, limit_active = customer[:9]
                telegram_id_cust = None
            
            # معلومات الزبون - الاسم والنوع والحد الائتماني
            text = f"👤 {full_name}\n"
            
            # عرض نوع الزبون
            type_emoji = "🏪" if customer_type == "RetailPoint" else "👤"
            type_name = "نقطة بيع" if customer_type == "RetailPoint" else "زبون آجل"
            text += f"{type_emoji} {type_name}\n"
            
            if limit_active == 1 or limit_active == True:
                percentage_used = (current_used / max_credit * 100) if max_credit > 0 else 0
                text += f"💳 الحد: {max_credit:,.0f} دينار ({percentage_used:.1f}%)"
            
            # أزرار الزبون الثلاث في نفس السطر
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_credit_customer_{customer_id}"),
                types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_credit_customer_{customer_id}"),
                types.InlineKeyboardButton("💳 الحد", callback_data=f"set_credit_limit_{customer_id}")
            )
            
            print(f"[MANAGE_CREDIT_CUSTOMERS] Sending customer: {full_name}")
            bot.send_message(message.chat.id, text, reply_markup=markup)
        
        # إرسال أزرار الإضافة والرجوع في الأسفل
        markup_footer = types.InlineKeyboardMarkup()
        markup_footer.add(types.InlineKeyboardButton("➕ إضافة زبون جديد", callback_data="add_credit_customer"))
        markup_footer.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
        
        bot.send_message(message.chat.id, "=" * 30, reply_markup=markup_footer)
        print(f"[MANAGE_CREDIT_CUSTOMERS] Completed successfully\n")
        
    except Exception as e:
        print(f"\n[ERROR] manage_credit_customers_new failed: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

# ====== معالجات إضافة زبون آجل جديد ======

@bot.callback_query_handler(func=lambda call: call.data == "add_credit_customer")
def handle_add_credit_customer(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    user_states[telegram_id] = {
        "step": "select_customer_type",
        "seller_id": seller[0]
    }
    
    # عرض خيارات نوع الزبون
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("👤 زبون آجل (مفرد)", callback_data="type_creditcustomer"),
        types.InlineKeyboardButton("🏪 نقطة بيع (جملة)", callback_data="type_retailpoint")
    )
    markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="back_to_credit_menu"))
    
    bot.send_message(call.message.chat.id,
                    "👤 إضافة زبون جديد\n\n"
                    "الخطوة 1️⃣: اختر نوع الزبون",
                    reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
def process_select_customer_type(call):
    telegram_id = call.from_user.id
    
    if telegram_id not in user_states or user_states[telegram_id]["step"] != "select_customer_type":
        bot.answer_callback_query(call.id, "⛔ جلسة غير صحيحة")
        return
    
    if call.data == "type_creditcustomer":
        user_states[telegram_id]["customer_type"] = "CreditCustomer"
        type_name = "زبون آجل"
    elif call.data == "type_retailpoint":
        user_states[telegram_id]["customer_type"] = "RetailPoint"
        type_name = "نقطة بيع"
    else:
        bot.answer_callback_query(call.id, "⛔ اختيار غير صحيح")
        return
    
    user_states[telegram_id]["step"] = "add_customer_name"
    
    bot.send_message(call.message.chat.id,
                    f"👤 إضافة {type_name}\n\n"
                    f"الخطوة 2️⃣: أدخل اسم الزبون")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_customer_name")
def process_add_customer_name(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    full_name = message.text.strip()
    if not full_name:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم صحيح!")
        return
    
    # حفظ الاسم والانتقال للخطوة التالية: طلب Telegram ID
    user_states[telegram_id]["customer_name"] = full_name
    user_states[telegram_id]["step"] = "add_customer_telegram_id"
    
    customer_type = state.get("customer_type", "CreditCustomer")
    type_display = "زبون آجل" if customer_type == "CreditCustomer" else "نقطة بيع"
    
    bot.send_message(message.chat.id,
                    f"👤 إضافة {type_display}\n\n"
                    f"✅ الاسم: {full_name}\n\n"
                    f"الخطوة 3️⃣: أدخل **Telegram ID** الزبون\n\n"
                    f"💡 **كيفية الحصول على الـ ID:**\n"
                    f"1. اطلب من الزبون فتح أي محادثة معك\n"
                    f"2. اضغط على اسم الزبون في أعلى المحادثة\n"
                    f"3. ستجد رقم مثل: `123456789`\n"
                    f"4. انسخ وألصق الرقم هنا\n\n"
                    f"أو اكتب `0` للتخطي (يمكن إضافته لاحقاً)",
                    parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "add_customer_telegram_id")
def process_add_customer_telegram_id(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    customer_telegram_id_input = message.text.strip()
    customer_name = state.get("customer_name", "")
    customer_type = state.get("customer_type", "CreditCustomer")
    type_display = "زبون آجل" if customer_type == "CreditCustomer" else "نقطة بيع"
    seller_id = state["seller_id"]
    
    # تحويل الـ ID أو تعيين None إذا كان 0
    customer_telegram_id = None
    if customer_telegram_id_input and customer_telegram_id_input != "0":
        try:
            customer_telegram_id = int(customer_telegram_id_input)
            if customer_telegram_id < 0:
                raise ValueError("ID سالب")
        except ValueError:
            bot.send_message(message.chat.id, "⚠️ الرجاء إدخال رقم صحيح أو `0` للتخطي!")
            return
    
    try:
        # إضافة الزبون مع Telegram ID
        customer_id = add_credit_customer(
            seller_id, 
            customer_name, 
            phone_number=None, 
            customer_type=customer_type, 
            telegram_id=customer_telegram_id
        )
        
        # رسالة النجاح
        id_text = f"🆔 ID: {customer_telegram_id}" if customer_telegram_id else "🆔 ID: لم يتم إدخاله (يمكن إضافته لاحقاً)"
        
        bot.send_message(message.chat.id,
                        f"✅ **تم إضافة الزبون بنجاح!**\n\n"
                        f"👤 الاسم: {customer_name}\n"
                        f"📦 النوع: {type_display}\n"
                        f"{id_text}\n\n"
                        f"💡 يمكنك الآن تعيين حد ائتماني له")
        del user_states[telegram_id]
        manage_credit_customers_new(message)
    except Exception as e:
        print(f"Error adding credit customer: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id,
                        f"❌ **حدث خطأ:**\n{str(e)}")
        del user_states[telegram_id]


# ====== معالجة Callback Queries العامة ======

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_my_statement_"))
def handle_view_my_statement(call):
    parts = call.data.split("_")
    seller_id = int(parts[3])
    customer_id = int(parts[4])
    
    seller = get_seller_by_id(seller_id)
    if not seller:
        bot.answer_callback_query(call.id, "المتجر غير موجود")
        return
    
    statement = get_customer_statement(customer_id, seller_id, limit=15)
    
    if not statement:
        bot.answer_callback_query(call.id, "لا توجد معاملات لديك مع هذا المتجر")
        return
    
    current_balance = get_customer_balance(customer_id, seller_id)
    limit_info = get_credit_limit_info(customer_id, seller_id)
    
    text = f"📊 **كشف حسابك مع المتجر**\n\n"
    text += f"🏪 المتجر: {seller[3]}\n"
    text += f"💰 الرصيد الحالي: {current_balance} IQD\n"
    text += f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
    text += f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
    text += f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n"
    text += f"🚨 الحالة: {limit_info['status']}\n\n"
    text += f"📋 **آخر 15 معاملة:**\n\n"
    
    for trans in statement:
        trans_type, amount, description, balance_before, balance_after, trans_date = trans
        
        trans_type_arabic = {
            'purchase': 'شراء',
            'payment': 'دفعة',
            'adjustment': 'تعديل'
        }.get(trans_type, trans_type)
        
        emoji = "🛒" if trans_type == 'purchase' else "💰" if trans_type == 'payment' else "📝"
        
        text += f"{emoji} **{trans_type_arabic}**\n"
        text += f"📅 {trans_date}\n"
        text += f"💵 المبلغ: {amount} IQD\n"
        
        if description:
            text += f"📝 {description}\n"
        
        text += f"💰 الرصيد: {balance_after} IQD\n"
        text += "────\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 العودة للقائمة", callback_data="back_to_my_credit"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_my_credit")
def handle_back_to_my_credit(call):
    my_credit_statement(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_customer_phone")
def process_edit_customer_phone(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    new_phone = message.text.strip()
    
    if new_phone.lower() in ["حذف", "delete", "none", "null"]:
        new_phone = None
    elif not new_phone:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم هاتف صحيح أو اكتب 'حذف' لحذف رقم الهاتف.")
        return
    
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    success = update_credit_customer(customer_id, seller_id, phone_number=new_phone)
    
    if success:
        phone_display = new_phone if new_phone else "تم الحذف"
        bot.send_message(message.chat.id, f"✅ **تم تحديث رقم الهاتف بنجاح!**\n\n📞 رقم الهاتف الجديد: {phone_display}")
    else:
        bot.send_message(message.chat.id, "⚠️ **حدث خطأ**\n\nتعذر تحديث رقم الهاتف.")
    
    del user_states[telegram_id]
    
    # إعادة عرض تفاصيل الزبون
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer = cursor.fetchone()
    conn.close()
    
    if customer:
        customer_id, seller_id, full_name, phone, created_at = customer
        text = f"👤 **معلومات الزبون الآجل**\n\n"
        text += f"🆔 معرف الزبون: {customer_id}\n"
        text += f"👤 الاسم: {full_name}\n"
        text += f"📞 الهاتف: {phone if phone else 'غير محدد'}\n"
        text += f"📅 تاريخ الإضافة: {created_at}\n\n"
        
        balance = get_customer_balance(customer_id, seller_id)
        text += f"💰 **الرصيد الحالي:** {balance} IQD\n"
        
        limit_info = get_credit_limit_info(customer_id, seller_id)
        text += f"💳 **الحد الائتماني:** {limit_info['max_limit']:,.0f} دينار\n"
        text += f"📊 **المستخدم:** {limit_info['current_used']:,.0f} دينار\n"
        text += f"📈 **المتبقي:** {limit_info['available']:,.0f} دينار\n"
        text += f"🚨 **الحالة:** {limit_info['status']}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 كشف حساب", callback_data=f"view_customer_statement_{customer_id}"),
            types.InlineKeyboardButton("💰 تسجيل دفعة", callback_data=f"select_customer_payment_{customer_id}"),
            types.InlineKeyboardButton("💳 إدارة الحد", callback_data=f"set_credit_limit_{customer_id}"),
            types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_credit_customer_{customer_id}"),
            types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_credit_customer_{customer_id}")
        )
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "delete_credit_customer_list")
def handle_delete_credit_customer_list(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    customers = get_all_credit_customers(seller[0])
    
    if not customers:
        bot.answer_callback_query(call.id, "لا يوجد زبائن آجلين للحذف")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for customer in customers:
        customer_id, seller_id, full_name, phone, created_at, max_credit, current_used, limit_active = customer
        markup.add(types.InlineKeyboardButton(f"🗑️ {full_name}", callback_data=f"delete_credit_customer_{customer_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.send_message(call.message.chat.id, "🗑️ **اختر الزبون الذي تريد حذفه:**", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_credit_customer_"))
def handle_edit_credit_customer(call):
    """تعديل بيانات زبون آجل"""
    try:
        customer_id = int(call.data.split("_")[-1])
        telegram_id = call.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        customer = cursor.fetchone()
        conn.close()
        
        if not customer:
            bot.answer_callback_query(call.id, "الزبون غير موجود")
            return
        
        customer_id, seller_id, full_name, phone, telegram_id_cust, customer_type, created_at = customer[:7]
        
        text = f"✏️ **تعديل بيانات الزبون**\n\n"
        text += f"👤 **الاسم الحالي:** {full_name}\n"
        text += f"📞 **الهاتف الحالي:** {phone if phone else 'غير محدد'}\n\n"
        text += "الرجاء إدخال الاسم الجديد للزبون:"
        
        user_states[telegram_id] = {
            "step": "edit_customer_name",
            "customer_id": customer_id,
            "seller_id": seller_id
        }
        
        bot.send_message(call.message.chat.id, text)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_edit_credit_customer: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء المعالجة")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "edit_customer_name")
def process_edit_customer_name(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    new_name = message.text.strip()
    if not new_name:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم صحيح!")
        return
    
    try:
        update_credit_customer(customer_id, seller_id, full_name=new_name)
        bot.send_message(message.chat.id, f"✅ تم تحديث بيانات الزبون بنجاح!\n\n👤 الاسم الجديد: {new_name}")
        del user_states[telegram_id]
        manage_credit_customers_new(message)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")
        del user_states[telegram_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_credit_limit_"))
def handle_set_credit_limit(call):
    """تعيين الحد الائتماني للزبون"""
    try:
        customer_id = int(call.data.split("_")[-1])
        telegram_id = call.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        customer = cursor.fetchone()
        conn.close()
        
        if not customer:
            bot.answer_callback_query(call.id, "الزبون غير موجود")
            return
        
        customer_id, seller_id, full_name, phone, telegram_id_cust, customer_type, created_at = customer[:7]
        
        # الحصول على الحد الحالي
        limit_info = get_credit_limit_info(customer_id, seller_id)
        current_limit = limit_info['max_limit']
        current_used = limit_info['current_used']
        
        text = f"💳 **تعيين الحد الائتماني**\n\n"
        text += f"👤 **الزبون:** {full_name}\n"
        text += f"💰 **الحد الحالي:** {current_limit:,.0f} دينار\n"
        text += f"📊 **المستخدم:** {current_used:,.0f} دينار\n\n"
        text += "الرجاء إدخال الحد الائتماني الجديد (رقم):\n"
        text += "مثال: 5000000"
        
        user_states[telegram_id] = {
            "step": "set_limit_amount",
            "customer_id": customer_id,
            "seller_id": seller_id
        }
        
        bot.send_message(call.message.chat.id, text)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_set_credit_limit: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء المعالجة")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "set_limit_amount")
def process_set_limit_amount(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    try:
        new_limit = float(message.text.strip())
        if new_limit <= 0:
            bot.send_message(message.chat.id, "⚠️ الحد الائتماني يجب أن يكون رقماً موجباً!")
            return
        
        set_credit_limit(customer_id, seller_id, new_limit)
        bot.send_message(message.chat.id, f"✅ تم تحديث الحد الائتماني بنجاح!\n\n💳 الحد الجديد: {new_limit:,.0f} دينار")
        del user_states[telegram_id]
        manage_credit_customers_new(message)
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال رقم صحيح!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")
        del user_states[telegram_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_credit_customer_"))
def handle_delete_credit_customer(call):
    try:
        customer_id = int(call.data.split("_")[-1])
        telegram_id = call.from_user.id
        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=%s AND SellerID=%s", (customer_id, seller[0]))
        else:
            cursor.execute("SELECT * FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        
        customer = cursor.fetchone()
        
        if not customer:
            bot.answer_callback_query(call.id, "الزبون غير موجود")
            conn.close()
            return
        
        customer_id, seller_id, full_name = customer[0], customer[1], customer[2]
        
        text = f"🗑️ **حذف الزبون**\n\n"
        text += f"👤 **الاسم:** {full_name}\n\n"
        text += "هل أنت متأكد من حذف هذا الزبون؟"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_delete_credit_customer_{customer_id}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data="add_credit_customer")
        )
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        conn.close()
    except Exception as e:
        print(f"Error in handle_delete_credit_customer: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء المعالجة")
        if 'conn' in locals():
            conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_credit_customer_"))
def handle_confirm_delete_credit_customer(call):
    customer_id = int(call.data.split("_")[-1])
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # الحصول على معلومات الزبون قبل الحذف
        if IS_POSTGRES:
            cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=%s AND SellerID=%s", (customer_id, seller[0]))
        else:
            cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        
        customer_info = cursor.fetchone()
        customer_name = customer_info[0] if customer_info else "الزبون"
        
        # حذف البيانات المرتبطة بالزبون
        if IS_POSTGRES:
            cursor.execute("DELETE FROM CustomerCredit WHERE CustomerID=%s", (customer_id,))
            cursor.execute("DELETE FROM CreditLimits WHERE CustomerID=%s", (customer_id,))
            cursor.execute("DELETE FROM CreditCustomers WHERE CustomerID=%s AND SellerID=%s", (customer_id, seller[0]))
        else:
            cursor.execute("DELETE FROM CustomerCredit WHERE CustomerID=?", (customer_id,))
            cursor.execute("DELETE FROM CreditLimits WHERE CustomerID=?", (customer_id,))
            cursor.execute("DELETE FROM CreditCustomers WHERE CustomerID=? AND SellerID=?", (customer_id, seller[0]))
        
        conn.commit()
        
        bot.answer_callback_query(call.id, "✅ تم حذف الزبون بنجاح")
        bot.edit_message_text(f"✅ **تم حذف الزبون بنجاح!**\n\n👤 الزبون: {customer_name}", 
                             call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        
        # إعادة عرض قائمة الزبائن بعد ثانية واحدة
        import time
        time.sleep(1)
        manage_credit_customers_new(call.message)
        
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء الحذف")
        print(f"Delete Credit Customer Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("request_access_"))
def handle_request_access(call):
    """معالج طلب الوصول للمتجر المقفول - يطلب من الزبون إدخال اسمه"""
    telegram_id = call.from_user.id
    
    try:
        parts = call.data.split("_")
        seller_id = int(parts[2])
        
        # حفظ حالة الطلب
        user_states[telegram_id] = {
            "step": "request_access_name",
            "seller_id": seller_id,
            "customer_telegram_id": telegram_id
        }
        
        seller = get_seller_by_id(seller_id)
        store_name = seller[3] if seller else "المتجر"
        
        bot.send_message(call.message.chat.id,
                        f"👤 طلب الوصول - {store_name}\n\n"
                        f"الخطوة 1️⃣: أدخل اسمك الكامل\n\n"
                        f"سيتم إرسال طلبك إلى البائع للمراجعة",
                        parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_request_access: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "request_access_name")
def process_request_access_name(message):
    """معالجة إدخال اسم الزبون في طلب الوصول"""
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    full_name = message.text.strip()
    if not full_name:
        bot.send_message(message.chat.id, "⚠️ الرجاء إدخال اسم صحيح!")
        return
    
    seller_id = state["seller_id"]
    customer_telegram_id = state["customer_telegram_id"]
    
    try:
        # إضافة الزبون مع حفظ Telegram ID الخاص به
        customer_id = add_credit_customer(
            seller_id, 
            full_name, 
            phone_number=None, 
            customer_type='CreditCustomer',  # افتراضي للطلبات
            telegram_id=customer_telegram_id  # ⭐ حفظ Telegram ID
        )
        
        if customer_id:
            # إرسال إشعار للبائع
            seller = get_seller_by_id(seller_id)
            if seller:
                seller_telegram_id = seller[1]
                bot.send_message(seller_telegram_id,
                                f"🔔 **طلب وصول جديد**\n\n"
                                f"👤 الاسم: {full_name}\n"
                                f"🆔 Telegram ID: {customer_telegram_id}\n\n"
                                f"تم إضافة الزبون تلقائياً. يمكنه الآن الوصول للمتجر.",
                                parse_mode='Markdown')
            
            # رسالة للزبون
            bot.send_message(message.chat.id,
                            f"✅ **تم إرسال طلبك بنجاح!**\n\n"
                            f"👤 الاسم: {full_name}\n\n"
                            f"🎉 تم إضافتك كزبون. يمكنك الآن الدخول للمتجر!\n\n"
                            f"💡 جرب الآن: اختر المتجر من قائمة المتاجر",
                            parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "⚠️ فشل في معالجة الطلب. حاول لاحقاً")
        
        del user_states[telegram_id]
    except Exception as e:
        print(f"Error in process_request_access_name: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")
        del user_states[telegram_id]

@bot.callback_query_handler(func=lambda call: call.data == "record_payment")
def handle_record_payment(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.answer_callback_query(call.id, "⛔ أنت لست بائعاً مسجلاً!")
        return
    
    customers = get_all_customers_with_balance(seller[0])
    
    if not customers:
        bot.answer_callback_query(call.id, "لا يوجد زبائن لهم رصيد آجل")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for customer in customers:
        customer_id, full_name, phone, created_at, balance, max_credit, current_used, limit_active = customer
        display_name = full_name
        markup.add(types.InlineKeyboardButton(f"👤 {display_name} - {balance} IQD", callback_data=f"select_customer_payment_{customer_id}"))
    
    bot.send_message(call.message.chat.id, "👤 **اختر الزبون لتسجيل دفعة:**", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_customer_payment_"))
def handle_select_customer_payment(call):
    customer_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    user_states[telegram_id] = {
        "step": "record_payment_amount",
        "customer_id": customer_id,
        "seller_id": seller[0]
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName, PhoneNumber FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    current_balance = get_customer_balance(customer_id, seller[0])
    
    # الحصول على معلومات الحد الائتماني
    limit_info = get_credit_limit_info(customer_id, seller[0])
    
    bot.send_message(call.message.chat.id,
                    f"💰 **تسجيل دفعة للزبون**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"💰 الرصيد الحالي: {current_balance} IQD\n"
                    f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
                    f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
                    f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n\n"
                    f"يرجى إدخال مبلغ الدفعة (بالدينار العراقي):")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "record_payment_amount")
def process_payment_amount(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    try:
        amount = float(message.text)
        if amount <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال مبلغ صحيح أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للمبلغ.")
        return
    
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    
    current_balance = get_customer_balance(customer_id, seller_id)
    
    if amount > current_balance:
        bot.send_message(message.chat.id,
                        f"⚠️ **تحذير:** المبلغ المدخل ({amount} IQD) أكبر من الرصيد الحالي ({current_balance} IQD)\n\n"
                        f"هل تريد المتابعة؟ (اكتب 'نعم' للموافقة أو 'لا' للإلغاء)")
        
        user_states[telegram_id]["step"] = "confirm_payment"
        user_states[telegram_id]["amount"] = amount
        return
    
    # تسجيل الدفعة
    add_credit_transaction(customer_id, seller_id, 'payment', amount, f"دفعة نقدية من الزبون")
    
    new_balance = get_customer_balance(customer_id, seller_id)
    limit_info = get_credit_limit_info(customer_id, seller_id)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تسجيل الدفعة بنجاح!**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"💰 المبلغ: {amount} IQD\n"
                    f"💰 الرصيد السابق: {current_balance} IQD\n"
                    f"💰 الرصيد الجديد: {new_balance} IQD\n"
                    f"💳 الحد المتبقي: {limit_info['available']:,.0f} دينار")
    
    del user_states[telegram_id]
    customer_credit_dashboard(message)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "confirm_payment")
def confirm_payment(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    if message.text == "🏠 الرئيسية":
        del user_states[telegram_id]
        handle_main_menu(message)
        return
    
    if message.text.lower() not in ['نعم', 'yes']:
        bot.send_message(message.chat.id, "❌ تم إلغاء تسجيل الدفعة.")
        del user_states[telegram_id]
        customer_credit_dashboard(message)
        return
    
    amount = state["amount"]
    customer_id = state["customer_id"]
    seller_id = state["seller_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    
    current_balance = get_customer_balance(customer_id, seller_id)
    
    add_credit_transaction(customer_id, seller_id, 'payment', amount, f"دفعة نقدية من الزبون (مبلغ زائد)")
    
    new_balance = get_customer_balance(customer_id, seller_id)
    limit_info = get_credit_limit_info(customer_id, seller_id)
    
    bot.send_message(message.chat.id,
                    f"✅ **تم تسجيل الدفعة بنجاح!**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"💰 المبلغ: {amount} IQD\n"
                    f"💰 الرصيد السابق: {current_balance} IQD\n"
                    f"💰 الرصيد الجديد: {new_balance} IQD\n"
                    f"💳 الحد المتبقي: {limit_info['available']:,.0f} دينار\n\n"
                    f"⚠️ **ملاحظة:** الزبون لديه رصيد ائتماني بقيمة {-new_balance} IQD")
    
    del user_states[telegram_id]
    customer_credit_dashboard(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_customer_statement_"))
def handle_view_customer_statement(call):
    customer_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT FullName, PhoneNumber FROM CreditCustomers WHERE CustomerID=?", (customer_id,))
    customer_info = cursor.fetchone()
    conn.close()
    
    customer_name = customer_info[0] if customer_info else "الزبون"
    customer_phone = customer_info[1] if customer_info and customer_info[1] else "غير متوفر"
    
    statement = get_customer_statement(customer_id, seller[0], limit=20)
    
    if not statement:
        bot.answer_callback_query(call.id, "لا توجد معاملات لهذا الزبون")
        return
    
    current_balance = get_customer_balance(customer_id, seller[0])
    limit_info = get_credit_limit_info(customer_id, seller[0])
    
    text = f"📊 **كشف حساب الزبون**\n\n"
    text += f"👤 الزبون: {customer_name}\n"
    text += f"📞 الهاتف: {customer_phone}\n"
    text += f"💰 الرصيد الحالي: {current_balance} IQD\n"
    text += f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
    text += f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
    text += f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n"
    text += f"🚨 الحالة: {limit_info['status']}\n\n"
    text += f"📋 **آخر 20 معاملة:**\n\n"
    
    for trans in statement:
        trans_type, amount, description, balance_before, balance_after, trans_date = trans
        
        trans_type_arabic = {
            'purchase': 'شراء',
            'payment': 'دفعة',
            'adjustment': 'تعديل'
        }.get(trans_type, trans_type)
        
        emoji = "🛒" if trans_type == 'purchase' else "💰" if trans_type == 'payment' else "📝"
        
        text += f"{emoji} **{trans_type_arabic}**\n"
        text += f"📅 {trans_date}\n"
        text += f"💵 المبلغ: {amount} IQD\n"
        
        if description:
            text += f"📝 {description}\n"
        
        text += f"💰 الرصيد: {balance_after} IQD\n"
        text += "────\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ تسجيل دفعة", callback_data=f"select_customer_payment_{customer_id}"))
    markup.add(types.InlineKeyboardButton("💳 إدارة الحد", callback_data=f"set_credit_limit_{customer_id}"))
    markup.add(types.InlineKeyboardButton("📋 العودة للقائمة", callback_data="back_to_credit_menu"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "credit_stats")
def handle_credit_stats(call):
    telegram_id = call.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    customers = get_all_customers_with_balance(seller[0])
    
    if not customers:
        bot.answer_callback_query(call.id, "لا يوجد زبائن لهم رصيد آجل")
        return
    
    total_balance = 0
    positive_balance = 0
    negative_balance = 0
    customer_count = len(customers)
    
    total_max_credit = 0
    total_used_credit = 0
    active_limits = 0
    
    for customer in customers:
        balance = customer[4]
        max_credit = customer[5]
        current_used = customer[6]
        limit_active = customer[7]
        
        total_balance += balance
        
        if balance > 0:
            positive_balance += balance
        else:
            negative_balance += balance
        
        if limit_active == 1:
            active_limits += 1
            total_max_credit += max_credit
            total_used_credit += current_used
    
    text = f"📊 **إحصائيات الائتمان**\n🏪 المتجر: {seller[3]}\n\n"
    text += f"👥 عدد الزبائن: {customer_count}\n"
    text += f"💳 عدد الحدود النشطة: {active_limits}\n"
    text += f"💰 إجمالي المديونيات: {positive_balance} IQD\n"
    text += f"💳 إجمالي الرصيد الائتماني: {-negative_balance} IQD\n"
    text += f"⚖️ صافي الرصيد: {total_balance} IQD\n\n"
    
    if active_limits > 0:
        text += f"📈 **إحصائيات الحدود:**\n"
        text += f"• إجمالي الحدود المسموحة: {total_max_credit:,.0f} دينار\n"
        text += f"• إجمالي المبالغ المستخدمة: {total_used_credit:,.0f} دينار\n"
        text += f"• نسبة الاستخدام: {(total_used_credit/total_max_credit*100 if total_max_credit > 0 else 0):.1f}%\n\n"
    
    if positive_balance > 0:
        text += f"📋 **أكبر المديونيات:**\n"
        sorted_customers = sorted(customers, key=lambda x: x[4], reverse=True)[:5]
        
        for customer in sorted_customers:
            customer_id, full_name, phone, created_at, balance = customer[:5]
            if balance > 0:
                display_name = full_name
                text += f"• {display_name}: {balance} IQD\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_credit_menu")
def handle_back_to_credit_menu(call):
    customer_credit_dashboard(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == "💰 كشف حسابي الآجل")
def my_credit_statement(message):
    telegram_id = message.from_user.id
    user = get_user(telegram_id)
    
    if not user:
        bot.send_message(message.chat.id, "⚠️ لم يتم العثور على بياناتك.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT s.SellerID, s.StoreName, 
               COALESCE((
                   SELECT cc.FullName 
                   FROM CreditCustomers cc 
                   WHERE cc.PhoneNumber = ? AND cc.SellerID = s.SellerID
                   LIMIT 1
               ), (
                   SELECT cc.FullName 
                   FROM CreditCustomers cc 
                   WHERE cc.FullName LIKE ? AND cc.SellerID = s.SellerID
                   LIMIT 1
               )) as CustomerName,
               COALESCE((
                   SELECT cc.CustomerID 
                   FROM CreditCustomers cc 
                   WHERE cc.PhoneNumber = ? AND cc.SellerID = s.SellerID
                   LIMIT 1
               ), (
                   SELECT cc.CustomerID 
                   FROM CreditCustomers cc 
                   WHERE cc.FullName LIKE ? AND cc.SellerID = s.SellerID
                   LIMIT 1
               )) as CustomerID
        FROM Sellers s
        WHERE EXISTS (
            SELECT 1 FROM CreditCustomers cc 
            WHERE cc.SellerID = s.SellerID 
            AND (cc.PhoneNumber = ? OR cc.FullName LIKE ?)
        )
    """, (user[4], f"%{user[5]}%", user[4], f"%{user[5]}%", user[4], f"%{user[5]}%"))
    
    sellers_with_customers = cursor.fetchall()
    conn.close()
    
    if not sellers_with_customers:
        bot.send_message(message.chat.id, "💰 **حسابك الآجل**\n\nليس لديك أي مديونيات أو رصيد ائتماني حالياً.")
        return
    
    text = f"💰 **كشف حسابك الآجل**\n👤 {user[5] if user[5] else user[2]}\n\n"
    
    total_balance = 0
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for seller_id, store_name, customer_name, customer_id in sellers_with_customers:
        if customer_id:
            balance = get_customer_balance(customer_id, seller_id)
            total_balance += balance
            
            limit_info = get_credit_limit_info(customer_id, seller_id)
            
            text += f"🏪 **{store_name}**\n"
            text += f"💰 الرصيد: {balance} IQD\n"
            
            if balance > 0:
                text += f"📋 **مدين بمبلغ:** {balance} IQD\n"
            elif balance < 0:
                text += f"💳 **لديك رصيد ائتماني:** {-balance} IQD\n"
            else:
                text += f"✅ **حسابك متوازن**\n"
            
            text += f"💳 **الحد الائتماني:** {limit_info['max_limit']:,.0f} دينار\n"
            text += f"📊 **المستخدم:** {limit_info['current_used']:,.0f} دينار\n"
            text += f"📈 **المتبقي:** {limit_info['available']:,.0f} دينار\n"
            text += f"🚨 **الحالة:** {limit_info['status']}\n"
            
            text += "────\n\n"
            
            if balance != 0 or limit_info['available'] < limit_info['max_limit']:
                markup.add(types.InlineKeyboardButton(f"📊 كشف حساب {store_name}", callback_data=f"view_my_statement_{seller_id}_{customer_id}"))
    
    text += f"💰 **إجمالي الرصيد:** {total_balance} IQD"
    
    if total_balance > 0:
        text += f"\n📋 **إجمالي المديونيات:** {total_balance} IQD"
    elif total_balance < 0:
        text += f"\n💳 **إجمالي الرصيد الائتماني:** {-total_balance} IQD"
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_my_statement_"))
def handle_view_my_statement(call):
    parts = call.data.split("_")
    seller_id = int(parts[3])
    customer_id = int(parts[4])
    
    seller = get_seller_by_id(seller_id)
    if not seller:
        bot.answer_callback_query(call.id, "المتجر غير موجود")
        return
    
    statement = get_customer_statement(customer_id, seller_id, limit=15)
    
    if not statement:
        bot.answer_callback_query(call.id, "لا توجد معاملات لديك مع هذا المتجر")
        return
    
    current_balance = get_customer_balance(customer_id, seller_id)
    limit_info = get_credit_limit_info(customer_id, seller_id)
    
    text = f"📊 **كشف حسابك مع المتجر**\n\n"
    text += f"🏪 المتجر: {seller[3]}\n"
    text += f"💰 الرصيد الحالي: {current_balance} IQD\n"
    text += f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
    text += f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
    text += f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n"
    text += f"🚨 الحالة: {limit_info['status']}\n\n"
    text += f"📋 **آخر 15 معاملة:**\n\n"
    
    for trans in statement:
        trans_type, amount, description, balance_before, balance_after, trans_date = trans
        
        trans_type_arabic = {
            'purchase': 'شراء',
            'payment': 'دفعة',
            'adjustment': 'تعديل'
        }.get(trans_type, trans_type)
        
        emoji = "🛒" if trans_type == 'purchase' else "💰" if trans_type == 'payment' else "📝"
        
        text += f"{emoji} **{trans_type_arabic}**\n"
        text += f"📅 {trans_date}\n"
        text += f"💵 المبلغ: {amount} IQD\n"
        
        if description:
            text += f"📝 {description}\n"
        
        text += f"💰 الرصيد: {balance_after} IQD\n"
        text += "────\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 العودة للقائمة", callback_data="back_to_my_credit"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_my_credit")
def handle_back_to_my_credit(call):
    my_credit_statement(call.message)
    bot.answer_callback_query(call.id)

# ====== معالجة Callback Queries العامة ======

# ====== حذف الطلب وتحديث الكميات ======
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_order_"))
def handle_delete_order(call):
    try:
        order_id = int(call.data.split("_")[2])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get Order Items to restore quantity (subtract already returned items)
        if IS_POSTGRES:
            cursor.execute("SELECT ProductID, (Quantity - COALESCE(ReturnedQuantity, 0)) FROM OrderItems WHERE OrderID = %s", (order_id,))
        else:
            cursor.execute("SELECT ProductID, (Quantity - COALESCE(ReturnedQuantity, 0)) FROM OrderItems WHERE OrderID = ?", (order_id,))
            
        items = cursor.fetchall()
        
        # 2. Restore Quantities
        for item in items:
            pid, qty = item
            if IS_POSTGRES:
                cursor.execute("UPDATE Products SET Quantity = Quantity + %s WHERE ProductID = %s", (qty, pid))
            else:
                cursor.execute("UPDATE Products SET Quantity = Quantity + ? WHERE ProductID = ?", (qty, pid))
                
        # 3. Delete Order (Cascades to OrderItems usually, but safe to delete items first if no cascade)
        # Assuming CASCADE or manual deletion. Let's delete items first to be safe.
        # 3. Delete Order (Delete children first to avoid FK constraints)
        if IS_POSTGRES:
            cursor.execute("DELETE FROM Messages WHERE OrderID = %s", (order_id,))
            cursor.execute("DELETE FROM OrderItems WHERE OrderID = %s", (order_id,))
            # Check for Returns if any
            cursor.execute("DELETE FROM Returns WHERE OrderID = %s", (order_id,))
            cursor.execute("DELETE FROM Orders WHERE OrderID = %s", (order_id,))
            
        else:
            cursor.execute("DELETE FROM Messages WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM OrderItems WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM Returns WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM Orders WHERE OrderID = ?", (order_id,))
            
        # Capture rowcount before closing connection
        deleted_count = cursor.rowcount
            
        conn.commit()
        conn.close()
        
        # 4. Update View
        if deleted_count > 0:
            bot.answer_callback_query(call.id, "✅ تم حذف الطلب واعادة الكميات")
            bot.edit_message_text(
                f"🗑️ **تم حذف الطلب #{order_id}**\n\nتم إعادة الكميات للمخزن.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=None
            )
        else:
            bot.answer_callback_query(call.id, f"⚠️ لم يتم العثور على الطلب #{order_id}", show_alert=True)
            bot.edit_message_text(
                f"⚠️ **الطلب #{order_id} غير موجود**\n\nربما تم حذفه مسبقاً.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=None
            )
        
    except Exception as e:
        print(f"Error deleting order: {e}")
        bot.answer_callback_query(call.id, f"خطأ: {str(e)[:50]}", show_alert=True)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        call_data = call.data
        print(f"\n{'='*60}")
        print(f"🔍 CALLBACK RECEIVED: '{call_data}'")
        print(f"{'='*60}\n")
        
        # تخطي معالجات الزبائن الآجلين لأنها موجودة كمعالجات منفصلة
        if (call.data.startswith("edit_credit_customer_") or 
            call.data.startswith("edit_customer_name_") or 
            call.data.startswith("edit_customer_phone_") or
            call.data.startswith("delete_credit_customer_") or
            call.data.startswith("confirm_delete_credit_customer_") or
            call.data == "delete_credit_customer_list"):
            # هذه المعالجات موجودة كمعالجات منفصلة قبل هذا المعالج
            return
        
        if call.data.startswith("copy_store_link_"):
            handle_copy_store_link(call)
        elif call.data == "create_admin_store":
            handle_create_admin_store(call)
        elif call.data == "admin_mode_only":
            handle_admin_mode_only(call)
        elif call.data.startswith("toggle_store_reg_"):
            handle_toggle_store_registration(call)
        elif call.data.startswith("viewcat_"):
            print(f"✅ MATCHED: viewcat_ handler will be called")
            print(f"✅ استدعاء handle_view_category مع callback data: {call.data}")
            handle_view_category(call)
        elif call.data.startswith("back_to_categories_"):
            handle_back_to_categories(call)
        elif call.data == "list_active_stores":
            list_active_stores_callback(call)
        elif call.data == "list_suspended_stores":
            list_suspended_stores_callback(call)
        elif call.data == "suspend_store_menu":
            suspend_store_menu(call)
        elif call.data.startswith("suspend_store_"):
            suspend_store_selected(call)
        elif call.data == "activate_store_menu":
            activate_store_menu(call)
        elif call.data.startswith("activate_store_"):
            activate_store_selected(call)
        elif call.data == "add_new_category":
            handle_add_new_category(call)
        elif call.data == "go_to_edit_category":
            handle_go_to_edit_category(call)
        elif call.data.startswith("edit_cat_"):
            handle_edit_category(call)
        elif call.data.startswith("select_category_"):
            handle_select_category_for_product(call)
        elif call.data.startswith("edit_product_"):
            handle_select_product_to_edit(call)
        elif call.data.startswith("edit_prod_"):
            handle_edit_product_field(call)
        elif call.data.startswith("select_new_cat_"):
            handle_select_new_category(call)
        elif call.data == "back_to_menu":
            handle_back_to_menu(call)
        elif call.data == "seller_main_menu":
            handle_back_to_menu(call)  # Same as back_to_menu for sellers
        elif call.data == "back_to_edit_product":
            handle_back_to_edit_product(call)
        elif call.data.startswith("contact_buyer_"):
            handle_contact_buyer(call)
        elif call.data.startswith("order_details_"):
            handle_order_details(call)
        elif call.data.startswith("confirm_order_"):
            handle_confirm_order_seller(call)
        elif call.data.startswith("ship_order_"):
            handle_ship_order(call)
        elif call.data.startswith("deliver_order_"):
            handle_deliver_order(call)
        elif call.data.startswith("reject_order_"):
            handle_reject_order(call)
        elif call.data.startswith("view_return_"):
            handle_view_return(call)
        elif call.data.startswith("approve_return_"):
            handle_approve_return(call)
        elif call.data.startswith("reject_return_"):
            handle_reject_return(call)
        elif call.data.startswith("viewstore_"):
            handle_view_store(call)
        elif call.data.startswith("manage_store_reg_"):
            handle_manage_store_registration(call)
        elif call.data.startswith("toggle_store_reg_"):
            handle_toggle_store_registration(call)
        elif call.data.startswith("back_to_categories_"):
            handle_back_to_categories(call)
        elif call.data.startswith("select_images_"):
            handle_select_images(call)
        elif call.data.startswith("buy_images_"):
            handle_buy_images(call)
        elif call.data == "cancel_image_selection":
            handle_cancel_image_selection(call)
        elif call.data.startswith("manage_product_images_"):
            handle_manage_product_images(call)
        elif call.data.startswith("add_product_image_"):
            handle_add_product_image(call)
        elif call.data.startswith("del_img_"):
            handle_delete_product_image(call)
        elif call.data.startswith("delete_product_image_"):
            handle_delete_product_image(call)
        elif call.data.startswith("addtocart_"):
            handle_add_to_cart(call)
        elif call.data == "back_to_returns":
            handle_back_to_returns(call)
        elif call.data.startswith("return_details_"):
            handle_return_details(call)
        elif call.data.startswith("process_return_"):
            handle_process_return(call)
        elif call.data == "checkout_cart":
            handle_checkout_cart(call)
        elif call.data == "clear_cart":
            handle_clear_cart(call)
        elif call.data == "edit_cart_quantities":
            handle_edit_cart_quantities(call)
        elif call.data.startswith("increase_cart_"):
            handle_increase_cart(call)
        elif call.data.startswith("decrease_cart_"):
            handle_decrease_cart(call)
        elif call.data.startswith("remove_cart_"):
            handle_remove_cart(call)
        elif call.data.startswith("set_quantity_"):
            handle_set_quantity(call)
        elif call.data.startswith("skip_seller_"):
             handle_skip_seller(call)
        elif call.data.startswith("payment_cash_"):
             handle_payment_cash(call)
        elif call.data in ["edit_name", "edit_phone"]:
            handle_edit_user_info(call)
        elif call.data.startswith("customer_type_"):
            handle_customer_type(call)
        # ملاحظة: معالجات delete_credit_customer_ و edit_credit_customer_ موجودة كمعالجات منفصلة قبل هذا المعالج
        else:
            bot.answer_callback_query(call.id, "هذا الزر غير نشط حالياً")
    except Exception as e:
        print(f"❌ ERROR in callback_handler: {e}")
        traceback.print_exc()
        try:
            bot.answer_callback_query(call.id, f"حدث خطأ: {str(e)[:50]}")
        except:
            pass

def list_active_stores_callback(call):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, 
               CASE WHEN s.Status = 'active' THEN '✅' ELSE '⏸️' END as StatusIcon
        FROM Sellers s
        WHERE s.Status = 'active'
        ORDER BY s.StoreName
    """)
    stores = cursor.fetchall()
    conn.close()
    
    if not stores:
        bot.answer_callback_query(call.id, "لا توجد متاجر نشطة")
        return
    
    text = "📋 **قائمة المتاجر النشطة**\n\n"
    
    for store in stores:
        seller_id, telegram_id, username, store_name, created_at, status = store[:6]
        status_icon = store[6] if len(store) > 6 else ""
        
        safe_store_name = escape_markdown_v1(store_name)
        
        text += f"{status_icon} **المتجر:** {safe_store_name}\n"
        text += f"👤 {format_seller_mention(username, telegram_id)}\n"
        text += f"🆔 المعرف: {telegram_id}\n"
        text += f"📅 تاريخ الإنشاء: {created_at}\n"
        text += "────\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def list_suspended_stores_callback(call):
    suspended_stores = get_suspended_sellers()
    
    if not suspended_stores:
        bot.answer_callback_query(call.id, "لا توجد متاجر معلقة")
        return
    
    text = "⚠️ **قائمة المتاجر المعلقة**\n\n"
    
    for store in suspended_stores:
        seller_id, telegram_id, username, store_name = store[:4]
        reason = store[6] if store[6] else "غير محدد"
        suspended_at = store[8]
        suspender_name = store[9] if store[9] else "غير معروف"
        
        safe_store_name = escape_markdown_v1(store_name)
        safe_reason = escape_markdown_v1(reason)
        
        text += f"⏸️ **المتجر:** {safe_store_name}\n"
        text += f"👤 {format_seller_mention(username, telegram_id)}\n"
        text += f"🆔 المعرف: {telegram_id}\n"
        text += f"📋 السبب: {safe_reason}\n"
        text += f"👮 معلق بواسطة: {escape_markdown_v1(suspender_name)}\n"
        text += f"⏰ تاريخ التعليق: {suspended_at}\n"
        text += "────\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def suspend_store_menu(call):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.SellerID, s.StoreName, s.UserName, s.TelegramID
        FROM Sellers s
        WHERE s.Status = 'active'
        ORDER BY s.StoreName
    """)
    active_stores = cursor.fetchall()
    conn.close()
    
    if not active_stores:
        bot.answer_callback_query(call.id, "لا توجد متاجر نشطة")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for store in active_stores:
        store_id, store_name, username, telegram_id = store
        label = f"{store_name} - {format_seller_mention(username, telegram_id)}"
        markup.add(types.InlineKeyboardButton(
            label,
            callback_data=f"suspend_store_{store_id}"
        ))
    
    bot.send_message(call.message.chat.id, "⚠️ **اختر المتجر لتعليقه:**", reply_markup=markup)
    bot.answer_callback_query(call.id)

def suspend_store_selected(call):
    store_id = int(call.data.split("_")[2])
    
    user_states[call.from_user.id] = {
        "step": "suspend_store_reason",
        "store_id": store_id
    }
    
    bot.send_message(call.message.chat.id,
                    "📝 **سبب التعليق**\n\n"
                    "يرجى إدخال سبب تعليق المتجر:")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "suspend_store_reason")
def process_suspend_reason(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    store_id = state["store_id"]
    reason = message.text
    
    suspend_seller(store_id, user_id, reason)
    
    bot.send_message(message.chat.id, f"✅ تم تعليق المتجر بنجاح")
    
    del user_states[user_id]
    
    if is_bot_admin(message.from_user.id):
        show_bot_admin_menu(message)
    else:
        show_admin_dashboard(message)

def activate_store_menu(call):
    suspended_stores = get_suspended_sellers()
    
    if not suspended_stores:
        bot.answer_callback_query(call.id, "لا توجد متاجر معلقة")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for store in suspended_stores:
        store_id = store[0]
        store_name = store[3]
        username = store[2]
        reason = store[6] if store[6] else "غير محدد"
        
        label = f"{store_name} - {format_seller_mention(username, store_id)}"
        markup.add(types.InlineKeyboardButton(
            label,
            callback_data=f"activate_store_{store_id}"
        ))
    
    bot.send_message(call.message.chat.id, "▶️ **اختر المتجر لتنشيطه:**", reply_markup=markup)
    bot.answer_callback_query(call.id)

def activate_store_selected(call):
    store_id = int(call.data.split("_")[2])
    
    activate_seller(store_id, call.from_user.id)
    
    bot.answer_callback_query(call.id, "✅ تم تنشيط المتجر بنجاح")
    
    bot.send_message(call.message.chat.id, "✅ تم تنشيط المتجر بنجاح")

# ====== معالجة المتاجر والعرض ======
# تم حذف متجر TELEBOT - الآن يتم الاتصال المباشر مع المتاجر المغلقة
def send_store_catalog_by_telegram_id(chat_id, seller_telegram_id, customer_telegram_id=None):
    """إرسال كتالوج المتجر - يتطلب تسجيل الزبون في CreditCustomers إذا كان الإعداد مفعلاً"""
    
    try:
        print(f"🔍 send_store_catalog_by_telegram_id: seller_telegram_id={seller_telegram_id}, customer_telegram_id={customer_telegram_id}")
        
        # Ensure customer exists in Users table (required for Foreign Key constraint in Carts)
        if customer_telegram_id:
            print(f"[DEBUG] send_store_catalog: Checking customer {customer_telegram_id}...")
            user = get_user(customer_telegram_id)
            if not user:
                print(f"[INFO] Customer {customer_telegram_id} not found in Users table. Creating user entry...")
                try:
                    user_created = add_user(customer_telegram_id, None, 'buyer', None, None)
                    if not user_created:
                        print(f"[ERROR] Failed to create user entry for customer {customer_telegram_id}")
                    else:
                        # Small delay to ensure database commit is complete
                        import time
                        time.sleep(0.2)
                        
                        # Verify user was created
                        user = get_user(customer_telegram_id)
                        if user:
                            print(f"[SUCCESS] Created and verified user entry for customer {customer_telegram_id}")
                        else:
                            print(f"[WARNING] User {customer_telegram_id} still not found after creation")
                except Exception as user_error:
                    print(f"[ERROR] Failed to create user entry: {user_error}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[OK] Customer {customer_telegram_id} exists in Users table")
        
        seller = get_seller_by_telegram(seller_telegram_id)
        print(f"✅ get_seller_by_telegram returned: {seller is not None}")
    except Exception as e:
        print(f"❌ Error in send_store_catalog_by_telegram_id: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, f"⚠️ حدث خطأ في فتح المتجر: {str(e)}")
        return
    
    # seller هو tuple: (SellerID, TelegramID, UserName, StoreName, ...)
    # التحقق من أن البائع موجود
    if not seller:
        bot.send_message(chat_id, "⚠️ المتجر غير موجود.")
        return
    
    # seller هو tuple: (SellerID, TelegramID, UserName, StoreName, Created, Status, ...)
    # استخراج البيانات من tuple
    seller_id = seller[0]
    seller_telegram_id = seller[1]
    username = seller[2] if len(seller) > 2 else "بائع"
    store_name = seller[3] if len(seller) > 3 else "متجر"
    # Status عادة في seller[5]، لكن RequireCustomerRegistration قد يكون في seller[9]
    require_registration = seller[9] if len(seller) > 9 else 0
    
    print(f"🔐 متجر معرف: {store_name}, require_registration={require_registration}, customer_id={customer_telegram_id}, seller_id={seller_telegram_id}")
    print(f"🔐 المقارنة: customer_id({type(customer_telegram_id).__name__})={customer_telegram_id} != seller_id({type(seller_telegram_id).__name__})={seller_telegram_id}")
    
    # التحقق من أن المستخدم مسجل في CreditCustomers لهذا المتجر (فقط إذا كان الإعداد مفعلاً)
    # استثناء: صاحب المتجر نفسه يمكنه الدخول دائماً
    customer_is_registered = True  # افتراضياً: مسجل
    
    if require_registration:
        print(f"✅ المتجر مقفول - البحث عن التسجيل")
        
        if not customer_telegram_id:
            print(f"⚠️ تحذير: customer_telegram_id = None - زبون غير معروف")
            customer_is_registered = False
        elif customer_telegram_id == seller_telegram_id:
            print(f"✅ صاحب المتجر - السماح بالدخول كاملاً")
            customer_is_registered = True
        else:
            print(f"✅ فحص التسجيل: يجب التحقق من تسجيل الزبون {customer_telegram_id}")
            # التحقق من Telegram ID مباشرة
            is_registered = is_customer_registered_for_store_by_telegram_id(customer_telegram_id, seller_id)
            print(f"⚠️ نتيجة التحقق: is_registered={is_registered}")
            customer_is_registered = is_registered
    else:
        print(f"ℹ️ المتجر مفتوح - لا حاجة للتحقق من التسجيل")
        customer_is_registered = True
    
    categories = get_categories(seller_id)
    print(f"DEBUG: Categories found: {len(categories) if categories else 0}")
    
    if not categories:
        print(f"DEBUG: No categories, fetching products directly for seller_id={seller_id}")
        
        # إذا لم يكن مسجلاً، أظهر رسالة رفض بدل المنتجات
        if require_registration and not customer_is_registered:
            print(f"❌ زبون غير مسجل بدون فئات - رسالة رفض")
            bot.send_message(chat_id,
                f"🏪 **{store_name}**\n👤 البائع: {format_seller_mention(username, seller_id)}\n\n"
                f"⚠️ **نعتذر، المتجر مغلق**\n\n"
                f"حساب ك غير مسجل في هذا المتجر.\n"
                f"يرجى التواصل مع البائع للتسجيل.",
                parse_mode='Markdown')
            return
        
        products = get_products(seller_id=seller_id)
        print(f"DEBUG: Products found: {len(products) if products else 0}")
        
        if not products:
            bot.send_message(chat_id, f"🏪 **{store_name}**\n👤 البائع: {format_seller_mention(username, seller_id)}\n\nالمتجر فارغ حالياً.")
            return
        
        bot.send_message(chat_id, f"🏪 **{store_name}**\n👤 البائع: {format_seller_mention(username, seller_id)}\n\n🛍️ المنتجات المتاحة:")
        
        # ⚡ إرسال المنتجات بسرعة (بدون صور لتجنب timeout)
        for product in products:
            pid, name, desc, price, wholesale_price, qty, img_path = product
            print(f"DEBUG: Displaying product {pid}: {name}, qty={qty}")
            if qty > 0:
                # إرسال رسالة نصية سريعة بدل الصورة
                caption = f"🛒 **{name}**\n💰 السعر: {price} IQD"
                if wholesale_price and wholesale_price > 0:
                    caption += f"\n💰 سعر الجملة: {wholesale_price} IQD"
                caption += f"\n📦 متاح: {qty}"
                if desc:
                    caption += f"\n📝 {desc[:50]}{'...' if len(desc) > 50 else ''}"
                
                markup = types.InlineKeyboardMarkup()
                markup = create_product_markup_with_qty(pid, 1)
                bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')
    else:
        # عرض الفئات للجميع (مسجلين وغير مسجلين)
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cat_id, cat_name in categories:
            # حفظ معلومة ما إذا كان مسجلاً في callback_data
            # سنرسل customer_is_registered مع البيانات
            callback_data = f"viewcat_{cat_id}_{seller_id}"
            print(f"🔘 إضافة زر: '{cat_name}' مع callback: '{callback_data}'")
            markup.add(types.InlineKeyboardButton(cat_name, callback_data=callback_data))
        
        seller_display = format_seller_mention(username, seller_id)
        print(f"📤 إرسال كتالوج المتجر: {store_name} (seller_id={seller_id}, categories={len(categories)})")
        bot.send_message(chat_id, 
            f"🏪 **{store_name}**\n👤 البائع: {seller_display}\n\n📁 اختر القسم:", 
            reply_markup=markup, 
            parse_mode='Markdown')
    
    
    # إضافة قائمة الأزرار للمشتري بعد عرض المتجر
    if customer_telegram_id and customer_telegram_id != seller_telegram_id:
        try:
            print(f"🔍 DEBUG: Showing buyer buttons for customer: {customer_telegram_id}")
            # لا نستدعي show_buyer_main_menu() لأنها ترسل رسالة ترحيب
            # بدلاً من ذلك، نرسل الأزرار مباشرة
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒")
            markup.row("👤 تعديل بياناتي")
            
            bot.send_message(chat_id, "👇 يمكنك استخدام الأزرار أدناه:", reply_markup=markup)
            print(f"✅ DEBUG: Buyer buttons sent successfully")
        except Exception as e:
            print(f"❌ Error showing buyer buttons: {e}")
            import traceback
            traceback.print_exc()


# ====== زر الرجوع إلى الوضع الإداري ======
@bot.message_handler(func=lambda message: message.text == "الرجوع إلى الوضع الإداري 👑" and is_bot_admin(message.from_user.id))
def return_to_admin_mode(message):
    """العودة من وضع المشتري إلى قائمة الـ Admin"""
    telegram_id = message.from_user.id
    print(f"👑 Admin {telegram_id} returning to admin mode")
    show_bot_admin_menu(message)


@bot.message_handler(func=lambda message: message.text == "تصفح المتاجر 🛍️")
def browse_stores(message):
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    telegram_id = message.from_user.id
    is_admin = is_bot_admin(telegram_id)
    is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
    
    # إذا كان المستخدم جديداً (لم يختر تسجيل أو تصفح بدون تسجيل)، نسجله كزائر
    if not is_guest and telegram_id not in user_states and not is_admin:
        user = get_user(telegram_id)
        if not user:
            # المستخدم جديد تماماً، نسجله كزائر
            user_states[telegram_id] = {
                'is_guest': True,
                'name': message.from_user.first_name,
                'username': message.from_user.username
            }
            is_guest = True
    
    # عرض المتاجر
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TelegramID, UserName, StoreName 
        FROM Sellers 
        WHERE Status = 'active'
        ORDER BY StoreName
    """)
    sellers = cursor.fetchall()
    conn.close()
    
    if not sellers:
        bot.send_message(message.chat.id, "لا توجد متاجر متاحة حالياً.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for seller in sellers:
        try:
            seller_telegram_id, username, store_name = seller
            
            # Sanitize store name
            if not store_name or not store_name.strip():
                store_name = "متجر بدون اسم"
            
            # Replace replacement character if present
            store_name = store_name.replace('\ufffd', '?')
            
            label = f"🏪 {store_name} - {format_seller_mention(username, seller_telegram_id)}"
            markup.add(types.InlineKeyboardButton(
                label, 
                callback_data=f"viewstore_{seller_telegram_id}"
            ))
        except Exception as e:
            print(f"Skipping bad store: {e}")
            continue
    
    try:
        bot.send_message(message.chat.id, "🛍️ **المتاجر المتاحة:**", reply_markup=markup)
        
        # الأزرار تختلف حسب نوع المستخدم
        if is_admin:
            # زر الرجوع للوضع الإداري للـ admin
            markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup2.row("الرجوع إلى الوضع الإداري 👑")
        else:
            # أزرار المشتري العادي
            markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup2.row("تصفح المتاجر 🛍️", "سلة المشتريات 🛒")
            markup2.row("👤 تعديل بياناتي")
        
        bot.send_message(message.chat.id, "👇 استخدم الأزرار أدناه:", reply_markup=markup2)
    except Exception as e:
        print(f"Error sending stores list: {e}")
        bot.send_message(message.chat.id, "حدث خطأ في عرض قائمة المتاجر.")

def handle_view_store(call):
    try:
        print(f"DEBUG: handle_view_store called with data: {call.data}")
        data_parts = call.data.split("_")
        print(f"DEBUG: data_parts: {data_parts}")
        
        if len(data_parts) < 2:
            bot.answer_callback_query(call.id, "❌ بيانات غير صحيحة")
            return
            
        telegram_id = int(data_parts[1])
        customer_telegram_id = call.from_user.id
        
        print(f"DEBUG: telegram_id={telegram_id}, customer_telegram_id={customer_telegram_id}")
        
        # تأكيد تسجيل الزبون قبل عرض المتجر
        user = get_user(customer_telegram_id)
        if not user:
            print(f"[INFO] Creating new customer {customer_telegram_id}...")
            add_user(customer_telegram_id, call.from_user.username, 'buyer', None, call.from_user.first_name)
            import time
            time.sleep(0.1)
        
        # الآن عرض المتجر
        print(f"DEBUG: Calling send_store_catalog_by_telegram_id...")
        print(f"📊 PARAMS: chat_id={call.message.chat.id}, seller_telegram_id={telegram_id}, customer_telegram_id={customer_telegram_id}")
        send_store_catalog_by_telegram_id(call.message.chat.id, telegram_id, customer_telegram_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error in handle_view_store: {error_msg}")
        import traceback
        traceback.print_exc()
        bot.send_message(call.message.chat.id, f"❌ خطأ: {error_msg}")
        bot.answer_callback_query(call.id, "خطأ في عرض المتجر")


# Inline callbacks for buyer quick actions (useful for mobile clients)
@bot.callback_query_handler(func=lambda call: call.data == 'inline_open_cart')
def handle_inline_open_cart(call):
    try:
        # Open cart for the pressing user
        view_cart(call.message, user_id=call.from_user.id)
    except Exception as e:
        print(f"Error in handle_inline_open_cart: {e}")
    finally:
        try:
            bot.answer_callback_query(call.id)
        except:
            pass


@bot.callback_query_handler(func=lambda call: call.data == 'inline_edit_profile')
def handle_inline_edit_profile(call):
    try:
        # Show edit-profile menu for the pressing user (use call.from_user.id)
        send_edit_profile_menu(call.message.chat.id, call.from_user.id)
    except Exception as e:
        print(f"Error in handle_inline_edit_profile: {e}")
    finally:
        try:
            bot.answer_callback_query(call.id)
        except:
            pass

def handle_manage_store_registration(call):
    """إدارة إعداد قيد الدخول للمتجر"""
    try:
        seller_id = int(call.data.split("_")[3])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                SELECT SellerID, StoreName, COALESCE(RequireCustomerRegistration, 0) as RequireCustomerRegistration
                FROM Sellers WHERE SellerID=%s
            """, (seller_id,))
        else:
            cursor.execute("""
                SELECT SellerID, StoreName, COALESCE(RequireCustomerRegistration, 0) as RequireCustomerRegistration
                FROM Sellers WHERE SellerID=?
            """, (seller_id,))
        
        store = cursor.fetchone()
        conn.close()
        
        if not store:
            bot.answer_callback_query(call.id, "⚠️ المتجر غير موجود")
            return
        
        store_name = store[1]
        current_setting = store[2] if len(store) > 2 else 0
        
        text = f"🔐 **إدارة قيد الدخول للمتجر**\n\n"
        text += f"🏪 **المتجر:** {store_name}\n\n"
        text += f"**الحالة الحالية:**\n"
        if current_setting == 1:
            text += f"🔒 **مفعل** - المتجر مفتوح فقط للزبائن المسجلين في CreditCustomers\n\n"
            text += f"⚠️ **ملاحظة:** الزبائن غير المسجلين لن يتمكنوا من الوصول للمتجر."
        else:
            text += f"🔓 **معطل** - المتجر مفتوح للجميع\n\n"
            text += f"✅ **ملاحظة:** أي شخص يمكنه الوصول للمتجر بدون تسجيل."
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        if current_setting == 1:
            markup.add(types.InlineKeyboardButton("🔓 إلغاء قيد الدخول (فتح للجميع)", callback_data=f"toggle_store_reg_{seller_id}_0"))
        else:
            markup.add(types.InlineKeyboardButton("🔒 تفعيل قيد الدخول (الزبائن المسجلين فقط)", callback_data=f"toggle_store_reg_{seller_id}_1"))
        markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_stores_list"))
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_manage_store_registration: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

def handle_toggle_store_registration(call):
    """تفعيل/إلغاء قيد الدخول للمتجر"""
    try:
        parts = call.data.split("_")
        seller_id = int(parts[3])
        new_value = int(parts[4])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            cursor.execute("""
                UPDATE Sellers 
                SET RequireCustomerRegistration = %s 
                WHERE SellerID = %s
            """, (new_value, seller_id))
        else:
            cursor.execute("""
                UPDATE Sellers 
                SET RequireCustomerRegistration = ? 
                WHERE SellerID = ?
            """, (new_value, seller_id))
        
        conn.commit()
        
        # الحصول على اسم المتجر
        if IS_POSTGRES:
            cursor.execute("SELECT StoreName FROM Sellers WHERE SellerID=%s", (seller_id,))
        else:
            cursor.execute("SELECT StoreName FROM Sellers WHERE SellerID=?", (seller_id,))
        
        store_result = cursor.fetchone()
        store_name = store_result[0] if store_result else "المتجر"
        conn.close()
        
        status_text = "تم تفعيل قيد الدخول" if new_value == 1 else "تم إلغاء قيد الدخول"
        icon = "🔒" if new_value == 1 else "🔓"
        
        bot.answer_callback_query(call.id, f"✅ {status_text}")
        bot.send_message(call.message.chat.id, 
            f"{icon} **{status_text}**\n\n"
            f"🏪 المتجر: {store_name}\n\n"
            f"{'المتجر الآن مفتوح فقط للزبائن المسجلين في CreditCustomers' if new_value == 1 else 'المتجر الآن مفتوح للجميع'}",
            parse_mode='Markdown')
        
        # تحديث الرسالة السابقة
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass
    except Exception as e:
        print(f"Error in handle_toggle_store_registration: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_stores_list")
def handle_back_to_stores_list(call):
    """العودة لقائمة المتاجر"""
    if is_bot_admin(call.from_user.id):
        # إعادة عرض قائمة المتاجر
        message = call.message
        message.text = "📋 قائمة المتاجر"
        list_stores(message)
        bot.answer_callback_query(call.id)

def handle_view_category(call):
    try:
        print(f"\n{'='*60}")
        print(f"🔥 handle_view_category STARTED")
        print(f"📦 call.data = {call.data}")
        print(f"👤 Telegram User Info:")
        print(f"   call.from_user.id = {call.from_user.id}")
        print(f"   call.from_user.first_name = {call.from_user.first_name}")
        print(f"   call.from_user.last_name = {call.from_user.last_name}")
        print(f"   call.from_user.username = {call.from_user.username}")
        print(f"{'='*60}\n")
        
        parts = call.data.split("_")
        category_id = int(parts[1])
        seller_id = int(parts[2])
        
        print(f"✅ Parsed: category_id={category_id}, seller_id={seller_id}")
        
        category = get_category_by_id(category_id)
        print(f"🔍 get_category_by_id({category_id}) returned: {category}")
        if not category:
            print(f"❌ Category not found!")
            bot.answer_callback_query(call.id, "القسم غير موجود")
            return
        
        # category هو tuple: (CategoryID, SellerID, Name)
        category_name = category[2] if len(category) > 2 else "قسم"
        print(f"✅ Category found: {category_name}")
        
        seller = get_seller_by_id(seller_id)
        print(f"🔍 get_seller_by_id({seller_id}) returned: {seller}")
        if not seller:
            print(f"❌ Seller not found!")
            bot.answer_callback_query(call.id, "المتجر غير موجود")
            return
        
        seller_name = seller[3] if seller else "المتجر"
        requires_registration = seller[9] if len(seller) > 9 else 0
        customer_telegram_id = call.from_user.id
        seller_telegram_id = seller[1]
        
        print(f"🔍 DEBUG handle_view_category: category_id={category_id}, seller_id={seller_id}, category_name={category_name}")
        print(f"🔍 DEBUG: seller length={len(seller) if seller else 0}, requires_registration={requires_registration}")
        print(f"🔍 DEBUG: customer_telegram_id={customer_telegram_id}, seller_telegram_id={seller_telegram_id}")
        print(f"🔍 DEBUG: هل صاحب المتجر؟ {customer_telegram_id == seller_telegram_id}")
        
        # ⚡ الإجابة السريعة على callback query أولاً لتجنب timeout
        bot.answer_callback_query(call.id)
        
        # التحقق من تسجيل الزبون إذا كان المتجر مقفولاً
        is_registered = True  # افتراضياً: مسجل
        
        if requires_registration:
            print(f"🔐 متجر مقفول - البحث عن التسجيل")
            print(f"📊 requires_registration={requires_registration}, نوع={type(requires_registration)}")
            # التحقق من تسجيل الزبون
            if customer_telegram_id != seller_telegram_id:  # ليس صاحب المتجر
                print(f"✅ العميل ليس صاحب المتجر - جاري التحقق من التسجيل")
                try:
                    # تحقق من TelegramID في CreditCustomers فقط
                    is_registered = is_customer_registered_for_store_by_telegram_id(customer_telegram_id, seller_id)
                    print(f"✅ التحقق من CreditCustomers: is_registered={is_registered}")
                except Exception as e:
                    print(f"⚠️ خطأ في التحقق: {e}, افتراض أن العميل غير مسجل")
                    is_registered = False
        else:
            print(f"ℹ️ متجر مفتوح")
        
        # إذا كان المتجر مغلقاً وليس مسجلاً - عرض رسالة رفض
        if requires_registration and not is_registered:
            print(f"❌ متجر مغلق وعميل غير مسجل")
            bot.send_message(call.message.chat.id,
                f"❌ **زبون غير مسجل**\n\n"
                f"حسابك غير مسجل في هذا المتجر.",
                parse_mode='Markdown')
            return
        
        print(f"✅ يمكن عرض المنتجات")
        print(f"🔍 جاري جلب المنتجات من قاعدة البيانات...")
        
        # ⚡ إرسال رسالة التحميل سريعاً قبل جلب المنتجات
        try:
            bot.send_message(call.message.chat.id, f"📁 **قسم: {category_name}**\n🏪 {seller_name}\n\n⏳ جاري تحميل المنتجات...")
        except Exception as e:
            print(f"⚠️ خطأ في إرسال رسالة التحميل: {e}")
        
        # إذا كان مسجلاً، عرض المنتجات
        try:
            products = get_products(seller_id=seller_id, category_id=category_id)
            print(f"📦 نوع المنتجات: {type(products)}")
            print(f"📦 عدد المنتجات: {len(products) if products else 0}")
        except Exception as e:
            print(f"❌ خطأ في جلب المنتجات: {e}")
            import traceback
            traceback.print_exc()
            bot.send_message(call.message.chat.id, f"❌ خطأ في جلب المنتجات: {e}")
            return
        
        if not products:
            print(f"⚠️ products is None or empty list")
            bot.send_message(call.message.chat.id, f"📦 لا توجد منتجات في قسم {category_name}")
            return
        
        # عرض المنتجات (نفس المنطق السابق)
        if requires_registration and is_registered:
            # متجر مقفول لكن الزبون مسجل - عرض بدون صور
            print(f"🎯 عرض بدون صور (متجر مقفول)")
            markup = types.InlineKeyboardMarkup()
            
            for product in products:
                pid, name, desc, price, wholesale_price, qty, img_path = product
                if qty > 0:
                    add_button = types.InlineKeyboardButton("اضافة للسلة", callback_data=f"addtocart_{pid}_1")
                    back_button = types.InlineKeyboardButton("رجوع للقائمة", callback_data=f"back_to_categories_{seller_id}")
                    inc_button = types.InlineKeyboardButton("➕", callback_data=f"qty_inc_{pid}_1")
                    dec_button = types.InlineKeyboardButton("➖", callback_data=f"qty_dec_{pid}_1")
                    qty_display = types.InlineKeyboardButton("1", callback_data="noop")
                    
                    markup.add(types.InlineKeyboardButton(f"{name}", callback_data="noop"))
                    markup.row(dec_button, qty_display, inc_button)
                    markup.row(add_button, back_button)
            
            text = "🛍️ اختر المنتجات:"
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
        else:
            # متجر مفتوح - عرض مع الصور
            print(f"🎯 عرض مع صور (متجر مفتوح)")
            
            # ⚡ إرسال رسالة سريعة أولاً لتجنب timeout
            text = f"📁 **قسم: {category_name}**\n🏪 {seller_name}\n\n🛍️ جاري تحميل المنتجات..."
            try:
                bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
            except:
                pass
            
            # ⚡ إرسال المنتجات بسرعة (بدون صور أولاً، ثم الصور)
            products_sent = 0
            for product in products:
                pid, name, desc, price, wholesale_price, qty, img_path = product
                if qty > 0:
                    try:
                        markup = types.InlineKeyboardMarkup()
                        markup = create_product_markup_with_qty(pid, 1)
                        # إرسال نص سريع بدل الصورة (أسرع بكثير)
                        caption = f"🛒 **{name}**\n💰 السعر: {price} IQD"
                        if wholesale_price and wholesale_price > 0:
                            caption += f"\n💰 سعر الجملة: {wholesale_price} IQD"
                        caption += f"\n📦 متاح: {qty}"
                        if desc:
                            caption += f"\n📝 {desc[:50]}{'...' if len(desc) > 50 else ''}"
                        
                        bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode='Markdown')
                        products_sent += 1
                        
                        # تأخير صغير لتجنب flood
                        if products_sent % 5 == 0:
                            import time
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"⚠️ Error sending product {pid}: {e}")
                        continue
            
            print(f"✅ تم إرسال {products_sent} منتج")
    except Exception as e:
        print(f"❌ Error in handle_view_category: {e}")
        import traceback
        traceback.print_exc()
        try:
            bot.send_message(call.message.chat.id, "❌ حدث خطأ في تحميل المنتجات")
        except:
            pass


def handle_back_to_categories(call):
    """الرجوع لقائمة الفئات"""
    try:
        seller_id = int(call.data.split("_")[-1])
        seller = get_seller_by_id(seller_id)
        
        if not seller:
            bot.answer_callback_query(call.id, "المتجر غير موجود")
            return
        
        seller_telegram_id = seller[1]
        customer_telegram_id = call.from_user.id
        
        # محو الرسالة السابقة وإرسال قائمة الفئات
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        # إعادة عرض الفئات
        send_store_catalog_by_telegram_id(call.message.chat.id, seller_telegram_id, customer_telegram_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_back_to_categories: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ")

def handle_select_images(call):
    """معالج اختيار عدد الصور للمنتج"""
    try:
        product_id = int(call.data.split("_")[2])
        product = get_product_by_id(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, "⚠️ المنتج غير موجود")
            return
        
        seller_id = product[1]
        product_name = product[3]
        price = product[5]
        available_qty = product[7]
        
        # الحصول على صور المنتج
        images = get_product_images(product_id)
        
        if not images:
            bot.answer_callback_query(call.id, "⚠️ لا توجد صور متاحة لهذا المنتج")
            return
        
        # التحقق من رقم الهاتف المسجل
        telegram_id = call.from_user.id
        user_phone = None
        if telegram_id in user_states:
            state = user_states[telegram_id]
            if 'verified_phone' in state and 'verified_seller_id' in state:
                if state['verified_seller_id'] == seller_id:
                    user_phone = state['verified_phone']
        
        if not user_phone:
            bot.answer_callback_query(call.id, "⚠️ يجب التحقق من رقم الهاتف أولاً")
            return
        
        # الحصول على معلومات الزبون
        customer = get_customer_by_phone_for_seller(user_phone, seller_id)
        if not customer:
            bot.answer_callback_query(call.id, "⚠️ أنت غير مسجل كزبون آجل")
            return
        
        customer_id, customer_name, customer_phone = customer
        
        # عرض عدد الصور المتاحة واختيار العدد
        text = f"📸 **اختر عدد الصور**\n\n"
        text += f"📦 المنتج: {product_name}\n"
        text += f"💰 السعر: {price:,.0f} د.ع للصورة الواحدة\n"
        text += f"📊 الصور المتاحة: {len(images)} صورة\n"
        text += f"📦 الكمية المتاحة: {available_qty} صورة\n\n"
        text += f"👤 الزبون: {customer_name}\n"
        text += f"📱 الهاتف: {customer_phone}\n\n"
        text += f"اختر عدد الصور التي تريد شراءها:"
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        
        # أزرار الكمية (1-10)
        qty_buttons = []
        max_qty = min(available_qty, len(images), 10)
        for i in range(1, max_qty + 1):
            qty_buttons.append(types.InlineKeyboardButton(str(i), callback_data=f"buy_images_{product_id}_{i}"))
            if len(qty_buttons) == 3:
                markup.row(*qty_buttons)
                qty_buttons = []
        
        if qty_buttons:
            markup.row(*qty_buttons)
        
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_image_selection"))
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_select_images: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

def handle_buy_images(call):
    """معالج شراء الصور وإرسالها للمستخدم"""
    try:
        parts = call.data.split("_")
        product_id = int(parts[2])
        quantity = int(parts[3])
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "⚠️ المنتج غير موجود")
            return
        
        seller_id = product[1]
        product_name = product[3]
        price = product[5]
        available_qty = product[7]
        
        if quantity > available_qty:
            bot.answer_callback_query(call.id, f"⚠️ الكمية المتاحة فقط {available_qty} صورة")
            return
        
        # الحصول على صور المنتج
        images = get_product_images(product_id)
        if not images or len(images) < quantity:
            bot.answer_callback_query(call.id, "⚠️ لا توجد صور كافية")
            return
        
        # التحقق من رقم الهاتف المسجل
        telegram_id = call.from_user.id
        user_phone = None
        if telegram_id in user_states:
            state = user_states[telegram_id]
            if 'verified_phone' in state and 'verified_seller_id' in state:
                if state['verified_seller_id'] == seller_id:
                    user_phone = state['verified_phone']
        
        if not user_phone:
            bot.answer_callback_query(call.id, "⚠️ يجب التحقق من رقم الهاتف أولاً")
            return
        
        # الحصول على معلومات الزبون
        customer = get_customer_by_phone_for_seller(user_phone, seller_id)
        if not customer:
            bot.answer_callback_query(call.id, "⚠️ أنت غير مسجل كزبون آجل")
            return
        
        customer_id, customer_name, customer_phone = customer
        
        # حساب المبلغ الإجمالي
        total_amount = price * quantity
        
        # إرسال الصور للمستخدم من قاعدة البيانات
        sent_images = []
        for i in range(quantity):
            try:
                image_id = images[i][0]  # ImageID
                image_filename = images[i][1]  # اسم الملف
                
                # جلب بيانات الصورة من قاعدة البيانات
                conn = get_db_connection()
                cursor = conn.cursor()
                
                if IS_POSTGRES:
                    cursor.execute("SELECT filedata FROM imagestorage WHERE imageid=%s", (image_id,))
                else:
                    cursor.execute("SELECT filedata FROM imagestorage WHERE ImageID=?", (image_id,))
                
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0]:
                    file_data = result[0]
                    # إنشاء file-like object من البيانات الثنائية
                    from io import BytesIO
                    photo_buffer = BytesIO(file_data)
                    photo_buffer.name = image_filename
                    
                    # إرسال الصورة للمستخدم
                    bot.send_photo(telegram_id, photo_buffer)
                    sent_images.append(image_filename)
                    print(f"✅ Image {i+1} sent: {image_filename}")
            except Exception as e:
                print(f"❌ Error sending image {i+1}: {e}")
                import traceback
                traceback.print_exc()
        
        if not sent_images:
            bot.answer_callback_query(call.id, "❌ فشل إرسال الصور")
            return
        
        # إضافة المبلغ لحساب الزبون
        description = f"شراء {quantity} صورة من منتج: {product_name}"
        if add_credit_transaction(customer_id, seller_id, total_amount, description):
            # تحديث كمية المنتج (تأكد من عدم السالب)
            conn = get_db_connection()
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("UPDATE Products SET Quantity = GREATEST(0, Quantity - %s) WHERE ProductID = %s", (quantity, product_id))
            else:
                # SQLite: استخدم CASE بدل MAX
                cursor.execute("UPDATE Products SET Quantity = CASE WHEN Quantity - ? < 0 THEN 0 ELSE Quantity - ? END WHERE ProductID = ?", (quantity, quantity, product_id))
            conn.commit()
            conn.close()
            
            # ✅ حذف الصور المشتراة من قاعدة البيانات باستخدام الدالة الجديدة
            print(f"🗑️ حذف {quantity} صور من ProductID {product_id}")
            deleted_count, deleted_images = delete_n_images_from_product(product_id, quantity)
            print(f"✅ تم حذف {deleted_count} صورة: {deleted_images}")
            
            # إرسال رسالة للمستخدم
            bot.send_message(telegram_id,
                f"✅ **تم الشراء بنجاح!**\n\n"
                f"📦 المنتج: {product_name}\n"
                f"📸 عدد الصور: {quantity}\n"
                f"💰 المبلغ: {total_amount:,.0f} د.ع\n\n"
                f"تم إضافة المبلغ إلى حسابك الآجل.",
                parse_mode='Markdown')
            
            # إرسال إشعار للبائع
            seller = get_seller_by_id(seller_id)
            if seller:
                seller_telegram_id = seller[1]
                # sent_images تحتوي على أسماء الملفات مباشرة
                images_list = "\n".join([f"• {img}" for img in sent_images])
                
                bot.send_message(seller_telegram_id,
                    f"🛒 **طلب شراء صور**\n\n"
                    f"👤 الزبون: {customer_name}\n"
                    f"📱 الهاتف: {customer_phone}\n\n"
                    f"📦 المنتج: {product_name}\n"
                    f"📸 عدد الصور: {quantity}\n"
                    f"💰 المبلغ: {total_amount:,.0f} د.ع\n\n"
                    f"📸 الصور المشتراة:\n{images_list}\n\n"
                    f"✅ تم إضافة المبلغ {total_amount:,.0f} د.ع إلى حساب الزبون.",
                    parse_mode='Markdown')
            
            bot.answer_callback_query(call.id, f"✅ تم إرسال {len(sent_images)} صورة")
        else:
            bot.answer_callback_query(call.id, "❌ فشل إضافة المبلغ للحساب")
    except Exception as e:
        print(f"Error in handle_buy_images: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_image_selection")
def handle_cancel_image_selection(call):
    """إلغاء اختيار الصور"""
    bot.answer_callback_query(call.id, "تم الإلغاء")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

def add_product_image_db(product_id, image_path, image_order=0):
    """إضافة صورة للمنتج مباشرة إلى imagestorage مع بيانات الصورة"""
    try:
        # image_path قد يكون اسم ملف فقط، نحتاج إلى المسار الكامل
        if not os.path.isabs(image_path):
            # إذا كان اسم ملف فقط، أضف مسار المجلد
            full_image_path = os.path.join(IMAGES_FOLDER, image_path)
        else:
            full_image_path = image_path
        
        print(f"[DEBUG] Attempting to read image from: {full_image_path}")
        print(f"[DEBUG] IMAGES_FOLDER: {IMAGES_FOLDER}")
        print(f"[DEBUG] Folder exists: {os.path.exists(IMAGES_FOLDER)}")
        print(f"[DEBUG] File exists: {os.path.exists(full_image_path)}")
        
        # قراءة بيانات الصورة
        try:
            if not os.path.exists(full_image_path):
                print(f"[ERROR] Image file not found: {full_image_path}")
                return None
                
            with open(full_image_path, 'rb') as f:
                file_data = f.read()
            print(f"[DEBUG] ✅ Read image file: {full_image_path}, size: {len(file_data)} bytes")
        except Exception as e:
            print(f"[ERROR] Failed to read image file {full_image_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        conn = get_db_connection()
        cursor_wrapper = conn.cursor()
        
        original_filename = os.path.basename(image_path)
        unique_filename = f"{product_id}_{image_order}_{original_filename}"
        
        if IS_POSTGRES:
            print(f"[DEBUG] PostgreSQL - Adding image for product {product_id}")
            
            try:
                import psycopg2
                cursor_wrapper.execute("""
                    INSERT INTO imagestorage (filename, filedata, productid, imageorder, updatedat)
                    VALUES (%s, %s, %s, %s, NOW())
                    RETURNING imageid
                """, (unique_filename, psycopg2.Binary(file_data), product_id, image_order))
                
                # CursorWrapper already calls fetchone() for RETURNING queries
                # so we get image_id from lastrowid
                image_id = cursor_wrapper.lastrowid
                if not image_id:
                    # Fallback: try fetchone if lastrowid didn't work
                    result = cursor_wrapper.fetchone()
                    image_id = result[0] if result else None
                    
                print(f"[DEBUG] ✅ Inserted into imagestorage - Image ID: {image_id}, filesize: {len(file_data)} bytes")
            except Exception as e:
                print(f"[ERROR] Failed to insert into imagestorage: {e}")
                import traceback
                traceback.print_exc()
                conn.close()
                return None
        else:
            try:
                cursor_wrapper.execute("""
                    INSERT INTO ImageStorage (FileName, FileData, ProductID, ImageOrder)
                    VALUES (?, ?, ?, ?)
                """, (unique_filename, file_data, product_id, image_order))
                image_id = cursor_wrapper.lastrowid
                print(f"[DEBUG] ✅ Inserted into ImageStorage - Image ID: {image_id}, filesize: {len(file_data)} bytes")
            except Exception as e:
                print(f"[ERROR] Failed to insert into ImageStorage: {e}")
                import traceback
                traceback.print_exc()
                conn.close()
                return None
        
        conn.commit()
        cursor_wrapper.close()
        conn.close()
        print(f"[DEBUG] ✅ Image saved successfully with data. Returning image_id: {image_id}")
        return image_id
    except Exception as e:
        print(f"[ERROR] Error adding product image: {e}")
        import traceback
        traceback.print_exc()
        return None
        
        conn.commit()
        cursor_wrapper.close()
        conn.close()
        print(f"[DEBUG] ✅ All operations completed successfully. Returning image_id: {image_id}")
        return image_id
    except Exception as e:
        print(f"[ERROR] Error adding product image: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()
        return None

def delete_product_image_db(image_id):
    """حذف صورة من المنتج"""
    try:
        conn = get_db_connection()
        cursor_wrapper = conn.cursor()
        
        try:
            if IS_POSTGRES:
                cursor_wrapper.execute('DELETE FROM imagestorage WHERE imageid=%s', (image_id,))
            else:
                cursor_wrapper.execute("DELETE FROM imagestorage WHERE imageid=?", (image_id,))
            
            conn.commit()
            deleted = cursor_wrapper.rowcount > 0
            return deleted
        finally:
            cursor_wrapper.close()
            conn.close()
    except Exception as e:
        print(f"Error deleting product image: {e}")
        import traceback
        traceback.print_exc()
        return False

def handle_manage_product_images(call):
    """إدارة صور المنتج - عرض صور حقيقية"""
    try:
        product_id = int(call.data.split("_")[3])
        telegram_id = call.from_user.id
        
        print(f"[DEBUG] handle_manage_product_images: product_id={product_id}, telegram_id={telegram_id}")
        
        # الحصول على بيانات المنتج
        product = get_product_by_id(product_id)
        if not product:
            print(f"[DEBUG] Product {product_id} not found")
            bot.answer_callback_query(call.id, "⚠️ المنتج غير موجود")
            return
        
        print(f"[DEBUG] Product found: {product}")
        
        # الحصول على بيانات المتجر (البائع)
        seller = get_seller_by_id(product[1])  # الحصول على بائع المنتج
        if not seller:
            print(f"[DEBUG] Seller not found for seller_id={product[1]}")
            bot.answer_callback_query(call.id, "⛔ المتجر غير موجود")
            return
        
        print(f"[DEBUG] Product seller: seller_id={seller[0]}")
        
        # تحقق من ملكية المنتج
        user_seller = get_seller_by_telegram(telegram_id)
        if not user_seller or product[1] != user_seller[0]:
            print(f"[DEBUG] Permission denied: not the owner")
            bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية لتعديل هذا المنتج")
            return
        
        # الحصول على الصور
        product_name = product[3]
        print(f"[DEBUG] Fetching images for product_id={product_id}")
        
        try:
            images = get_product_images(product_id)
            print(f"[DEBUG] Images fetched: {len(images)} images found")
            for img in images:
                print(f"[DEBUG] Image: {img}")
        except Exception as e:
            print(f"[ERROR] Failed to get_product_images: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, "❌ خطأ في تحميل الصور")
            return
        
        # إنشء الرسالة الأولى مع معلومات المنتج والصور
        text = "🖼️ إدارة صور المنتج\n\n"
        text += f"📦 المنتج: {product_name}\n"
        text += f"📸 عدد الصور: {len(images)}"
        
        # إنشاء لوحة التحكم
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        if images:
            # إضافة أزرار الحذف لكل صورة
            for img_id, img_path, img_order in images:
                print(f"[DEBUG] Creating delete button: product_id={product_id}, img_id={img_id}")
                markup.add(types.InlineKeyboardButton(
                    "🗑️ حذف", 
                    callback_data=f"del_img_{product_id}_{img_id}"  # استخدام اختصار أقصر
                ))
        
        # أزرار الإضافة والرجوع في أسفل الصفحة
        markup.add(
            types.InlineKeyboardButton("➕ إضافة صورة", callback_data=f"add_product_image_{product_id}"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data=f"edit_product_{product_id}")
        )
        
        # إرسال رسالة المعلومات بدون صور
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
        
        # الآن إرسال قائمة الصور
        if images:
            text_images = "📸 **الصور الحالية:**\n\n"
            for idx, (img_id, img_path, img_order) in enumerate(images, 1):
                img_name = os.path.basename(img_path) if img_path else f"صورة_{img_id}"
                text_images += f"{idx}️⃣ {img_name}\n"
            
            bot.send_message(call.message.chat.id, text_images)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        print(f"[ERROR] Error in handle_manage_product_images: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ في تحميل الصور")

def handle_add_product_image(call):
    """بدء عملية إضافة صورة جديدة للمنتج"""
    try:
        product_id = int(call.data.split("_")[3])
        telegram_id = call.from_user.id
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "⚠️ المنتج غير موجود")
            return
        
        # التحقق من أن البائع يملك المنتج
        seller = get_seller_by_telegram(telegram_id)
        if not seller or product[1] != seller[0]:
            bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية لتعديل هذا المنتج")
            return
        
        # حفظ الحالة
        user_states[telegram_id] = {
            'step': 'add_product_image_to_db',
            'product_id': product_id
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("📸 إرسال صورة", "❌ إلغاء")
        
        bot.send_message(call.message.chat.id,
            f"📸 **إضافة صورة جديدة**\n\n"
            f"📦 المنتج: {product[3]}\n\n"
            f"يرجى إرسال الصورة التي تريد إضافتها للمنتج:",
            reply_markup=markup,
            parse_mode='Markdown')
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_add_product_image: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "add_product_image_to_db")
def handle_save_product_image(message):
    """حفظ الصورة الجديدة للمنتج"""
    try:
        telegram_id = message.from_user.id
        state = user_states[telegram_id]
        product_id = state['product_id']
        
        # حفظ الصورة
        image_path = save_photo_from_message(message)
        if not image_path:
            bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الصورة")
            del user_states[telegram_id]
            return
        
        # إضافة الصورة لقاعدة البيانات
        images = get_product_images(product_id)
        image_order = len(images)  # ترتيب الصورة الجديدة
        
        print(f"[DEBUG] Calling add_product_image_db - product_id={product_id}, image_order={image_order}")
        image_id = add_product_image_db(product_id, image_path, image_order)
        print(f"[DEBUG] add_product_image_db returned: image_id={image_id}")
        
        if image_id:
            print(f"[DEBUG] Image saved successfully with ID: {image_id}")
            # تحديث كمية المنتج تلقائياً إذا كان المتجر مقفول
            product = get_product_by_id(product_id)
            if product:
                seller_id = product[1]
                seller = get_seller_by_id(seller_id)
                
                # تحديث الكمية لجميع المتاجر = عدد الصور
                conn = get_db_connection()
                cursor_wrapper = conn.cursor()
                try:
                    if IS_POSTGRES:
                        cursor_wrapper.execute('SELECT COUNT(*) FROM imagestorage WHERE productid=%s', (product_id,))
                    else:
                        cursor_wrapper.execute("SELECT COUNT(*) FROM imagestorage WHERE productid=?", (product_id,))
                    result = cursor_wrapper.fetchone()
                    image_count = result[0] if result else 0
                    
                    print(f"📊 تم إضافة صورة جديدة. عدد الصور الآن: {image_count}")
                    
                    # تحديث الكمية
                    if IS_POSTGRES:
                        cursor_wrapper.execute("UPDATE products SET quantity=%s WHERE productid=%s", (image_count, product_id))
                    else:
                        cursor_wrapper.execute("UPDATE products SET quantity=? WHERE productid=?", (image_count, product_id))
                    conn.commit()
                    
                    print(f"✅ تم تحديث الكمية إلى: {image_count}")
                except Exception as e:
                    print(f"[ERROR] Error updating product quantity: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    cursor_wrapper.close()
                    conn.close()
            
            bot.send_message(message.chat.id,
                f"✅ تم إضافة الصورة بنجاح!\n\n"
                f"📸 تم حفظ الصورة: {os.path.basename(image_path)}\n\n"
                f"يمكنك إضافة المزيد من الصور")
            
            # إضافة زر العودة للرئيسية
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="main_menu"))
            bot.send_message(message.chat.id,
                "اختر:",
                reply_markup=markup)
        else:
            print(f"[ERROR] add_product_image_db returned None - image not saved")
            bot.send_message(message.chat.id, "❌ حدث خطأ في إضافة الصورة لقاعدة البيانات")
        
        # إزالة الحالة
        del user_states[telegram_id]
    except Exception as e:
        print(f"[ERROR] Error in handle_save_product_image: {e}")
        import traceback
        traceback.print_exc()
        telegram_id = message.from_user.id
        try:
            bot.send_message(message.chat.id, f"⚠️ حدث خطأ غير متوقع:\n\n`{str(e)}`", parse_mode='Markdown')
        except:
            pass
        if telegram_id in user_states:
            del user_states[telegram_id]

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "add_product_image_to_db" and
                     message.text == "❌ إلغاء")
def handle_cancel_add_image(message):
    """إلغاء إضافة صورة"""
    telegram_id = message.from_user.id
    if telegram_id in user_states:
        state = user_states[telegram_id]
        product_id = state.get('product_id')
        del user_states[telegram_id]
        
        if product_id:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row("🏠 الرئيسية")
            bot.send_message(message.chat.id, "❌ تم إلغاء العملية", reply_markup=markup)

def handle_delete_product_image(call):
    """حذف صورة من المنتج"""
    try:
        # دعم صيغتين:
        # del_img_{product_id}_{img_id} (الصيغة الجديدة المختصرة)
        # delete_product_image_{product_id}_{img_id} (الصيغة القديمة)
        
        if call.data.startswith("del_img_"):
            data_str = call.data.replace("del_img_", "")
        else:
            data_str = call.data.replace("delete_product_image_", "")
        
        parts = data_str.split("_")
        
        if len(parts) < 2:
            print(f"[ERROR] Invalid callback_data: {call.data}")
            bot.answer_callback_query(call.id, "❌ خطأ في البيانات")
            return
        
        try:
            product_id = int(parts[0])
            image_id = int(parts[1])
        except ValueError as e:
            print(f"[ERROR] Failed to parse IDs: {e}, data={call.data}")
            bot.answer_callback_query(call.id, "❌ خطأ في معالجة البيانات")
            return
        
        telegram_id = call.from_user.id
        
        print(f"[DEBUG] Deleting image - image_id={image_id}, product_id={product_id}, telegram_id={telegram_id}")
        
        # الحصول على معلومات الصورة
        conn = get_db_connection()
        cursor_wrapper = conn.cursor()
        
        try:
            if IS_POSTGRES:
                cursor_wrapper.execute("""
                    SELECT img.imageid, img.productid, img.filename, p.sellerid, p.name
                    FROM imagestorage img
                    JOIN products p ON img.productid = p.productid
                    WHERE img.imageid = %s
                """, (image_id,))
            else:
                cursor_wrapper.execute("""
                    SELECT img.imageid, img.productid, img.filename, p.sellerid, p.name
                    FROM imagestorage img
                    JOIN products p ON img.productid = p.productid
                    WHERE img.imageid = ?
                """, (image_id,))
            
            result = cursor_wrapper.fetchone()
        finally:
            cursor_wrapper.close()
            conn.close()
        
        if not result:
            print(f"[DEBUG] Image {image_id} not found")
            bot.answer_callback_query(call.id, "⚠️ الصورة غير موجودة")
            return
        
        img_id, product_id_db, img_path, seller_id, product_name = result
        product_id = product_id or product_id_db  # استخدم من النتيجة إذا لم يكن معطى
        
        print(f"[DEBUG] Image found: product_id={product_id}, seller_id={seller_id}")
        
        # التحقق من أن البائع يملك المنتج
        seller = get_seller_by_telegram(telegram_id)
        if not seller or seller[0] != seller_id:
            print(f"[DEBUG] Permission denied: seller_id={seller[0] if seller else None} != {seller_id}")
            bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية لحذف هذه الصورة")
            return
        
        # حذف الصورة
        print(f"[DEBUG] Deleting image {image_id}")
        if delete_product_image_db(image_id):
            print(f"[DEBUG] Image deleted successfully")
            
            bot.answer_callback_query(call.id, "✅ تم حذف الصورة بنجاح")
            
            # إرسال رسالة تأكيد مع زر العودة للرئيسية
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="main_menu"))
            bot.send_message(
                call.message.chat.id,
                "✅ تم حذف الصورة!",
                reply_markup=markup
            )
        else:
            print(f"[DEBUG] Failed to delete image from database")
            bot.answer_callback_query(call.id, "❌ فشل حذف الصورة")
            
    except Exception as e:
        print(f"[ERROR] Error in handle_delete_product_image: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ حدث خطأ في حذف الصورة")

@bot.callback_query_handler(func=lambda call: call.data.startswith("addtocart_"))
def handle_add_to_cart(call):
    try:
        parts = call.data.split("_")
        product_id = int(parts[1])
        
        # New: Parse quantity if present, default to 1
        quantity = 1
        if len(parts) > 2:
            try:
                quantity = int(parts[2])
            except:
                pass
        
        user_id = call.from_user.id
        
        # ====== التعديل: إزالة شرط التحقق من نوع المستخدم ======
        # يمكن لأي مستخدم (زائر، مشتري، بائع، أدمن) إضافة منتجات للسلة
        
        # Ensure user exists in Users table (required for Foreign Key constraint)
        print(f"[DEBUG] handle_add_to_cart: Checking user {user_id}...")
        user = get_user(user_id)
        if not user:
            # Create user entry if doesn't exist
            print(f"[INFO] User {user_id} not found. Creating user entry...")
            username = call.from_user.username or None
            full_name = None
            if call.from_user.first_name or call.from_user.last_name:
                full_name = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip()
            
            user_created = add_user(user_id, username, 'buyer', None, full_name)
            if not user_created:
                print(f"[ERROR] Failed to create user {user_id}")
                bot.answer_callback_query(call.id, "❌ حدث خطأ في إنشاء المستخدم")
                return
            
            # Small delay to ensure database commit is complete
            import time
            time.sleep(0.2)
            
            # Verify user was created
            user = get_user(user_id)
            if not user:
                print(f"[ERROR] User {user_id} still not found after creation")
                bot.answer_callback_query(call.id, "❌ حدث خطأ في التحقق من المستخدم")
                return
            print(f"[SUCCESS] User {user_id} created and verified")
        else:
            print(f"[OK] User {user_id} exists")
        
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "المنتج غير موجود")
            return

        # منع الشراء من متجر الأدمن - REMOVED
        seller_id = product[1]
        # seller = get_seller_by_id(seller_id)
        # Check removed to allow buying from admin
        
        if product[7] <= 0:
            bot.answer_callback_query(call.id, "⛔ المنتج غير متوفر حالياً")
            return
        
        # الحصول على سعر المنتج المناسب للزبون
        seller_id = product[1]
        phone = None
        full_name = None
        
        # فقط للمستخدمين المسجلين، نحاول الحصول على معلوماتهم
        if user:
            phone = user[4] if len(user) > 4 else None
            full_name = user[5] if len(user) > 5 else None
        
        price = get_product_price_for_customer(product_id, seller_id, phone, full_name)
        
        success = add_to_cart_db(user_id, product_id, quantity, price)
        
        if success:
            product_name = product[3]
            bot.answer_callback_query(call.id, f"✅ تم إضافة {quantity}x {product_name} إلى السلة")
        else:
            bot.answer_callback_query(call.id, "❌ حدث خطأ في إضافة المنتج للسلة")
        
    except Exception as e:
        print(f"Error in handle_add_to_cart: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"خطأ: {str(e)[:50]}")

# ====== إدارة السلة ======
@bot.message_handler(func=lambda message: message.text == "سلة المشتريات 🛒")
def view_cart(message, user_id=None):
    try:
        telegram_id = user_id if user_id else message.from_user.id
        
        # ====== التعديل الجديد ======
        # التحقق إذا كان المستخدم زائراً (غير مسجل)
        is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
        
        # if not is_guest:
        #     # للمستخدمين المسجلين، التحقق من نوع المستخدم
        #     user = get_user(telegram_id)
        #     if not user or user[3] != 'buyer':
        #         # bot.send_message(message.chat.id, "⛔ يجب أن تكون مشترياً لعرض السلة")
        #         pass
        
        cart_items = get_cart_items_db(telegram_id)
        
        if not cart_items:
            bot.send_message(message.chat.id, "🛒 **سلة المشتريات**\n\nالسلة فارغة حالياً.")
            return
        
        # Build Consolidated Cart View
        markup = types.InlineKeyboardMarkup(row_width=4)
        cart_text = "🛒 **سلة المشتريات**\n\n"
        
        total = 0
        idx = 1
        
        # Group by seller for display structure (optional, but good for organization)
        # For the consolidated list, we can just list them sequentially but maybe group headers if needed.
        # Let's simple list them as requested: Image(No) Name Price Qty Total Controls
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            item_total = price * quantity
            total += item_total
            
            # Escape special markdown characters to avoid parsing errors
            safe_name = escape_markdown_v1(name) if name else "منتج"
            safe_seller_name = escape_markdown_v1(seller_name) if seller_name else "متجر"
            
            # Text Line
            # 1. Product Name (xQty) - Total
            cart_text += f"{idx}. **{safe_name}**\n"
            cart_text += f"   💰 {price:,.0f} x {quantity} = {item_total:,.0f} IQD\n"
            cart_text += f"   🏪 {safe_seller_name}\n"
            cart_text += "   ────────────────────\n"
            
            # Control Row for this item
            # [ ➖ ] [ Qty ] [ ➕ ] [ 🗑️ ]
            markup.row(
                types.InlineKeyboardButton("➖", callback_data=f"decrease_cart_{product_id}"),
                types.InlineKeyboardButton(f"{quantity}", callback_data="noop"),
                types.InlineKeyboardButton("➕", callback_data=f"increase_cart_{product_id}"),
                types.InlineKeyboardButton("🗑️", callback_data=f"remove_cart_{product_id}")
            )
            idx += 1
            
        cart_text += f"\n📊 **الإجمالي الكلي: {total:,.0f} IQD**\n"
        
        # Footer Actions
        markup.row(
            types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"),
            types.InlineKeyboardButton("✅ تأكيد الطلب", callback_data="checkout_cart")
        )
        markup.row(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu"))
        
        bot.send_message(message.chat.id, cart_text, reply_markup=markup, parse_mode='Markdown')     

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض السلة:\n{str(e)}")
        traceback.print_exc()

def update_cart_view(chat_id, message_id, user_id):
    """Updates the existing cart message with new state"""
    try:
        cart_items = get_cart_items_db(user_id)
        
        if not cart_items:
            # Cart is empty, edit message to say empty
            bot.edit_message_text("🛒 **سلة المشتريات**\n\nالسلة فارغة حالياً.", chat_id, message_id, parse_mode='Markdown', reply_markup=None)
            return

        markup = types.InlineKeyboardMarkup(row_width=4)
        cart_text = "🛒 **سلة المشتريات**\n\n"
        
        total = 0
        idx = 1
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            item_total = price * quantity
            total += item_total
            
            # Escape special markdown characters
            safe_name = escape_markdown_v1(name) if name else "منتج"
            safe_seller_name = escape_markdown_v1(seller_name) if seller_name else "متجر"
            
            cart_text += f"{idx}. **{safe_name}**\n"
            cart_text += f"   💰 {price:,.0f} x {quantity} = {item_total:,.0f} IQD\n"
            cart_text += f"   🏪 {safe_seller_name}\n"
            cart_text += "   ────────────────────\n"
            
            markup.row(
                types.InlineKeyboardButton("➖", callback_data=f"decrease_cart_{product_id}"),
                types.InlineKeyboardButton(f"{quantity}", callback_data="noop"),
                types.InlineKeyboardButton("➕", callback_data=f"increase_cart_{product_id}"),
                types.InlineKeyboardButton("🗑️", callback_data=f"remove_cart_{product_id}")
            )
            idx += 1
            
        cart_text += f"\n📊 **الإجمالي الكلي: {total:,.0f} IQD**\n"
        
        markup.row(
            types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"),
            types.InlineKeyboardButton("✅ تأكيد الطلب", callback_data="checkout_cart")
        )
        markup.row(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu"))
        
        bot.edit_message_text(cart_text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error updating cart view: {e}")
        # If edit fails (e.g. same content), ignore


    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض السلة:\n{str(e)}")
        traceback.print_exc()


def delete_product_images_for_closed_store(seller_id, items_list):
    """
    حذف صور المنتجات من المتجر المغلق بناءً على الكمية المشتراة فقط
    
    Args:
        seller_id: معرّف البائع
        items_list: قائمة المنتجات المشتراة [(product_id, quantity, price, name), ...]
    """
    try:
        if not items_list:
            print("⚠️ لا توجد منتجات للحذف")
            return 0
        
        print(f"🔍 DEBUG: البدء بحذف الصور للمنتجات: {len(items_list)}")
        for idx, item in enumerate(items_list):
            print(f"   [{idx}] {item}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        deleted_count = 0
        
        for product_id, quantity, price, name in items_list:
            try:
                # تحويل إلى int للتأكد
                quantity = int(quantity)
                product_id = int(product_id)
                
                print(f"🔧 معالجة منتج: {product_id} (الكمية: {quantity})")
                
                # الحصول على قائمة صور المنتج (مرتبة بالترتيب)
                if IS_POSTGRES:
                    cursor.execute(
                        'SELECT imageid, filename FROM imagestorage WHERE productid = %s ORDER BY imageorder ASC',
                        (product_id,)
                    )
                else:
                    cursor.execute(
                        'SELECT imageid, filename FROM imagestorage WHERE productid = ? ORDER BY imageorder ASC',
                        (product_id,)
                    )
                
                images = cursor.fetchall()
                print(f"   ✓ وجدنا {len(images)} صور للمنتج {product_id}")
                
                # حذف فقط الصور المشتراة (بالكمية المطلوبة)
                images_to_delete = images[:quantity]  # أول N صورة حيث N = الكمية المشتراة
                
                print(f"📸 المنتج {product_id}: حذف {len(images_to_delete)} صورة من {len(images)} صور (الكمية المشتراة: {quantity})")
                
                for img_row in images_to_delete:
                    image_id, filename = img_row
                    img_path = os.path.join(IMAGES_FOLDER, filename)
                    
                    try:
                        # حذف الملف من القرص المحلي
                        if os.path.exists(img_path):
                            os.remove(img_path)
                            print(f"🗑️  حذف ملف الصورة: {filename}")
                            deleted_count += 1
                    except Exception as e:
                        print(f"⚠️  خطأ في حذف الملف {filename}: {e}")
                    
                    # حذف من قاعدة البيانات
                    try:
                        if IS_POSTGRES:
                            cursor.execute(
                                'DELETE FROM imagestorage WHERE imageid = %s',
                                (image_id,)
                            )
                        else:
                            cursor.execute(
                                'DELETE FROM imagestorage WHERE imageid = ?',
                                (image_id,)
                            )
                    except Exception as e:
                        print(f"⚠️  خطأ في حذف الصورة من قاعدة البيانات {image_id}: {e}")
                
            except Exception as e:
                print(f"❌ خطأ في معالجة صور المنتج {product_id}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ تم حذف {deleted_count} صورة من متجر مغلق (seller_id={seller_id})")
        return deleted_count
        
    except Exception as e:
        print(f"❌ خطأ في حذف صور المتجر المغلق: {e}")
        traceback.print_exc()
        return 0


def create_confirmed_order_for_closed_store(message, telegram_id, seller_id, seller_data, user_info):
    """
    For closed (registration-required) stores: Create ONLY a Message, NO Order.
    Customer gets notified immediately, seller gets message notification.
    """
    try:
        # Format items: [(product_id, quantity, price), ...]
        items = [(int(product_id), int(quantity), float(price)) for product_id, quantity, price, name in seller_data['items']]
        
        # ❌ DO NOT CREATE ORDER - Only create message for closed stores
        # The purchase is recorded as a message, not an order
        order_id = None
        
        print(f"✅ Processing closed store purchase as MESSAGE (no order created)")
        
        # Get seller info to send notification
        seller = get_seller_by_id(seller_id)
        seller_telegram_id = seller[1]
        
        # Get customer name and ID from CreditCustomers
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT CustomerID, FullName FROM CreditCustomers WHERE TelegramID = ? AND SellerID = ?", (telegram_id, seller_id))
        cust_result = cursor.fetchone()
        
        if cust_result:
            customer_id = cust_result[0]
            customer_name = cust_result[1]  # استخدم الاسم المسجل في إدارة الزبائن الآجلين
        else:
            customer_id = None
            customer_name = user_info[2] if user_info and len(user_info) > 2 else "عميل"
        
        cursor.close()
        conn.close()
        
        total_amount = seller_data['subtotal']
        
        # 💳 ADD AMOUNT TO CUSTOMER'S CREDIT ACCOUNT
        if customer_id:
            print(f"💳 Adding {total_amount} د.ع to customer {customer_id}'s account...")
            add_credit_transaction(
                customer_id=customer_id,
                seller_id=seller_id,
                amount=total_amount,
                description=f"شراء من متجر مغلق"
            )
            print(f"✅ Credit added to customer account!")
        else:
            print(f"⚠️ Warning: Could not find customer ID for telegram {telegram_id}")
        
        # 📤 SEND PRODUCTS WITH IMAGES TO CUSTOMER (Show images immediately)
        print(f"📸 Sending product images to customer {telegram_id}...")
        print(f"🔍 DEBUG: telegram_id = {telegram_id}, type = {type(telegram_id)}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build a message with all products and their images
        sent_images_count = 0
        
        for product_id, quantity, price, name in seller_data['items']:
            try:
                # Get product details from Products table
                if IS_POSTGRES:
                    cursor.execute("""
                        SELECT "productid", "name", "description" 
                        FROM products 
                        WHERE "productid"=%s
                    """, (product_id,))
                else:
                    cursor.execute("""
                        SELECT ProductID, ProductName, Description 
                        FROM Products 
                        WHERE ProductID=?
                    """, (product_id,))
                product = cursor.fetchone()
                
                if product:
                    prod_id, prod_name, prod_desc = product
                    
                    # جرّب الحصول على صور المنتج (بالعدد المطلوب شراؤه)
                    if IS_POSTGRES:
                        cursor.execute("""
                            SELECT filename FROM imagestorage 
                            WHERE productid = %s
                            ORDER BY imageorder ASC
                            LIMIT %s
                        """, (product_id, quantity))
                    else:
                        cursor.execute("""
                            SELECT FileName FROM imagestorage 
                            WHERE ProductID = ?
                            ORDER BY imageorder
                            LIMIT ?
                        """, (product_id, quantity))
                    
                    images = cursor.fetchall()
                    
                    if images:
                        print(f"📸 Sending {len(images)} images for product {prod_id} to customer {telegram_id}")
                        
                        # Send each image to the customer immediately
                        for img_row in images:
                            img_filename = img_row[0]
                            img_path = os.path.join(IMAGES_FOLDER, img_filename)
                            
                            try:
                                if os.path.exists(img_path):
                                    with open(img_path, 'rb') as photo:
                                        bot.send_photo(
                                            telegram_id,
                                            photo,
                                            caption=f"📦 {escape_markdown_v1(prod_name)}\n💰 السعر: {price} د.ع\n📊 الكمية: {quantity}\n\n✅ تم شراؤها بنجاح!",
                                            parse_mode='Markdown'
                                        )
                                        sent_images_count += 1
                                        print(f"✅ Image sent to customer: {img_filename}")
                                else:
                                    print(f"⚠️ Image file not found: {img_path}")
                                    # Send text version as fallback
                                    bot.send_message(
                                        telegram_id,
                                        f"📦 *{escape_markdown_v1(prod_name)}*\n\n💰 السعر: {price} د.ع\n📊 الكمية: {quantity}\n\n✅ تم شراؤها بنجاح!",
                                        parse_mode='Markdown'
                                    )
                            except Exception as e:
                                print(f"❌ Error sending photo to customer: {type(e).__name__}: {str(e)}")
                                # Send text version as fallback
                                bot.send_message(
                                    telegram_id,
                                    f"📦 *{escape_markdown_v1(prod_name)}*\n\n💰 السعر: {price} د.ع\n📊 الكمية: {quantity}\n\n✅ تم شراؤها بنجاح!",
                                    parse_mode='Markdown'
                                )
                    else:
                        # No images available, send text only
                        print(f"⚠️ No images found for product {product_id}")
                        bot.send_message(
                            telegram_id,
                            f"📦 *{escape_markdown_v1(prod_name)}*\n\n💰 السعر: {price} د.ع\n📊 الكمية: {quantity}\n\n✅ تم شراؤها بنجاح!",
                            parse_mode='Markdown'
                        )
            except Exception as e:
                print(f"❌ Error processing product {product_id}: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
        
        cursor.close()
        conn.close()
        
        # Send purchase notification to customer (no order confirmation needed)
        bot.send_message(
            telegram_id,
            f"✅ تم تسجيل طلبك بنجاح!\n\n"
            f"💰 المبلغ الإجمالي: {total_amount} د.ع\n"
            f"📦 تم إضافة المبلغ إلى حسابك الآجل\n"
            f"📋 سيتم معالجة طلبك من قبل البائع",
            parse_mode='Markdown'
        )
        
        # 📋 CREATE MESSAGE FOR SELLER (NOT ORDER)
        items_text = "\n".join([f"• {escape_markdown_v1(name)} x {qty} = {qty * price} د.ع" for _, qty, price, name in seller_data['items']])
        
        message_text = (
            f"طلب جديد من متجر مغلق\n\n"
            f"👤 الزبون: {escape_markdown_v1(customer_name)}\n"
            f"📋 المنتجات:\n{items_text}\n"
            f"💰 الإجمالي: {total_amount} د.ع\n\n"
            f"تم إضافة المبلغ على الحساب الآجل للزبون"
        )
        
        # Create message in Messages table
        create_message(None, seller_id, 'closed_store_purchase', message_text)
        
        # 📱 SAVE NOTIFICATION FOR APP
        product_names = ", ".join([name for _, _, _, name in seller_data['items']])
        print(f"💾 حفظ إشعار في قاعدة البيانات للعميل {telegram_id}")
        notification_saved = save_notification(
            customer_telegram_id=telegram_id,
            notification_type='closed_store_purchase',
            title=f"✅ تم تأكيد طلبك",
            message=f"تم شراء {len(seller_data['items'])} منتج(ات) بنجاح! المبلغ: {total_amount} د.ع",
            product_names=product_names,
            total_amount=total_amount,
            seller_id=seller_id,
            data=None
        )
        print(f"✅ تم حفظ الإشعار: {notification_saved}")
        
        # Send notification to seller with message (no order reference)
        seller_notification = (
            f"📬 *رسالة جديدة - شراء من متجر مغلق*\n\n"
            f"👤 الزبون: *{escape_markdown_v1(customer_name)}*\n"
            f"📋 *المنتجات:*\n{items_text}\n"
            f"💰 *الإجمالي:* {total_amount} د.ع\n\n"
            f"✅ تم إضافة المبلغ على الحساب الآجل"
        )
        
        bot.send_message(seller_telegram_id, seller_notification, parse_mode='Markdown')
        
        # 🗑️ حذف تلقائي لصور المنتجات المشتراة من المتجر المغلق (بناءً على الكمية فقط)
        deleted_count = delete_product_images_for_closed_store(seller_id, seller_data['items'])
        
        if deleted_count > 0:
            bot.send_message(
                seller_telegram_id,
                f"🗑️ تم حذف {deleted_count} صور من المنتجات المشتراة (توفير مساحة في قاعدة البيانات)",
                parse_mode='Markdown'
            )
        
        print(f"✅ Closed store purchase recorded as MESSAGE (no order) - notifications sent!")
        return True
        
    except Exception as e:
        print(f"❌ Error processing closed store purchase: {e}")
        traceback.print_exc()
        return False


@bot.callback_query_handler(func=lambda call: call.data == "checkout_cart")
def handle_checkout_cart(call):
    try:
        telegram_id = call.from_user.id
        cart_items = get_cart_items_db(telegram_id)
        
        if not cart_items:
            bot.answer_callback_query(call.id, "السلة فارغة")
            return

        # Admin store filtering removed to allow purchases
        cleaned_cart = cart_items

        if not cleaned_cart:
            bot.send_message(call.message.chat.id, "⛔ السلة لا تحتوي على منتجات قابلة للشراء حالياً.")
            return

        # استخدم cleaned_cart للمتابعة
        cart_items = cleaned_cart
        
        # ====== التعديل الجديد ======
        # التحقق إذا كان المستخدم زائراً (غير مسجل)
        is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
        
        if is_guest:
            # للزوار، نطلب منهم إدخال معلوماتهم أولاً
            user_states[telegram_id] = {
                "step": "guest_checkout_info",
                "is_guest": True,
                "cart_items": cart_items
            }
            
            bot.send_message(call.message.chat.id,
                            "📝 **معلومات الزائر**\n\n"
                            "بما أنك زائر (غير مسجل)، نحتاج لمعلوماتك لإتمام الطلب.\n\n"
                            "يرجى إدخال اسمك الكامل:")
            
            bot.answer_callback_query(call.id)
            return
        
        # تجميع المنتجات حسب البائع
        items_by_seller = {}
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            
            if seller_id not in items_by_seller:
                items_by_seller[seller_id] = {
                    'seller_name': seller_name,
                    'items': [],
                    'subtotal': 0
                }
            
            # Store only the essential data: (product_id, quantity, price, name)
            items_by_seller[seller_id]['items'].append((product_id, quantity, price, name))
            items_by_seller[seller_id]['subtotal'] += price * quantity
        
        # ========== التحقق من نوع المتاجر (مغلقة أم مفتوحة) ==========
        # إذا كانت جميع المتاجر مغلقة والزبون مسجل، عمل طلب مؤكد مباشرة
        
        all_sellers_closed = True
        user_info = get_user(telegram_id)
        
        for seller_id in items_by_seller.keys():
            seller = get_seller_by_id(seller_id)
            if not seller:
                all_sellers_closed = False
                break
            
            # seller columns: sellerid, telegramid, username, storename, createdat, status, suspensionreason, suspendedby, suspendedat, imagepath, requirecustomerregistration
            # index:           0          1             2         3           4         5       6                  7            8           9           10
            require_registration = seller[10] if len(seller) > 10 else 0
            if not require_registration:
                # متجر مفتوح
                all_sellers_closed = False
                break
            
            # التحقق من أن الزبون مسجل في هذا المتجر المقفول
            if not user_info:
                all_sellers_closed = False
                break
            
            is_registered = is_customer_registered_for_store_by_telegram_id(telegram_id, seller_id)
            if not is_registered:
                all_sellers_closed = False
                break
        
        # إذا كانت جميع المتاجر مغلقة والزبون مسجل في جميعها
        if all_sellers_closed and user_info:
            print(f"✅ جميع المتاجر مغلقة - إنشاء طلب مؤكد مباشرة")
            # إنشاء طلب لكل متجر مقفول
            total_amount_all = 0
            for seller_id, seller_data in items_by_seller.items():
                create_confirmed_order_for_closed_store(call.message, telegram_id, seller_id, seller_data, user_info)
                total_amount_all += seller_data.get('subtotal', 0)
            
            # حذف المنتجات من السلة
            clear_cart_db(telegram_id)
            
            bot.answer_callback_query(call.id, "✅ تم تأكيد طلبك!")
            
            # رسالة مفصلة تتضمن المبلغ المخصوم
            detail_msg = f"✅ تم إنزال طلبك بنجاح!\n\n"
            detail_msg += f"💰 المبلغ المخصوم: {total_amount_all:,.0f} د.ع\n"
            detail_msg += f"سيتم معالجة الطلب من قبل البائع."
            
            bot.send_message(call.message.chat.id, detail_msg)
            return
        
        # خلاف ذلك، استخدم النظام الحالي (خطوات إضافية للمتاجر المفتوحة)
        user_states[telegram_id] = {
            "step": "checkout_select_seller",
            "items_by_seller": items_by_seller,
            "current_seller_index": 0
        }
        
        seller_ids = list(items_by_seller.keys())
        first_seller_id = seller_ids[0]
        first_seller_data = items_by_seller[first_seller_id]
        
        start_checkout_for_seller(call.message, telegram_id, first_seller_id, first_seller_data)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        bot.send_message(call.message.chat.id, f"⚠️ خطأ في إتمام الطلب: {e}")
        traceback.print_exc()

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "guest_checkout_info")
def process_guest_checkout_info(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    full_name = message.text.strip()
    
    if not full_name:
        bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
        return
    
    state["guest_name"] = full_name
    state["step"] = "guest_checkout_phone"
    
    bot.send_message(message.chat.id,
                    "📞 **رقم الهاتف**\n\n"
                    "يرجى إدخال رقم هاتفك للتواصل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم يكن هناك رقم هاتف.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "guest_checkout_phone")
def process_guest_checkout_phone(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    phone = message.text.strip()
    if phone.lower() == "تخطي":
        phone = None
    
    state["guest_phone"] = phone
    
    # تحويل عناصر السلة إلى تنسيق مناسب
    cart_items = state["cart_items"]
    items_by_seller = {}
    
    for item in cart_items:
        product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
        
        if seller_id not in items_by_seller:
            items_by_seller[seller_id] = {
                'seller_name': seller_name,
                'items': [],
                'subtotal': 0
            }
        
        items_by_seller[seller_id]['items'].append((product_id, quantity, price, name))
        items_by_seller[seller_id]['subtotal'] += price * quantity
    
    # تحديث حالة المستخدم
    state["step"] = "checkout_select_seller"
    state["items_by_seller"] = items_by_seller
    state["current_seller_index"] = 0
    state["is_guest"] = True
    
    seller_ids = list(items_by_seller.keys())
    first_seller_id = seller_ids[0]
    first_seller_data = items_by_seller[first_seller_id]
    
    start_checkout_for_seller(message, telegram_id, first_seller_id, first_seller_data)

def start_checkout_for_seller(message, user_id, seller_id, seller_data):
    seller = get_seller_by_id(seller_id)
    seller_name = seller[3] if seller else seller_data['seller_name']
    safe_seller_name = escape_markdown_v1(seller_name) if seller_name else "متجر"
    
    subtotal = seller_data['subtotal']
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = user_id in user_states and user_states.get(user_id, {}).get('is_guest', False)
    
    if is_guest:
        text = f"🏪 **إنهاء طلب من المتجر**\n\n"
        text += f"المتجر: {safe_seller_name}\n"
        text += f"💰 المجموع: {subtotal} IQD\n\n"
        text += "🔸 **وضع الزائر:**\n"
        text += "• يمكنك الشراء نقداً فقط\n"
        text += "• لا يمكنك الشراء على الحساب\n"
        text += "• لن يتم حفظ سجل طلباتك\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📤 إرسال الطلب", callback_data=f"payment_cash_{seller_id}"))
        markup.add(types.InlineKeyboardButton("❌ إلغاء الطلب من هذا المتجر", callback_data=f"skip_seller_{seller_id}"))
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        return
    
    # للمستخدمين المسجلين
    user_info = get_user(user_id)
    customer = None
    if user_info:
        customer = get_credit_customer(seller_id, user_info[4], user_info[5])
    
    customer_balance = 0
    limit_info = None
    
    if customer:
        customer_balance = get_customer_balance(customer[0], seller_id)
        limit_info = get_credit_limit_info(customer[0], seller_id)
    
    text = f"🏪 **إنهاء طلب من المتجر**\n\n"
    text += f"المتجر: {safe_seller_name}\n"
    text += f"💰 المجموع: {subtotal} IQD\n"
    
    if customer:
        text += f"💰 رصيدك الآجل: {customer_balance} IQD\n"
        
        if limit_info:
            text += f"💳 الحد الائتماني: {limit_info['max_limit']:,.0f} دينار\n"
            text += f"📊 المستخدم: {limit_info['current_used']:,.0f} دينار\n"
            text += f"📈 المتبقي: {limit_info['available']:,.0f} دينار\n"
            # The 'status' line was removed as per the instruction's implied removal of check_credit_limit output
        
        if customer_balance > 0:
            text += f"💰 المبلغ المتبقي بعد خصم الرصيد: {max(0, subtotal - customer_balance)} IQD\n"
    
    
    # FORCED SINGLE BUTTON LAYOUT
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📤 إرسال الطلب", callback_data=f"payment_cash_{seller_id}"))
    markup.add(types.InlineKeyboardButton("❌ إلغاء الطلب من هذا المتجر", callback_data=f"skip_seller_{seller_id}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_cash_"))
def handle_payment_cash(call):
    seller_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    if telegram_id not in user_states or "items_by_seller" not in user_states[telegram_id]:
        bot.answer_callback_query(call.id, "انتهت الجلسة")
        return
    
    state = user_states[telegram_id]
    seller_data = state["items_by_seller"][seller_id]
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = state.get('is_guest', False)
    
    if is_guest:
        # للزوار، لا يوجد رصيد آجل
        user_states[telegram_id]["current_seller_payment"] = "cash"
        user_states[telegram_id]["current_seller_id"] = seller_id
        user_states[telegram_id]["fully_paid"] = True
        
        bot.send_message(call.message.chat.id,
                        "📦 **معلومات التوصيل**\n\n"
                        "يرجى إدخال عنوان التوصيل (اختياري):\n"
                        "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
        
        bot.answer_callback_query(call.id)
        return
    
    # للمستخدمين المسجلين (الكود القديم)
    # التحقق إذا كان الزبون آجلاً
    user_info = get_user(telegram_id)
    customer = None
    if user_info:
        customer = get_credit_customer(seller_id, user_info[4], user_info[5])
    
    if customer:
        customer_balance = get_customer_balance(customer[0], seller_id)
        subtotal = seller_data['subtotal']
        
        if customer_balance >= subtotal:
            # يمكن الدفع من الرصيد الآجل
            # User requested one button flow. Let's redirect to "Full Cash" logic automatically or show choice?
            # Request was "There appear two buttons... make it one".
            # If I show choice here, it's 2 buttons again.
            # Let's skip this for now to ensure "One Button" feel, or maybe just proceed as Standard Order.
            # If we skip, we treat it as Cash/Standard.
            pass
            
            # markup = types.InlineKeyboardMarkup(row_width=2)
            # markup.add(
            #     types.InlineKeyboardButton("💵 دفع نقداً كاملاً", callback_data=f"payment_full_cash_{seller_id}"),
            #     types.InlineKeyboardButton("💳 دفع من الرصيد الآجل", callback_data=f"payment_from_balance_{seller_id}")
            # )
            
            # bot.send_message(call.message.chat.id,
            #                 f"💰 **لديك رصيد آجل**\n\n"
            #                 f"رصيدك الآجل: {customer_balance} IQD\n"
            #                 f"قيمة الطلب: {subtotal} IQD\n\n"
            #                 f"اختر طريقة الدفع:",
            #                 reply_markup=markup)
            # bot.answer_callback_query(call.id)
            # return
    
    user_states[telegram_id]["current_seller_payment"] = "cash"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = True
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_full_cash_"))
def handle_payment_full_cash(call):
    seller_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    user_states[telegram_id]["current_seller_payment"] = "cash"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = True
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_from_balance_"))
def handle_payment_from_balance(call):
    seller_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    if telegram_id not in user_states or "items_by_seller" not in user_states[telegram_id]:
        bot.answer_callback_query(call.id, "انتهت الجلسة")
        return
    
    state = user_states[telegram_id]
    seller_data = state["items_by_seller"][seller_id]
    subtotal = seller_data['subtotal']
    
    user_info = get_user(telegram_id)
    customer = None
    if user_info:
        customer = get_credit_customer(seller_id, user_info[4], user_info[5])
    
    if not customer:
        bot.answer_callback_query(call.id, "أنت لست زبوناً آجلاً")
        return
    
    customer_balance = get_customer_balance(customer[0], seller_id)
    
    if customer_balance < subtotal:
        bot.answer_callback_query(call.id, "رصيدك الآجل غير كافٍ")
        return
    
    user_states[telegram_id]["current_seller_payment"] = "credit"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = True
    user_states[telegram_id]["use_balance"] = True
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_credit_"))
def handle_payment_credit(call):
    seller_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    if telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest'):
        bot.answer_callback_query(call.id, "⛔ الزوار لا يمكنهم الشراء على الحساب")
        return
    
    if telegram_id not in user_states or "items_by_seller" not in user_states[telegram_id]:
        bot.answer_callback_query(call.id, "انتهت الجلسة")
        return
    
    seller = get_seller_by_id(seller_id)
    if not seller:
        bot.answer_callback_query(call.id, "المتجر غير موجود")
        return
    
    state = user_states[telegram_id]
    seller_data = state["items_by_seller"][seller_id]
    subtotal = seller_data['subtotal']
    
    # التحقق إذا كان الزبون آجلاً
    user_info = get_user(telegram_id)
    customer = None
    if user_info:
        customer = get_credit_customer(seller_id, user_info[4], user_info[5])
    
    if not customer:
        bot.answer_callback_query(call.id, "⛔ يجب أن تكون زبوناً آجلاً للشراء على الحساب")
        return
    
    # التحقق من الحد الائتماني
    can_purchase, message_text, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, subtotal)
    
    if not can_purchase:
        bot.answer_callback_query(call.id, message_text)
        return
    
    current_balance = get_customer_balance(customer[0], seller_id)
    new_balance = current_balance + subtotal
    
    confirm_text = f"💳 **الشراء على الحساب**\n\n"
    confirm_text += f"المتجر: {seller[3]}\n"
    confirm_text += f"💰 قيمة الطلب: {subtotal} IQD\n"
    confirm_text += f"💰 رصيدك الحالي: {current_balance} IQD\n"
    confirm_text += f"💰 رصيدك بعد الشراء: {new_balance} IQD\n"
    confirm_text += f"💳 الحد المتبقي: {remaining:,.0f} دينار\n\n"
    
    if message_text and "تحذير" in message_text:
        confirm_text += f"⚠️ **ملاحظة:** {message_text}\n\n"
    
    if current_balance >= subtotal:
        confirm_text += f"💡 **ملاحظة:** لديك رصيد كافٍ لتغطية الطلب. هل تريد الدفع من الرصيد الآجل؟\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💳 دفع من الرصيد", callback_data=f"pay_from_balance_{seller_id}"),
            types.InlineKeyboardButton("📝 إضافة للدين", callback_data=f"add_to_credit_{seller_id}")
        )
        
        bot.send_message(call.message.chat.id, confirm_text, reply_markup=markup, parse_mode='Markdown')
    else:
        confirm_text += f"هل تريد إضافة هذا المبلغ للدين؟"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ نعم، إضافة للدين", callback_data=f"add_to_credit_{seller_id}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_checkout")
        )
        
        bot.send_message(call.message.chat.id, confirm_text, reply_markup=markup, parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_from_balance_"))
def handle_pay_from_balance(call):
    seller_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    user_states[telegram_id]["current_seller_payment"] = "credit"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = True
    user_states[telegram_id]["use_balance"] = True
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_credit_"))
def handle_add_to_credit(call):
    seller_id = int(call.data.split("_")[3])
    telegram_id = call.from_user.id
    
    user_states[telegram_id]["current_seller_payment"] = "credit"
    user_states[telegram_id]["current_seller_id"] = seller_id
    user_states[telegram_id]["fully_paid"] = False
    user_states[telegram_id]["use_balance"] = False
    
    bot.send_message(call.message.chat.id,
                    "📦 **معلومات التوصيل**\n\n"
                    "يرجى إدخال عنوان التوصيل (اختياري):\n"
                    "يمكنك كتابة 'تخطي' إذا لم تكن بحاجة للتوصيل.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("skip_seller_"))
def handle_skip_seller(call):
    seller_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    if telegram_id not in user_states or "items_by_seller" not in user_states[telegram_id]:
        bot.answer_callback_query(call.id, "انتهت الجلسة")
        return
    
    state = user_states[telegram_id]
    
    # حذف عناصر هذا البائع من السلة
    seller_items = state["items_by_seller"][seller_id]['items']
    for product_id, quantity, price, name in seller_items:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carts WHERE UserID=? AND ProductID=?", (telegram_id, product_id))
        conn.commit()
        conn.close()
    
    # حذف البائع من القائمة
    del state["items_by_seller"][seller_id]
    
    if not state["items_by_seller"]:
        bot.send_message(call.message.chat.id, "✅ تم إلغاء جميع الطلبات")
        del user_states[telegram_id]
        show_buyer_main_menu(call.message)
    else:
        seller_ids = list(state["items_by_seller"].keys())
        next_seller_id = seller_ids[0]
        next_seller_data = state["items_by_seller"][next_seller_id]
        
        start_checkout_for_seller(call.message, telegram_id, next_seller_id, next_seller_data)
    
    bot.answer_callback_query(call.id)

# معالج منفصل ومحدد لإدخال عنوان التوصيل
@bot.message_handler(func=lambda message: 
                     message.from_user.id in user_states and 
                     "current_seller_payment" in user_states[message.from_user.id] and
                     "current_seller_id" in user_states[message.from_user.id])
def process_delivery_address(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    
    delivery_address = message.text.strip()
    if delivery_address.lower() == 'تخطي':
        delivery_address = None
    
    seller_id = state["current_seller_id"]
    payment_method = state["current_seller_payment"]
    seller_data = state["items_by_seller"][seller_id]
    fully_paid = state.get("fully_paid", False)
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = state.get('is_guest', False)
    
    if is_guest:
        # للزوار، إنشاء طلب خاص
        guest_name = state.get("guest_name", "زائر")
        guest_phone = state.get("guest_phone")
        
        # إنشاء طلب للزائر
        # Extract only (product_id, quantity, price) from seller_data['items']
        cart_items_for_guest = [(pid, qty, price) for pid, qty, price, name in seller_data['items']]
        order_id, total = create_order_for_guest(
            telegram_id, 
            seller_id, 
            cart_items_for_guest, 
            delivery_address, 
            guest_name, 
            guest_phone, 
            payment_method, 
            fully_paid
        )
        
        if order_id is None:
            bot.send_message(message.chat.id, f"❌ **تعذر إنشاء الطلب:** {total}")
            # حذف البائع من القائمة ومتابعة مع البائع التالي
            del state["items_by_seller"][seller_id]
            
            if state["items_by_seller"]:
                seller_ids = list(state["items_by_seller"].keys())
                next_seller_id = seller_ids[0]
                next_seller_data = state["items_by_seller"][next_seller_id]
                
                start_checkout_for_seller(message, telegram_id, next_seller_id, next_seller_data)
            else:
                del user_states[telegram_id]
                browse_without_registration(message)
            return
    else:
        # للمستخدمين المسجلين (الكود القديم)
        # التحقق من الحد الائتماني إذا كان الشراء على الحساب
        if payment_method == 'credit' and not fully_paid:
            user_info = get_user(telegram_id)
            if user_info:
                customer = get_credit_customer(seller_id, user_info[4], user_info[5])
                if customer:
                    subtotal = seller_data['subtotal']
                    can_purchase, message_text, max_limit, current_used, remaining = check_credit_limit(customer[0], seller_id, subtotal)
                    
                    if not can_purchase:
                        bot.send_message(message.chat.id, f"❌ **تعذر إنشاء الطلب:** {message_text}")
                        # حذف البائع من القائمة ومتابعة مع البائع التالي
                        del state["items_by_seller"][seller_id]
                        
                        if state["items_by_seller"]:
                            seller_ids = list(state["items_by_seller"].keys())
                            next_seller_id = seller_ids[0]
                            next_seller_data = state["items_by_seller"][next_seller_id]
                            
                            start_checkout_for_seller(message, telegram_id, next_seller_id, next_seller_data)
                        else:
                            del user_states[telegram_id]
                            show_buyer_main_menu(message)
                        return
        
        # إنشاء الطلب
        # Extract only (product_id, quantity, price) from seller_data['items']
        cart_items_for_order = [(pid, qty, price) for pid, qty, price, name in seller_data['items']]
        order_id, total = create_order(
            telegram_id, 
            seller_id, 
            cart_items_for_order, 
            delivery_address, 
            None, 
            payment_method, 
            fully_paid
        )
        
        if order_id is None:
            # فشل إنشاء الطلب بسبب الحد الائتماني
            bot.send_message(message.chat.id, f"❌ **تعذر إنشاء الطلب:** {total}")
            # حذف البائع من القائمة ومتابعة مع البائع التالي
            del state["items_by_seller"][seller_id]
            
            if state["items_by_seller"]:
                seller_ids = list(state["items_by_seller"].keys())
                next_seller_id = seller_ids[0]
                next_seller_data = state["items_by_seller"][next_seller_id]
                
                start_checkout_for_seller(message, telegram_id, next_seller_id, next_seller_data)
            else:
                del user_states[telegram_id]
                show_buyer_main_menu(message)
            return
    
    # حذف عناصر هذا البائع من السلة
    for product_id, quantity, price, name in seller_data['items']:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carts WHERE UserID=? AND ProductID=?", (telegram_id, product_id))
        conn.commit()
        conn.close()
    
    # حذف البائع من القائمة
    del state["items_by_seller"][seller_id]
    
    seller = get_seller_by_id(seller_id)
    seller_name = seller[3] if seller else "المتجر"
    
    # For closed stores, generate and send receipt image instead of waiting message
    if is_guest or (seller and seller[9] == 1):  # 1 = closed store
        try:
            from utils.receipt_generator import generate_order_card
            
            # Get buyer info
            buyer_info = get_user(telegram_id)
            buyer_name = buyer_info[2] if buyer_info and len(buyer_info) > 2 else "الزبون"
            buyer_phone = buyer_info[4] if buyer_info and len(buyer_info) > 4 else "N/A"
            
            # Prepare order details for receipt
            order_details = (order_id, 0, 0, total, "Confirmed", "", delivery_address, "")
            
            # Prepare items for receipt - need all details
            items_full = []
            for pid, qty, price, name in seller_data['items']:
                items_full.append((pid, qty, price, name, "", "", "", "", "", "", ""))
            
            # Generate receipt image
            receipt_img = generate_order_card(order_details, items_full, buyer_name, buyer_phone, seller_name)
            
            if receipt_img:
                caption = (f"✅ **تم إنشاء الطلب بنجاح!**\n\n"
                          f"🆔 رقم الطلب: {order_id}\n"
                          f"🏪 المتجر: {seller_name}\n"
                          f"💰 الإجمالي: {total} IQD\n"
                          f"💳 طريقة الدفع: {'نقداً' if payment_method == 'cash' else 'على الحساب'}\n"
                          f"💵 حالة الدفع: مؤكد وجاهز للتنفيذ\n\n"
                          f"سيقوم البائع بمعالجة الطلب قريباً.")
                
                bot.send_photo(message.chat.id, receipt_img, caption=caption, parse_mode='Markdown')
                print(f"✅ Receipt image sent for Order #{order_id}")
            else:
                # Fallback to text message if image generation fails
                bot.send_message(message.chat.id,
                                f"✅ **تم إنشاء الطلب بنجاح!**\n\n"
                                f"🆔 رقم الطلب: {order_id}\n"
                                f"🏪 المتجر: {seller_name}\n"
                                f"💰 الإجمالي: {total} IQD\n"
                                f"💳 طريقة الدفع: {'نقداً' if payment_method == 'cash' else 'على الحساب'}\n"
                                f"💵 حالة الدفع: مؤكد وجاهز للتنفيذ\n\n"
                                f"سيقوم البائع بمعالجة الطلب قريباً.")
        except Exception as e:
            print(f"⚠️ Error generating receipt image: {e}")
            # Fallback to text message
            bot.send_message(message.chat.id,
                            f"✅ **تم إنشاء الطلب بنجاح!**\n\n"
                            f"🆔 رقم الطلب: {order_id}\n"
                            f"🏪 المتجر: {seller_name}\n"
                            f"💰 الإجمالي: {total} IQD\n"
                            f"💳 طريقة الدفع: {'نقداً' if payment_method == 'cash' else 'على الحساب'}\n"
                            f"💵 حالة الدفع: مؤكد وجاهز للتنفيذ\n\n"
                            f"سيقوم البائع بمعالجة الطلب قريباً.")
    else:
        # For open stores, send regular message
        bot.send_message(message.chat.id,
                        f"✅ **تم إنشاء الطلب بنجاح!**\n\n"
                        f"🆔 رقم الطلب: {order_id}\n"
                        f"🏪 المتجر: {seller_name}\n"
                        f"💰 الإجمالي: {total} IQD\n"
                        f"💳 طريقة الدفع: {'نقداً' if payment_method == 'cash' else 'على الحساب'}\n"
                        f"💵 حالة الدفع: {'مدفوع بالكامل' if fully_paid else 'غير مدفوع بالكامل'}\n\n"
                        f"سيقوم البائع بالتواصل معك قريباً.")
    
    # الانتقال للبائع التالي إن وجد
    if state["items_by_seller"]:
        seller_ids = list(state["items_by_seller"].keys())
        next_seller_id = seller_ids[0]
        next_seller_data = state["items_by_seller"][next_seller_id]
        
        start_checkout_for_seller(message, telegram_id, next_seller_id, next_seller_data)
    else:
        # ====== التعديل الجديد ======
        # التحقق إذا كان المستخدم زائراً (غير مسجل)
        if is_guest:
            del user_states[telegram_id]
            browse_without_registration(message)
        else:
            del user_states[telegram_id]
            show_buyer_main_menu(message)
    """
    Create 'Confirmed' order immediately for closed stores with registered customers.
    
    Parameters:
    - message: Telegram message object
    - telegram_id: Customer telegram ID
    - seller_id: Seller ID
    - seller_data: Dict containing {'seller_name', 'items': [(product_id, quantity, price, name)], 'subtotal'}
    - user_info: Tuple from get_user() containing customer info
    
    Returns: True if successful, False otherwise
    """
    try:
        print(f"🔄 Creating confirmed order for closed store {seller_id} for customer {telegram_id}")
        
        # 1. Format items for order creation: [(product_id, quantity, price), ...]
        items = [(int(product_id), int(quantity), float(price)) for product_id, quantity, price, name in seller_data['items']]
        
        # 2. Create order with status='Confirmed' (آجل)
        # Using create_order with credit payment (آجل) and set to Confirmed
        result = create_order(
            buyer_id=telegram_id,
            seller_id=seller_id,
            cart_items=items,
            delivery_address=None,  # No address needed for closed stores
            payment_method='credit',  # آجل (credit)
            fully_paid=False
        )
        
        # Handle both tuple (order_id, total) and single value responses
        if isinstance(result, tuple) and len(result) == 2:
            order_id, total_amount = result
            # Check if order_id is None (error case)
            if order_id is None:
                print(f"❌ Order creation failed: {total_amount}")
                return False
        else:
            order_id = result
            total_amount = seller_data.get('subtotal', 0)
        
        if not order_id:
            print(f"❌ Failed to create order for closed store {seller_id}")
            return False
        
        print(f"✅ Order created with ID: {order_id}")
        
        # 3. Get seller telegram ID for notification
        seller = get_seller_by_id(seller_id)
        if not seller:
            print(f"⚠️ Seller {seller_id} not found")
            return False
        
        seller_telegram_id = seller[1] if seller else None
        seller_name = escape_markdown_v1(seller[3]) if seller else "المتجر"
        
        # 4. Get customer name from user_info
        # user_info structure: (user_id, telegram_id, first_name, last_name, phone, ...)
        customer_name = escape_markdown_v1(user_info[2] if len(user_info) > 2 else "الزبون")
        
        # 5. Format items list for notification
        items_text = "\n".join([f"• {escape_markdown_v1(name)} x {qty}" for _, qty, _, name in seller_data['items']])
        
        # 6. Create notification message for store owner
        subtotal = seller_data.get('subtotal', 0)
        notification = (
            f"📦 *طلب جديد من زبون آجل*\n\n"
            f"👤 الزبون: *{customer_name}*\n"
            f"🏪 المتجر: *{seller_name}*\n\n"
            f"📋 *المنتجات المطلوبة:*\n"
            f"{items_text}\n\n"
            f"💰 *الإجمالي:* {subtotal} د.ع\n\n"
            f"📌 رقم الطلب: `{order_id}`"
        )
        
        # 7. Send notification to store owner
        if seller_telegram_id:
            try:
                bot.send_message(seller_telegram_id, notification, parse_mode='Markdown')
                print(f"✅ Notification sent to seller {seller_telegram_id}")
            except Exception as notify_error:
                print(f"⚠️ Failed to send notification to seller: {notify_error}")
                # Don't fail the order creation if notification fails
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating confirmed order for closed store: {e}")
        traceback.print_exc()
        return False

def create_order_for_guest(buyer_id, seller_id, cart_items, delivery_address=None, guest_name=None, guest_phone=None, payment_method='cash', fully_paid=False):
    """إنشاء طلب للزوار (غير المسجلين)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    total = 0
    
    for pid, qty, price in cart_items:
        total += price * qty

    # إضافة مستخدم مؤقت للزائر
    temp_user_id = f"guest_{buyer_id}_{int(time.time())}"
    
    # إدراج طلب مع معلومات الزائر
    query = """
        INSERT INTO Orders (BuyerID, SellerID, Total, DeliveryAddress, Notes, PaymentMethod, FullyPaid) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    params = (temp_user_id, seller_id, total, delivery_address, f"زائر: {guest_name} - {guest_phone}", payment_method, fully_paid)
    
    if IS_POSTGRES:
        query += " RETURNING OrderID"
    
    cursor.execute(query, params)
    order_id = cursor.lastrowid
    
    # 🛡️ Safe Fallback for Postgres
    if IS_POSTGRES and not order_id:
        try:
            res = cursor.fetchone()
            if res:
                order_id = res[0]
                print(f"DEBUG: Retrieved Guest OrderID via fallback fetchone")
        except Exception as e:
            print(f"DEBUG: Error in guest fallback fetchone: {e}")

    # Optimize: Fetch product data using valid transaction cursor to avoid locking/visibility issues
    # Pre-fetch check or inline check
    for pid, qty, price in cart_items:
        # Inline lookup using SAME cursor
        cursor.execute("SELECT Quantity FROM Products WHERE ProductID = ?", (pid,))
        res = cursor.fetchone()
        
        if not res:
            print(f"⚠️ Warning: Product {pid} not found during Guest Order {order_id} creation. Skipping Item.")
            continue
            
        current_qty_in_db = res[0]
        
        cursor.execute("INSERT INTO OrderItems (OrderID, ProductID, Quantity, Price) VALUES (?, ?, ?, ?)",
                       (order_id, pid, qty, price))
                       
        new_qty = current_qty_in_db - qty
        if new_qty < 0:
            new_qty = 0
        cursor.execute("UPDATE Products SET Quantity=? WHERE ProductID=?", (new_qty, pid))
        
        # 🗑️ حذف الصور من ImageStorage (الصور ترسل للمشتري ثم تُحذف من قاعدة البيانات)
        if IS_POSTGRES:
            cursor.execute("""
                SELECT filename FROM imagestorage WHERE productid=%s
            """, (pid,))
        else:
            cursor.execute("""
                SELECT FileName FROM imagestorage WHERE ProductID=?
            """, (pid,))
        
        image_paths = cursor.fetchall()
        for (filename,) in image_paths:
            if filename:
                try:
                    if IS_POSTGRES:
                        cursor.execute("DELETE FROM imagestorage WHERE FileName = %s", (filename,))
                    else:
                        cursor.execute("DELETE FROM imagestorage WHERE FileName = ?", (filename,))
                    print(f"🗑️ حذفت صورة {filename} من ImageStorage بعد البيع (guest order)")
                except Exception as del_err:
                    print(f"⚠️ خطأ في حذف الصورة {filename}: {del_err}")
        
        # 📢 إشعار عندما تصبح الكمية صفر
        if new_qty == 0:
            try:
                cursor.execute("SELECT ProductID, Name FROM Products WHERE ProductID = ?", (pid,))
                prod_info = cursor.fetchone()
                
                cursor.execute("SELECT StoreName, TelegramID FROM Sellers WHERE SellerID = ?", (seller_id,))
                seller_info = cursor.fetchone()
                
                if prod_info and seller_info:
                    product_name = prod_info[1]
                    store_name = seller_info[0]
                    seller_telegram = seller_info[1]
                    
                    try:
                        msg = f"⚠️ **تنبيه: انتهت الكمية!**\n\n"
                        msg += f"🏪 المتجر: {store_name}\n"
                        msg += f"📦 المنتج: {product_name}\n"
                        msg += f"⏰ التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        msg += f"الكمية أصبحت صفر - يرجى إضافة منتجات جديدة"
                        bot.send_message(seller_telegram, msg, parse_mode='Markdown')
                    except Exception as msg_err:
                        print(f"⚠️ خطأ في إرسال إشعار البائع: {msg_err}")
            except Exception as notif_err:
                print(f"⚠️ خطأ في إرسال الإشعارات: {notif_err}")
    
    conn.commit()
    conn.close()
    
    notify_seller_of_order(order_id, temp_user_id, seller_id)
    return order_id, total

@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def handle_clear_cart(call):
    try:
        telegram_id = call.from_user.id
        clear_cart_db(telegram_id)
        
        bot.answer_callback_query(call.id, "✅ تم تفريغ السلة")
        bot.send_message(call.message.chat.id, "✅ تم تفريغ سلة المشتريات بنجاح.")
        
        # ====== التعديل الجديد ======
        # التحقق إذا كان المستخدم زائراً (غير مسجل)
        is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
        
        if is_guest:
            browse_without_registration(call.message)
        else:
            show_buyer_main_menu(call.message)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in clear_cart: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "edit_cart_quantities")
def handle_edit_cart_quantities(call):
    try:
        telegram_id = call.from_user.id
        cart_items = get_cart_items_db(telegram_id)
        
        if not cart_items:
            bot.answer_callback_query(call.id, "السلة فارغة")
            return
        
        for item in cart_items:
            product_id, quantity, price, name, desc, img_path, available_qty, seller_id, seller_name = item
            
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("➕", callback_data=f"increase_cart_{product_id}"),
                types.InlineKeyboardButton(f"الكمية: {quantity}", callback_data=f"set_quantity_{product_id}"),
                types.InlineKeyboardButton("➖", callback_data=f"decrease_cart_{product_id}"),
                types.InlineKeyboardButton("🗑️ حذف", callback_data=f"remove_cart_{product_id}")
            )
            
            caption = f"🛒 **{name}**\n💰 السعر: {price} IQD\n📦 الكمية: {quantity}\n💰 المجموع: {price * quantity} IQD\n🏪 {seller_name}"
            
            if img_path and os.path.exists(img_path):
                try:
                    with open(img_path, 'rb') as photo:
                        bot.send_photo(call.message.chat.id, photo, caption=caption, reply_markup=markup, parse_mode='Markdown')
                except:
                    bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode='Markdown')
            else:
                bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode='Markdown')
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in edit_cart_quantities: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("increase_cart_"))
def handle_increase_cart(call):
    product_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    cart_items = get_cart_items_db(telegram_id)
    current_qty = 0
    
    for item in cart_items:
        if item[0] == product_id:
            current_qty = item[1]
            break
    
    product = get_product_by_id(product_id)
    if not product:
        bot.answer_callback_query(call.id, "المنتج غير موجود")
        return
    
    available_qty = product[7]
    
    if current_qty >= available_qty:
        bot.answer_callback_query(call.id, f"⚠️ الحد الأقصى للكمية المتاحة: {available_qty}")
        return
    
    update_cart_quantity_db(telegram_id, product_id, current_qty + 1)
    
    # Update View
    update_cart_view(call.message.chat.id, call.message.message_id, telegram_id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("decrease_cart_"))
def handle_decrease_cart(call):
    product_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    cart_items = get_cart_items_db(telegram_id)
    current_qty = 0
    for item in cart_items:
        if item[0] == product_id:
            current_qty = item[1]
            break
            
    if current_qty > 1:
        update_cart_quantity_db(telegram_id, product_id, current_qty - 1)
        update_cart_view(call.message.chat.id, call.message.message_id, telegram_id)
        bot.answer_callback_query(call.id)
    else:
        bot.answer_callback_query(call.id, "الحد الأدنى هو 1. للحذف استخدم زر الحذف.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_cart_"))
def handle_remove_cart(call):
    try:
        product_id = int(call.data.split("_")[2])
        telegram_id = call.from_user.id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carts WHERE UserID=? AND ProductID=?", (telegram_id, product_id))
        conn.commit()
        conn.close()
        
        update_cart_view(call.message.chat.id, call.message.message_id, telegram_id)
        bot.answer_callback_query(call.id, "تم حذف المنتج")
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in remove_cart: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_quantity_"))
def handle_set_quantity(call):
    product_id = int(call.data.split("_")[2])
    telegram_id = call.from_user.id
    
    user_states[telegram_id] = {
        "step": "set_cart_quantity",
        "product_id": product_id
    }
    
    bot.send_message(call.message.chat.id,
                    "📦 **تحديد الكمية**\n\n"
                    "يرجى إدخال الكمية الجديدة:")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] == "set_cart_quantity")
def process_set_cart_quantity(message):
    telegram_id = message.from_user.id
    state = user_states[telegram_id]
    product_id = state["product_id"]
    
    try:
        new_quantity = int(message.text)
        if new_quantity <= 0:
            bot.send_message(message.chat.id, "الرجاء إدخال كمية صحيحة أكبر من صفر.")
            return
    except:
        bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح للكمية.")
        return
    
    product = get_product_by_id(product_id)
    if not product:
        bot.send_message(message.chat.id, "المنتج غير موجود")
        del user_states[telegram_id]
        return
    
    available_qty = product[7]
    
    if new_quantity > available_qty:
        bot.send_message(message.chat.id, f"⚠️ الحد الأقصى للكمية المتاحة: {available_qty}")
        del user_states[telegram_id]
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Carts SET Quantity = ? WHERE UserID=? AND ProductID=?", 
                  (new_quantity, telegram_id, product_id))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"✅ تم تحديث الكمية إلى {new_quantity}")
    
    del user_states[telegram_id]
    view_cart(message, user_id=telegram_id)

# ====== نظام الرسائل ======
# ====== نظام الرسائل ======
@bot.message_handler(func=lambda message: "الرسائل" in message.text)
def seller_messages(message):
    print(f"📩 DEBUG: Message handler triggered for '{message.text}' by {message.from_user.id}")
    try:
        telegram_id = message.from_user.id
        from utils.receipt_generator import generate_order_card # Late import to avoid circular issues
        
        # Double check it is a seller
        if not is_seller(telegram_id):
            print(f"⛔ User {telegram_id} is NOT a seller.")
            return

        if not is_seller_active(telegram_id):
            bot.send_message(message.chat.id,
                            "⛔ **حسابك معطل**\n\n"
                            "لا يمكنك الوصول إلى الرسائل لأن حسابك معطل.")
            return

        seller = get_seller_by_telegram(telegram_id)
        
        if not seller:
            bot.send_message(message.chat.id, "⛔ أنت لست بائعاً مسجلاً!")
            return
        
        # جلب الطلبات الحديثة (بدلاً من الرسائل)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب آخر 10 طلبات (المعلقة أولاً)
        query = """
            SELECT o.OrderID, o.Total, o.Status, o.CreatedAt, 
                   COALESCE(u.FullName, 'زائر') as BuyerName,
                   COALESCE(u.PhoneNumber, 'غير متوفر') as BuyerPhone,
                   o.PaymentMethod, o.DeliveryAddress
            FROM Orders o
            LEFT JOIN Users u ON o.BuyerID = u.TelegramID
            WHERE o.SellerID = ? 
            ORDER BY 
                CASE WHEN o.Status = 'Pending' THEN 0 ELSE 1 END,
                o.CreatedAt DESC
            LIMIT 10
        """
        cursor.execute(query, (seller[0],))
        orders = cursor.fetchall()
        
        if not orders:
            bot.send_message(message.chat.id, "📭 لا توجد طلبات أو رسائل.")
            conn.close()
            return

        bot.send_message(message.chat.id, "📩 **الطلبات والرسائل (Inbox)**")

        for order in orders:
            oid, total, status, date, buyer, phone, pay_method, address = order

            # --- NEW CARD LOGIC ---
            from utils.receipt_generator import generate_order_card
            try:
                # Use standard function (Safe with LEFT JOIN)
                order_details_full, items_full = get_order_details(oid)

                receipt_img = None
                try:
                    receipt_img = generate_order_card(order_details_full, items_full, buyer, phone, seller[3])
                    if receipt_img:
                        receipt_img.name = f"receipt_{oid}.png"
                except Exception as e:
                    print(f"Img Gen Error {oid}: {e}")

                clean_date = str(date).split('.')[0]
                caption = f"📦 طلب #{oid} | 💰 {total:,.0f} IQD\n📅 {clean_date}"

                if receipt_img:
                    try:
                        bot.send_photo(message.chat.id, receipt_img, caption=caption, parse_mode='Markdown')
                    except Exception as e:
                        bot.send_message(message.chat.id, caption + "\n⚠️ (Img Send Error)", parse_mode='Markdown')
                else:
                    bot.send_message(message.chat.id, caption + "\n⚠️ (Img Gen Failed)", parse_mode='Markdown')

            except Exception as e:
                print(f"Error handling order {oid}: {e}")
                # Fallback
                clean_date = str(date).split('.')[0]
                bot.send_message(message.chat.id, f"📦 طلب #{oid}\n💰 {total:,.0f}\n📅 {clean_date}", parse_mode='Markdown')
            
            # Avoid hitting Telegram rate limits (approx 30 msgs/sec, but good to be safe with photos)
            time.sleep(0.3)
            continue # Skip legacy text logic below
            # --- END NEW LOGIC ---
            
            # جلب المنتجات للعرض (نستخدم LEFT JOIN لضمان ظهور العناصر حتى لو حذف المنتج الأصلي)
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.Price, p.ImagePath 
                FROM OrderItems oi 
                LEFT JOIN Products p ON oi.ProductID = p.ProductID 
                WHERE oi.OrderID = ?
            """, (oid,))
            items = cursor.fetchall()
            
            # تنسيق قائمة المنتجات
            items_text = ""
            first_image_path = None
            
            if not items:
                items_text = "" # User requested to remove warning
            else:
                for i in items:
                    p_name = i[0] if i[0] else "منتج محذوف"
                    p_qty = i[1]
                    p_price = i[2] if i[2] else 0
                    p_image = i[3]
                    
                    # Capture first image found to use as card cover
                    if not first_image_path and p_image and os.path.exists(p_image):
                         first_image_path = p_image
                    
                    row_total = p_qty * p_price
                    items_text += f"▫️ {p_name}\n   {p_qty}x | 💰 {p_price:,.0f} = {row_total:,.0f}\n"

            status_icon = "⏳" if status == 'Pending' else "✅" if status == 'Confirmed' else "🚚" if status == 'Shipped' else "❌" if status == 'Rejected' else ""
            status_text = "قيد الانتظار" if status == 'Pending' else "تم التأكيد" if status == 'Confirmed' else "تم الشحن" if status == 'Shipped' else "مرفوض" if status == 'Rejected' else status

            # تنسيق البطاقة
            card_text = f"{status_icon} طلب رقم #{oid}\n"
            card_text += f"📅 {date}\n\n"
            
            # المنتجات
            if items_text:
                card_text += f"{items_text}\n"
            
            # الإجمالي
            card_text += f"💰 **الإجمالي: {total:,.0f} IQD**\n"
            
            # معلومات العميل

            
            # معلومات العميل
            card_text += f"👤 {buyer}\n📞 {phone}\n"
            if address:
                card_text += f"📍 {address}\n"
            

            # Buttons: Removed as per user request (Details only)
            # markup = types.InlineKeyboardMarkup(row_width=3)
            # ... buttons removed ...
            
            # إرسال الرسالة (صورة أو نص)
            try:
                # ملاحظة: في تيليجرام لا يمكن وضع صور صغيرة بجانب كل سطر، لذا سنضع صورة المنتج الأول كغلاف للطلب إذا وجدت
                if first_image_path:
                    with open(first_image_path, 'rb') as photo:
                        bot.send_photo(message.chat.id, photo, caption=card_text, parse_mode='Markdown')
                else:
                    bot.send_message(message.chat.id, card_text, parse_mode='Markdown')
            except Exception as e:
                print(f"Error sending order card {oid}: {e}")
                # Fallback to text if image fails
                bot.send_message(message.chat.id, card_text, parse_mode='Markdown')
            
        conn.close()
        
        # إعادة عرض القائمة لتحديث العداد
        show_seller_menu(message)
        
    except Exception as e:
        print(f"❌ Error in seller_messages: {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء عرض الرسائل: {e}")

# ====== معالجة Callback Queries للطلبات ======
def handle_contact_buyer(call):
    parts = call.data.split("_")
    if len(parts) < 3:
        return
    
    buyer_id = int(parts[2])
    buyer_info = get_user(buyer_id)
    
    if not buyer_info:
        bot.answer_callback_query(call.id, "معلومات المشتري غير متوفرة")
        return
    
    buyer_name = buyer_info[5] if buyer_info[5] else buyer_info[2]
    buyer_phone = buyer_info[4] if buyer_info[4] else "غير متوفر"
    buyer_username = f"@{buyer_info[2]}" if buyer_info[2] else "لا يوجد"
    
    text = f"📞 **معلومات الاتصال بالمشتري**\n\n"
    text += f"👤 الاسم: {buyer_name}\n"
    text += f"📞 الهاتف: {buyer_phone}\n"
    text += f"🔗 المعرف: {buyer_username}\n"
    text += f"🆔 الرقم: {buyer_id}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    if buyer_phone != "غير متوفر":
        markup.add(types.InlineKeyboardButton("📞 اتصال فوري", url=f"tel:{buyer_phone}"))
    if buyer_info[2]:
        markup.add(types.InlineKeyboardButton("✉️ مراسلة", url=f"https://t.me/{buyer_info[2]}"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def handle_order_details(call):
    order_id = int(call.data.split("_")[2])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT o.OrderID, o.Total, o.Status, o.CreatedAt, 
               COALESCE(u.FullName, 'زائر') as BuyerName,
               COALESCE(u.PhoneNumber, 'غير متوفر') as BuyerPhone,
               o.PaymentMethod, o.DeliveryAddress, o.Notes
        FROM Orders o
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        WHERE o.OrderID = ?
    """
    
    cursor.execute(query, (order_id,))
    order = cursor.fetchone()
    
    if not order:
        bot.answer_callback_query(call.id, "الطلب غير موجود")
        conn.close()
        return

    oid, total, status, date, buyer, phone, pay_method, address, notes = order

    # تنسيق المنتجات
    cursor.execute("""
        SELECT p.name, oi.quantity, oi.price, p.imagepath 
        FROM OrderItems oi 
        LEFT JOIN Products p ON oi.productid = p.productid 
        WHERE oi.orderid = ?
    """, (oid,))
    items = cursor.fetchall()
    
    conn.close()

    # تنسيق المنتجات
    items_text = ""
    first_image_path = None
    
    if not items:
        # Check if we really have no items, might be sync delay
        items_text = "⚠️ لا توجد منتجات (ربما تم حذفها أو لم تتم المزامنة بعد)"
    else:
        for i in items:
            p_name = i[0] if i[0] else "منتج محذوف"
            p_qty = i[1]
            p_price = i[2] if i[2] else 0
            p_image = i[3]
            
            if not first_image_path and p_image and os.path.exists(p_image):
                    first_image_path = p_image
            
            row_total = p_qty * p_price
            items_text += f"▫️ {p_name}\n   {p_qty}x | 💰 {p_price:,.0f} = {row_total:,.0f}\n"

    status_icon = {
        'Pending': '⏳',
        'Confirmed': '✅',
        'Shipped': '🚚',
        'Delivered': '🎉',
        'Rejected': '❌'
    }.get(status, '❓')
    
    status_text_ar = {
        'Pending': 'قيد الانتظار',
        'Confirmed': 'تم التأكيد',
        'Shipped': 'تم الشحن',
        'Delivered': 'تم التسليم',
        'Rejected': 'مرفوض'
    }.get(status, status)
    
    # تنسيق البطاقة
    try:
        # Try to parse if string, or format if datetime
        if isinstance(date, str):
             date_str = date.split(' ')[0]
        else:
             date_str = date.strftime('%Y-%m-%d')
    except:
        date_str = str(date)[:10]

    card_text = f"{status_icon} **تفاصيل الطلب #{oid}**\n"
    card_text += f"📅 {date_str}\n"
    card_text += f"📊 الحالة: {status_text_ar}\n\n"
    
    card_text += f"👤 العميل: {buyer}\n"
    card_text += f"📞 الهاتف: {phone}\n"
    if address:
        card_text += f"📍 العنوان: {address}\n"
    card_text += "─────────────────\n"
    
    card_text += f"{items_text}"
    card_text += "─────────────────\n"
    card_text += f"💰 **الإجمالي: {float(total):,.0f} IQD**\n"
    
    if pay_method:
        pm = "نقداً" if pay_method == 'cash' else "آجل"
        card_text += f"💳 الدفع: {pm}\n"
        
    # الأزرار (Confirm, Delete, Details, etc)
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    if status == 'Pending':
            buttons.append(types.InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_order_{oid}"))
    
    if status in ['Pending', 'Confirmed']:
            buttons.append(types.InlineKeyboardButton("🚚 شحن", callback_data=f"ship_order_{oid}"))
    
    buttons.append(types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_order_{oid}"))
    
    markup.add(*buttons)
    
    # Generate Image Receipt
    try:
        # Prepare data for generator
        # order_details: (oid, buyer_id, seller_id, total, status, date, address, phone...)
        # We need to construct a tuple similar to what the generator expects or update generator to handle dicts
        # Generator expects: (OrderID, BuyerID, SellerID, Total, Status, CreatedAt, Address)
        # We have: oid, total, status, date, buyer, phone, pay_method, address
        order_tuple = (oid, None, None, total, status, date, address) 
        
        print(f"DEBUG: Generating Receipt for Order #{oid}") # DEBUG
        
        # Items logic for generator check: generator seems to iterate items list of tuples
        # Generator expects: index 3->quantity, 4->price, 8->name, 10->imagepath
        # Our 'items' query returns: (name, qty, price, imagepath)
        # So we need to map our query result to what generator expects (which seems to be based on `get_order_items` full query)
        # Let's map it to a format the generator likes:
        # We can construct a list of mock tuples that match the indices used in generator.
        # Generator usage: item[3]=qty, item[4]=price, item[8]=name, item[10/13]=image
        
        # Construct mock items
        generator_items = []
        for i in items:
            # i = (name, qty, price, imagepath)
            # Create a tuple of size 14 with correct placements
            mock_item = [None]*14
            mock_item[3] = i[1] # Qty
            mock_item[4] = i[2] # Price
            mock_item[8] = i[0] # Name
            mock_item[10] = i[3] # ImagePath
            generator_items.append(mock_item)
            
        receipt_image = generate_order_card(order_tuple, generator_items, address, notes, None) 
        
        if receipt_image:
             # Minimal caption for image (Status + Total only, buttons below)
             minimal_caption = f"📊 {status_text_ar}\n💰 الإجمالي: {float(total):,.0f} IQD\n(v4)"
             bot.send_photo(call.message.chat.id, receipt_image, caption=minimal_caption, reply_markup=markup, parse_mode='Markdown')
        else:
             bot.send_message(call.message.chat.id, card_text, reply_markup=markup, parse_mode='Markdown')
             
    except Exception as e:
        print(f"Failed to generate receipt: {e}")
        # DEBUG: Show error to user to diagnose why image failed
        bot.send_message(call.message.chat.id, card_text + f"\n\n⚠️ Error: {str(e)}", reply_markup=markup, parse_mode='Markdown')
        
    bot.answer_callback_query(call.id)

# ==================== دوال مزامنة حالة الطلب ====================

def send_order_notification(buyer_id, order_id, status):
    """
    إرسال إشعار للعميل عند تغيير حالة الطلب
    :param buyer_id: معرف المشتري (TelegramID)
    :param order_id: رقم الطلب
    :param status: الحالة الجديدة (Confirmed, Shipped, Delivered, Rejected, etc)
    """
    messages = {
        'Confirmed': f"✅ **تم تأكيد طلبك #{order_id}**\n\nتم تأكيد طلبك من قبل البائع. سيتم تجهيزه قريباً.",
        'Shipped': f"🚚 **تم شحن طلبك #{order_id}**\n\nطلبك في الطريق إليك! تابع معنا للمزيد من التحديثات.",
        'Delivered': f"🎉 **تم تسليم طلبك #{order_id}**\n\nتم تسليم طلبك بنجاح. شكراً لثقتك بنا! 💝",
        'Rejected': f"❌ **تم رفض طلبك #{order_id}**\n\nنعتذر، تم رفض طلبك من قبل البائع."
    }
    
    try:
        message = messages.get(status, f"📦 تم تحديث حالة طلبك #{order_id}")
        bot.send_message(buyer_id, message, parse_mode='Markdown')
        print(f"✅ تم إرسال الإشعار للعميل {buyer_id} - الحالة: {status}")
        return True
    except Exception as e:
        print(f"⚠️ لم يتمكن من إرسال الإشعار للعميل {buyer_id}: {e}")
        return False


def sync_order_status_to_cloud(order_id, new_status, buyer_id=None):
    """
    مزامنة حالة الطلب مع السحابة (PostgreSQL) والقاعدة المحلية (SQLite)
    
    :param order_id: رقم الطلب
    :param new_status: الحالة الجديدة (Confirmed, Shipped, Delivered, Rejected)
    :param buyer_id: معرف المشتري (اختياري، للإشعارات)
    :return: True إذا نجحت المزامنة، False إذا فشلت
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تحديث حالة الطلب في قاعدة البيانات
        cursor.execute("UPDATE Orders SET Status=? WHERE OrderID=?", (new_status, order_id))
        conn.commit()
        conn.close()
        
        print(f"✅ تم تحديث حالة الطلب {order_id} إلى '{new_status}'")
        
        # إرسال الإشعار للعميل إذا كان معرفاً
        if buyer_id:
            send_order_notification(buyer_id, order_id, new_status)
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في مزامنة الطلب {order_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def handle_confirm_order_seller(call):
    order_id = int(call.data.split("_")[2])
    
    # الحصول على معرف المشتري أولاً
    order_details, _ = get_order_details(order_id)
    buyer_id = order_details[1] if order_details else None
    
    # مزامنة حالة الطلب مع السحابة والقاعدة المحلية + إرسال الإشعار
    if sync_order_status_to_cloud(order_id, "Confirmed", buyer_id):
        print(f"✅ تم مزامنة الطلب {order_id} إلى 'Confirmed'")
    else:
        print(f"⚠️ تحذير: قد يكون هناك خطأ في مزامنة الطلب {order_id}")
    
    mark_messages_read_by_order(order_id) # Fix: Clear message counter
    
    bot.answer_callback_query(call.id, "✅ تم تأكيد الطلب ومزامنة البيانات")
    
    try:
        bot.edit_message_text(
            f"{call.message.text}\n\n✅ **تم تأكيد الطلب**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
        
        # INSTANT UPDATE: Refresh Counters
        show_seller_menu(call.message)
    except:
        pass

def send_order_images_to_buyer(order_id, buyer_id, seller_id):
    """إرسال صور المنتجات المطلوبة للزبون عند الشحن"""
    try:
        from db_manager import get_product_images_for_order, delete_product_images, get_product_by_id
        
        # الحصول على تفاصيل الطلب
        order_details, items = get_order_details(order_id)
        if not order_details or not items:
            print(f"❌ لم يتم العثور على تفاصيل الطلب {order_id}")
            return False
        
        seller = get_seller_by_id(seller_id)
        seller_name = seller[3] if seller else "المتجر"
        
        # إرسال رسالة ترحيب
        bot.send_message(buyer_id,
                        f"📦 **صور طلبك #{order_id}** 📸\n\n"
                        f"🏪 المتجر: {seller_name}\n"
                        f"جاري إرسال صور المنتجات المطلوبة...",
                        parse_mode='Markdown')
        
        images_to_delete = []
        product_updates = {}
        
        # معالجة كل منتج في الطلب
        # items يحتوي على: OrderItemID, OrderID, ProductID, Quantity, Price, Name, Description, ImagePath
        for item in items:
            order_item_id, order_id_check, product_id, quantity, price = item[0], item[1], item[2], item[3], item[4]
            product_name = item[5] if len(item) > 5 else "منتج"
            product_desc = item[6] if len(item) > 6 else None
            
            product = get_product_by_id(product_id)
            if not product:
                print(f"⚠️ المنتج {product_id} غير موجود")
                continue
            
            # الحصول على الصور المطلوبة
            images = get_product_images_for_order(product_id, quantity)
            
            if not images:
                bot.send_message(buyer_id,
                                f"⚠️ لم توجد صور متاحة للمنتج: {product_name}",
                                parse_mode='Markdown')
                continue
            
            # إرسال رسالة المنتج
            product_msg = f"📦 **{product_name}**\n"
            if product_desc:
                product_msg += f"📝 {product_desc}\n"
            product_msg += f"💰 السعر: {price:,.0f} د.ع\n"
            product_msg += f"📊 العدد المطلوب: {quantity}\n\n"
            product_msg += f"📸 الصور ({len(images)}):"
            
            bot.send_message(buyer_id, product_msg, parse_mode='Markdown')
            
            print(f"🔍 DEBUG: المنتج {product_id} - الكمية {quantity}")
            print(f"🔍 DEBUG: عدد الصور المتاحة: {len(images)}")
            
            # إرسال الصور
            for idx, image_data in enumerate(images):
                image_id, prod_id, image_path = image_data
                print(f"🔍 DEBUG: إرسال الصورة {image_id} من {image_path}")
                
                try:
                    # محاولة إرسال الصورة
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            bot.send_photo(buyer_id, f,
                                         caption=f"صورة {idx + 1} من {len(images)}")
                    else:
                        print(f"⚠️ الصورة غير موجودة: {image_path}")
                        bot.send_message(buyer_id,
                                       f"⚠️ لم تتمكن من إرسال الصورة {idx + 1}",
                                       parse_mode='Markdown')
                    
                    # إضافة الصورة قائمة الحذف
                    images_to_delete.append(image_id)
                    print(f"✅ تمت إضافة الصورة {image_id} لقائمة الحذف")
                    
                except Exception as e:
                    print(f"❌ خطأ في إرسال الصورة {image_id}: {e}")
            
            # تسجيل تحديث الكمية
            product_updates[product_id] = quantity
        
        # حذف الصور بعد الإرسال
        print(f"🔍 DEBUG: عدد الصور المراد حذفها: {len(images_to_delete)}")
        print(f"🔍 DEBUG: IDs الصور: {images_to_delete}")
        
        if images_to_delete:
            if delete_product_images(images_to_delete):
                print(f"✅ تم حذف {len(images_to_delete)} صورة من الطلب {order_id}")
            else:
                print(f"❌ فشل حذف الصور")
        
        # تحديث كمية المنتجات
        for product_id, quantity in product_updates.items():
            try:
                product = get_product_by_id(product_id)
                if product:
                    new_qty = max(0, product.quantity - quantity)
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE Products SET Quantity = ? WHERE ProductID = ?",
                                 (new_qty, product_id))
                    conn.commit()
                    conn.close()
                    print(f"✅ تم تحديث كمية المنتج {product_id}: {new_qty}")
            except Exception as e:
                print(f"❌ خطأ في تحديث كمية المنتج {product_id}: {e}")
        
        # رسالة ختامية
        bot.send_message(buyer_id,
                        f"✅ **انتهاء الشحن**\n\n"
                        f"🎉 تم إرسال جميع صور طلبك #{order_id}\n"
                        f"شكراً لك على الشراء! 💝",
                        parse_mode='Markdown')
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إرسال صور الطلب {order_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def handle_ship_order(call):
    order_id = int(call.data.split("_")[2])
    
    # الحصول على معرف المشتري أولاً
    order_details, items = get_order_details(order_id)
    buyer_id = order_details[1] if order_details else None
    seller_id = order_details[2] if order_details else None
    
    # مزامنة حالة الطلب مع السحابة والقاعدة المحلية + إرسال الإشعار
    if sync_order_status_to_cloud(order_id, "Shipped", buyer_id):
        print(f"✅ تم مزامنة الطلب {order_id} إلى 'Shipped'")
    else:
        print(f"⚠️ تحذير: قد يكون هناك خطأ في مزامنة الطلب {order_id}")
    
    mark_messages_read_by_order(order_id) # Fix: Clear message counter
    
    # إرسال الصور للزبون (اختياري - إذا كانت الدالة موجودة)
    if buyer_id and seller_id and callable(globals().get('send_order_images_to_buyer')):
        try:
            send_order_images_to_buyer(order_id, buyer_id, seller_id)
        except Exception as e:
            print(f"⚠️ تحذير: لم يتمكن من إرسال الصور: {e}")
    
    bot.answer_callback_query(call.id, "🚚 تم تحديث حالة الشحن ومزامنة البيانات")
    
    try:
        bot.edit_message_text(
            f"{call.message.text}\n\n🚚 **تم شحن الطلب**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
        
        # INSTANT UPDATE: Refresh Counters
        show_seller_menu(call.message)
    except:
        pass

def handle_deliver_order(call):
    order_id = int(call.data.split("_")[2])
    
    # الحصول على معرف المشتري أولاً
    order_details, _ = get_order_details(order_id)
    buyer_id = order_details[1] if order_details else None
    
    # مزامنة حالة الطلب مع السحابة والقاعدة المحلية + إرسال الإشعار
    if sync_order_status_to_cloud(order_id, "Delivered", buyer_id):
        print(f"✅ تم مزامنة الطلب {order_id} إلى 'Delivered'")
    else:
        print(f"⚠️ تحذير: قد يكون هناك خطأ في مزامنة الطلب {order_id}")
    
    mark_messages_read_by_order(order_id) # Fix: Clear message counter
    
    bot.answer_callback_query(call.id, "✅ تم تسليم الطلب ومزامنة البيانات")
    
    try:
        bot.edit_message_text(
            f"{call.message.text}\n\n✅ **تم تسليم الطلب**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
        
        # INSTANT UPDATE: Refresh Counters
        show_seller_menu(call.message)
    except:
        pass

def handle_reject_order(call):
    order_id = int(call.data.split("_")[2])
    
    # الحصول على معرف المشتري أولاً
    order_details, _ = get_order_details(order_id)
    buyer_id = order_details[1] if order_details else None
    
    # مزامنة حالة الطلب مع السحابة والقاعدة المحلية + إرسال الإشعار
    if sync_order_status_to_cloud(order_id, "Rejected", buyer_id):
        print(f"✅ تم مزامنة الطلب {order_id} إلى 'Rejected'")
    else:
        print(f"⚠️ تحذير: قد يكون هناك خطأ في مزامنة الطلب {order_id}")
    
    mark_messages_read_by_order(order_id) # Fix: Clear message counter
    
    bot.answer_callback_query(call.id, "❌ تم رفض الطلب ومزامنة البيانات")
    
    try:
        bot.edit_message_text(
            f"{call.message.text}\n\n❌ **تم رفض الطلب**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
        
        # INSTANT UPDATE: Refresh Counters
        show_seller_menu(call.message)
    except:
        pass

def handle_view_return(call):
    return_id = int(call.data.split("_")[2])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, p.Name as ProductName, o.OrderID, o.BuyerID, 
               u.FullName, u.PhoneNumber, u.UserName
        FROM Returns r
        JOIN Products p ON r.ProductID = p.ProductID
        JOIN Orders o ON r.OrderID = o.OrderID
        LEFT JOIN Users u ON o.BuyerID = u.TelegramID
        WHERE r.ReturnID = ?
    """, (return_id,))
    
    ret = cursor.fetchone()
    conn.close()
    
    if not ret:
        bot.answer_callback_query(call.id, "طلب الإرجاع غير موجود")
        return
    
    text = f"📦 **طلب إرجاع #{return_id}**\n\n"
    text += f"🆔 رقم الطلب: {ret[2]}\n"
    text += f"👤 المشتري: {ret[10] if ret[10] else ret[12]}\n"
    text += f"📞 الهاتف: {ret[11] if ret[11] else 'غير متوفر'}\n"
    text += f"🛒 المنتج: {ret[8]}\n"
    text += f"📦 الكمية: {ret[4]}\n"
    text += f"📝 السبب: {ret[5]}\n"
    text += f"📊 الحالة: {ret[6]}\n"
    text += f"📅 التاريخ: {ret[7]}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if ret[6] == 'Pending':
        markup.add(
            types.InlineKeyboardButton("✅ قبول الإرجاع", callback_data=f"approve_return_{return_id}"),
            types.InlineKeyboardButton("❌ رفض الإرجاع", callback_data=f"reject_return_{return_id}"),
            types.InlineKeyboardButton("📞 اتصل بالمشتري", callback_data=f"contact_buyer_{ret[9]}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("📞 اتصل بالمشتري", callback_data=f"contact_buyer_{ret[9]}"),
            types.InlineKeyboardButton("📋 العودة للقائمة", callback_data="back_to_returns")
        )
    
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def handle_return_details(call):
    message_id = int(call.data.split("_")[2])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT OrderID, MessageText FROM Messages WHERE MessageID = ?", (message_id,))
    msg = cursor.fetchone()
    conn.close()
    
    if msg:
        order_id = msg[0]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 تفاصيل الإرجاع", callback_data=f"view_return_{order_id}"))
        bot.send_message(call.message.chat.id, msg[1], reply_markup=markup, parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

def handle_process_return(call):
    message_id = int(call.data.split("_")[2])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT OrderID FROM Messages WHERE MessageID = ?", (message_id,))
    msg = cursor.fetchone()
    conn.close()
    
    if msg:
        order_id = msg[0]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ معالجة الإرجاع", callback_data=f"approve_return_{order_id}"))
        bot.send_message(call.message.chat.id, f"اختر إجراء للإرجاع للطلب #{order_id}:", reply_markup=markup)
    
    bot.answer_callback_query(call.id)

def handle_approve_return(call):
    return_id = int(call.data.split("_")[2])
    
    user_states[call.from_user.id] = {
        "step": "approve_return",
        "return_id": return_id
    }
    
    bot.send_message(call.message.chat.id, 
                    "✅ **قبول طلب الإرجاع**\n\n"
                    "يرجى إدخال ملاحظات إضافية (اختياري):")
    
    bot.answer_callback_query(call.id)

def handle_reject_return(call):
    return_id = int(call.data.split("_")[2])
    
    user_states[call.from_user.id] = {
        "step": "reject_return",
        "return_id": return_id
    }
    
    bot.send_message(call.message.chat.id, 
                    "❌ **رفض طلب الإرجاع**\n\n"
                    "يرجى إدخال سبب الرفض:")
    
    bot.answer_callback_query(call.id)

def handle_back_to_returns(call):
    telegram_id = call.from_user.id
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(call.message)
    elif is_seller(telegram_id):
        show_seller_menu(call.message)
    else:
        show_buyer_main_menu(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['contact'])
def handle_contact_message(message):
    """معالج رسائل جهة الاتصال (رقم الهاتف)"""
    telegram_id = message.from_user.id
    
    if telegram_id not in user_states:
        return
    
    state = user_states[telegram_id]
    
    if state.get('step') == 'verify_store_access':
        # التحقق من رقم الهاتف للوصول للمتجر
        phone_number = message.contact.phone_number if message.contact else None
        
        if not phone_number:
            bot.send_message(message.chat.id, "⚠️ لم يتم الحصول على رقم الهاتف. يرجى المحاولة مرة أخرى.")
            return
        
        seller_id = state.get('seller_id')
        store_name = state.get('store_name', 'المتجر')
        username = state.get('username')
        
        # التحقق من رقم الهاتف
        if is_customer_registered_for_store_by_phone(phone_number, seller_id):
            # حفظ رقم الهاتف للجلسة
            user_states[telegram_id]['verified_phone'] = phone_number
            user_states[telegram_id]['verified_seller_id'] = seller_id
            user_states[telegram_id]['step'] = None
            
            # إزالة لوحة المفاتيح
            markup = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id,
                f"✅ **تم التحقق بنجاح!**\n\n"
                f"📱 رقم الهاتف: {phone_number}\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"يمكنك الآن الوصول إلى جميع منتجات المتجر.",
                reply_markup=markup,
                parse_mode='Markdown')
            
            # عرض المتجر
            seller_telegram_id = None
            conn = get_db_connection()
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID=%s", (seller_id,))
            else:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID=?", (seller_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                seller_telegram_id = result[0]
                send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id, telegram_id)
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📞 التواصل مع البائع", url=f"https://t.me/{username}" if username else None))
            
            bot.send_message(message.chat.id,
                f"❌ **رقم الهاتف غير مسجل**\n\n"
                f"📱 رقم الهاتف: {phone_number}\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"⚠️ هذا الرقم غير مسجل في قائمة الزبائن الآجلين.\n\n"
                f"📝 **للحصول على الوصول:**\n"
                f"• تواصل مع البائع لإضافتك كزبون آجل\n"
                f"• أو اطلب من البائع إضافتك من خلال قائمة '🏪 إدارة الزبائن الآجلين'",
                reply_markup=markup if username else None,
                parse_mode='Markdown')
            
            # إزالة الحالة
            del user_states[telegram_id]

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id].get("step") == "verify_store_access" and
                     message.text and message.text != "❌ إلغاء")
def handle_phone_number_text(message):
    """معالج إدخال رقم الهاتف يدوياً"""
    telegram_id = message.from_user.id
    
    if telegram_id not in user_states:
        return
    
    state = user_states[telegram_id]
    
    if state.get('step') == 'verify_store_access':
        phone_number = message.text.strip()
        
        # التحقق من أن النص هو رقم هاتف
        if not phone_number or len(phone_number) < 7:
            bot.send_message(message.chat.id, "⚠️ يرجى إدخال رقم هاتف صحيح (مثال: 07701234567)")
            return
        
        seller_id = state.get('seller_id')
        store_name = state.get('store_name', 'المتجر')
        username = state.get('username')
        
        # التحقق من رقم الهاتف
        if is_customer_registered_for_store_by_phone(phone_number, seller_id):
            # حفظ رقم الهاتف للجلسة
            user_states[telegram_id]['verified_phone'] = phone_number
            user_states[telegram_id]['verified_seller_id'] = seller_id
            user_states[telegram_id]['step'] = None
            
            # إزالة لوحة المفاتيح
            markup = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id,
                f"✅ **تم التحقق بنجاح!**\n\n"
                f"📱 رقم الهاتف: {phone_number}\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"يمكنك الآن الوصول إلى جميع منتجات المتجر.",
                reply_markup=markup,
                parse_mode='Markdown')
            
            # عرض المتجر
            seller_telegram_id = None
            conn = get_db_connection()
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID=%s", (seller_id,))
            else:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID=?", (seller_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                seller_telegram_id = result[0]
                send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id, telegram_id)
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📞 التواصل مع البائع", url=f"https://t.me/{username}" if username else None))
            
            bot.send_message(message.chat.id,
                f"❌ **رقم الهاتف غير مسجل**\n\n"
                f"📱 رقم الهاتف: {phone_number}\n"
                f"🏪 المتجر: {store_name}\n\n"
                f"⚠️ هذا الرقم غير مسجل في قائمة الزبائن الآجلين.\n\n"
                f"📝 **للحصول على الوصول:**\n"
                f"• تواصل مع البائع لإضافتك كزبون آجل\n"
                f"• أو اطلب من البائع إضافتك من خلال قائمة '🏪 إدارة الزبائن الآجلين'",
                reply_markup=markup if username else None,
                parse_mode='Markdown')
            
            # إزالة الحالة
            del user_states[telegram_id]

@bot.message_handler(func=lambda message: message.text == "❌ إلغاء" and 
                     message.from_user.id in user_states and
                     user_states[message.from_user.id].get("step") == "verify_store_access")
def handle_cancel_phone_verification(message):
    """إلغاء عملية التحقق من رقم الهاتف"""
    telegram_id = message.from_user.id
    if telegram_id in user_states:
        del user_states[telegram_id]
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "❌ تم إلغاء عملية التحقق.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] in ["approve_return", "reject_return"])
def process_return_decision(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    return_id = state["return_id"]
    action = state["step"]
    
    notes = message.text if message.text else "لا توجد ملاحظات"
    
    if action == "approve_return":
        success, result = process_return_request(return_id, 'Approved', user_id, notes)
        response_text = "✅ تم قبول طلب الإرجاع"
    else:
        success, result = process_return_request(return_id, 'Rejected', user_id, notes)
        response_text = "❌ تم رفض طلب الإرجاع"
    
    if success:
        bot.send_message(message.chat.id, response_text)
    else:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ: {result}")
    
    del user_states[user_id]

# ====== تعديل بيانات المستخدم ======
@bot.message_handler(func=lambda message: message.text == "👤 تعديل بياناتي")
def edit_user_info(message):
    # Delegate to helper so callbacks can reuse the same UI
    send_edit_profile_menu(message.chat.id, message.from_user.id)


def send_edit_profile_menu(chat_id, user_id):
    user = get_user(user_id)
    if not user:
        bot.send_message(chat_id, "⚠️ لم يتم العثور على بياناتك.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✏️ تعديل الاسم", callback_data="edit_name"),
        types.InlineKeyboardButton("📞 تعديل الهاتف", callback_data="edit_phone")
    )

    bot.send_message(chat_id,
                    f"👤 **بياناتك الحالية:**\n\n"
                    f"🆔 المعرف: {user[1]}\n"
                    f"👤 الاسم: {user[5] if user[5] else 'غير محدد'}\n"
                    f"📞 الهاتف: {user[4] if user[4] else 'غير محدد'}\n\n"
                    f"اختر ما تريد تعديله:",
                    reply_markup=markup)

def handle_edit_user_info(call):
    if call.data == "edit_name":
        user_states[call.from_user.id] = {"step": "edit_name"}
        bot.send_message(call.message.chat.id, "✏️ **تعديل الاسم**\n\nيرجى إدخال اسمك الكامل الجديد:")
    else:
        user_states[call.from_user.id] = {"step": "edit_phone"}
        bot.send_message(call.message.chat.id, "📞 **تعديل رقم الهاتف**\n\nيرجى إدخال رقم هاتفك الجديد:")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                     user_states[message.from_user.id]["step"] in ["edit_name", "edit_phone"])
def process_edit_user_info(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    
    if state["step"] == "edit_name":
        new_name = message.text.strip()
        if not new_name:
            bot.send_message(message.chat.id, "الرجاء إدخال اسم صحيح.")
            return
        update_user_info(user_id, full_name=new_name)
        bot.send_message(message.chat.id, f"✅ تم تحديث اسمك إلى: {new_name}")
    else:
        new_phone = message.text.strip()
        if not new_phone:
            new_phone = None
        update_user_info(user_id, phone_number=new_phone)
        phone_display = new_phone if new_phone else 'غير محدد'
        bot.send_message(message.chat.id, f"✅ تم تحديث رقم هاتفك إلى: {phone_display}")
    
    del user_states[user_id]
    show_buyer_main_menu(message)

# ====== عرض الطلبات للمشتري ======
@bot.message_handler(func=lambda message: message.text == "📋 طلباتي")
def handle_my_orders(message):
    telegram_id = message.from_user.id
    print(f"DEBUG: handle_my_orders processing for {telegram_id}") # Confirm handler is reached
    
    try:
        # التحقق إذا كان المستخدم مسجلاً
        user = get_user(telegram_id)
        if not user:
            bot.send_message(message.chat.id, "⚠️ يجب عليك تسجيل الدخول أولاً.")
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب الطلبات الخاصة بالمشتري (BuyerID)
        # استخدام BuyerID (TelegramID)
        query = """
            SELECT o.OrderID, s.StoreName, o.Total, o.Status, o.CreatedAt
            FROM Orders o
            JOIN Sellers s ON o.SellerID = s.SellerID
            WHERE o.BuyerID = ? OR o.BuyerID = ?
            ORDER BY o.CreatedAt DESC
            LIMIT 10
        """
        
        cursor.execute(query, (telegram_id, str(telegram_id)))
        orders = cursor.fetchall()
        conn.close()
        
        if not orders:
            bot.send_message(message.chat.id, "📭 لا توجد لديك طلبات سابقة.")
            return
            
        text = "📋 **قائمة طلباتي**\n\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for order in orders:
            order_id, store_name, total, status, date = order
            
            status_icon = {
                'Pending': '⏳',
                'Confirmed': '✅',
                'Shipped': '🚚',
                'Delivered': '🎉',
                'Rejected': '❌'
            }.get(status, '❓')
            
            # Formating Total
            try:
                total_fmt = f"{float(total):,.0f}"
            except:
                total_fmt = str(total)

            button_text = f"{status_icon} طلب #{order_id} - {store_name} ({total_fmt} IQD)"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f"my_order_{order_id}"))
            
        bot.send_message(message.chat.id, "اختر طلباً لعرض التفاصيل:", reply_markup=markup)
        
    except Exception as e:
        print(f"ERROR in handle_my_orders: {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ تقني:\n{str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("my_order_"))
def handle_buyer_order_details(call):
    try:
        order_id = int(call.data.split("_")[2])
        
        order_details, items = get_order_details(order_id)
        
        if not order_details:
            bot.answer_callback_query(call.id, "الطلب غير موجود")
            return
            
        # order_details structure based on get_order_details return:
        # 0:OrderID, 1:BuyerID, 2:SellerID, 3:Total, 4:Status, 5:OrderDate, 6:Address, 7:Phone, 8:PaymentMethod, 9:FullyPaid
        
        store_name = "المتجر" 
        # نحتاج لجلب اسم المتجر، الدالة get_order_details لا ترجعه مباشرة بـ JOIN
        # سنحاول جلبه بشكل منفصل أو الاعتماد على seller_id
        seller_id = order_details[2]
        seller = get_seller_by_id(seller_id)
        if seller:
            store_name = seller[3]
            
        text = f"📋 **تفاصيل طلبي #{order_id}**\n\n"
        text += f"🏪 المتجر: {store_name}\n"
        text += f"📅 التاريخ: {order_details[5]}\n"
        text += f"📊 الحالة: {order_details[4]}\n"
        text += f"💰 الإجمالي: {order_details[3]} IQD\n"
        
        payment_method = 'نقداً' if order_details[8] == 'cash' else 'آجل'
        payment_status = 'مدفوع' if order_details[9] else 'غير مدفوع'
        text += f"💳 الدفع: {payment_method} ({payment_status})\n"
        
        if order_details[6]:
            text += f"📍 العنوان: {order_details[6]}\n"
            
        text += "\n📦 **المنتجات:**\n"
        
        for item in items:
            # item: ID, OrderID, ProductID, Qty, Price, RetQty, RetReason, RetDate, ProductName
            prod_name = item[8]
            qty = item[3]
            price = item[4]
            total_item = qty * price
            
            text += f"- {prod_name} (x{qty}) = {total_item:,.0f}\n"
            
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")) # or back to list?
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ")
        print(f"Error in buyer order details: {e}")

# ====== الأوامر الإضافية ======
@bot.message_handler(commands=['myid'])
def get_my_id(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "لا يوجد"
    
    user_type = get_user_type(user_id)
    user_type_display = {
        'bot_admin': '👑 أدمن البوت',
        'seller': '🏪 بائع',
        'buyer': '🛍️ مشتري'
    }.get(user_type, 'مستخدم')
    
    bot.send_message(
        message.chat.id,
        f"👤 **معلومات حسابك:**\n\n"
        f"🆔 **معرفك:** `{user_id}`\n"
        f"👤 **الاسم:** {first_name}\n"
        f"🔗 **اليوزر:** @{username}\n"
        f"🎭 **النوع:** {user_type_display}\n\n"
        f"يمكنك استخدام هذا المعرف في إعدادات البوت.",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = """
🆘 **مساعدة بوت المتجر** 🆘

🔹 **الأوامر المتاحة:**
/start - بدء الاستخدام
/myid - عرض معرفك
/help - عرض هذه الرسالة

🔹 **للمشترين والزوار:**
• تصفح المتاجر المتاحة
• إضافة المنتجات للسلة
• إنهاء الطلبات
• الشراء نقداً (للجميع)
• الشراء على الحساب (للمسجلين فقط)

🔹 **للمسجلين فقط:**
• حفظ طلباتك السابقة
• كشف الحساب الآجل
• متابعة الحدود الائتمانية
• طلب إرجاع المنتجات
• تعديل بياناتك الشخصية

🔹 **للبائعين:**
• إدارة المنتجات والأقسام
• متابعة الطلبات الجديدة
• إدارة كشف حساب الزبائن الآجل
• إدارة مرتجعات العملاء
• إدارة الحدود الائتمانية للزبائن

🔹 **لأدمن البوت:**
• إدارة حسابات المتاجر
• عرض إحصائيات النظام
• إنشاء متاجر جديدة
• تعليق/تنشيط المتاجر

🔹 **نظام الدفع:**
• الدفع نقداً (للجميع)
• الشراء على الحساب (للمسجلين فقط)
• متابعة المديونيات
• نظام الحدود الائتمانية

🔹 **التسجيل:**
• التسجيل مجاني
• يوفر جميع المزايا
• يمكن التصفح بدون تسجيل
"""
    
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🔙 رجوع")
def handle_back_button(message):
    telegram_id = message.from_user.id
    
    # التحقق إذا كان المستخدم زائراً
    is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
    if is_guest:
        browse_without_registration(message)
        return
    
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(message)
    elif is_seller(telegram_id):
        show_seller_menu(message)
    else:
        show_buyer_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "🏠 الرئيسية")
def handle_main_menu(message):
    telegram_id = message.from_user.id
    
    # Clear any active state when Main Button is pressed!
    if telegram_id in user_states:
        del user_states[telegram_id]
    
    # ====== التعديل الجديد ======
    # التحقق إذا كان المستخدم زائراً (غير مسجل)
    is_guest = telegram_id in user_states and user_states.get(telegram_id, {}).get('is_guest', False)
    
    if is_guest:
        browse_without_registration(message)
        return
    
    if is_bot_admin(telegram_id):
        show_bot_admin_menu(message)
    elif is_seller(telegram_id):
        show_seller_menu(message)
    else:
        show_buyer_main_menu(message)

# ====== تنظيف الصور غير المستخدمة ======
@bot.message_handler(commands=['clean_images', 'clear_images'])
def clean_unused_images(message):
    if not is_bot_admin(message.from_user.id):
        return

    try:
        bot.send_message(message.chat.id, "🔄 **جاري فحص الصور غير المستخدمة...**")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get all used images from DB (Sellers, Categories, Products)
        used_images = set()
        
        # Products
        cursor.execute("SELECT \"ImagePath\" FROM \"Products\" WHERE \"ImagePath\" IS NOT NULL AND \"ImagePath\" != ''")
        for row in cursor.fetchall():
            used_images.add(os.path.basename(row[0])) # Store filename only
            
        # Categories
        cursor.execute("SELECT \"ImagePath\" FROM \"Categories\" WHERE \"ImagePath\" IS NOT NULL AND \"ImagePath\" != ''")
        for row in cursor.fetchall():
            used_images.add(os.path.basename(row[0]))
            
        # Sellers
        cursor.execute("SELECT \"ImagePath\" FROM \"Sellers\" WHERE \"ImagePath\" IS NOT NULL AND \"ImagePath\" != ''")
        for row in cursor.fetchall():
            used_images.add(os.path.basename(row[0]))
            
        # 2. Clean ImageStorage Table (Cloud Backup)
        # We need to delete rows where FileName is NOT in used_images
        # Since we are using DBWrapper/CursorWrapper, we should check if table exists first
        deleted_db_count = 0
        try:
            # Get all stored images
            cursor.execute("SELECT FileName FROM ImageStorage")
            stored_files = cursor.fetchall()
            
            for row in stored_files:
                file_name = row[0]
                if file_name not in used_images:
                     cursor.execute("DELETE FROM ImageStorage WHERE FileName = ?", (file_name,))
                     deleted_db_count += 1
                     print(f"🗑️ Cleaned cloud image: {file_name}")
            
            conn.commit()
        except Exception as db_e:
            print(f"⚠️ ImageStorage cleanup skipped (Table might not exist): {db_e}")

        conn.close()
        
        # 3. Clean Local Disk (Images Folder)
        images_dir = os.path.join(DATA_DIR, 'Images')
        deleted_disk_count = 0
        reclaimed_space = 0
        
        if os.path.exists(images_dir):
            all_files = os.listdir(images_dir)
            for filename in all_files:
                file_path = os.path.join(images_dir, filename)
                
                # Skip valid usage
                if filename in used_images:
                    continue
                    
                # Skip non-files
                if not os.path.isfile(file_path):
                    continue
                    
                # DELETE ORPHAN
                try:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_disk_count += 1
                    reclaimed_space += file_size
                    print(f"🗑️ Cleaned disk image: {filename}")
                except Exception as e:
                    print(f"⚠️ Failed to delete {filename}: {e}")
        
        # Convert bytes to readable
        size_str = f"{reclaimed_space} B"
        if reclaimed_space > 1024:
            size_str = f"{reclaimed_space / 1024:.2f} KB"
        if reclaimed_space > 1024 * 1024:
            size_str = f"{reclaimed_space / (1024 * 1024):.2f} MB"

        msg = (f"✅ **تم تنظيف الصور!**\n\n"
               f"🗑️ محذوف من السحابة (DB): {deleted_db_count}\n"
               f"🗑️ محذوف من القرص (Disk): {deleted_disk_count}\n"
               f"💾 مساحة القرص المسترجعة: {size_str}\n"
               f"🖼️ الصور النشطة المتبقية: {len(used_images)}")

        if used_images:
            msg += "\n\n📂 **قائمة الصور النشطة:**\n"
            # Show first 20 images
            for img in list(used_images)[:20]:
                msg += f"- `{img}`\n"
                
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ: {e}")
        print(f"Clean Images Error: {e}")
        traceback.print_exc()

@bot.message_handler(commands=['find_image'])
def find_image_usage(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Usage: /find_image <filename>")
            return
            
        target_name = args[1]
        bot.reply_to(message, f"🔍 Searching for '{target_name}'...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        found_msg = ""
        
        # Products
        if IS_POSTGRES:
            cursor.execute("SELECT ProductID, Name FROM Products WHERE ImagePath LIKE %s", (f"%{target_name}%",))
        else:
            cursor.execute("SELECT ProductID, Name FROM Products WHERE ImagePath LIKE ?", (f"%{target_name}%",))
            
        for row in cursor.fetchall():
            found_msg += f"📦 **Product:** {row[1]} (ID: {row[0]})\n"
            
        # Categories
        if IS_POSTGRES:
            cursor.execute("SELECT \"CategoryID\", \"Name\" FROM \"Categories\" WHERE \"ImagePath\" LIKE %s", (f"%{target_name}%",))
        else:
            cursor.execute("SELECT \"CategoryID\", \"Name\" FROM \"Categories\" WHERE \"ImagePath\" LIKE ?", (f"%{target_name}%",))
            
        for row in cursor.fetchall():
            found_msg += f"📂 **Category:** {row[1]} (ID: {row[0]})\n"
            
        # Sellers
        if IS_POSTGRES:
            cursor.execute("SELECT SellerID, StoreName FROM Sellers WHERE ImagePath LIKE %s", (f"%{target_name}%",))
        else:
            cursor.execute("SELECT SellerID, StoreName FROM Sellers WHERE ImagePath LIKE ?", (f"%{target_name}%",))
            
        for row in cursor.fetchall():
            found_msg += f"🏪 **Seller:** {row[1]} (ID: {row[0]})\n"
            
        conn.close()
        
        if found_msg:
             bot.reply_to(message, f"✅ **Found References:**\n{found_msg}", parse_mode='Markdown')
        else:
             bot.reply_to(message, "❌ Image not found in any active table.")
             
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

# ====== تشغيل البوت ======
print("[INFO] Bot started...")
print("[OK] All features enabled:")
print("   [OK] Admin system")
print("   [OK] Store management")
print("   [OK] Share link feature")
print("   [OK] Returns system")
print("   [OK] Messaging system")
print("   [OK] Credit account statement")
print("   [OK] Credit limit system")
print("   [OK] System statistics")
print("   [OK] Product and category management")
print("   [OK] Enhanced image system")
print("   [OK] Cash and credit payments")
print("   [OK] Credit customers")
print("   [OK] Wholesale price for credit customers")
print("   [OK] NEW FEATURES:")
print("   [OK] Browse stores without registration")
print("   [OK] Add products to cart as guest")
print("   [OK] Complete guest orders")
print("   [OK] Register account anytime")
print("   [OK] Different rules for guests and registered users")


# ====== PRIORITY Handler for ADMIN - يجب أن يكون قبل جميع الـ handlers ======
# (تم دمج منطق الـ admin مباشرة داخل send_welcome)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """معالج أمر /start - نسخة مبسطة من تطبيق Flutter"""
    try:
        telegram_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        full_name = message.from_user.full_name
        text = message.text or ""
        
        print(f"\n{'='*60}")
        print(f"📍 /start handler - User: {telegram_id}, BOT_ADMIN_ID={BOT_ADMIN_ID}")
        print(f"{'='*60}\n")
        
        # ===== أولاً: التحقق من كون المستخدم ADMIN =====
        if telegram_id == BOT_ADMIN_ID:
            print(f"👑 ADMIN DETECTED ({telegram_id}) - showing admin menu")
            show_bot_admin_menu(message)
            return
        
        # ===== معالجة رابط المتجر (store_SELLER_ID) =====
        if "store_" in text:
            try:
                idx = text.index("store_")
                token = text[idx+len("store_"):].strip()
                token = token.split()[0]
                seller_telegram_id = int(token)
                
                if telegram_id == seller_telegram_id:
                    seller = get_seller_by_telegram(telegram_id)
                    if seller and is_seller_active(telegram_id):
                        show_seller_menu(message)
                    else:
                        bot.send_message(message.chat.id, "⛔ **حسابك معطل أو غير مسجل كبائع**")
                else:
                    send_store_catalog_by_telegram_id(message.chat.id, seller_telegram_id, telegram_id)
                return
            except Exception as e:
                print(f"⚠️ خطأ في فتح رابط المتجر: {e}")
                pass

        # ===== تسجيل المستخدم الجديد (مثل Flutter) =====
        user = get_user(telegram_id)
        if not user:
            add_user(telegram_id, username, "seller", None, full_name)
            try:
                add_seller(telegram_id, username, f"متجر {username}")
            except Exception as e:
                print(f"⚠️ خطأ في إنشاء حساب بائع: {e}")
        
        # ===== المنطق البسيط (مثل Flutter) =====
        # 1. التحقق: هل هو بائع؟ (يجب أن يكون موجود في جدول Sellers)
        seller = get_seller_by_telegram(telegram_id)
        if seller and is_seller_active(telegram_id):
            print(f"🏪 User {telegram_id} is SELLER - showing seller menu")
            show_seller_menu(message)
            return
        
        # 2. إذا لم يكن بائع وليس admin -> أخطأ! (مثل Flutter)
        # (لا نعرض قائمة مشتري في الواقع)
        print(f"❌ User {telegram_id} is NOT seller and NOT admin")
        bot.send_message(message.chat.id, "❌ لم يتم العثور على حساب.\n\nيرجى التواصل مع الإدارة.")
        
    except Exception as e:
        print(f"❌ Error in start command: {e}")
        import traceback
        traceback.print_exc()
        bot.reply_to(message, "حدث خطأ بسيط، حاول مرة أخرى.")

# ====== Debug Command ======

@bot.message_handler(commands=['debug_db'])
def debug_db_status(message):
    try:
        db_url = os.environ.get('DATABASE_URL')
        status = "✅ Using PostgreSQL" if IS_POSTGRES else "⚠️ Using SQLite (Local)"
        
        info = f"**Database Status:**\n{status}\n\n"
        if db_url:
            masked_url = db_url[:15] + "..." + db_url[-5:]
            info += f"URL Found: `{masked_url}`\n"
        else:
            info += "URL Not Found in Enviroment\n"
            
        # Try a quick count
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Products")
            count = cursor.fetchone()[0]
            conn.close()
            info += f"\nProducts Count: {count}"
        except Exception as e:
            info += f"\nDB Error: {e}"

        bot.send_message(message.chat.id, info, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "Error checking status")


@bot.message_handler(commands=['check_images'])
def check_images_status(message):
    """فحص حالة الصور في السحابة"""
    if not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط")
        return
    
    try:
        if not IS_POSTGRES:
            bot.reply_to(message, "⚠️ هذا الأمر يعمل فقط مع PostgreSQL (Cloud)")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Count images in ImageStorage
        cursor.execute("SELECT COUNT(*) FROM ImageStorage")
        img_count = cursor.fetchone()[0]
        
        # Count products with images
        cursor.execute("SELECT COUNT(*) FROM Products WHERE ImagePath IS NOT NULL AND ImagePath != ''")
        prod_count = cursor.fetchone()[0]
        
        # Get sample images
        cursor.execute("SELECT FileName FROM ImageStorage LIMIT 5")
        samples = cursor.fetchall()
        
        # Get total size
        cursor.execute("SELECT SUM(LENGTH(FileData))::bigint FROM ImageStorage")
        total_size = cursor.fetchone()[0] or 0
        
        info = f"📸 **حالة الصور في السحابة**\n\n"
        info += f"✅ الصور في ImageStorage: {img_count}\n"
        info += f"✅ المنتجات بصور: {prod_count}\n"
        info += f"✅ الحجم الإجمالي: {total_size/1024/1024:.2f} MB\n\n"
        
        if samples:
            info += f"📋 **عينات:**\n"
            for (fname,) in samples:
                info += f"• {fname[:40]}...\n"
        
        conn.close()
        bot.send_message(message.chat.id, info, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")
        import traceback
        traceback.print_exc()


# ====== Ping Command (No DB) ======
@bot.message_handler(commands=['ping'])
def ping_pong(message):
    try:
        bot.reply_to(message, "Pong! 🏓\nI am alive and listening.")
    except Exception as e:
        print(f"Ping error: {e}")


# ====== إدارة الطلبات (أزرار البطاقة) ======
@bot.callback_query_handler(func=lambda call: call.data.startswith(('confirm_order_', 'ship_order_', 'delete_order_', 'order_details_')))
def handle_order_actions(call):
    try:
        parts = call.data.split('_')
        action = parts[0] + '_' + parts[1] # e.g. confirm_order
        order_id = int(parts[2])
        
        seller_id = call.from_user.id
        # Verify seller owns this order (Basic check via DB helps security)
        # For now, simplistic status update.
        
        new_status = None
        notify_user_msg = None
        
        if action == "confirm_order":
            new_status = "Confirmed"
            notify_user_msg = "✅ تم تأكيد طلبك! سيتم تجهيزه قريباً."
            feedback = "✅ تم تأكيد الطلب بنجاح."
            
        elif action == "ship_order":
            new_status = "Shipped"
            notify_user_msg = "🚚 تم شحن طلبك! وهو في الطريق إليك."
            feedback = "🚚 تم تحديث الحالة إلى 'تم الشحن'."
            
        elif action == "delete_order":
            # Just Cancelled or actually Delete? 
            # Usually Cancelled is better for records.
            new_status = "Cancelled" 
            notify_user_msg = "❌ تم إلغاء طلبك من قبل المتجر."
            feedback = "🗑️ تم إلغاء الطلب."
        
        elif action == "order_details":
            # Show full text details
            order, items = get_order_details(order_id)
            if order:
                # Reuse notification logic or simple text
                 # بناء النص
                txt = f"📝 تفاصيل الطلب #{order_id}\n\n"
                txt += f"👤 المشتري: {order[11]}\n" # FullName from query
                txt += f"📞 {order[12]}\n"
                txt += f"📍 {order[6]}\n"
                txt += "📦 المنتجات:\n"
                for it in items:
                     txt += f"- {it[8]} (x{it[3]}) - {it[8]} IQD\n" # Index 8=Name
                
                bot.send_message(call.message.chat.id, txt)
                bot.answer_callback_query(call.id)
                return

        if new_status:
            # Update DB
            update_order_status(order_id, new_status)
            bot.answer_callback_query(call.id, feedback)
            bot.send_message(call.message.chat.id, f"📝 {feedback} (تسلسل #{order_id})")
            
            # Notify Buyer
            order_info, _ = get_order_details(order_id)
            if order_info:
                buyer_id = order_info[1]
                try:
                    bot.send_message(buyer_id, f"🔔 تحديث حالة الطلب #{order_id}:\n{notify_user_msg}")
                except:
                    pass

    except Exception as e:
        print(f"Order Action Error: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ أثناء تنفيذ الإجراء")

# ===================== نظام المزادات - المعالجات =====================

# حالات المستخدمين للمزادات
auction_states = {}

@bot.message_handler(func=lambda message: "🔨 رفع منتج للمزاد" in message.text and is_seller(message.from_user.id))
def upload_product_to_auction(message):
    """معالج رفع منتج للمزاد"""
    telegram_id = message.from_user.id
    seller = get_seller_by_telegram(telegram_id)
    
    if not seller:
        bot.send_message(message.chat.id, "❌ أنت لست بائعاً مسجلاً")
        return
    
    # التحقق من أن المتجر مفتوح
    seller_id = seller[0]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT RequireCustomerRegistration FROM Sellers WHERE SellerID = ?", (seller_id,))
    result = cursor.fetchone()
    conn.close()
    
    is_closed = result and result[0] == 1
    
    if is_closed:
        bot.send_message(message.chat.id, 
                        "⛔ **متجرك مغلق**\n\n"
                        "لا يمكنك رفع المنتجات للمزاد إلا إذا كان متجرك مفتوحاً.\n"
                        "استخدم الأمر /set_open_store لفتح متجرك.")
        return
    
    # جلب منتجات البائع
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ProductID, Name, Price FROM Products 
        WHERE SellerID = ? AND Status = 'active' 
        ORDER BY ProductID DESC
    """, (seller_id,))
    
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        bot.send_message(message.chat.id, "❌ ليس لديك منتجات لرفعها للمزاد")
        return
    
    # عرض قائمة المنتجات
    msg = "🏷️ **اختر المنتج الذي تريد رفعه للمزاد:**\n\n"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    for product_id, name, price in products:
        msg += f"• {name} - {price} دينار\n"
        markup.add(f"📦 {product_id}: {name}")
    
    markup.add("❌ إلغاء")
    
    auction_states[telegram_id] = {"step": "select_product"}
    bot.send_message(message.chat.id, msg, reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in auction_states and 
                     auction_states[message.from_user.id].get("step") == "select_product" and
                     "📦" in message.text)
def select_auction_product(message):
    """معالج اختيار المنتج"""
    telegram_id = message.from_user.id
    
    try:
        # استخراج معرف المنتج من الرسالة
        product_id = int(message.text.split(":")[0].replace("📦 ", ""))
        
        # التحقق من وجود المنتج
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ProductID, Name, Price FROM Products WHERE ProductID = ?", (product_id,))
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            bot.send_message(message.chat.id, "❌ المنتج غير موجود")
            return
        
        auction_states[telegram_id]["product_id"] = product_id
        auction_states[telegram_id]["product_name"] = product[1]
        auction_states[telegram_id]["original_price"] = product[2]
        auction_states[telegram_id]["step"] = "enter_start_price"
        
        bot.send_message(message.chat.id, 
                        f"💰 **ادخل سعر بداية المزاد للمنتج:**\n\n"
                        f"📦 المنتج: {product[1]}\n"
                        f"💰 السعر الأصلي: {product[2]}")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")
        del auction_states[telegram_id]

@bot.message_handler(func=lambda message: message.from_user.id in auction_states and 
                     auction_states[message.from_user.id].get("step") == "enter_start_price")
def enter_auction_start_price(message):
    """معالج إدخال سعر بداية المزاد"""
    telegram_id = message.from_user.id
    
    try:
        start_price = float(message.text)
        
        if start_price <= 0:
            bot.send_message(message.chat.id, "⚠️ السعر يجب أن يكون أكبر من صفر")
            return
        
        auction_states[telegram_id]["start_price"] = start_price
        auction_states[telegram_id]["step"] = "enter_start_date"
        
        bot.send_message(message.chat.id,
                        "📅 **أدخل تاريخ بداية المزاد**\n\n"
                        "الصيغة: YYYY-MM-DD HH:MM\n"
                        "مثال: 2025-01-20 10:00")
        
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ أدخل رقماً صحيحاً")

@bot.message_handler(func=lambda message: message.from_user.id in auction_states and 
                     auction_states[message.from_user.id].get("step") == "enter_start_date")
def enter_auction_start_date(message):
    """معالج إدخال تاريخ بداية المزاد"""
    telegram_id = message.from_user.id
    
    try:
        start_dt = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        
        auction_states[telegram_id]["start_date"] = start_dt
        auction_states[telegram_id]["step"] = "enter_end_date"
        
        bot.send_message(message.chat.id,
                        "📅 **أدخل تاريخ نهاية المزاد**\n\n"
                        "الصيغة: YYYY-MM-DD HH:MM\n"
                        "مثال: 2025-01-25 18:00")
        
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ التاريخ غير صحيح! استخدم الصيغة: YYYY-MM-DD HH:MM")

@bot.message_handler(func=lambda message: message.from_user.id in auction_states and 
                     auction_states[message.from_user.id].get("step") == "enter_end_date")
def enter_auction_end_date(message):
    """معالج إدخال تاريخ نهاية المزاد"""
    telegram_id = message.from_user.id
    
    try:
        end_dt = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        state = auction_states[telegram_id]
        
        # التحقق من أن تاريخ النهاية أكبر من تاريخ البداية
        if end_dt <= state["start_date"]:
            bot.send_message(message.chat.id, "⚠️ تاريخ النهاية يجب أن يكون بعد تاريخ البداية")
            return
        
        # إنشاء المزاد
        seller_id = get_seller_by_telegram(telegram_id)[0]
        success, message_text, auction_id = create_auction_for_product(
            seller_id,
            state["product_id"],
            state["start_price"],
            state["start_date"],
            end_dt
        )
        
        if success:
            bot.send_message(message.chat.id,
                            f"✅ **تم إنشاء المزاد بنجاح!**\n\n"
                            f"🔨 رقم المزاد: #{auction_id}\n"
                            f"📦 المنتج: {state['product_name']}\n"
                            f"💰 سعر البداية: {state['start_price']} دينار\n"
                            f"📅 البداية: {state['start_date']}\n"
                            f"📅 النهاية: {end_dt}")
        else:
            bot.send_message(message.chat.id, message_text)
        
        del auction_states[telegram_id]
        show_seller_menu(message)
        
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ التاريخ غير صحيح! استخدم الصيغة: YYYY-MM-DD HH:MM")

@bot.message_handler(func=lambda message: message.from_user.id in auction_states and 
                     message.text == "❌ إلغاء")
def cancel_auction_process(message):
    """إلغاء عملية رفع المنتج للمزاد"""
    telegram_id = message.from_user.id
    
    if telegram_id in auction_states:
        del auction_states[telegram_id]
    
    bot.send_message(message.chat.id, "❌ تم إلغاء العملية")
    show_seller_menu(message)

# ===================== نظام المزادات - المشترين (البيديرز) =====================

# حالات المشترين في المزادات
bidder_states = {}

# DISABLED: This handler conflicts with the main browse_stores handler at line 9732
# @bot.message_handler(func=lambda message: "تصفح المتاجر 🛍️" in message.text)
# USE THE HANDLER AT LINE 9732 INSTEAD

@bot.message_handler(func=lambda message: "🔨 المزادات" in message.text)
def browse_auctions(message):
    """عرض قائمة المزادات النشطة"""
    telegram_id = message.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جلب المزادات النشطة مع تفاصيل المنتجات
    cursor.execute("""
        SELECT a.AuctionID, p.Name, a.StartPrice, a.AuctionStartAt, a.AuctionEndAt, 
               a.ProductID, COUNT(b.BidID) as BidCount
        FROM Auctions a
        JOIN Products p ON a.ProductID = p.ProductID
        LEFT JOIN AuctionBids b ON a.AuctionID = b.AuctionID
        WHERE a.Status = 'active'
        GROUP BY a.AuctionID, p.Name, a.StartPrice, a.AuctionStartAt, a.AuctionEndAt, a.ProductID
        ORDER BY a.AuctionEndAt ASC
    """)
    
    auctions = cursor.fetchall()
    conn.close()
    
    if not auctions:
        bot.send_message(message.chat.id, "📭 لا توجد مزادات متاحة حالياً")
        return
    
    # عرض المزادات
    msg = "🔨 **قائمة المزادات النشطة:**\n\n"
    
    for auction in auctions:
        auction_id, product_name, start_price, start_at, end_at, product_id, bid_count = auction
        
        # تنسيق التواريخ
        try:
            start_dt = datetime.fromisoformat(str(start_at).replace(" ", "T"))
            end_dt = datetime.fromisoformat(str(end_at).replace(" ", "T"))
            start_str = start_dt.strftime("%Y-%m-%d %H:%M")
            end_str = end_dt.strftime("%Y-%m-%d %H:%M")
        except:
            start_str = str(start_at)
            end_str = str(end_at)
        
        msg += f"🔨 **مزاد #{auction_id}**\n"
        msg += f"📦 المنتج: {product_name}\n"
        msg += f"💰 سعر البداية: {start_price} دينار\n"
        msg += f"⏰ النهاية: {end_str}\n"
        msg += f"📊 العروض: {bid_count}\n"
        msg += f"─" * 30 + "\n\n"
    
    # عرض زر اختيار المزاد
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for auction in auctions:
        auction_id, product_name = auction[0], auction[1]
        markup.add(f"🎯 مزاد #{auction_id}: {product_name[:20]}")
    
    markup.add("👈 العودة", "🏠 الرئيسية")
    
    bot.send_message(message.chat.id, msg, reply_markup=markup)

@bot.message_handler(func=lambda message: "🎯 مزاد #" in message.text)
def select_auction_to_bid(message):
    """اختيار مزاد للمزايدة"""
    telegram_id = message.from_user.id
    
    try:
        # استخراج معرف المزاد من الرسالة
        auction_id = int(message.text.split("#")[1].split(":")[0])
        
        # التحقق من وجود المزاد
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.AuctionID, p.Name, p.Description, a.StartPrice, 
                   a.AuctionStartAt, a.AuctionEndAt, p.ImagePath
            FROM Auctions a
            JOIN Products p ON a.ProductID = p.ProductID
            WHERE a.AuctionID = ? AND a.Status = 'active'
        """, (auction_id,))
        
        auction = cursor.fetchone()
        conn.close()
        
        if not auction:
            bot.send_message(message.chat.id, "❌ المزاد غير موجود أو انتهى")
            return
        
        auction_id, product_name, description, start_price, start_at, end_at, image_path = auction
        
        # حفظ معرف المزاد في الحالة
        bidder_states[telegram_id] = {
            "step": "register_bidder",
            "auction_id": auction_id,
            "product_name": product_name,
            "start_price": start_price
        }
        
        # عرض تفاصيل المزاد
        msg = f"🔨 **تفاصيل المزاد:**\n\n"
        msg += f"📦 المنتج: {product_name}\n"
        msg += f"💰 سعر البداية: {start_price} دينار\n"
        
        if description:
            msg += f"📝 الوصف: {description}\n"
        
        msg += f"\n✅ لكي تشارك في المزاد، يرجى إدخال اسمك ورقم تلفونك\n"
        
        bot.send_message(message.chat.id, msg)
        
        # طلب اسم المزايد
        bot.send_message(message.chat.id, "👤 **أدخل اسمك:**")
        
        # إرسال صورة المنتج إن وجدت
        if image_path:
            try:
                if IS_POSTGRES:
                    with open(image_path, 'rb') as photo:
                        bot.send_photo(message.chat.id, photo)
            except:
                pass
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")
        if telegram_id in bidder_states:
            del bidder_states[telegram_id]

@bot.message_handler(func=lambda message: message.from_user.id in bidder_states and 
                     bidder_states[message.from_user.id].get("step") == "register_bidder")
def enter_bidder_name(message):
    """إدخال اسم المزايد"""
    telegram_id = message.from_user.id
    
    bidder_states[telegram_id]["bidder_name"] = message.text.strip()
    bidder_states[telegram_id]["step"] = "enter_bidder_phone"
    
    bot.send_message(message.chat.id, "📞 **أدخل رقم تلفونك:**")

@bot.message_handler(func=lambda message: message.from_user.id in bidder_states and 
                     bidder_states[message.from_user.id].get("step") == "enter_bidder_phone")
def enter_bidder_phone(message):
    """إدخال رقم تلفون المزايد"""
    telegram_id = message.from_user.id
    state = bidder_states[telegram_id]
    
    # التحقق من صيغة رقم التلفون
    phone = message.text.strip()
    if not phone or len(phone) < 7:
        bot.send_message(message.chat.id, "⚠️ رقم التلفون غير صحيح!")
        return
    
    # تسجيل المزايد في قاعدة البيانات
    success, msg, bidder_id = register_auction_bidder(
        state["auction_id"],
        state["bidder_name"],
        phone,
        telegram_id
    )
    
    if not success:
        bot.send_message(message.chat.id, msg)
        del bidder_states[telegram_id]
        return
    
    state["bidder_id"] = bidder_id
    state["step"] = "enter_bid_amount"
    
    bot.send_message(message.chat.id,
                    f"✅ تم تسجيل بيانات الدخول بنجاح!\n\n"
                    f"👤 الاسم: {state['bidder_name']}\n"
                    f"📞 التلفون: {phone}\n\n"
                    f"💰 **الآن أدخل السعر الذي تريد المزايدة به:**\n"
                    f"(السعر الأدنى: {state['start_price']} دينار)")

@bot.message_handler(func=lambda message: message.from_user.id in bidder_states and 
                     bidder_states[message.from_user.id].get("step") == "enter_bid_amount")
def enter_bid_amount(message):
    """إدخال مبلغ العطاء"""
    telegram_id = message.from_user.id
    state = bidder_states[telegram_id]
    
    try:
        bid_amount = float(message.text)
        
        if bid_amount < state["start_price"]:
            bot.send_message(message.chat.id, 
                            f"⚠️ السعر يجب أن يكون على الأقل {state['start_price']} دينار")
            return
        
        # تسجيل العطاء
        success, msg, bid_id = place_auction_bid(
            state["auction_id"],
            state["bidder_id"],
            bid_amount
        )
        
        if success:
            bot.send_message(message.chat.id,
                            f"✅ **تم تسجيل عطاؤك بنجاح!**\n\n"
                            f"🔨 مزاد #{state['auction_id']}\n"
                            f"📦 المنتج: {state['product_name']}\n"
                            f"💰 السعر المعروض: {bid_amount} دينار\n\n"
                            f"شكراً لمشاركتك في المزاد!")
        else:
            bot.send_message(message.chat.id, msg)
        
        del bidder_states[telegram_id]
        
        # العودة إلى القائمة الرئيسية
        main_menu(message)
        
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ أدخل رقماً صحيحاً")

# ===================== خدمة التحقق من انتهاء المزادات =====================

def check_ended_auctions():
    """
    تحقق دوري من المزادات التي انتهت وأرسل إشعارات للبائعين والمتجر
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # جلب المزادات التي انتهت وتحتاج إلى إغلاق
        if IS_POSTGRES:
            cursor.execute("""
                SELECT a.AuctionID, a.ProductID, a.OriginalSellerID, a.AuctionStoreID, a.AuctionEndAt,
                       p.Name, s.TelegramID, s.StoreName
                FROM Auctions a
                JOIN Products p ON a.ProductID = p.ProductID
                JOIN Sellers s ON a.OriginalSellerID = s.SellerID
                WHERE a.Status = 'active' AND a.AuctionEndAt < NOW()
                ORDER BY a.AuctionEndAt DESC
            """)
        else:
            cursor.execute("""
                SELECT a.AuctionID, a.ProductID, a.OriginalSellerID, a.AuctionStoreID, a.AuctionEndAt,
                       p.Name, s.TelegramID, s.StoreName
                FROM Auctions a
                JOIN Products p ON a.ProductID = p.ProductID
                JOIN Sellers s ON a.OriginalSellerID = s.SellerID
                WHERE a.Status = 'active' AND a.AuctionEndAt < datetime('now')
                ORDER BY a.AuctionEndAt DESC
            """)
        
        ended_auctions = cursor.fetchall()
        
        if not ended_auctions:
            return
        
        print(f"🔔 عدد المزادات المنتهية: {len(ended_auctions)}")
        
        for auction_info in ended_auctions:
            auction_id, product_id, seller_id, auction_store_id, end_at, product_name, seller_tg_id, seller_name = auction_info
            
            # إغلاق المزاد والحصول على الفائز
            success, winner = close_auction(auction_id)
            
            if not success:
                continue
            
            # بناء رسالة النتائج
            # جلب قائمة جميع العطاءات مرتبة تصاعدياً
            bids = get_auction_bids(auction_id)
            
            result_msg = f"🔨 **انتهى المزاد #{auction_id}**\n\n"
            result_msg += f"📦 المنتج: {product_name}\n"
            result_msg += f"📅 وقت الانتهاء: {end_at}\n\n"
            
            result_msg += f"📊 **قائمة العطاءات (مرتب تصاعدياً):**\n"
            result_msg += "─" * 40 + "\n"
            
            if bids:
                for idx, bid in enumerate(bids, 1):
                    bidder_name, bidder_phone, highest_bid, bid_count = bid
                    if highest_bid:
                        result_msg += f"{idx}. 👤 {bidder_name}\n"
                        result_msg += f"   📞 {bidder_phone}\n"
                        result_msg += f"   💰 السعر: {highest_bid} دينار\n"
                        result_msg += f"   📊 عدد العروض: {bid_count}\n"
                        result_msg += "─" * 40 + "\n"
                
                if winner:
                    bidder_id, bidder_name, bidder_phone, final_price = winner
                    result_msg += f"\n🏆 **الفائز:**\n"
                    result_msg += f"👤 الاسم: {bidder_name}\n"
                    result_msg += f"📞 التلفون: {bidder_phone}\n"
                    result_msg += f"💰 السعر النهائي: {final_price} دينار"
                else:
                    result_msg += f"\n📭 **لم يتلقَ المزاد أي عروض**"
            else:
                result_msg += "📭 لم يتم استقبال أي عروض"
            
            # إرسال الرسالة إلى صاحب المتجر الأصلي
            try:
                bot.send_message(seller_tg_id, result_msg, parse_mode='Markdown')
                print(f"✅ تم إرسال نتيجة المزاد #{auction_id} إلى البائع (ID: {seller_tg_id})")
            except Exception as e:
                print(f"⚠️ فشل إرسال رسالة إلى البائع: {e}")
            
            # إرسال الرسالة إلى متجر المزادات
            try:
                cursor.execute("SELECT TelegramID FROM Sellers WHERE SellerID = ?", (auction_store_id,))
                auction_store = cursor.fetchone()
                if auction_store:
                    auction_store_tg_id = auction_store[0]
                    bot.send_message(auction_store_tg_id, result_msg, parse_mode='Markdown')
                    print(f"✅ تم إرسال نتيجة المزاد #{auction_id} إلى متجر المزادات")
            except Exception as e:
                print(f"⚠️ فشل إرسال رسالة إلى متجر المزادات: {e}")
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ خطأ في التحقق من المزادات المنتهية: {e}")
        conn.rollback()
    finally:
        conn.close()

# تشغيل البوت
if __name__ == "__main__":
    print("[INFO] Bot script is running...")
    
    # 1. Log Token Status
    if TOKEN:
        print(f"[OK] Token Loaded: {TOKEN[:5]}...{TOKEN[-5:]} (Length: {len(TOKEN)})")
    else:
        print("[ERROR] CRITICAL: No Token Found in Environment!")

    if os.environ.get('DATABASE_URL'):
        print("[INFO] DATABASE MODE: CLOUD (PostgreSQL)")
    else:
        print("[INFO] DATABASE MODE: LOCAL (SQLite)")

    try:
        print("[INFO] Initializing Database...")
        init_db()
        print("[OK] Database Initialized Successfully")
        
        # Initialize Auction Store
        print("[INFO] Initializing Auction Store...")
        try:
            initialize_auction_store()
            print("[OK] Auction Store Initialized Successfully")
        except Exception as auction_err:
            print(f"[WARN] Auction Store initialization failed (non-critical): {auction_err}")
        
        # Debug: Check products count after initialization
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Products")
            result = cursor.fetchone()
            product_count = result[0] if result else 0
            print(f"[INFO] Total products in database: {product_count}")
            
            cursor.execute("SELECT COUNT(*) FROM Products WHERE Quantity > 0 AND Status='active'")
            result = cursor.fetchone()
            active_product_count = result[0] if result else 0
            print(f"[INFO] Active products with Quantity > 0: {active_product_count}")
            
            conn.close()
        except Exception as db_check_err:
            print(f"[WARN] Database check failed (non-critical): {db_check_err}")
    except Exception as e:
        print(f"[ERROR] DATABASE INITIALIZATION ERROR: {e}")
        traceback.print_exc()
        print("[WARN] Attempting to continue anyway...")
    try:
        print("[INFO] Clearing Webhooks...")
        bot.remove_webhook()
        
    except Exception as e:
        print(f"[WARN] Failed to remove webhook: {e}")

    print("[INFO] Waiting 5 seconds for Telegram API to clear old session...")
    time.sleep(5)
    
    print("[INFO] Starting Polling...")
    
    # Start background task to check auctions
    import threading
    
    def check_auctions_periodically():
        """Check ended auctions every minute"""
        while True:
            try:
                check_ended_auctions()
            except Exception as e:
                print(f"[WARN] Auction check error: {e}")
            
            # Wait 60 seconds before next check
            time.sleep(60)
    
    # Start background thread
    auction_thread = threading.Thread(target=check_auctions_periodically, daemon=True)
    auction_thread.start()
    print("[OK] Auction check service ready")
    
    # Check if polling is disabled (for when Railway instance is running)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create FeatureFlags table if it doesn't exist
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FeatureFlags (
                FlagName TEXT PRIMARY KEY,
                FlagValue INTEGER DEFAULT 0,
                Description TEXT
            )
        """)
        conn.commit()
    except:
        pass
    
    polling_disabled = False
    try:
        cursor.execute("SELECT FlagValue FROM FeatureFlags WHERE FlagName=?", ("DISABLE_POLLING",))
        result = cursor.fetchone()
        polling_disabled = result[0] == 1 if result else False
    except:
        polling_disabled = False
    
    cursor.close()
    conn.close()
    
    # Start Flask API in a separate thread
    print("[INFO] Starting Flask API server in background...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(2)  # Give Flask time to start
    print("✅ Flask API started successfully")
    
    if polling_disabled:
        print("[WARN] POLLING DISABLED - Bot is in standby mode (Railway instance is active)")
        print("[INFO] To re-enable polling locally, run: python enable_local_polling.py")
# ===================== خادم التطبيق الخلفي (Background Monitoring) =====================

import threading

def cleanup_purchased_images():
    """
    خادم خلفي يراقب الصور المباعة ويحذفها تلقائياً
    يتحقق كل 30 ثانية
    """
    print("🔄 تم بدء خادم تنظيف الصور الخلفي...")
    
    while True:
        try:
            print("\n🔍 فحص الصور المباعة...")
            
            # للمنتجات المشترية، نحتاج لحذف الصور
            # نحن نراقب النتاجات في جدول CustomerCredit ذات TransactionType='Purchase'
            # ونرى إذا كانت الصور لهذا المنتج موجودة
            
            try:
                conn = get_db_connection()
            except Exception as db_err:
                print(f"⚠️ خطأ في الاتصال بقاعدة البيانات: {db_err}")
                time.sleep(60)
                continue
            
            cursor = conn.cursor()
            
            # الحصول على آخر 20 معاملة شراء
            try:
                if IS_POSTGRES:
                    cursor.execute("""
                        SELECT DISTINCT productid FROM imagestorage 
                        WHERE productid IS NOT NULL
                        LIMIT 50
                    """)
                else:
                    cursor.execute("""
                        SELECT DISTINCT productid FROM imagestorage
                    """)
                
                products_with_images = cursor.fetchall()
            except Exception as query_err:
                print(f"⚠️ خطأ في استعلام قاعدة البيانات: {query_err}")
                conn.close()
                time.sleep(60)
                continue
            
            if products_with_images:
                print(f"📦 عدد المنتجات المشترية التي قد تحتوي على صور: {len(products_with_images)}")
            
            conn.close()
            
            # نتحقق من كل منتج
            for (product_id,) in products_with_images:
                try:
                    images = get_product_images(product_id)
                    product = get_product_by_id(product_id)
                    
                    if not product:
                        continue
                    
                    # إذا كانت الكمية = 0 والصور موجودة، نحذفها
                    available_qty = product[7]
                    image_count = len(images) if images else 0
                    
                    if available_qty == 0 and image_count > 0:
                        print(f"🗑️ حذف {image_count} صور من المنتج {product_id} (الكمية=0)")
                        delete_n_images_from_product(product_id, image_count)
                    
                except Exception as e:
                    print(f"⚠️ خطأ في معالجة المنتج {product_id}: {e}")
            
            # الانتظار 30 ثانية قبل الفحص التالي
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ خطأ في خادم التنظيف الخلفي: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)
            # تابع الحلقة
# بدء خادم التنظيف في thread منفصل
cleanup_thread = threading.Thread(target=cleanup_purchased_images, daemon=True)
cleanup_thread.start()
print("✅ تم بدء خادم التنظيف الخلفي في thread منفصل")

# ===================== بدء البوت =====================
# Infinite loop to auto-restart on crashes/connection errors
print("🚀 جاري بدء البوت...")
try:
    while True:
        try:
            # infinity_polling handles many errors internally, but this loop catches the rest
            print("📡 جاري الاتصال بـ Telegram...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60, allowed_updates=['message', 'callback_query', 'my_chat_member'])
        except KeyboardInterrupt:
            print("\n⚠️ تم إيقاف البوت من قبل المستخدم")
            break
        except Exception as e:
            print(f"[WARN] Polling Error (Restarting in 5s): {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)
except Exception as main_err:
    print(f"❌ خطأ رئيسي: {main_err}")
    import traceback
    traceback.print_exc()
finally:
    print("🛑 تم إغلاق البوت")



