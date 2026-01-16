"""
سكريبت اختبار نظام متجر TELEBOT
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def test_telebot_system():
    """اختبار نظام TELEBOT"""
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL غير موجود")
        return
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=" * 60)
        print("🧪 اختبار نظام متجر TELEBOT")
        print("=" * 60)
        
        # 1. التحقق من وجود متجر TELEBOT
        print("\n1️⃣ التحقق من وجود متجر TELEBOT...")
        cursor.execute("SELECT * FROM Sellers WHERE UserName = %s", ('telebot',))
        telebot_store = cursor.fetchone()
        
        if telebot_store:
            print(f"   ✅ متجر TELEBOT موجود:")
            print(f"      - SellerID: {telebot_store['sellerid']}")
            print(f"      - StoreName: {telebot_store['storename']}")
            print(f"      - TelegramID: {telebot_store['telegramid']}")
            print(f"      - Status: {telebot_store['status']}")
        else:
            print("   ❌ متجر TELEBOT غير موجود!")
            return
        
        # 2. عد المتاجر المقفولة
        print("\n2️⃣ عد المتاجر المقفولة (RequireCustomerRegistration = 1)...")
        cursor.execute(
            "SELECT COUNT(*) as count FROM Sellers WHERE RequireCustomerRegistration = 1 AND Status = 'active'"
        )
        closed_stores_count = cursor.fetchone()['count']
        print(f"   ✅ عدد المتاجر المقفولة: {closed_stores_count}")
        
        # 3. إذا كان هناك متاجر مقفولة، عد منتجاتها
        if closed_stores_count > 0:
            print("\n3️⃣ المتاجر المقفولة:")
            cursor.execute(
                "SELECT SellerID, StoreName, UserName FROM Sellers WHERE RequireCustomerRegistration = 1 AND Status = 'active' ORDER BY StoreName"
            )
            closed_stores = cursor.fetchall()
            
            for store in closed_stores:
                cursor.execute(
                    "SELECT COUNT(*) as product_count FROM Products WHERE SellerID = %s AND Status = 'active'",
                    (store['sellerid'],)
                )
                product_count = cursor.fetchone()['product_count']
                print(f"   - {store['storename']} (ID: {store['sellerid']}) - {product_count} منتج")
            
            # 4. عد منتجات المتاجر المقفولة
            print("\n4️⃣ عد منتجات المتاجر المقفولة...")
            cursor.execute(
                """
                SELECT COUNT(DISTINCT p.ProductID) as product_count
                FROM Products p
                JOIN Sellers s ON p.SellerID = s.SellerID
                WHERE s.RequireCustomerRegistration = 1 AND s.Status = 'active' AND p.Status = 'active'
                """
            )
            closed_products_count = cursor.fetchone()['product_count']
            print(f"   ✅ عدد منتجات المتاجر المقفولة: {closed_products_count}")
        else:
            print("\n3️⃣ لا توجد متاجر مقفولة حالياً")
            print("   💡 لإنشاء متجر مقفول:")
            print("      UPDATE Sellers SET RequireCustomerRegistration = 1 WHERE SellerID = <id>;")
        
        # 5. التحقق من الاستعلام الأساسي
        print("\n5️⃣ اختبار الاستعلام الأساسي لـ TELEBOT:")
        cursor.execute(
            """
            SELECT DISTINCT p.ProductID, p.SellerID, p.Name, s.StoreName
            FROM Products p
            JOIN Sellers s ON p.SellerID = s.SellerID
            WHERE s.RequireCustomerRegistration = 1 AND s.Status = 'active' AND p.Status = 'active'
            ORDER BY s.StoreName, p.ProductID
            LIMIT 5
            """
        )
        sample_products = cursor.fetchall()
        
        if sample_products:
            print(f"   ✅ عينة من المنتجات (أول 5):")
            for product in sample_products:
                print(f"      - {product['name']} من {product['storename']}")
        else:
            print("   ℹ️ لا توجد منتجات في المتاجر المقفولة حالياً")
        
        print("\n" + "=" * 60)
        print("✅ اختبار نظام TELEBOT اكتمل بنجاح!")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_telebot_system()
