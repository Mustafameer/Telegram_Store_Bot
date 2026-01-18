#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from bot import add_category, get_categories

# Add test categories for TELEBOT (seller_id = 27)
print("=" * 60)
print("🔧 إضافة فئات اختبارية للـ TELEBOT:")
print("=" * 60)

seller_id = 27

test_categories = [
    "الإلكترونيات",
    "الملابس",
    "الأحذية",
    "الإكسسوارات"
]

for cat_name in test_categories:
    print(f"\n➕ إضافة: {cat_name}")
    add_category(seller_id, cat_name)

print("\n" + "=" * 60)
print("✅ التحقق من الفئات بعد الإضافة:")
print("=" * 60)

categories = get_categories(seller_id)
if categories:
    for cat in categories:
        print(f"  ✅ {cat[1]} (ID: {cat[0]})")
    print(f"\nالمجموع: {len(categories)} فئة")
else:
    print("❌ لم تتم إضافة أي فئات!")
