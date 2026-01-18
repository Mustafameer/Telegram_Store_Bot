#!/usr/bin/env python3
"""
Simple launcher to start the bot with subprocess
"""
import subprocess
import sys
import os
import time

os.chdir(r'c:\Users\Hp\Desktop\TelegramStoreBot')

# Kill any existing python processes for the bot
try:
    subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                   capture_output=True, 
                   timeout=5)
    time.sleep(2)
except:
    pass

# Start the bot
try:
    subprocess.Popen([sys.executable, 'bot.py'])
    print("Bot started successfully")
except Exception as e:
    print(f"Error starting bot: {e}")
