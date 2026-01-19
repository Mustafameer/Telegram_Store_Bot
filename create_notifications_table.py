#!/usr/bin/env python3
"""
إضافة جدول Notifications لتخزين إشعارات التطبيق
يسمح للتطبيق بجلب الإشعارات عند الشراء من متاجر مغلقة
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """الاتصال ببيانات PostgreSQL"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return None
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def create_notifications_table():
    """إنشاء جدول Notifications"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # تحقق من وجود الجدول
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'Notifications'
            );
        """)
        
        if cursor.fetchone()[0]:
            print("⚠️  جدول Notifications موجود بالفعل")
            cursor.close()
            conn.close()
            return True
        
        # إنشاء الجدول
        print("📝 إنشاء جدول Notifications...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Notifications" (
                "NotificationID" SERIAL PRIMARY KEY,
                "CustomerTelegramID" BIGINT NOT NULL,
                "SellerID" INT,
                "Type" VARCHAR(50) NOT NULL,        -- 'closed_store_purchase', 'order_confirmed', etc
                "Title" VARCHAR(255),
                "Message" TEXT NOT NULL,
                "ProductNames" VARCHAR(1000),       -- اسماء المنتجات المشتراة
                "TotalAmount" DECIMAL(10,2),        -- المبلغ الإجمالي
                "IsRead" BOOLEAN DEFAULT FALSE,
                "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "ReadAt" TIMESTAMP,
                "Data" JSONB                        -- بيانات إضافية (JSON)
            );
        """)
        
        # إنشاء فهرس للبحث السريع
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_customer 
            ON "Notifications"("CustomerTelegramID");
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_created 
            ON "Notifications"("CreatedAt" DESC);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_unread 
            ON "Notifications"("CustomerTelegramID") 
            WHERE "IsRead" = FALSE;
        """)
        
        conn.commit()
        print("✅ جدول Notifications تم إنشاؤه بنجاح!")
        
        # اعرض معلومات الجدول
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'Notifications'
            ORDER BY ordinal_position;
        """)
        
        print("\n📋 أعمدة الجدول:")
        for row in cursor.fetchall():
            print(f"  • {row[0]}: {row[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == "__main__":
    print("🔧 إضافة جدول Notifications...\n")
    success = create_notifications_table()
    if not success:
        print("\n❌ فشل الإنشاء")
        exit(1)
    print("\n✅ تم بنجاح!")
