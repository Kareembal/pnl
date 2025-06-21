from PIL import Image, ImageDraw, ImageFont
import datetime
import os

def format_pnl(value):
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif abs_value >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:.2f}"

def draw_crypto_pro_pnl_calendar(pnl_data, username):
    # === IMAGE SETUP ===
    width, height = 1200, 720
    background_color = (18, 18, 18)  # Dark theme
    text_color = (255, 255, 255)
    profit_color = (0, 255, 100)
    loss_color = (255, 80, 80)
    grid_color = (60, 60, 60)
    brand_color = (0, 120, 255)

    img = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(img)

    # === FONT ===
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    big_font = ImageFont.truetype(font_path, 40)
    med_font = ImageFont.truetype(font_path, 30)
    small_font = ImageFont.truetype(font_path, 24)

    # === TITLE ===
    title = f"📆 PNL Report - {datetime.date.today().strftime('%B %Y')}"
    draw.text((40, 25), title, font=big_font, fill=brand_color)

    # === CALENDAR GRID ===
    left, top = 60, 100
    cell_w, cell_h = 140, 90
    padding = 15
    
    sorted_days = sorted(pnl_data.keys())

    for i, day in enumerate(sorted_days):
        col = i % 7
        row = i // 7
        x = left + col * (cell_w + padding)
        y = top + row * (cell_h + padding)

        # Draw grid cell
        draw.rectangle([x, y, x + cell_w, y + cell_h], outline=grid_color, width=2)

        # Date label
        draw.text((x + 10, y + 8), day.strftime('%d %b'), font=small_font, fill=text_color)

        # PNL value
        pnl = pnl_data[day]
        formatted_pnl = format_pnl(pnl) + "$"
        pnl_fill = profit_color if pnl >= 0 else loss_color
        draw.text((x + 10, y + 40), formatted_pnl, font=med_font, fill=pnl_fill)

    # === Footer ===
    draw.text((40, height - 50), f"Generated for: @{username}", font=small_font, fill=(180, 180, 180))
    draw.text((width - 260, height - 50), "powered by xPNL", font=small_font, fill=brand_color)

    # === SAVE ===
    os.makedirs("reports", exist_ok=True)
    path = f"reports/{username}_pnl_calendar.png"
    img.save(path)
    return path
