"""
Complete Favicon Generator for UCP Demo Apps:
- Generates 100% pure-vector SVG favicons (no emoji text reliance)
- Generates valid PNG favicons (16x16, 32x32) using standard library zlib
- Generates modern multi-resolution PNG-embedded ICO files (16x16, 32x32, 48x48)
- Writes all assets to public/ and src/ for all 4 demo applications
"""

import os
import struct
import zlib

SVG_TEMPLATES = {
    'frontend': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="bg-bistrot-chat" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#292524"/>
      <stop offset="100%" stop-color="#1c1917"/>
    </linearGradient>
    <linearGradient id="amber-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#d97706"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="url(#bg-bistrot-chat)"/>
  <rect x="2" y="2" width="60" height="60" rx="14" fill="none" stroke="url(#amber-glow)" stroke-width="3"/>
  <path d="M24 13 Q21 17 24 21" stroke="#fde68a" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M32 10 Q29 15 32 20" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M40 13 Q37 17 40 21" stroke="#fde68a" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M18 24 L46 24 C46 36 41 42 32 42 C23 42 18 36 18 24 Z" fill="#fef3c7" stroke="#d97706" stroke-width="1.5"/>
  <path d="M44 26 C51 26 51 37 43 38" fill="none" stroke="#fef3c7" stroke-width="3.5" stroke-linecap="round"/>
  <ellipse cx="32" cy="46" rx="19" ry="3.5" fill="#fbbf24"/>
  <circle cx="48" cy="48" r="11" fill="#d97706"/>
  <circle cx="48" cy="48" r="11" fill="none" stroke="#fde68a" stroke-width="1.5"/>
  <path d="M43 44 C43 41.8 45.2 40 48 40 C50.8 40 53 41.8 53 44 C53 46.2 50.8 48 48 48 C47.2 48 46.5 47.8 45.8 47.4 L43.5 48.5 L44.2 46.3 C43.5 45.6 43 44.8 43 44 Z" fill="#ffffff"/>
</svg>""",

    'bopis-dashboard': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="bg-bopis-kds" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#27272a"/>
      <stop offset="100%" stop-color="#18181b"/>
    </linearGradient>
    <linearGradient id="amber-orange" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#ea580c"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="url(#bg-bopis-kds)"/>
  <rect x="2" y="2" width="60" height="60" rx="14" fill="none" stroke="url(#amber-orange)" stroke-width="3"/>
  <path d="M16 26 L32 17 L48 26 L32 35 Z" fill="#fdba74" stroke="#ea580c" stroke-width="1.5"/>
  <path d="M16 26 L32 35 L32 49 L16 40 Z" fill="#f97316" stroke="#ea580c" stroke-width="1.5"/>
  <path d="M32 35 L48 26 L48 40 L32 49 Z" fill="#c2410c" stroke="#ea580c" stroke-width="1.5"/>
  <path d="M24 21.5 L40 30.5" stroke="#ea580c" stroke-width="2.5"/>
  <circle cx="48" cy="48" r="11" fill="#ea580c"/>
  <circle cx="48" cy="48" r="11" fill="none" stroke="#fed7aa" stroke-width="1.5"/>
  <path d="M49 41 L43 49 L47.5 49 L46.5 55 L53 47 L48.5 47 Z" fill="#ffffff"/>
</svg>""",

    'storefront-webmcp': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="bg-bistrot-store" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#292524"/>
      <stop offset="100%" stop-color="#1c1917"/>
    </linearGradient>
    <linearGradient id="amber-crema" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#b45309"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="url(#bg-bistrot-store)"/>
  <rect x="2" y="2" width="60" height="60" rx="14" fill="none" stroke="url(#amber-crema)" stroke-width="3"/>
  <path d="M23 23 C23 14 41 14 41 23" fill="none" stroke="#fef3c7" stroke-width="3.5" stroke-linecap="round"/>
  <path d="M16 23 L48 23 L44 49 L20 49 Z" fill="#fbbf24" stroke="#d97706" stroke-width="1.5"/>
  <rect x="27" y="29" width="10" height="12" rx="2" fill="#d97706"/>
  <circle cx="32" cy="33" r="1.5" fill="#fef3c7"/>
  <line x1="32" y1="36" x2="32" y2="39" stroke="#fef3c7" stroke-width="1.5" stroke-linecap="round"/>
  <circle cx="48" cy="48" r="11" fill="#b45309"/>
  <circle cx="48" cy="48" r="11" fill="none" stroke="#fde68a" stroke-width="1.5"/>
  <path d="M49 41 L43 49 L47.5 49 L46.5 55 L53 47 L48.5 47 Z" fill="#ffffff"/>
</svg>""",

    'shopper-client': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="bg-shopper" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#140f29"/>
      <stop offset="100%" stop-color="#0c0a17"/>
    </linearGradient>
    <linearGradient id="violet-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#a855f7"/>
      <stop offset="100%" stop-color="#6366f1"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="url(#bg-shopper)"/>
  <rect x="2" y="2" width="60" height="60" rx="14" fill="none" stroke="url(#violet-glow)" stroke-width="3"/>
  <line x1="32" y1="12" x2="32" y2="18" stroke="#c084fc" stroke-width="3" stroke-linecap="round"/>
  <circle cx="32" cy="11" r="3" fill="#38bdf8"/>
  <rect x="13" y="27" width="4" height="10" rx="2" fill="#7c3aed"/>
  <rect x="47" y="27" width="4" height="10" rx="2" fill="#7c3aed"/>
  <rect x="17" y="19" width="30" height="26" rx="6" fill="#6366f1" stroke="#8b5cf6" stroke-width="1.5"/>
  <rect x="22" y="25" width="6" height="5" rx="2" fill="#38bdf8"/>
  <rect x="36" y="25" width="6" height="5" rx="2" fill="#38bdf8"/>
  <line x1="26" y1="36" x2="38" y2="36" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
  <circle cx="48" cy="48" r="11" fill="#7c3aed"/>
  <circle cx="48" cy="48" r="11" fill="none" stroke="#d8b4fe" stroke-width="1.5"/>
  <path d="M48 42 Q48 48 42 48 Q48 48 48 54 Q48 48 54 48 Q48 48 48 42 Z" fill="#ffffff"/>
</svg>"""
}

