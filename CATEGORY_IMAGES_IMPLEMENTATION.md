# Category Images Database Storage Implementation

## Summary
Migrated category image storage from local file paths to PostgreSQL database BYTEA columns. This ensures images persist across app restarts and are properly synchronized.

## Changes Made

### 1. Database Schema (PostgreSQL)
Added three new columns to the `Categories` table:
- `ImageFileName` (VARCHAR(255)): Name of the stored image file
- `ImageUrl` (VARCHAR(1000)): Firebase CDN URL (for future Firebase upload support)
- `ImageData` (BYTEA): Raw image binary data (hex-encoded)

**Migration Script**: `add_category_image_columns.py`
```bash
python add_category_image_columns.py
```

### 2. Flutter Models (database_models.dart)
Updated `Category` class with new fields:
```dart
class Category {
  final int categoryId;
  final int sellerId;
  final String name;
  final int orderIndex;
  final String? imagePath;        // Legacy: local file path
  final String? imageFileName;    // NEW: database image file name
  final String? imageUrl;         // NEW: Firebase URL (if uploaded)
  
  Category copyWith({...}); // Added for easy updates
}
```

### 3. PostgreSQL Service (postgres_service.dart)
Added three new methods for category image management:

```dart
// Save image to database
Future<bool> saveCategoryImage(int categoryId, Uint8List imageData, String fileName)

// Retrieve image from database
Future<Uint8List?> getCategoryImageData(int categoryId)

// Delete image from database
Future<bool> deleteCategoryImage(int categoryId)

// Get last inserted category
Future<Category?> getLastCategory(int sellerId)
```

**How it works**:
1. Image data is converted to hex string for storage
2. Hex is decoded back to bytes for display
3. Images are cached with 60-minute validity
4. Firebase URLs can be stored for future CDN support

### 4. Categories Tab (categories_tab.dart)
**Changes**:

#### CategoryFormDialog
- Now accepts `imageBytes` from file picker
- Stores both file path (for UI) and bytes (for database)
- Saves image to database after category is created/updated

```dart
onSave: (name, imagePath, imageBytes) async {
  // Save category
  // Then save image bytes to database
  await PostgresService().saveCategoryImage(categoryId, imageBytes, fileName);
}
```

#### Image Display
- New `_CategoryImageBuilder` widget fetches image from database
- Falls back to category icon if no image exists
- Displays `Image.memory()` for database-stored images

```dart
_CategoryImageBuilder(categoryId: category.categoryId)
```

### 5. Database Helper (database_helper.dart)
Added proxy method to access new PostgreSQL functions:
```dart
Future<Category?> getLastCategory(int sellerId)
```

## Image Flow

### Upload (New/Update Category)
```
FilePickerResult
    ↓
Uint8List (imageBytes)
    ↓
saveCategoryImage(categoryId, imageBytes, fileName)
    ↓
PostgreSQL: hex-encode → BYTEA column
```

### Display
```
PostgreSQL: BYTEA column (hex)
    ↓
getCategoryImageData(categoryId)
    ↓
_hexToBytes() conversion
    ↓
Image.memory(Uint8List)
```

### Delete
```
deleteCategoryImage(categoryId)
    ↓
UPDATE Categories SET ImageFileName=NULL, ImageData=NULL
```

## Database Schema Migration

The migration script (`add_category_image_columns.py`) checks for existing columns before adding them:

```sql
ALTER TABLE "Categories" ADD COLUMN "ImageFileName" VARCHAR(255);
ALTER TABLE "Categories" ADD COLUMN "ImageUrl" VARCHAR(1000);
ALTER TABLE "Categories" ADD COLUMN "ImageData" BYTEA;
```

**Status**: ✅ Successfully applied

## Benefits

1. **Persistence**: Images survive app restarts
2. **Synchronization**: Same image data across all devices
3. **Database Integrity**: Images stored as BLOB like products
4. **Fallback Support**: Can use Firebase URLs later
5. **Consistency**: Uses same pattern as product images

## Testing Checklist

- [ ] Add category with image
- [ ] Restart app - image should still display
- [ ] Update category image
- [ ] Delete category image
- [ ] Verify image persists on cloud database
- [ ] Test on web, iOS, Android platforms

## Future Enhancements

1. **Firebase Integration**: Upload images to Firebase Storage
   - Set `ImageUrl` to CDN URL
   - Use `Image.network()` with fallback to `Image.memory()`

2. **Image Compression**: Reduce database storage
   - Compress JPEG to 80% quality
   - Similar to product image compression

3. **Image Caching**: Improve load times
   - Cache category images in memory
   - 60-minute validity window (already implemented in postgres_service.dart)

## Important Notes

⚠️ **Legacy ImagePath Field**:
- `imagePath` field still exists for backward compatibility
- New images use database storage (imageFileName + imageData)
- Can migrate old images if needed later

⚠️ **Database Constraints**:
- BYTEA column stores raw binary data
- Hex encoding adds ~2x size to storage (reversible)
- Each image stored independently (no compression yet)

## Troubleshooting

**Images not displaying after restart**:
1. Check PostgreSQL connection is working
2. Verify columns exist: `SELECT ImageFileName, ImageData FROM "Categories" LIMIT 1;`
3. Ensure image bytes were properly encoded to hex

**Error: column "ImageFileName" does not exist**:
1. Run migration script: `python add_category_image_columns.py`
2. Verify columns added: Check PostgreSQL directly

**Out of memory with large images**:
1. Add image compression before saving
2. Reduce image quality to 80-85%
3. Resize images to max 500x500 pixels
