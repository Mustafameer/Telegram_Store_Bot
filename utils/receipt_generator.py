
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
    Rev 20: White Body, Navy Text, Blue Header/Footer
    """
    try:
        # 1. Constants & Setup
        WIDTH = 800 
        PADDING = 40
        
        # Design Specs
        HEADER_HEIGHT = 280 
        
        # Calculate Height
        display_count = len(items) if items else 1
        BODY_HEIGHT = (display_count * 140) + 160 
        TOTAL_HEIGHT = HEADER_HEIGHT + BODY_HEIGHT + 30
        
        # Colors 
        COLOR_BG = (255, 255, 255) # White Body
        COLOR_TEXT_WHITE = (255, 255, 255)
        COLOR_TEXT_NAVY = (0, 30, 90) # Navy Blue for Product Text
        COLOR_TEXT_GREY = (180, 190, 200) 
        COLOR_ACCENT = (76, 175, 80) 
        COLOR_DIVIDER = (230, 230, 230) # Light Grey

        # 1. Backgrounds
        img = Image.new('RGB', (WIDTH, TOTAL_HEIGHT), COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # Header/Footer BG (Blue)
        HEADER_BG = (20, 40, 80) 
        draw.rectangle([(0, 0), (WIDTH, HEADER_HEIGHT)], fill=HEADER_BG)
        
        FOOTER_Y = TOTAL_HEIGHT - 160
        # Draw explicit Footer BG
        draw.rectangle([(0, FOOTER_Y), (WIDTH, TOTAL_HEIGHT)], fill=HEADER_BG)
        
        # 2. Fonts
        title_font = get_cached_font('bold', 55)    
        price_font = get_cached_font('bold', 40)    
        normal_font = get_cached_font('normal', 36) 
        small_font = get_cached_font('small', 30)   
        icon_symbol_font = get_cached_font('bold', 30) 
        
        # 3. Icon Helper
        def draw_visual_icon(x, y, color, symbol):
            radius = 25
            draw.ellipse([(x-radius, y-radius), (x+radius, y+radius)], fill=color)
            draw.text((x-10, y-18), symbol, font=icon_symbol_font, fill=(255,255,255))

        def draw_row(symbol_char, text, y, icon_color):
             icon_cx = WIDTH - 50 
             icon_cy = y + 15 
             draw_visual_icon(icon_cx, icon_cy, icon_color, symbol_char)
             draw_text_rtl(draw, text, y, small_font, COLOR_TEXT_WHITE, right_margin=100, canvas_width=WIDTH)

        # 3. HEADER
        current_y = 50 
        
        order_id = str(order_details[0])
        try:
           date_obj = order_details[5]
           if isinstance(date_obj, str):
               date_str = date_obj.split()[0]
           else:
               date_str = date_obj.strftime('%Y-%m-%d')
        except: date_str = "---"
        
        draw.text((40, current_y), f"#{order_id}", font=title_font, fill=COLOR_TEXT_WHITE)
        draw_row("📅", date_str, current_y, (0, 180, 200))
        
        current_y += 80
        try:
             note_txt = order_details[7] if len(order_details) > 7 else ""
        except: note_txt = ""
        if not note_txt: note_txt = "---"
        
        draw_row("📝", note_txt, current_y, (255, 160, 0))
        
        current_y += 60
        address = order_details[6]
        if address:
             draw_row("📍", address, current_y, (220, 60, 60))
             current_y += 60

        
        # 4. Items List
        current_y = HEADER_HEIGHT + 30
        
        if not items:
             draw_text_rtl(draw, "لا توجد منتجات", current_y, normal_font, (100, 100, 100), right_margin=WIDTH//2, canvas_width=WIDTH)
             current_y += 80
             
        for item in items:
            qty = item[3]
            price = item[4]
            name = item[8] if len(item) > 8 else "Unknown"
            
            # Thumbnail
            img_size = 100 
            img_x = 40
            img_y = current_y
            
            thumb_img = None
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
                draw.rounded_rectangle([(img_x, img_y), (img_x+img_size, img_y+img_size)], radius=15, fill=(220,230,240))
                draw.text((img_x+25, img_y+35), "IMG", font=small_font, fill=(100,100,100))

            # Name (Right) -> NAVY Color, Normal Size again
            draw_text_rtl(draw, f"{name}", current_y, normal_font, COLOR_TEXT_NAVY, right_margin=40, canvas_width=WIDTH)
            
            # Subtext -> Accent Color 
            total_item = qty * float(price)
            subtext = f"{qty}x | {float(price):,.0f}"
            draw.text((img_x + img_size + 20, current_y + 40), subtext, font=price_font, fill=COLOR_ACCENT)
            
            current_y += 140 
            
            # Separator
            draw.line([(img_x + img_size + 20, current_y-20), (WIDTH-40, current_y-20)], fill=COLOR_DIVIDER, width=2)
            
        
        # 6. Summary in Footer
        
        total_val = order_details[3]
        total_txt = f"{int(total_val):,}" 
        
        icon_cx = WIDTH - 50
        icon_cy = FOOTER_Y + 75
        draw_visual_icon(icon_cx, icon_cy, (40, 180, 60), "$")
        
        
        # Text White
        draw_text_rtl(draw, total_txt, FOOTER_Y + 50, title_font, COLOR_TEXT_WHITE, right_margin=100, canvas_width=WIDTH)
        
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio

    except Exception as e:
        print(f"Card Gen Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_product_card(product, store_name):
    """
    Generate a 600px wide product card.
    Top 50% = Image (Contained).
    Bottom 50% = Details.
    """
    try:
        # Unpack
        pid, name, desc, price, wholesale_price, qty, img_path = product
        
        # 1. Constants
        WIDTH = 600
        # Dynamic height? Or Fixed? Let's try Fixed for consistency, or dynamic if desc is long.
        # But user asked for specific layout. Let's go with 800px total height, 400px image.
        HEIGHT = 800
        IMAGE_AREA_HEIGHT = 400
        
        COLOR_BG = (255, 255, 255)
        COLOR_TEXT_NAVY = (0, 30, 90)
        COLOR_TEXT_GREY = (100, 100, 100)
        COLOR_ACCENT = (76, 175, 80) # Green for Price
        COLOR_HEADER_BG = (20, 40, 80)
        
        img = Image.new('RGB', (WIDTH, HEIGHT), COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # 2. Fonts
        title_font = get_cached_font('bold', 45)
        price_font = get_cached_font('bold', 50)
        normal_font = get_cached_font('normal', 32)
        small_font = get_cached_font('small', 26)
        
        # 3. Draw Image (Top Half)
        # Background for image area (optional, maybe light grey or white)
        draw.rectangle([(0, 0), (WIDTH, IMAGE_AREA_HEIGHT)], fill=(250, 250, 250))
        
        product_img = None
        
        # Helper to find image
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

        final_path = find_image_file(img_path)
        if final_path:
             try: product_img = Image.open(final_path).convert('RGBA')
             except: pass
        
        if product_img:
            # Resize to fit within IMAGE_AREA_HEIGHT x WIDTH (Contain)
            iw, ih = product_img.size
            msg_ratio = WIDTH / IMAGE_AREA_HEIGHT
            img_ratio = iw / ih
            
            target_w, target_h = WIDTH, IMAGE_AREA_HEIGHT
            
            if img_ratio > msg_ratio:
                 # Wider than container, fit to width
                 target_w = WIDTH
                 target_h = int(WIDTH / img_ratio)
            else:
                 # Taller or same, fit to height
                 target_h = IMAGE_AREA_HEIGHT
                 target_w = int(IMAGE_AREA_HEIGHT * img_ratio)
            
            product_img = product_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            # Center position
            pos_x = (WIDTH - target_w) // 2
            pos_y = (IMAGE_AREA_HEIGHT - target_h) // 2
            
            # Paste
            # Create a white background/canvas for the top half to paste onto if transparency exists
            img.paste(product_img, (pos_x, pos_y), product_img if 'A' in product_img.getbands() else None)
        else:
            # Placeholder
            draw.text((WIDTH//2 - 50, IMAGE_AREA_HEIGHT//2 - 20), "No Image", font=normal_font, fill=COLOR_TEXT_GREY)

        # 4. Details (Bottom Half)
        current_y = IMAGE_AREA_HEIGHT + 30
        
        # Store Name (Pill)
        # draw_pill returns w, h
        if store_name:
             draw_pill(draw, WIDTH - 250, current_y, store_name[:20], small_font, COLOR_HEADER_BG, (255,255,255))
        
        # Product Name
        current_y += 60
        draw_text_rtl(draw, name, current_y, title_font, COLOR_TEXT_NAVY, right_margin=40, canvas_width=WIDTH)
        
        current_y += 70
        # Description (Truncated)
        if desc:
            desc_short = desc[:50] + "..." if len(desc) > 50 else desc
            draw_text_rtl(draw, desc_short, current_y, normal_font, COLOR_TEXT_GREY, right_margin=40, canvas_width=WIDTH)
            current_y += 50
        
        current_y += 40
        # Divider
        draw.line([(40, current_y), (WIDTH-40, current_y)], fill=(230, 230, 230), width=2)
        current_y += 40
        
        # Price
        price_txt = f"{price:,.0f} IQD"
        draw_text_rtl(draw, price_txt, current_y, price_font, COLOR_ACCENT, right_margin=40, canvas_width=WIDTH)
        
        # Wholesale Price (if relevant)
        if wholesale_price and wholesale_price > 0:
            current_y += 60
            ws_txt = f"جملة: {wholesale_price:,.0f} IQD"
            draw_text_rtl(draw, ws_txt, current_y, small_font, (200, 100, 50), right_margin=40, canvas_width=WIDTH)

        # Footer Decor (Bottom Strip)
        draw.rectangle([(0, HEIGHT-20), (WIDTH, HEIGHT)], fill=COLOR_HEADER_BG)

        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio

    except Exception as e:
        print(f"Product Card Gen Error: {e}")
        import traceback
        traceback.print_exc()
        return None
