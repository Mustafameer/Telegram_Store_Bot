#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows Service Wrapper للبوت
يشغل البوت ويحافظ عليه يعمل حتى لو حدثت مشاكل

استخدام:
    python service_wrapper.py
"""

import subprocess
import time
import os
import sys
from pathlib import Path

# المسار الكامل للمشروع
PROJECT_DIR = Path(__file__).parent
BOT_SCRIPT = PROJECT_DIR / "bot.py"
LOG_FILE = PROJECT_DIR / "bot_service.log"

def log_message(message):
    """تسجيل الرسالة في ملف"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    print(log_entry.strip())
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log: {e}")

def run_bot():
    """تشغيل البوت مع إعادة محاولة تلقائية"""
    
    log_message("=" * 60)
    log_message("🤖 خدمة البوت تبدأ")
    log_message("=" * 60)
    
    restart_count = 0
    max_restarts = 5
    restart_delay = 10  # ثواني
    
    while restart_count < max_restarts:
        try:
            log_message(f"🚀 محاولة #{restart_count + 1}: تشغيل bot.py...")
            
            # تشغيل البوت
            process = subprocess.Popen(
                [sys.executable, str(BOT_SCRIPT)],
                cwd=str(PROJECT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            
            log_message(f"✅ البوت يعمل (PID: {process.pid})")
            
            # انتظر البوت
            while True:
                line = process.stdout.readline()
                if line:
                    print(line.strip())
                    try:
                        with open(LOG_FILE, "a", encoding="utf-8") as f:
                            f.write(line)
                    except:
                        pass
                elif process.poll() is not None:
                    break
            
            returncode = process.returncode
            log_message(f"❌ البوت توقف برمز خروج: {returncode}")
            
        except KeyboardInterrupt:
            log_message("⚠️ تم إيقاف الخدمة بواسطة المستخدم")
            break
        except Exception as e:
            log_message(f"❌ خطأ: {e}")
        
        # محاولة إعادة التشغيل
        restart_count += 1
        
        if restart_count < max_restarts:
            log_message(f"⏳ سيتم إعادة المحاولة بعد {restart_delay} ثانية...")
            time.sleep(restart_delay)
        else:
            log_message("❌ تم تجاوز عدد محاولات إعادة التشغيل!")
    
    log_message("=" * 60)
    log_message("🛑 خدمة البوت توقفت")
    log_message("=" * 60)

if __name__ == "__main__":
    os.chdir(PROJECT_DIR)
    run_bot()
