
import sys

# Reconfigure stdout to handle utf-8
sys.stdout.reconfigure(encoding='utf-8')

filename = r"c:\Users\Hp\Desktop\TelegramStoreBot\bot.py"
search_str = "delete_order_"

try:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if search_str in line:
                print(f"Found at line {i+1}: {line.strip()}")
except Exception as e:
    print(f"Error: {e}")
