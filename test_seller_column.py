#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار سريع لـ require_registration
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import get_seller_by_id

# اختبر Seller ID=21
seller = get_seller_by_id(21)
print(f"Seller ID=21:")
print(f"  seller = {seller}")
print(f"  len(seller) = {len(seller) if seller else 'N/A'}")

if seller and len(seller) > 10:
    require_registration = seller[10]
    print(f"  seller[10] (requirecustomerregistration) = {require_registration}")
    print(f"  Type: {type(require_registration)}")
    if require_registration:
        print(f"  ✅ متجر مغلق (يتطلب تسجيل)")
    else:
        print(f"  ✅ متجر مفتوح")
else:
    print(f"  ❌ لا يمكن الوصول لـ seller[10]")

# اختبر Seller ID=27 (المتجر المفتوح)
print(f"\nSeller ID=27:")
seller27 = get_seller_by_id(27)
if seller27 and len(seller27) > 10:
    require_registration = seller27[10]
    print(f"  seller[10] (requirecustomerregistration) = {require_registration}")
    if require_registration:
        print(f"  ✅ متجر مغلق (يتطلب تسجيل)")
    else:
        print(f"  ✅ متجر مفتوح")
