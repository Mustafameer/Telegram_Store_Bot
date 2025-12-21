
import sys
import os

# Set Token to avoid exit
os.environ['TELEGRAM_BOT_TOKEN'] = "8562406465:AAEudEf_n6ZDnMlVy_UTwJ7eG1hBdDb1Tgw"

# Ensure we can import bot.py from CWD
sys.path.append(r"c:\Users\Hp\Desktop\TelegramStoreBot")

print("Importing bot to trigger init_db()...")
try:
    import bot
    print("Bot imported successfully.")
except Exception as e:
    print(f"Error importing bot: {e}")
