#!/usr/bin/env python3
"""
اختبار: محاكاة العملية الكاملة - إضافة منتج بصورة في متجر مفتوح
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

import psycopg2
from psycopg2.extras import RealDictCursor

def save_dummy_image_to_cloud():
    """حفظ صورة وهمية في ImageStorage"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # إنشاء ملف وهمي
    timestamp = int(time.time())
    from uuid import uuid4
    uuid_hex = uuid4().hex
    filename = f"{timestamp}_{uuid_hex}.jpg"
    
    # بيانات صورة وهمية (صورة JPG صغيرة جداً)
    dummy_jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd3\xff\xd9'
    
    # إدراج في ImageStorage
    cursor.execute("""
        INSERT INTO ImageStorage (FileName, FileData, UpdatedAt)
        VALUES (%s, %s, NOW())
        ON CONFLICT (FileName) DO UPDATE
        SET FileData = EXCLUDED.FileData, UpdatedAt = NOW()
    """, (filename, dummy_jpeg))
    
    conn.commit()
    conn.close()
    return filename

print("\n" + "="*70)
print("🧪 محاكاة كاملة: إضافة منتج بصورة في متجر مفتوح")
print("="*70)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# 1. الحصول على متجر مفتوح
cursor.execute("""
    SELECT SellerID, StoreName
    FROM Sellers
    WHERE RequireCustomerRegistration = 0
    LIMIT 1
""")

seller = cursor.fetchone()
if not seller:
    print("❌ لا توجد متاجر مفتوحة!")
    conn.close()
    exit(1)

seller_id = seller['sellerid']
print(f"\n✅ متجر مفتوح: SellerID={seller_id}, StoreName={seller['storename']}")

# 2. الحصول على فئة
cursor.execute("""
    SELECT CategoryID FROM Categories WHERE SellerID = %s LIMIT 1
""", (seller_id,))

category = cursor.fetchone()
if not category:
    print(f"❌ لا توجد فئات للمتجر {seller_id}")
    conn.close()
    exit(1)

category_id = category['categoryid']
print(f"✅ الفئة: CategoryID={category_id}")

# 3. إنشاء منتج جديد
product_name = f"Test Product {int(time.time())}"
price = 100000.0
quantity = 5

print(f"\n🔄 إضافة منتج جديد:")
print(f"   Name: {product_name}")
print(f"   Price: {price}")
print(f"   Quantity: {quantity}")

cursor.execute("""
    INSERT INTO Products (SellerID, CategoryID, Name, Price, Quantity, ImagePath, Status)
    VALUES (%s, %s, %s, %s, %s, '', 'active')
""", (seller_id, category_id, product_name, price, quantity))

# 4. الحصول على ProductID
cursor.execute("""
    SELECT ProductID FROM Products
    WHERE SellerID=%s AND CategoryID=%s AND Name=%s
    ORDER BY ProductID DESC LIMIT 1
""", (seller_id, category_id, product_name))

result = cursor.fetchone()
if not result:
    print("❌ فشل إنشاء المنتج!")
    conn.rollback()
    conn.close()
    exit(1)

product_id = result['productid']
print(f"✅ تم إنشاء المنتج: ProductID={product_id}")

# 5. حفظ صورة في ImageStorage
print(f"\n🔄 حفظ صورة:")
filename = save_dummy_image_to_cloud()
print(f"✅ تم حفظ الصورة: {filename}")

# 6. محاكاة إدراج الصورة في ProductImages (نفس ما يفعله finish_adding_product)
print(f"\n🔄 محاكاة إدراج الصورة في ProductImages:")

# محاكاة المنطق من finish_adding_product
image_path = filename  # الملف الذي تم حفظه
require_registration = 0  # متجر مفتوح

all_images = []
if not require_registration and image_path:
    all_images.append(image_path)
    print(f"✅ تمت إضافة الصورة إلى all_images: {image_path}")

# إدراج الصور في ProductImages
for idx, img_filename in enumerate(all_images):
    cursor.execute("""
        INSERT INTO ProductImages (ProductID, ImagePath, ImageOrder)
        VALUES (%s, %s, %s)
    """, (product_id, img_filename, idx))
    print(f"✅ تم إدراج الصورة في ProductImages: ImageOrder={idx}, FileName={img_filename}")

conn.commit()

# 7. التحقق
print(f"\n📸 التحقق من النتائج:")
cursor.execute("""
    SELECT imageid, imagepath, imageorder
    FROM ProductImages
    WHERE productid = %s
    ORDER BY imageorder
""", (product_id,))

images = cursor.fetchall()
if images:
    print(f"✅ وجدت {len(images)} صورة في ProductImages:")
    for img in images:
        print(f"   - ImageID:{img['imageid']} | ImagePath:{img['imagepath']} | Order:{img['imageorder']}")
else:
    print(f"❌ لا توجد صور في ProductImages!")

# التحقق من ImageStorage
cursor.execute("""
    SELECT FileName, LENGTH(FileData) as size
    FROM ImageStorage
    WHERE FileName = %s
""", (filename,))

storage = cursor.fetchone()
if storage:
    print(f"✅ الصورة موجودة في ImageStorage: {storage['filename']} ({storage['size']} bytes)")
else:
    print(f"❌ الصورة غير موجودة في ImageStorage!")

conn.close()
print("\n" + "="*70 + "\n")
