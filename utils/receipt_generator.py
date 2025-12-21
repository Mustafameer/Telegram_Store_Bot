import os
import io

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def generate_order_receipt(order_details, items, store_name, buyer_name, buyer_phone):
    """
    Generates a visual receipt for the order.
    
    Args:
        order_details: Tuple (OrderID, BuyerID, SellerID, Total, Status, Date, Address, Phone, PaymentMethod, FullyPaid)
        items: List of tuples (ItemID, OrderID, ProductID, Qty, Price, ..., ProductName, Desc, ImagePath) 
               Note: The structure depends on the SQL query. We assume the last elements are Product Info.
        store_name: String
        buyer_name: String
        buyer_phone: String
        
    Returns:
        BytesIO object containing the image, or None if PIL is missing or error occurs.
    """
    if not HAS_PIL:
        print("⚠️ Pillow library not found. Skipping receipt generation.")
        return None

    try:
        # Configuration
        WIDTH = 800
        PADDING = 40
        HEADER_HEIGHT = 150
        ITEM_HEIGHT = 120
        FOOTER_HEIGHT = 100
        
        # Calculate dynamic height
        num_items = len(items)
        # Limit visible items to prevent huge images, maybe show "and X more..." logically, 
        # but for now let's draw all or up to 10.
        DISPLAY_LIMIT = 10
        visible_items = items[:DISPLAY_LIMIT]
        
        content_height = len(visible_items) * ITEM_HEIGHT
        total_height = HEADER_HEIGHT + content_height + FOOTER_HEIGHT + 60 # Extra padding
        
        if len(items) > DISPLAY_LIMIT:
            total_height += 50 # Space for "+ X more items"
            
        # Colors
        BG_COLOR = (24, 24, 28) # Dark Background
        CARD_COLOR = (35, 35, 40) # Slightly lighter for items
        TEXT_COLOR = (255, 255, 255)
        ACCENT_COLOR = (0, 122, 255) # Blue
        PRICE_COLOR = (46, 204, 113) # Green
        
        # Fonts (Try to load a font, fallback to default)
        try:
            # Try to find a standard font like Arial or Segoe UI on Windows/Data dir
            # For Arabic support, we need a font that supports it.
            # We will try a few common paths.
            font_path = "arial.ttf" # Fallback
            
            # Check for a font in data directory if you have one
            # local_font = "data/fonts/Cairo-Regular.ttf"
            # if os.path.exists(local_font):
            #     font_path = local_font
                
            regular_font = ImageFont.truetype(font_path, 24)
            title_font = ImageFont.truetype(font_path, 36)
            bold_font = ImageFont.truetype(font_path, 28)
            small_font = ImageFont.truetype(font_path, 18)
        except:
            regular_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
            bold_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Create Image
        img = Image.new('RGB', (WIDTH, total_height), BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        order_id = order_details[0]
        total_amount = order_details[3]
        order_date = str(order_details[5]).split()[0]
        
        # --- HEADER ---
        # Draw Store Name and ID
        draw.text((WIDTH - PADDING, PADDING), f"#{order_id}", font=title_font, fill=ACCENT_COLOR, anchor="rt")
        draw.text((PADDING, PADDING), f"متجر: {store_name}", font=title_font, fill=TEXT_COLOR, anchor="lt")
        
        # Draw Status (Simplified)
        status = order_details[4] # e.g., Pending
        status_text = "قيد الانتظار ⏳" if status == 'Pending' else status
        draw.text((WIDTH // 2, PADDING), status_text, font=bold_font, fill=(255, 165, 0), anchor="mt")
        
        # Buyer Info
        draw.text((WIDTH - PADDING, PADDING + 60), f"📅 {order_date}", font=regular_font, fill=(200, 200, 200), anchor="rt")
        draw.text((WIDTH - PADDING, PADDING + 100), f"👤 {buyer_name}", font=regular_font, fill=(200, 200, 200), anchor="rt")
        draw.text((WIDTH - PADDING, PADDING + 140), f"📞 {buyer_phone}", font=regular_font, fill=(200, 200, 200), anchor="rt")
        
        # Address (Left side)
        address = order_details[6]
        if address:
             draw.text((PADDING, PADDING + 100), f"📍 {address[:30]}", font=small_font, fill=(200, 200, 200), anchor="lt")

        # Line Separator
        line_y = HEADER_HEIGHT + 40
        draw.line((PADDING, line_y, WIDTH - PADDING, line_y), fill=(60, 60, 60), width=2)
        
        # --- ITEMS ---
        current_y = line_y + 20
        
        for idx, item in enumerate(visible_items):
            # Parse Item
            # item structure matches fetchall() from get_order_details:
            # oi.* (0-7), p.Name (8), p.Desc (9), p.ImagePath (10)
            qty = item[3]
            price = item[4]
            prod_name = item[8]
            prod_img_path = item[10] if len(item) > 10 else None
            
            # Item Background
            # draw.rectangle((PADDING, current_y, WIDTH - PADDING, current_y + ITEM_HEIGHT - 10), fill=CARD_COLOR, outline=None)
            
            # Product Image (Placeholder or Load)
            img_x = WIDTH - PADDING - 100 # Right aligned image
            
            if prod_img_path and os.path.exists(prod_img_path):
                try:
                    p_img = Image.open(prod_img_path).convert("RGBA")
                    p_img = p_img.resize((90, 90))
                    # Create rounded mask
                    mask = Image.new("L", (90, 90), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.rounded_rectangle((0, 0, 90, 90), radius=10, fill=255)
                    img.paste(p_img, (img_x, current_y), mask)
                except:
                    # Fallback rect
                    draw.rectangle((img_x, current_y, img_x + 90, current_y + 90), fill=(50, 50, 50))
            else:
                 # No image placeholder
                 draw.rectangle((img_x, current_y, img_x + 90, current_y + 90), fill=(50, 50, 50))
                 draw.text((img_x + 45, current_y + 45), "No Img", font=small_font, fill=(150, 150, 150), anchor="mm")

            # Product Name & Details (Right aligned text, to the left of image)
            text_x = img_x - 20 
            draw.text((text_x, current_y + 10), prod_name, font=bold_font, fill=TEXT_COLOR, anchor="rt")
            
            # Qty & Price
            detail_text = f"{qty} x {price:,.0f} د.ع"
            draw.text((text_x, current_y + 50), detail_text, font=regular_font, fill=(200, 200, 200), anchor="rt")
            
            # Total for item (Left aligned)
            item_total = qty * price
            draw.text((PADDING + 20, current_y + 35), f"{item_total:,.0f}", font=bold_font, fill=ACCENT_COLOR, anchor="lt")

            current_y += ITEM_HEIGHT
            
        if len(items) > DISPLAY_LIMIT:
            remaining = len(items) - DISPLAY_LIMIT
            draw.text((WIDTH // 2, current_y), f"+ {remaining} منتجات أخرى...", font=regular_font, fill=(150, 150, 150), anchor="mt")
            current_y += 50
            
        # --- FOOTER ---
        # Total Box
        # draw.rectangle((PADDING, current_y + 10, WIDTH - PADDING, current_y + 80), fill=ACCENT_COLOR)
        draw.line((PADDING, current_y, WIDTH - PADDING, current_y), fill=(60, 60, 60), width=2)
        current_y += 30
        
        draw.text((WIDTH - PADDING, current_y + 10), "المجموع الكلي:", font=title_font, fill=TEXT_COLOR, anchor="rt")
        draw.text((PADDING, current_y + 10), f"{total_amount:,.0f} د.ع", font=title_font, fill=PRICE_COLOR, anchor="lt")
        
        # Output to BytesIO
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output

    except Exception as e:
        print(f"⚠️ Error generating receipt image: {e}")
        import traceback
        traceback.print_exc()
        return None
