#!/usr/bin/env python3
"""
إعادة تعيين البوت - مسح webhook القديم
Reset Bot - Clear old webhook
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

API_KEY = os.getenv("TELEGRAM_API_KEY")
print(f"🔄 جاري مسح webhook القديم...")
print(f"🔄 Clearing old webhook...")

# مسح webhook
url = f"https://api.telegram.org/bot{API_KEY}/deleteWebhook"
response = requests.get(url)
print(f"✅ {response.json()}")

# الحصول على معلومات البوت
url = f"https://api.telegram.org/bot{API_KEY}/getMe"
response = requests.get(url)
bot_info = response.json()
print(f"\n🤖 معلومات البوت:")
print(f"   الاسم: {bot_info['result']['first_name']}")
print(f"   Username: @{bot_info['result']['username']}")
print(f"   ID: {bot_info['result']['id']}")

print(f"\n✅ تم إعادة تعيين البوت بنجاح!")
print(f"✅ Bot reset successfully!")
print(f"\nالآن شغّل: python start_server.py")
