
import sys
import os
import datetime

# Add current directory to sys.path so we can import utils
sys.path.append(os.getcwd())

from utils.receipt_generator import generate_order_card

# Mock Data
order_details = (
    8700, # 0: OrderID
    123,  # 1: BuyerID
    456,  # 2: SellerID
    245000, # 3: Total
    "Pending", # 4: Status
    datetime.datetime.now(), # 5: CreatedAt
    "Baghdad, Al-Mansour", # 6: Address (unused in new logic directly from tuple, passed as arg)
    "07701234567" # 7: Phone (unused in tuple)
)

items = [
    # (ID, OID, PID, Qty, Price, ..., ..., ..., Name, Desc, ImagePath)
    ("item_id", "order_id", "prod_id", 1, 22500, "2023-01-01", "Notes", "2023-01-01", "قميص ردن كاملة", "Desc", "c:/Users/Hp/Desktop/TelegramStoreBot/data/Images/test_image.jpg", 10, 10, "c:/Users/Hp/Desktop/TelegramStoreBot/data/Images/test_image.jpg"),
    ("item_id", "order_id", "prod_id", 1, 200000, "2023-01-01", "Notes", "2023-01-01", "بدلة رسمية كلاسيك", "Desc", "invalid_path.jpg", 10, 10, "invalid_path.png"),
    (3, 87, 103, 2, 15000, 0, None, None, "تيشيرت قطن", "Desc", None) # No image
]

print("Generating card...")
try:
    img_bio = generate_order_card(
        order_details, 
        items, 
        "علي محمد (استلام من المتجر)", 
        "07801234567", 
        "متجر الألبسة الرجالية"
    )

    if img_bio:
        with open("test_card_output.png", "wb") as f:
            f.write(img_bio.getbuffer())
        print("✅ Success! Generated 'test_card_output.png'")
    else:
        print("❌ Failed to generate card (returned None)")

except Exception as e:
    print(f"FAILED to generate card: {e}")
    import traceback
    traceback.print_exc()
