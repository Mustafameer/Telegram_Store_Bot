from utils.receipt_generator import generate_product_card
import os

# Mock Product Data
# pid, name, desc, price, wholesale_price, qty, img_path
mock_product = (
    123, 
    "طقم كنب فاخر", 
    "طقم كنب مودرن 7 مقاعد مع طاولة وسط", 
    450000, 
    400000, 
    5, 
    "test_image.jpg" # This might fail if image doesn't exist, code handles None
)

store_name = "متجر الأثاث العصري"

print("Generating product card...")
try:
    img_bio = generate_product_card(mock_product, store_name)
    
    if img_bio:
        with open("test_product_card_output.png", "wb") as f:
            f.write(img_bio.getvalue())
        print("[SUCCESS] Card saved to test_product_card_output.png")
    else:
        print("[FAILED] Image generation returned None")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
