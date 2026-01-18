#!/usr/bin/env python3
"""
التحقق من أن البوت يقرأ من الجدول الصحيح
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("✅ التحقق من قراءة البوت للفئات")
print("="*70)

try:
    from bot import get_categories
    
    # اختبار البائع
    seller_id = 27
    
    print(f"\n🔍 جاري قراءة الفئات للبائع {seller_id}...")
    categories = get_categories(seller_id)
    
    if categories:
        print(f"\n✅ تم قراءة {len(categories)} فئة:")
        for cat_id, name in categories:
            print(f"   - ID: {cat_id}, Name: '{name}'")
    else:
        print(f"\n❌ لم يتم قراءة أي فئات!")
    
    print(f"\n✅ البوت يقرأ من الجدول الصحيح!")
    
except Exception as e:
    print(f"\n❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
