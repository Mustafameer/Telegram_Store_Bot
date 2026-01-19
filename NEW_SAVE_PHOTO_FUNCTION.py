"""
🖼️ Updated save_photo_from_message() function
استبدل الدالة القديمة في bot.py بهذه
"""

def save_photo_from_message(message):
    """
    يحفظ الصورة المرسلة - يرفعها إلى Firebase بدلاً من PostgreSQL
    """
    try:
        if not message.photo:
            return None
        
        # تحميل الصورة الأصلية
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        original_size = len(downloaded) / 1024
        
        # ✅ ضغط الصورة (توفير ~80% مساحة)
        from image_compression import ImageCompressor
        downloaded_compressed = ImageCompressor.compress_image(downloaded)
        compressed_size = len(downloaded_compressed) / 1024
        
        ext = os.path.splitext(file_info.file_path)[1]
        if not ext:
            ext = ".jpg"
        
        # ✅ نفس صيغة اسم الملف من Flutter: {timestamp}_{32-char-uuid}{ext}
        timestamp = int(time.time())
        uuid_hex = uuid.uuid4().hex  # 32 حرف hex بدون شرطات
        filename = f"{timestamp}_{uuid_hex}{ext}"
        
        path = os.path.join(IMAGES_FOLDER, filename)
        
        # ✅ Save to Disk (محلي) - مع الصورة المضغوطة
        with open(path, "wb") as f:
            f.write(downloaded_compressed)
        
        print(f"🖼️  ضغط الصورة: {original_size:.1f} KB → {compressed_size:.1f} KB (توفير {(1-compressed_size/original_size)*100:.1f}%)")
        
        # ✅ Upload to Firebase Storage - إذا كان مفعل
        firebase_url = None
        if FIREBASE_ENABLED:
            try:
                print(f"🔥 [Firebase] Uploading image {filename}...")
                bucket = storage.bucket()
                blob = bucket.blob(f'telegram-images/{filename}')
                blob.upload_from_string(downloaded_compressed, content_type='image/jpeg')
                
                # جعل الملف عام
                blob.make_public()
                firebase_url = blob.public_url
                
                print(f"✅ [Firebase] Uploaded: {firebase_url}")
            except Exception as fb_e:
                print(f"⚠️  [Firebase] Upload failed: {fb_e}")
                firebase_url = None
        
        # ✅ Upload to PostgreSQL ImageStorage (كـ fallback)
        if IS_POSTGRES:
            try:
                print(f"🔄 [Cloud] Attempting to upload image {filename} to PostgreSQL...")
                conn_pg = get_db_connection()
                cursor_pg = conn_pg.cursor()
                
                # إذا لدينا رابط Firebase، احفظه مباشرة
                if firebase_url:
                    cursor_pg.execute(
                        '''INSERT INTO imagestorage (filename, url, firebase_filename) 
                           VALUES (%s, %s, %s) 
                           ON CONFLICT (filename) DO UPDATE 
                           SET url = EXCLUDED.url, firebase_filename = EXCLUDED.firebase_filename''',
                        (filename, firebase_url, filename)
                    )
                else:
                    # بدون Firebase - احفظ البيانات الثنائية كـ fallback
                    import psycopg2
                    cursor_pg.execute(
                        '''INSERT INTO imagestorage (filename, filedata, url) 
                           VALUES (%s, %s, %s) 
                           ON CONFLICT (filename) DO UPDATE 
                           SET filedata = EXCLUDED.filedata''',
                        (filename, psycopg2.Binary(downloaded_compressed), firebase_url)
                    )
                
                conn_pg.commit()
                conn_pg.close()
                print(f"✅ [Cloud] Saved image {filename} to PostgreSQL")
                
            except Exception as pg_e:
                print(f"❌ [Cloud] Upload Failed: {type(pg_e).__name__}: {pg_e}")
                import traceback
                traceback.print_exc()
                if 'conn_pg' in locals():
                    try:
                        conn_pg.close()
                    except: pass
        else:
            print("⚠️ [Local] IS_POSTGRES is False. Using SQLite only.")
        
        return filename  # ارجع اسم الملف
        
    except Exception as e:
        print(f"⚠️ خطأ في حفظ الصورة: {e}")
        import traceback
        traceback.print_exc()
        return None