def create_png(width, height, rgba_data):
    """Encodes 32-bit RGBA pixels into standard PNG bytes using zlib"""
    raw_data = bytearray()
    for row in rgba_data:
        raw_data.append(0)  # Filter type: None
        for r, g, b, a in row:
            raw_data.extend([r, g, b, a])
            
    compressed = zlib.compress(bytes(raw_data), level=9)
    
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
        
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0) # 8-bit RGBA
    
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr_data) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

def create_png_ico(png_list):
    """Creates a multi-resolution ICO containing raw PNG streams (modern standard)"""
    num_images = len(png_list)
    header = struct.pack('<HHH', 0, 1, num_images)
    entries = []
    offset = 6 + (16 * num_images)
    
    for w, h, p_bytes in png_list:
        entry_w = 0 if w >= 256 else w
        entry_h = 0 if h >= 256 else h
        res_size = len(p_bytes)
        entry = struct.pack('<BBBBHHII', entry_w, entry_h, 0, 0, 1, 32, res_size, offset)
        entries.append(entry)
        offset += res_size
        
    return header + b''.join(entries) + b''.join([p[2] for p in png_list])

def make_canvas(w, h, bg_color):
    return [[bg_color for _ in range(w)] for _ in range(h)]

def draw_squircle(canvas, w, h, bg, border_col, corner_r=5):
    for y in range(h):
        for x in range(w):
            dx = 0
            if x < corner_r:
                dx = corner_r - x
            elif x >= w - corner_r:
                dx = x - (w - corner_r - 1)
                
            dy = 0
            if y < corner_r:
                dy = corner_r - y
            elif y >= h - corner_r:
                dy = y - (h - corner_r - 1)
                
            dist_sq = dx * dx + dy * dy
            r_sq = corner_r * corner_r
            r_inner_sq = max(0, corner_r - 2) * max(0, corner_r - 2)
            
            if dist_sq > r_sq + corner_r:
                canvas[y][x] = (0, 0, 0, 0)
            elif dist_sq >= r_inner_sq:
                canvas[y][x] = border_col
            else:
                if x in (0, 1, w - 2, w - 1) or y in (0, 1, h - 2, h - 1):
                    canvas[y][x] = border_col
                else:
                    canvas[y][x] = bg

