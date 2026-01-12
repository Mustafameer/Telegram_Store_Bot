#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار سريع لمزامنة الصور
"""
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SEED_DIR = os.path.join(BASE_DIR, "seed_data")
IMAGES_FOLDER = os.path.join(DATA_DIR, "Images")

def ensure_images_synced():
    """
    نسخ الصور من seed_data/Images إلى data/Images
    """
    seed_images_dir = os.path.join(SEED_DIR, "Images")
    
    print(f"Checking: {seed_images_dir}")
    print(f"Target: {IMAGES_FOLDER}")
    
    if os.path.exists(seed_images_dir):
        try:
            os.makedirs(IMAGES_FOLDER, exist_ok=True)
            
            # نسخ جميع الصور
            for image_file in os.listdir(seed_images_dir):
                src = os.path.join(seed_images_dir, image_file)
                dst = os.path.join(IMAGES_FOLDER, image_file)
                
                if os.path.isfile(src):
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        print(f"✅ تم نسخ الصورة: {image_file}")
                    else:
                        print(f"⏭️ الصورة موجودة بالفعل: {image_file}")
            
            print(f"✅ تم مزامنة الصور بنجاح")
            
            # عرض الصور الموجودة
            if os.path.exists(IMAGES_FOLDER):
                images = os.listdir(IMAGES_FOLDER)
                print(f"\n📸 الصور في data/Images: {len(images)}")
                for img in images:
                    print(f"   - {img}")
        except Exception as e:
            print(f"⚠️ خطأ في مزامنة الصور: {e}")
    else:
        print(f"⚠️ لم يتم العثور على مجلد seed_data/Images")

if __name__ == "__main__":
    ensure_images_synced()
