"""
سكريبت لإضافة متجر TELEBOT للمتاجر المغلقة
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def add_telebot_store():
    """إضافة متجر TELEBOT للمتاجر المغلقة"""
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL غير موجود في متغيرات البيئة")
        return False
    
    try:
        # الاتصال بـ Railway PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # التحقق مما إذا كان TELEBOT موجوداً
        cursor.execute(
            "SELECT SellerID FROM Sellers WHERE UserName = %s OR StoreName = %s",
            ('telebot', 'TELEBOT')
        )
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️ متجر TELEBOT موجود بالفعل (ID: {existing['sellerid']})")
            cursor.close()
            conn.close()
            return True
        
        # إضافة متجر TELEBOT
        # استخدم TelegramID فريد وآمن
        telebot_telegram_id = 999999999  # TelegramID فريد لـ TELEBOT
        
        cursor.execute(
            """
            INSERT INTO Sellers (TelegramID, UserName, StoreName, Status, RequireCustomerRegistration)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING SellerID
            """,
            (telebot_telegram_id, 'telebot', 'TELEBOT - المتاجر المغلقة', 'active', 0)
        )
        
        seller_id = cursor.fetchone()['sellerid']
        conn.commit()
        
        print(f"✅ تم إضافة متجر TELEBOT بنجاح!")
        print(f"   SellerID: {seller_id}")
        print(f"   StoreName: TELEBOT - المتاجر المغلقة")
        print(f"   Status: active")
        print(f"\nملاحظة: يعرض هذا المتجر جميع منتجات المتاجر المغلقة")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.IntegrityError as e:
        print(f"❌ خطأ في السجل (قد يكون TELEBOT موجوداً بالفعل): {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 سكريبت إضافة متجر TELEBOT")
    print("=" * 50)
    add_telebot_store()
