
import io
import datetime
import os
import requests
from PIL import Image, ImageDraw, ImageFont

# Libraries for Arabic Text Support
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    print("Warning: arabic-reshaper or python-bidi not installed. Arabic text may render incorrectly.")
    arabic_reshaper = None
    get_display = None

def get_font(path_options, size):
    for path in path_options:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()

def process_text(text):
    """Reshapes and reorders Arabic text for correct display."""
    if not text:
        return ""
    if arabic_reshaper and get_display:
        reshaped_text = arabic_reshaper.reshape(str(text))
        bidi_text = get_display(reshaped_text)
        return bidi_text
    return str(text)

def draw_text_rtl(draw, text, y, font, fill, right_margin, canvas_width=600):
    """Draws text aligned to the right."""
    processed = process_text(text)
    
    try:
        bbox = draw.textbbox((0, 0), processed, font=font)
        text_width = bbox[2] - bbox[0]
    except:
        text_width = draw.textlength(processed, font=font)
        
    x = canvas_width - right_margin - text_width 
    draw.text((x, y), processed, font=font, fill=fill)
    return text_width

def draw_pill(draw, x, y, text, font, bg_color, text_color):
    """Draws a rounded pill with text."""
    processed = process_text(text)
    try:
        bbox = draw.textbbox((0, 0), processed, font=font)
        w = bbox[2] - bbox[0] + 30
        h = bbox[3] - bbox[1] + 16
    except:
        w = 100
        h = 40
    
    try:
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=15, fill=bg_color)
    except AttributeError:
         draw.rectangle([(x, y), (x + w, y + h)], fill=bg_color)
         
    # Center text
    draw.text((x + 15, y + 8), processed, font=font, fill=text_color)
    return w, h

# Font Cache
CACHED_FONTS = {}

def get_cached_font(font_type, size):
    key = (font_type, size)
    if key in CACHED_FONTS:
        return CACHED_FONTS[key]
    
    font_base = os.path.join(os.path.dirname(__file__), "..", "fonts")
    paths = []
    if font_type == 'bold':
        paths = [
            os.path.join(font_base, "Cairo-Bold.ttf"), 
            "fonts/Cairo-Bold.ttf", 
            "fonts/arialbd.ttf", # Priority Fallback
            "arialbd.ttf"
        ]
    elif font_type == 'header':
        paths = [
            os.path.join(font_base, "Cairo-Bold.ttf"), 
            "fonts/Cairo-Bold.ttf", 
            "fonts/arialbd.ttf", 
            "arialbd.ttf"
        ]
    elif font_type == 'normal':
        paths = [
            os.path.join(font_base, "Cairo-Regular.ttf"), 
            "fonts/Cairo-Regular.ttf", 
            "fonts/arial.ttf", # Priority Fallback
            "arial.ttf"
        ]
    else: # small
        paths = [
            os.path.join(font_base, "Cairo-Regular.ttf"), 
            "fonts/Cairo-Regular.ttf", 
            "fonts/arial.ttf", 
            "arial.ttf"
        ]
        
    font = get_font(paths, size)
    CACHED_FONTS[key] = font
    return font

