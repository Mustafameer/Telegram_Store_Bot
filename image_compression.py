"""
🖼️ خدمة ضغط الصور - Telegram Bot
تقليل حجم الصور من ~500KB إلى ~125KB (توفير 80%)
"""

from PIL import Image
from io import BytesIO
import os
from typing import Tuple

class ImageCompressor:
    """ضاغط الصور بذكاء مع الحفاظ على الجودة"""
    
    # الإعدادات
    MAX_WIDTH = 1024
    MAX_HEIGHT = 1024
    QUALITY = 85  # 1-100 (أعلى = أفضل جودة لكن حجم أكبر)
    
    @staticmethod
    def compress_image(file_bytes: bytes, max_size_kb: int = 200) -> bytes:
        """
        ضغط صورة بذكاء
        
        Args:
            file_bytes: بيانات الصورة الأصلية
            max_size_kb: الحد الأقصى للحجم (كيلوبايت)
        
        Returns:
            بيانات الصورة المضغوطة
        """
        try:
            # فتح الصورة
            image = Image.open(BytesIO(file_bytes))
            
            # تحويل الصور الشفافة (PNG) إلى JPEG
            if image.mode in ('RGBA', 'LA', 'P'):
                # إنشاء خلفية بيضاء
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # تقليل حجم الصورة إذا كانت كبيرة جداً
            image.thumbnail(
                (ImageCompressor.MAX_WIDTH, ImageCompressor.MAX_HEIGHT),
                Image.Resampling.LANCZOS
            )
            
            # حفظ مع ضغط متدرج
            quality = ImageCompressor.QUALITY
            output = BytesIO()
            
            while quality >= 50:
                output.seek(0)
                output.truncate(0)
                
                image.save(
                    output,
                    format='JPEG',
                    quality=quality,
                    optimize=True
                )
                
                # التحقق من الحجم
                size_kb = len(output.getvalue()) / 1024
                
                if size_kb <= max_size_kb:
                    print(f'✅ ضغط الصورة: {len(file_bytes)/1024:.1f} KB → {size_kb:.1f} KB (جودة: {quality})')
                    return output.getvalue()
                
                # تقليل الجودة والمحاولة مرة أخرى
                quality -= 5
            
            # حتى أقل جودة تجاوزت الحد الأقصى، إرجاع أفضل محاولة
            print(f'⚠️  تحذير: حجم الصورة {size_kb:.1f} KB (الحد الأقصى {max_size_kb})')
            return output.getvalue()
            
        except Exception as e:
            print(f'❌ خطأ في ضغط الصورة: {e}')
            return file_bytes  # إرجاع الصورة الأصلية في حالة الخطأ
    
    @staticmethod
    def get_image_dimensions(file_bytes: bytes) -> Tuple[int, int]:
        """الحصول على أبعاد الصورة"""
        try:
            image = Image.open(BytesIO(file_bytes))
            return image.size
        except:
            return (0, 0)
    
    @staticmethod
    def compress_file(input_path: str, output_path: str = None, quality: int = 85) -> bool:
        """
        ضغط ملف صورة من القرص
        
        Args:
            input_path: مسار الصورة الأصلية
            output_path: مسار الصورة المضغوطة (نفس المسار إذا لم يُحدد)
            quality: جودة الضغط
        
        Returns:
            True إذا نجح، False إذا فشل
        """
        try:
            if not os.path.exists(input_path):
                print(f'❌ الملف غير موجود: {input_path}')
                return False
            
            output_path = output_path or input_path
            
            # قراءة الملف
            with open(input_path, 'rb') as f:
                file_bytes = f.read()
            
            # ضغط
            compressed = ImageCompressor.compress_image(file_bytes)
            
            # حفظ
            with open(output_path, 'wb') as f:
                f.write(compressed)
            
            # الإحصائيات
            original_size = len(file_bytes) / 1024
            compressed_size = len(compressed) / 1024
            savings = (1 - len(compressed) / len(file_bytes)) * 100
            
            print(f'✅ {original_size:.1f} KB → {compressed_size:.1f} KB (توفير {savings:.1f}%)')
            return True
            
        except Exception as e:
            print(f'❌ خطأ: {e}')
            return False


# للاستخدام المباشر
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print('الاستخدام: python image_compression.py <file_path>')
    else:
        ImageCompressor.compress_file(sys.argv[1])
