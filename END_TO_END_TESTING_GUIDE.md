# End-to-End Testing Checklist

## Pre-Testing Setup

### 1. Verify Database Connection
```bash
python test_image_retrieval.py
```
Expected output:
```
✅ Connected to PostgreSQL
✅ imagestorage table exists
📊 Total images: 3
```

### 2. Build Flutter App
```bash
cd flutter_store_app
flutter pub get
flutter run -d windows
```
Expected: No compilation errors

---

## Test Case 1: Add Product with Image

### Steps
1. Open Flutter app
2. Go to "Products" tab
3. Click "➕" to add new product
4. Fill in details:
   - Name: "Test Product 1"
   - Category: (select one)
   - Price: 10000
   - Quantity: 5
5. Click image area to select image file
6. Click "حفظ" (Save)

### Expected Result
- ✅ Dialog closes automatically
- ✅ Product appears in list
- ✅ No error dialog

### Verify in Database
```bash
python test_image_upload_flutter.py
```
Should show:
- New product in products table
- New image in productimages table
- New binary data in imagestorage table

---

## Test Case 2: View Product in Bot

### Steps
1. Open Telegram bot
2. Click "تصفح المتاجر" (Browse Stores)
3. Select store with new product
4. Select category
5. Click on product name

### Expected Result
- ✅ Product details display
- ✅ **Product image displays** (this was the main fix!)
- ✅ Price and description visible
- ✅ "Add to Cart" button works

### Verify
If image shows: ✅ **Issue is FIXED!**

---

## Test Case 3: Update Product

### Steps
1. Flutter app - Products tab
2. Click edit icon (pencil) on a product
3. Change name or quantity
4. Click "حفظ" (Save)

### Expected Result
- ✅ Dialog closes
- ✅ Product list updates
- ✅ No error message

### Verify in Database
```sql
SELECT * FROM products WHERE name = 'new_name' LIMIT 1;
```

---

## Test Case 4: Delete Product

### Steps
1. Flutter app - Products tab
2. Click delete icon (trash) on a product
3. Confirm deletion

### Expected Result
- ✅ Product disappears from list
- ✅ Success SnackBar shows
- ✅ No error message

### Verify in Database
```sql
SELECT COUNT(*) FROM productimages WHERE productid = {deleted_product_id};
-- Should return 0 (cascade delete worked)
```

---

## Test Case 5: Manage Product Images

### Steps
1. Flutter app - Products tab
2. Click image icon (camera) on a product
3. Click "add images"
4. Select one or more image files
5. Wait for upload confirmation

### Expected Result
- ✅ Images added to product
- ✅ Success message shows
- ✅ Images appear in list

### Verify in Database
```bash
python test_image_upload_flutter.py
```
Should show product with multiple images

---

## Test Case 6: Delete Seller

### Steps
1. Flutter app - Home tab (الرئيسية)
2. Select a seller to delete
3. Click delete button
4. Confirm

### Expected Result
- ✅ Seller disappears
- ✅ Success SnackBar shows
- ✅ All related products deleted (cascade)

### Verify in Database
```sql
SELECT COUNT(*) FROM products WHERE sellerid = {deleted_seller_id};
-- Should return 0
```

---

## Troubleshooting

### Problem: No image displays in bot

**Check 1: Product has image in database**
```bash
python test_image_upload_flutter.py
# Should show product with images
```

**Check 2: Image filename format**
```bash
python -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute('SELECT imagepath FROM productimages LIMIT 1')
print('ProductImage path:', cur.fetchone()[0])
cur.execute('SELECT filename FROM imagestorage LIMIT 1')  
print('ImageStorage filename:', cur.fetchone()[0])
"
# If they don't match, there's still a mismatch
```

**Check 3: Flutter app logs**
Look for errors when adding product:
```
📤 Uploading image to cloud: {should see timestamped name}
✅ Image uploaded successfully: {filename}
```

### Problem: Flutter app crashes on add product

**Check logs:**
```
adb logcat | grep flutter  # Android
```

**Verify imports:**
- Is `package:path/path.dart as p;` imported?
- Is `package:uuid/uuid.dart;` imported?

### Problem: Product visible in Flutter but not in bot

**Check:**
1. Product quantity > 0?
2. Product status = 'active'?
3. Seller status = 'active'?

---

## Success Criteria

### ✅ All of these should work:
- [ ] Flutter app builds without errors
- [ ] Add product with image saves to database
- [ ] Product appears in Flutter product list
- [ ] Image displays in bot product card
- [ ] Update product works and saves changes
- [ ] Delete product removes from database
- [ ] Delete seller cascades to products and images
- [ ] Multiple images per product supported
- [ ] Bot can retrieve all images from cloud

### 🎉 If ALL checked: Issue is RESOLVED!

---

## Database Verification Scripts

### Quick Check - All Tables Present
```bash
python check_postgres_tables.py
```

### Check Image Storage
```bash
python test_image_upload_flutter.py
```

### Check Retrieval Works
```bash
python test_image_retrieval.py
```

---

## Performance Notes

- Image upload is asynchronous (non-blocking)
- Images stored as BYTEA in PostgreSQL (efficient binary storage)
- Filename format ensures no collisions
- Cascade deletes cleanup orphaned images

---

## Documentation References

See these files for detailed info:

- `IMAGE_DISPLAY_FIX_FINAL.md` - Complete image architecture
- `COMPLETE_SESSION_SUMMARY.md` - All three issues resolved
- `bot.py` lines 3068-3120 - `save_photo_from_message()` function
- `bot.py` lines 3162-3240 - `send_product_with_image()` function
- `flutter_store_app/lib/services/postgres_service.dart` - Database layer

---

## Final Verification Command

After all tests pass, run this to confirm:

```bash
python -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Count products, images, and sellers
cur.execute('SELECT COUNT(*) FROM products WHERE status = \\'active\\'')
products = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM imagestorage')
images = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM productimages')
links = cur.fetchone()[0]

print(f'✅ Active Products: {products}')
print(f'✅ Images in Storage: {images}')
print(f'✅ Product-Image Links: {links}')

if links > 0 and images > 0:
    print('\\n🎉 SYSTEM READY! Images can be displayed.')
else:
    print('\\n⚠️ No images found. Add products with images first.')
"
```

---

## Quick Links

| Task | File |
|------|------|
| Build Flutter | `flutter_store_app/` |
| Run Bot | `python bot.py` |
| Check DB | `test_image_upload_flutter.py` |
| View Logs | Check terminal output |
| Add Test Data | `seed_cloud_database.py` |
| Reset DB | Contact admin |

---

**Testing Duration**: ~15-20 minutes
**Expected Result**: ✅ All tests pass
**Next Step**: Go to COMPLETE_SESSION_SUMMARY.md for details

Last Updated: 2026-01-15