def generate_order_card(order_details, items, buyer_name, buyer_phone, store_name):
    """
    Generate a visual receipt card for the order.
    Rev 19: Drawn Icons & Tuned Fonts
    """
    try:
        # 1. Constants & Setup
        WIDTH = 800 
        PADDING = 40
        
        # Design Specs
        HEADER_HEIGHT = 280 
        
        # Calculate Height
        display_count = len(items) if items else 1
        BODY_HEIGHT = (display_count * 140) + 160 # Items(140px) + Footer space
        TOTAL_HEIGHT = HEADER_HEIGHT + BODY_HEIGHT + 30
        
        # Colors 
        COLOR_BG = (20, 25, 30) 
        COLOR_TEXT_WHITE = (255, 255, 255)
        COLOR_TEXT_GREY = (180, 190, 200)
        COLOR_ACCENT = (76, 175, 80) # Green for money
        COLOR_DIVIDER = (50, 60, 70)

        # 1. Backgrounds
        img = Image.new('RGB', (WIDTH, TOTAL_HEIGHT), COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # Header/Footer BG (Blue)
        HEADER_BG = (20, 40, 80) 
        draw.rectangle([(0, 0), (WIDTH, HEADER_HEIGHT)], fill=HEADER_BG)
        
        FOOTER_Y = TOTAL_HEIGHT - 160
        draw.rectangle([(0, FOOTER_Y), (WIDTH, TOTAL_HEIGHT)], fill=HEADER_BG)
        
        # 2. Fonts
        # "Keep numbers as they are" -> Keep Title/Price Large.
        # "Font smaller by 2 degrees" -> Reduce Normal/Small.
        title_font = get_cached_font('bold', 55)    # For Total/ID (Numbers)
        price_font = get_cached_font('bold', 40)    # New: For Item Prices (Numbers)
        normal_font = get_cached_font('normal', 36) # Reduced from 45 -> 36 (Names)
        small_font = get_cached_font('small', 30)   # Reduced from 38 -> 30 (Details)
        icon_symbol_font = get_cached_font('bold', 30) # For symbols inside circles
        
        # 3. Icon Helper (Draws Colored Circle + Symbol)
        def draw_visual_icon(x, y, color, symbol):
            """Draws a colored circle with a white symbol in center."""
            radius = 25
            # Circle
            draw.ellipse([(x-radius, y-radius), (x+radius, y+radius)], fill=color)
            # Symbol
            # calc centering crudely
            draw.text((x-10, y-18), symbol, font=icon_symbol_font, fill=(255,255,255))

        # Helper for Data Row (Icon Right, Text Left)
        def draw_row(symbol_char, text, y, icon_color):
             # Icon Center X
             icon_cx = WIDTH - 50 
             icon_cy = y + 15 # Adjust for vertical center relative to text
             
             draw_visual_icon(icon_cx, icon_cy, icon_color, symbol_char)
             
             # Text (Left of Icon, with margin)
             draw_text_rtl(draw, text, y, small_font, COLOR_TEXT_WHITE, right_margin=100, canvas_width=WIDTH)

        # 3. HEADER
        current_y = 50 
        
        order_id = str(order_details[0])
        
        # Date Format
        try:
           date_obj = order_details[5]
           if isinstance(date_obj, str):
               date_str = date_obj.split()[0]
           else:
               date_str = date_obj.strftime('%Y-%m-%d')
        except: date_str = "---"
        

        # Draw Order ID (Left)
        draw.text((40, current_y), f"#{order_id}", font=title_font, fill=COLOR_TEXT_WHITE)
        
        # Draw Date (Right) - Symbol "D" or calendar shape? Let's use generic shape or char.
        # "📅" might fail inside circle if font doesn't support it. Use "D" or "📅" if Arial supports it?
        # Arial supports basic shapes. Let's use simple letters for robustness per user issue.
        # D = Date, N = Note, A = Address. Or just symbols if we trust Arial.
        # Let's try Unicode symbols that are standard in Arial: 
        # Date: 📅 (Might fail). Let's use "📅" but if it fails it fails. 
        # Wait, user said "Icons not visible". 
        # Let's use pure shapes? No, let's use LETTERS. Robust.
        # Or better: "🕑", "📝", "📍". 
        # Let's use "::" style or just no symbol inside, just color? NO, need meaning.
        # Let's use:
        # Date: 📅 (Cyan)
        # Note: 📝 (Orange)
        # Address: 📍 (Red)
        # If they fail, at least the COLOR circle is visible.
        
        draw_row("📅", date_str, current_y, (0, 180, 200)) # Cyan
        
        current_y += 80
        
        # Draw Notes
        try:
             note_txt = order_details[7] if len(order_details) > 7 else ""
        except: note_txt = ""
        if not note_txt: note_txt = "---"
        
        draw_row("📝", note_txt, current_y, (255, 160, 0)) # Orange
        
        current_y += 60
        
        # Draw Address
        address = order_details[6]
        if address:
             draw_row("📍", address, current_y, (220, 60, 60)) # Red
             current_y += 60

        
        # 4. Items List
        current_y = HEADER_HEIGHT + 30
        
        if not items:
             draw_text_rtl(draw, "لا توجد منتجات", current_y, normal_font, COLOR_TEXT_GREY, right_margin=WIDTH//2, canvas_width=WIDTH)
             current_y += 80
             
        for item in items:
            qty = item[3]
            price = item[4]
            name = item[8] if len(item) > 8 else "Unknown"
            
            # Image Thumbnail
            img_size = 100 
            img_x = 40
            img_y = current_y
            
            thumb_img = None
            
            # Robust Helper
            def find_image_file(path_str):
                if not path_str or not isinstance(path_str, str): return None
                clean = path_str.split('?')[0].replace('\\', '/')
                if 'http' in clean: return None
                basename = os.path.basename(clean)
                base_dirs = [
                    os.getcwd(),
                    os.path.join(os.getcwd(), "data", "Images"),
                    "C:/Users/Hp/Desktop/TelegramStoreBot/data/Images"
                ]
                for d in base_dirs:
                    if os.path.exists(d):
                        fp = os.path.join(d, basename)
                        if os.path.exists(fp): return fp
                return None

            image_path = None
            if len(item) > 13 and isinstance(item[13], str) and len(item[13]) > 4: image_path = item[13]
            elif len(item) > 10 and isinstance(item[10], str) and len(item[10]) > 4: image_path = item[10]
            
            final_path = find_image_file(image_path)
            if final_path:
                 try: thumb_img = Image.open(final_path).convert('RGBA')
                 except: pass
            
            if thumb_img:
                thumb_img.thumbnail((img_size, img_size))
                mask = Image.new('L', thumb_img.size, 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.rounded_rectangle([(0,0), thumb_img.size], radius=15, fill=255)
                img.paste(thumb_img, (img_x, img_y), mask)
            else:
                draw.rounded_rectangle([(img_x, img_y), (img_x+img_size, img_y+img_size)], radius=15, fill=(40,45,50))
                draw.text((img_x+25, img_y+35), "IMG", font=small_font, fill=COLOR_TEXT_GREY)

            # Name (Right) - Use Normal Font (Smaller now)
            draw_text_rtl(draw, f"{name}", current_y, normal_font, COLOR_TEXT_WHITE, right_margin=40, canvas_width=WIDTH)
            
            # Subtext (Qty | Price) - Use PRICE FONT for Numbers (Keep Large)
            total_item = qty * float(price)
            subtext = f"{qty}x | {float(price):,.0f}"
            
            # Draw Qty/Price below name
            # We want numbers "as they are" (Large?). 
            # I created price_font (40) for this.
            draw.text((img_x + img_size + 20, current_y + 40), subtext, font=price_font, fill=COLOR_ACCENT)
            
            current_y += 140 
            
            # Separator
            draw.line([(img_x + img_size + 20, current_y-20), (WIDTH-40, current_y-20)], fill=(40, 45, 50), width=2)
            
        
        # 6. Summary in Footer
        
        # Total Price
        # Icon Right, Text Left
        total_val = order_details[3]
        total_txt = f"{int(total_val):,}" 
        
        # Draw Icon (Green $)
        icon_cx = WIDTH - 50
        icon_cy = FOOTER_Y + 75
        draw_visual_icon(icon_cx, icon_cy, (40, 180, 60), "$")
        
        # Draw Text (Left of Icon)
        # Using title_font (55) for Total Number (Keep Large)
        draw_text_rtl(draw, total_txt, FOOTER_Y + 50, title_font, COLOR_ACCENT, right_margin=100, canvas_width=WIDTH)
        
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio
        
        order_id = str(order_details[0])
        
        # Date Format
        try:
           date_obj = order_details[5]
           if isinstance(date_obj, str):
               date_str = date_obj.split()[0]
           else:
               date_str = date_obj.strftime('%Y-%m-%d')
        except: date_str = "---"
        
        # Helper for Icon+Text Row (Right Aligned)
        def draw_row(icon, text, y, icon_color=(255, 200, 0)):
             # Icon Position (Absolute Right)
             # Unicode Icons might vary in width, rigid spacing is safer.
             icon_x = WIDTH - 50
             draw.text((icon_x, y), icon, font=small_font, fill=icon_color)
             
             # Text Position (Left of Icon)
             draw_text_rtl(draw, text, y, small_font, COLOR_TEXT_WHITE, right_margin=60, canvas_width=WIDTH)

        # Draw Order ID (Left side, big)
        draw.text((20, current_y), f"#{order_id}", font=title_font, fill=COLOR_TEXT_WHITE)
        
        # Draw Date (Row 1 Right)
        draw_row("📅", date_str, current_y, (0, 255, 255)) # Cyan
        
        current_y += 50
        
        # Draw Notes
        try:
             note_txt = order_details[7] if len(order_details) > 7 else ""
        except: note_txt = ""
        if not note_txt: note_txt = "---"
        
        draw_row("📝", note_txt, current_y, (255, 200, 80)) # Orange
        
        current_y += 40
        
        # Draw Address
        address = order_details[6]
        if address:
             draw_row("📍", address, current_y, (255, 100, 100)) # Reddish
             current_y += 40
             
        # Divider
        current_y = HEADER_HEIGHT + 10 # Reset Y to below header explicitly
        # draw.line works but let's just stick to the flow.
        
        # 4. Items List
        current_y = HEADER_HEIGHT + 20
        
        if not items:
             draw_text_rtl(draw, "لا توجد منتجات", current_y, normal_font, COLOR_TEXT_GREY, right_margin=WIDTH//2, canvas_width=WIDTH)
             current_y += 60
             
        for item in items:
            qty = item[3]
            price = item[4]
            name = item[8] if len(item) > 8 else "Unknown"
            
            # 1. Image Thumbnail
            img_size = 60
            img_x = 20
            img_y = current_y
            
            thumb_img = None
            
            # Robust Helper
            def find_image_file(path_str):
                if not path_str or not isinstance(path_str, str): return None
                clean = path_str.split('?')[0].replace('\\', '/')
                if 'http' in clean: return None
                basename = os.path.basename(clean)
                
                # Search Paths
                base_dirs = [
                    os.getcwd(),
                    os.path.join(os.getcwd(), "data", "Images"),
                    "C:/Users/Hp/Desktop/TelegramStoreBot/data/Images"
                ]
                for d in base_dirs:
                    if os.path.exists(d):
                        fp = os.path.join(d, basename)
                        if os.path.exists(fp): return fp
                return None

            image_path = None
            if len(item) > 13 and isinstance(item[13], str) and len(item[13]) > 4: image_path = item[13]
            elif len(item) > 10 and isinstance(item[10], str) and len(item[10]) > 4: image_path = item[10]
            
            final_path = find_image_file(image_path)
            if final_path:
                 try: thumb_img = Image.open(final_path).convert('RGBA')
                 except: pass
            
            if thumb_img:
                thumb_img.thumbnail((img_size, img_size))
                # Circular or Rounded? Rounded.
                mask = Image.new('L', thumb_img.size, 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.rounded_rectangle([(0,0), thumb_img.size], radius=8, fill=255)
                # Paste
                img.paste(thumb_img, (img_x, img_y), mask)
            else:
                # Placeholder
                draw.rounded_rectangle([(img_x, img_y), (img_x+img_size, img_y+img_size)], radius=8, fill=(40,45,50))
                draw.text((img_x+10, img_y+20), "IMG", font=small_font, fill=COLOR_TEXT_GREY)

            # Name (Right)
            # Make sure it doesn't overlap left thumbnail
            # right_margin=20 is standard.
            draw_text_rtl(draw, f"{name}", current_y, normal_font, COLOR_TEXT_WHITE, right_margin=20, canvas_width=WIDTH)
            
            # Subtext (Qty/Price) - Below Name or Next to it?
            # User wants "lines".
            # Let's put price under name, aligned right? Use existing Left alignment?
            # Existing: draw.text((110, ...)) -> Left of thumbnail.
            # Let's align Price to Left (near thumbnail)
            
            total_item = qty * float(price)
            subtext = f"{qty}x | {float(price):,.0f}"
            draw.text((img_x + img_size + 15, current_y + 15), subtext, font=small_font, fill=COLOR_ACCENT)
            
            current_y += 80
            
            # Separator
            draw.line([(img_x + img_size + 15, current_y-10), (WIDTH-20, current_y-10)], fill=(40, 45, 50), width=1)
            
        
        # 6. Summary Layout (Bottom)
        # In Footer Area
        
        # Total Price Only (Centered/Right)
        total_val = order_details[3]
        total_txt = f"💰 {int(total_val):,}" 
        # Draw Center? Or Right?
        draw_text_rtl(draw, total_txt, FOOTER_Y + 30, title_font, COLOR_ACCENT, right_margin=20, canvas_width=WIDTH)
        
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio

    except Exception as e:
        print(f"Card Gen Error: {e}")
        import traceback
        traceback.print_exc()
        return None