def raster_chat(size):
    w, h = size, size
    bg = (28, 25, 23, 255)
    border = (245, 158, 11, 255)
    cup = (254, 243, 199, 255)
    gold = (251, 191, 36, 255)
    accent = (217, 119, 6, 255)
    
    canvas = make_canvas(w, h, bg)
    draw_squircle(canvas, w, h, bg, border, corner_r=max(2, size // 5))
    s = size / 32.0
    
    # Cup
    for y in range(int(14 * s), int(23 * s)):
        inset = int(1 * s) if y >= int(20 * s) else 0
        for x in range(int((10 + inset) * s), int((22 - inset) * s)):
            if 0 <= x < w and 0 <= y < h:
                canvas[y][x] = cup
    for x in range(int(11 * s), int(21 * s)):
        if 0 <= int(15 * s) < h and 0 <= x < w:
            canvas[int(15 * s)][x] = (120, 53, 15, 255)
    # Handle
    for y in range(int(15 * s), int(21 * s)):
        for x in range(int(22 * s), int(25 * s)):
            if (y == int(15 * s) or y == int(20 * s) or x == int(24 * s)) and 0 <= x < w and 0 <= y < h:
                canvas[y][x] = cup
    # Saucer
    if int(24 * s) < h:
        for x in range(int(8 * s), int(24 * s)):
            if 0 <= x < w:
                canvas[int(24 * s)][x] = gold
    # Badge
    cx, cy, br = int(24 * s), int(24 * s), max(2, int(5 * s))
    for y in range(cy - br, min(h, cy + br + 1)):
        for x in range(cx - br, min(w, cx + br + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= br ** 2 and 0 <= x < w and 0 <= y < h:
                canvas[y][x] = accent
    if 0 <= cy < h and 0 <= cx < w:
        canvas[cy][cx] = (255, 255, 255, 255)
        
    return canvas

def raster_storefront(size):
    w, h = size, size
    bg = (28, 25, 23, 255)
    border = (245, 158, 11, 255)
    bag_col = (251, 191, 36, 255)
    bag_shade = (180, 83, 9, 255)
    handle_col = (254, 243, 199, 255)
    
    canvas = make_canvas(w, h, bg)
    draw_squircle(canvas, w, h, bg, border, corner_r=max(2, size // 5))
    s = size / 32.0
    
    # Handles
    for y in range(int(8 * s), int(14 * s)):
        for x in (int(12 * s), int(13 * s), int(19 * s), int(20 * s)):
            if 0 <= x < w and 0 <= y < h:
                canvas[y][x] = handle_col
    for x in range(int(13 * s), int(20 * s)):
        if 0 <= int(8 * s) < h and 0 <= x < w:
            canvas[int(8 * s)][x] = handle_col
    # Body
    for y in range(int(14 * s), int(25 * s)):
        for x in range(int(9 * s), int(24 * s)):
            if 0 <= x < w and 0 <= y < h:
                if y in (int(14 * s), int(24 * s)) or x in (int(9 * s), int(23 * s)):
                    canvas[y][x] = handle_col
                else:
                    canvas[y][x] = bag_col
    # Tag
    for y in range(int(17 * s), int(21 * s)):
        for x in range(int(13 * s), int(19 * s)):
            if 0 <= x < w and 0 <= y < h:
                canvas[y][x] = bag_shade
    # Badge
    cx, cy, br = int(24 * s), int(24 * s), max(2, int(5 * s))
    for y in range(cy - br, min(h, cy + br + 1)):
        for x in range(cx - br, min(w, cx + br + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= br ** 2 and 0 <= x < w and 0 <= y < h:
                canvas[y][x] = (180, 83, 9, 255)
    if 0 <= cy < h and 0 <= cx < w:
        canvas[cy][cx] = (255, 255, 255, 255)
        
    return canvas

def raster_bopis(size):
    w, h = size, size
    bg = (24, 24, 27, 255)
    border = (234, 88, 12, 255)
    box_light = (253, 186, 116, 255)
    box_mid = (249, 115, 22, 255)
    
    canvas = make_canvas(w, h, bg)
    draw_squircle(canvas, w, h, bg, border, corner_r=max(2, size // 5))
    s = size / 32.0
    
    # Box
    for y in range(int(12 * s), int(24 * s)):
        for x in range(int(8 * s), int(24 * s)):
            if 0 <= x < w and 0 <= y < h:
                if y in (int(12 * s), int(23 * s)) or x in (int(8 * s), int(23 * s)):
                    canvas[y][x] = box_mid
                elif x in (int(15 * s), int(16 * s)):
                    canvas[y][x] = (220, 38, 38, 255)
                else:
                    canvas[y][x] = box_light
    if 0 <= int(15 * s) < h:
        for x in range(int(8 * s), int(24 * s)):
            if 0 <= x < w:
                canvas[int(15 * s)][x] = box_mid
    # Badge
    cx, cy, br = int(24 * s), int(24 * s), max(2, int(5 * s))
    for y in range(cy - br, min(h, cy + br + 1)):
        for x in range(cx - br, min(w, cx + br + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= br ** 2 and 0 <= x < w and 0 <= y < h:
                canvas[y][x] = (234, 88, 12, 255)
    if 0 <= cy < h and 0 <= cx < w:
        canvas[cy][cx] = (255, 255, 255, 255)
        
    return canvas

def raster_shopper(size):
    w, h = size, size
    bg = (12, 10, 23, 255)
    border = (139, 92, 246, 255)
    robot_face = (124, 58, 237, 255)
    robot_glow = (168, 85, 247, 255)
    eye = (56, 189, 248, 255)
    
    canvas = make_canvas(w, h, bg)
    draw_squircle(canvas, w, h, bg, border, corner_r=max(2, size // 5))
    s = size / 32.0
    
    # Antenna
    ax = int(16 * s)
    for y in range(int(7 * s), int(12 * s)):
        if 0 <= ax < w and 0 <= y < h:
            canvas[y][ax] = robot_glow
    if 0 <= int(6 * s) < h and 0 <= ax < w:
        canvas[int(6 * s)][ax] = (255, 255, 255, 255)
    # Head
    for y in range(int(12 * s), int(23 * s)):
        for x in range(int(9 * s), int(23 * s)):
            if 0 <= x < w and 0 <= y < h:
                if y in (int(12 * s), int(22 * s)) or x in (int(9 * s), int(22 * s)):
                    canvas[y][x] = robot_glow
                else:
                    canvas[y][x] = robot_face
    # Eyes
    ey = int(15 * s)
    for y in range(ey, min(h, ey + max(1, int(2 * s)))):
        for ex in (int(12 * s), int(13 * s), int(18 * s), int(19 * s)):
            if 0 <= ex < w and 0 <= y < h:
                canvas[y][ex] = eye
    # Smile
    sy = int(19 * s)
    for x in range(int(13 * s), int(19 * s)):
        if 0 <= sy < h and 0 <= x < w:
            canvas[sy][x] = (255, 255, 255, 255)
    # Badge
    cx, cy, br = int(24 * s), int(24 * s), max(2, int(5 * s))
    for y in range(cy - br, min(h, cy + br + 1)):
        for x in range(cx - br, min(w, cx + br + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= br ** 2 and 0 <= x < w and 0 <= y < h:
                canvas[y][x] = (109, 40, 217, 255)
    if 0 <= cy < h and 0 <= cx < w:
        canvas[cy][cx] = (255, 255, 255, 255)
        
    return canvas

def generate_and_save():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    app_configs = [
        ('frontend', raster_chat),
        ('bopis-dashboard', raster_bopis),
        ('storefront-webmcp', raster_storefront),
        ('shopper-client', raster_shopper),
    ]
    
    for app_name, raster_func in app_configs:
        app_dir = os.path.join(base, app_name)
        
        # 1. Generate PNGs (16x16, 32x32, 48x48)
        png16 = create_png(16, 16, raster_func(16))
        png32 = create_png(32, 32, raster_func(32))
        png48 = create_png(48, 48, raster_func(48))
        
        # 2. Generate multi-resolution PNG-embedded ICO
        ico_bytes = create_png_ico([
            (16, 16, png16),
            (32, 32, png32),
            (48, 48, png48)
        ])
        
        # 3. Pure-vector SVG
        svg_content = SVG_TEMPLATES[app_name].strip()
        
        # Save to both public/ and src/
        for sub in ['public', 'src']:
            target_dir = os.path.join(app_dir, sub)
            os.makedirs(target_dir, exist_ok=True)
            
            with open(os.path.join(target_dir, 'favicon.ico'), 'wb') as f:
                f.write(ico_bytes)
            with open(os.path.join(target_dir, 'favicon-32x32.png'), 'wb') as f:
                f.write(png32)
            with open(os.path.join(target_dir, 'favicon-16x16.png'), 'wb') as f:
                f.write(png16)
            with open(os.path.join(target_dir, 'favicon.svg'), 'w', encoding='utf-8') as f:
                f.write(svg_content)
                
        print(f"Generated complete favicons for {app_name}")

if __name__ == '__main__':
    generate_and_save()
    print("ALL FAVICONS CREATED SUCCESSFULLY!")
