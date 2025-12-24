
import sys

filename = r"c:\Users\Hp\Desktop\TelegramStoreBot\bot.py"
search_str = "def send_product_with_image"

try:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if search_str in line:
                print(f"Found at line {i+1}: {line.strip()}")
                sys.exit(0)
    print("Not found")
except Exception as e:
    print(f"Error: {e}")
