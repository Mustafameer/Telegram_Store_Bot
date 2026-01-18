"""
عرض آخر السجلات من Railway
"""
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

def get_railway_logs():
    """الحصول على السجلات من Railway"""
    try:
        print("📋 جاري جلب السجلات من Railway...")
        print("=" * 60)
        
        # محاولة استخدام railway CLI
        result = subprocess.run(
            ["railway", "logs", "--follow=false"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            # عرض آخر 50 سطر
            print('\n'.join(lines[-50:]))
        else:
            print(f"❌ خطأ في الاتصال: {result.stderr}")
            print("\nجرب تشغيل:")
            print("  railway logs")
            print("\nأو افتح Railway Dashboard مباشرة")
            
    except Exception as e:
        print(f"❌ خطأ: {e}")
        print("\n💡 بدلاً من ذلك، يمكنك:")
        print("1. فتح Railway Dashboard: https://railway.app")
        print("2. اختيار المشروع TelegramStoreBot")
        print("3. عرض السجلات من Logs tab")

if __name__ == "__main__":
    get_railway_logs()
