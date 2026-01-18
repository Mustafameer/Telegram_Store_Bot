#!/usr/bin/env python3
"""
حل مشكلة حذف المنتجات والفئات - حذف آمن مع المراجع الأجنبية
"""

import sys
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """الاتصال بـ PostgreSQL مباشرة"""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    return None

def list_foreign_keys():
    """عرض جميع القيود الأجنبية في قاعدة البيانات"""
    conn = get_connection()
    if not conn:
        print("❌ DATABASE_URL غير محدد")
        return
    
    cursor = conn.cursor()
    
    try:
        # جلب جميع الـ FK constraints
        cursor.execute("""
            SELECT 
                tc.constraint_name,
                kcu.table_name,
                kcu.column_name,
                ccu.table_name AS referenced_table_name,
                ccu.column_name AS referenced_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            ORDER BY kcu.table_name
        """)
        
        constraints = cursor.fetchall()
        
        if not constraints:
            print("ℹ️  لا توجد قيود أجنبية محددة بشكل صريح")
            return
        
        print("\n📋 جميع القيود الأجنبية في قاعدة البيانات:")
        print("=" * 120)
        
        for constraint in constraints:
            constraint_name, table_name, column_name, ref_table, ref_column = constraint
            print(f"📌 Constraint: {constraint_name}")
            print(f"   From: {table_name}.{column_name} → {ref_table}.{ref_column}")
            print()
            
    except Exception as e:
        print(f"❌ خطأ: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🔧 أداة إدارة حذف البيانات بشكل آمن")
    print("=" * 120)
    
    # عرض جميع القيود الأجنبية
    list_foreign_keys()
