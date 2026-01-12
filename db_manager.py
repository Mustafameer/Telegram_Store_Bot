import os
import sqlite3
import psycopg2
from contextlib import contextmanager
from integration_models import User, Seller, Category, Product, Order

# Database Configuration
IS_POSTGRES = os.environ.get('DATABASE_URL') is not None
DATABASE_URL = os.environ.get('DATABASE_URL')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "store_local_new.db")

def get_connection():
    """Returns a raw database connection (Postgres or SQLite)."""
    if IS_POSTGRES:
        try:
            return psycopg2.connect(DATABASE_URL, sslmode='require')
        except Exception as e:
            print(f"❌ DB Connection Error: {e}")
            raise e
    else:
        return sqlite3.connect(DB_FILE)

@contextmanager
def get_db_cursor(commit=False):
    """Context manager for database operations."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        conn.close()

# Helper to normalize query params for Postgres (%s) vs SQLite (?)
def normalize_query(query):
    if IS_POSTGRES:
        return query.replace('?', '%s')
    return query

# ==================== User & Seller Functions ====================

def get_seller_by_telegram(telegram_id) -> Seller:
    query = normalize_query("SELECT * FROM Sellers WHERE TelegramID = ?")
    with get_db_cursor() as cursor:
        cursor.execute(query, (telegram_id,))
        row = cursor.fetchone()
        return Seller.from_tuple(row) if row else None

# ==================== Category Functions ====================

def get_categories(seller_id) -> list[Category]:
    query = normalize_query("SELECT * FROM Categories WHERE SellerID = ?")
    with get_db_cursor() as cursor:
        cursor.execute(query, (seller_id,))
        rows = cursor.fetchall()
        return [Category.from_tuple(row) for row in rows]

def get_category_by_id(category_id) -> Category:
    query = normalize_query("SELECT * FROM Categories WHERE CategoryID = ?")
    with get_db_cursor() as cursor:
        cursor.execute(query, (category_id,))
        row = cursor.fetchone()
        return Category.from_tuple(row) if row else None

# ==================== Product Functions ====================

def get_products(seller_id, category_id=None) -> list[Product]:
    if category_id:
        query = normalize_query("SELECT * FROM Products WHERE SellerID = ? AND CategoryID = ?")
        params = (seller_id, category_id)
    else:
        query = normalize_query("SELECT * FROM Products WHERE SellerID = ?")
        params = (seller_id,)
        
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [Product.from_tuple(row) for row in rows]

def get_product_by_id(product_id) -> Product:
    query = normalize_query("SELECT * FROM Products WHERE ProductID = ?")
    with get_db_cursor() as cursor:
        cursor.execute(query, (product_id,))
        row = cursor.fetchone()
        return Product.from_tuple(row) if row else None
# ==================== Product Images Functions ====================

def get_product_images(product_id):
    """الحصول على صور المنتج من جدول ProductImages"""
    query = normalize_query("SELECT ImageID, ProductID, ImagePath FROM ProductImages WHERE ProductID = ? ORDER BY ImageID")
    with get_db_cursor() as cursor:
        cursor.execute(query, (product_id,))
        rows = cursor.fetchall()
        return rows

def get_product_images_for_order(product_id, quantity):
    """الحصول على عدد معين من الصور للطلب (حسب الكمية المطلوبة)"""
    query = normalize_query("SELECT ImageID, ProductID, ImagePath FROM ProductImages WHERE ProductID = ? LIMIT ?")
    with get_db_cursor() as cursor:
        cursor.execute(query, (product_id, quantity))
        rows = cursor.fetchall()
        return rows

def delete_product_images(image_ids):
    """حذف صور المنتج بعد الشحن"""
    if not image_ids:
        return True
    
    placeholders = ','.join(['%s' if IS_POSTGRES else '?' for _ in image_ids])
    query = f"DELETE FROM ProductImages WHERE ImageID IN ({placeholders})"
    
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, image_ids)
        return True
    except Exception as e:
        print(f"Error deleting product images: {e}")
        return False

def update_product_quantity(product_id, quantity):
    """تحديث كمية المنتج"""
    query = normalize_query("UPDATE Products SET Quantity = Quantity - ? WHERE ProductID = ?")
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (quantity, product_id))
        return True
    except Exception as e:
        print(f"Error updating product quantity: {e}")
        return False