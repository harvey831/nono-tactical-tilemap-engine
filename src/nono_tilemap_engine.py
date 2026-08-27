import math
import random
import base64
import shutil
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

godot_base = Path(r"C:\GPTfile\godot\adventure-of-self-realization-v-0.5")
asset_dir = godot_base / "圖片" / "地圖" / "荒原九大戰區_正式資產" / "00_邊境村落"
brain_dir = Path(r"C:\Users\ihate\.gemini\antigravity\brain\522dd70e-62d4-4f27-893e-70f3ade173ca")
skill_repo = Path(r"C:\GPTfile\godot\nono-tactical-tilemap-engine")
skill_assets_dir = skill_repo / "assets"
reports_dir = skill_repo / "reports"

# 字型
font_path = Path(r"C:\Windows\Fonts\msyh.ttc")
if not font_path.exists(): font_path = Path(r"C:\Windows\Fonts\simsun.ttc")
font_cell = ImageFont.truetype(str(font_path), 11)
font_hdr = ImageFont.truetype(str(font_path), 12)

# 色彩調色盤
WOOD_FRAME_DARK = (42, 28, 18, 255)
WOOD_FRAME_MID = (78, 54, 38, 255)
WOOD_PLANK_LIGHT = (148, 116, 85, 255)
WOOD_PLANK_DARK = (118, 88, 60, 255)
WOOD_HIGHLIGHT = (188, 154, 120, 255)

STONE_BASE_DARK = (52, 48, 44, 255)
STONE_BASE_MID = (98, 92, 85, 255)
STONE_BASE_LIGHT = (145, 138, 128, 255)
STONE_QUOIN = (175, 168, 158, 255)

ROOF_SHINGLE_DARK = (115, 48, 28, 255)
ROOF_SHINGLE_MID = (165, 78, 48, 255)
ROOF_SHINGLE_LIGHT = (198, 108, 72, 255)
ROOF_RIDGE = (88, 38, 22, 255)

FLOOR_PARQUET_1 = (172, 132, 94, 255)
FLOOR_PARQUET_2 = (152, 114, 78, 255)
RUG_BURGUNDY = (142, 32, 28, 255)
RUG_GOLD_FRINGE = (225, 185, 65, 255)
RUG_PATTERN = (185, 55, 45, 255)

GOLD_METALLIC = (255, 205, 45, 255)
GOLD_SHADOW = (185, 135, 20, 255)
BEER_FOAM = (255, 252, 238, 255)
FIRE_CORE = (255, 240, 160, 255)
FIRE_ORANGE = (255, 115, 25, 255)
FIRE_RED = (205, 45, 20, 255)
IRON_STEEL_DARK = (55, 62, 72, 255)
IRON_STEEL_MID = (95, 105, 120, 255)
IRON_STEEL_LIGHT = (185, 198, 215, 255)

POTION_RUBY = (245, 35, 55, 255)
POTION_SAPPHIRE = (35, 115, 245, 255)
POTION_EMERALD = (35, 215, 95, 255)
POTION_AMETHYST = (185, 45, 225, 255)
GLASS_HIGHLIGHT = (255, 255, 255, 210)

# ==============================================================================
# 0. 建築幾何與【屋頂 vs 店內獨立空間語意分層】
# ==============================================================================
BUILDINGS = {
    "MERCHANT": {"gx": 4, "gy": 5, "gw": 6, "gh": 5},
    "WATCHTOWER": {"gx": 16, "gy": 2, "gw": 4, "gh": 5},
    "BLACKSMITH": {"gx": 26, "gy": 5, "gw": 6, "gh": 5},
    "FURNACE": {"gx": 23, "gy": 6, "gw": 2, "gh": 2},
    "TAVERN": {"gx": 3, "gy": 25, "gw": 8, "gh": 6},
    "SHACK_W": {"gx": 2, "gy": 16, "gw": 4, "gh": 3},
    "SHACK_E": {"gx": 32, "gy": 14, "gw": 4, "gh": 3},
    "FARM_SHED": {"gx": 28, "gy": 26, "gw": 4, "gh": 3},
    "MARKET_A": {"gx": 16, "gy": 16, "gw": 2, "gh": 2},
    "MARKET_B": {"gx": 24, "gy": 16, "gw": 2, "gh": 2},
    "WELL": {"gx": 20, "gy": 17, "gw": 2, "gh": 2}
}

# --- Layer 1: 自然底地 ---
grid_l1 = [["[沙]" for _ in range(40)] for _ in range(40)]
def mark_road_sem(pts, w=2):
    for i in range(len(pts)-1):
        p0, p1 = pts[i], pts[i+1]
        steps = int(math.hypot(p1[0]-p0[0], p1[1]-p0[1]) * 2)
        for t in range(steps + 1):
            s = t / float(steps)
            cx, cy = int(p0[0] + (p1[0]-p0[0])*s), int(p0[1] + (p1[1]-p0[1])*s)
            for dy in range(-w//2, w//2 + 1):
                for dx in range(-w//2, w//2 + 1):
                    if 0 <= cx+dx < 40 and 0 <= cy+dy < 40: grid_l1[cy+dy][cx+dx] = "[路]"

mark_road_sem([(0, 23), (8, 22), (15, 20), (22, 19), (30, 19), (39, 17)], w=2)
mark_road_sem([(22, 19), (21, 26), (20, 39)], w=1)
mark_road_sem([(15, 20), (12, 14), (11, 8)], w=1)
mark_road_sem([(30, 19), (31, 14), (29, 9)], w=1)

for y in range(16, 23):
    for x in range(18, 26):
        if (x - 22)**2 + (y - 19)**2 <= 14: grid_l1[y][x] = "[石]"

for y in range(18, 35):
    for x in range(20, 40):
        if abs((y - 18) - (x - 20)*0.8) < 1.0: grid_l1[y][x] = "[渠]"

for fy in range(24, 33):
    for fx in range(23 + (fy - 24)//2, 38 - (fy - 24)//2):
        if grid_l1[fy][fx] != "[渠]": grid_l1[fy][fx] = "[田]"

# --- Layer 2: 建築店內層與本體 (Footprint & Interiors Only!) ---
# 注意：屋頂覆蓋的上部空間在 Layer 2 留空 [ · ]，店內層精準坐落於地基佔地與室內戰鬥空間！
grid_l2 = [["[ · ]" for _ in range(40)] for _ in range(40)]

# 1. 道具雜貨鋪 (gx: 4..9, gy: 6..9 為店內層，gy=5 為屋頂空間)
for dy in range(1, 5): # gy: 6..9
    for dx in range(6):
        grid_l2[5 + dy][4 + dx] = "[店地]"
grid_l2[6][5] = "[藥架]"
grid_l2[7][5] = "[藥架]"
grid_l2[6][8] = "[櫃台]"
grid_l2[7][8] = "[金箱]"
grid_l2[9][6] = "[店門]"
grid_l2[9][7] = "[石階]"

# 2. 鐵匠工坊 (gx: 26..31, gy: 6..9 為店內層，gy=5 為屋頂空間)
for dy in range(1, 5): # gy: 6..9
    for dx in range(6):
        grid_l2[5 + dy][26 + dx] = "[鐵地]"
grid_l2[6][27] = "[武架]"
grid_l2[7][27] = "[武架]"
grid_l2[6][30] = "[甲架]"
grid_l2[7][28] = "[鐵砧]"
grid_l2[9][28] = "[鐵門]"
grid_l2[9][29] = "[石階]"
# 熔爐
grid_l2[6][23] = "[熔爐]"
grid_l2[6][24] = "[熔爐]"
grid_l2[7][23] = "[熔爐]"
grid_l2[7][24] = "[熔爐]"

# 3. 邊境大酒館 (gx: 3..10, gy: 27..30 為店內層，gy: 25..26 為頂部空間)
for dy in range(2, 6): # gy: 27..30
    for dx in range(8):
        grid_l2[25 + dy][3 + dx] = "[酒地]"
grid_l2[27][4] = "[吧台]"
grid_l2[27][5] = "[吧台]"
grid_l2[27][9] = "[壁爐]"
grid_l2[27][10] = "[壁爐]"
grid_l2[28][4] = "[酒桶]"
grid_l2[28][5] = "[酒桶]"
grid_l2[28][7] = "[長桌]"
grid_l2[28][8] = "[長桌]"
grid_l2[29][7] = "[長桌]"
grid_l2[29][8] = "[長桌]"
grid_l2[30][6] = "[酒門]"
grid_l2[30][7] = "[酒門]"

# 4. 其他附屬建築
for dy in range(1, 5):
    for dx in range(4):
        grid_l2[2 + dy][16 + dx] = "[哨塔]"
grid_l2[17][2] = "[木棚]"; grid_l2[17][3] = "[木棚]"; grid_l2[18][2] = "[木棚]"; grid_l2[18][3] = "[木棚]"
grid_l2[15][32] = "[木棚]"; grid_l2[15][33] = "[木棚]"; grid_l2[16][32] = "[木棚]"; grid_l2[16][33] = "[木棚]"
grid_l2[27][28] = "[農棚]"; grid_l2[27][29] = "[農棚]"; grid_l2[28][28] = "[農棚]"; grid_l2[28][29] = "[農棚]"
grid_l2[16][16] = "[果攤]"; grid_l2[16][17] = "[果攤]"
grid_l2[16][24] = "[器攤]"; grid_l2[16][25] = "[器攤]"
grid_l2[17][20] = "[水井]"; grid_l2[17][21] = "[水井]"

# --- Layer 2.5: 環境雜物 ---
grid_l25 = [["[ · ]" for _ in range(40)] for _ in range(40)]
for y in range(40):
    for x in range(40):
        if (x * 7 + y * 13) % 19 == 0 and grid_l2[y][x] == "[ · ]": grid_l25[y][x] = "[碎石]"
        if (x * 5 + y * 11) % 23 == 0 and grid_l1[y][x] == "[沙]" and grid_l2[y][x] == "[ · ]": grid_l25[y][x] = "[枯草]"
grid_l25[25][11] = "[木箱]"
grid_l25[26][11] = "[酒桶]"
grid_l25[19][27] = "[木橋]"

# --- Layer 3: 屋頂專屬語意 (Roof Overlay Only!) ---
# 屋頂嚴格位於上方懸垂區，絕不與下方的門口/外牆腳共用！
grid_l3 = [["[ · ]" for _ in range(40)] for _ in range(40)]

# 1. 雜貨鋪屋頂 (gx: 4..9, gy: 5 屋頂懸垂)
for x in range(4, 10):
    grid_l3[5][x] = "[▲店頂]"

# 2. 鐵匠鋪屋頂 (gx: 26..31, gy: 5 屋頂懸垂)
for x in range(26, 32):
    grid_l3[5][x] = "[▲鐵頂]"

# 3. 大酒館屋頂 (gx: 3..10, gy: 25..26 兩行大屋頂懸垂)
for y in range(25, 27):
    for x in range(3, 11):
        grid_l3[y][x] = "[▲酒頂]"

# 4. 哨塔與棚頂
for y in range(2, 4):
    for x in range(16, 20):
        grid_l3[y][x] = "[▲塔頂]"
for x in range(2, 6): grid_l3[16][x] = "[▲棚頂]"
for x in range(32, 36): grid_l3[14][x] = "[▲棚頂]"
for x in range(28, 32): grid_l3[26][x] = "[▲棚頂]"

# ==============================================================================
# 🎨 1. 消除水平直線！繪製自然流暢 3/4 俯視人字山牆瓦頂
# ==============================================================================

def draw_organic_34_roof(draw, x0, y0, x1, y1, ridge_y, eaves_y, roof_type="tavern"):
    w = x1 - x0
    mid_x = (x0 + x1) // 2
    
    # 1. 屋簷自然人字微垂弧度 (Organic Eaves Pitch - 消除死板水平線！)
    # 左側簷口 (x0, eaves_y)、中央微垂 (mid_x, eaves_y + 8)、右側簷口 (x1, eaves_y)
    eaves_poly = [
        (x0, eaves_y),
        (mid_x, eaves_y + 8),
        (x1, eaves_y),
        (x1, ridge_y + 6),
        (mid_x, ridge_y),
        (x0, ridge_y + 6)
    ]
    draw.polygon(eaves_poly, fill=ROOF_SHINGLE_DARK)
    
    # 2. 逐層重疊板岩瓦 (Slate Shingle Rows with Curved Contour)
    rows = 6
    for r in range(rows):
        t_top = r / float(rows)
        t_bot = (r + 1) / float(rows)
        
        # 弧度向下延伸
        curv_top = int(6 * (1.0 - t_top))
        curv_bot = int(8 * t_bot)
        
        ry0_mid = int(ridge_y + (eaves_y + 8 - ridge_y) * t_top)
        ry1_mid = int(ridge_y + (eaves_y + 8 - ridge_y) * t_bot)
        ry0_side = int(ridge_y + 6 + (eaves_y - (ridge_y + 6)) * t_top)
        ry1_side = int(ridge_y + 6 + (eaves_y - (ridge_y + 6)) * t_bot)
        
        rx0_l = int(mid_x - (mid_x - x0) * t_top)
        rx0_r = int(mid_x + (x1 - mid_x) * t_top)
        rx1_l = int(mid_x - (mid_x - x0) * t_bot)
        rx1_r = int(mid_x + (x1 - mid_x) * t_bot)
        
        c = ROOF_SHINGLE_MID if r % 2 == 0 else ROOF_SHINGLE_LIGHT
        
        # 繪製單排微弧瓦片多邊形
        tile_row_poly = [
            (rx0_l, ry0_side), (mid_x, ry0_mid), (rx0_r, ry0_side),
            (rx1_r, ry1_side), (mid_x, ry1_mid), (rx1_l, ry1_side)
        ]
        draw.polygon(tile_row_poly, fill=c, outline=ROOF_SHINGLE_DARK)
        
        # 瓦片刻痕 (Vertical Shingle Edges)
        num_tiles = 10 + r * 2
        for i in range(1, num_tiles):
            frac = i / float(num_tiles)
            vx0 = int(rx0_l + (rx0_r - rx0_l) * frac)
            vy0 = int(ry0_side + (ry0_mid - ry0_side) * (1.0 - abs(frac - 0.5)*2))
            vx1 = int(rx1_l + (rx1_r - rx1_l) * frac)
            vy1 = int(ry1_side + (ry1_mid - ry1_side) * (1.0 - abs(frac - 0.5)*2))
            draw.line([(vx0, vy0), (vx1, vy1)], fill=ROOF_SHINGLE_DARK, width=1)
            draw.line([(vx0 + 1, vy1 - 1), (vx1, vy1 - 1)], fill=ROOF_SHINGLE_LIGHT, width=1)

    # 3. 山脊加固頂蓋脊瓦 (Ridge Cap)
    draw.polygon([(x0 + 16, ridge_y + 6), (mid_x, ridge_y), (x1 - 16, ridge_y + 6),
                  (x1 - 16, ridge_y + 10), (mid_x, ridge_y + 4), (x0 + 16, ridge_y + 10)],
                 fill=ROOF_RIDGE, outline=WOOD_HIGHLIGHT)
    
    # 4. 屋簷下方陰影 ＆ 封簷木板 (Fascia Board & Drop Shadow - 完美自然過渡！)
    draw.polygon([(x0, eaves_y), (mid_x, eaves_y + 8), (x1, eaves_y),
                  (x1, eaves_y + 6), (mid_x, eaves_y + 14), (x0, eaves_y + 6)],
                 fill=WOOD_FRAME_DARK)

def draw_detailed_facade_wall(draw, x0, y0, x1, y1):
    draw.rectangle([x0, y0, x1, y1], fill=WOOD_PLANK_LIGHT, outline=WOOD_FRAME_DARK, width=2)
    for wy in range(y0 + 6, y1, 8):
        draw.line([(x0, wy), (x1, wy)], fill=WOOD_PLANK_DARK, width=1)
        draw.line([(x0, wy + 1), (x1, wy + 1)], fill=WOOD_HIGHLIGHT, width=1)
    
    for px in range(x0, x1 + 1, 32):
        draw.rectangle([px - 2, y0, px + 2, y1], fill=WOOD_FRAME_MID, outline=WOOD_FRAME_DARK)
        draw.line([(px, y0), (px, y1)], fill=WOOD_FRAME_DARK, width=1)
    
    for qy in range(y0, y1, 10):
        h = min(8, y1 - qy)
        draw.rectangle([x0, qy, x0 + 6, qy + h], fill=STONE_QUOIN, outline=STONE_BASE_DARK)
        draw.rectangle([x1 - 6, qy, x1, qy + h], fill=STONE_QUOIN, outline=STONE_BASE_DARK)

def draw_detailed_doors(draw, dx0, dy0, dx1, dy1, is_double=True):
    draw.rectangle([dx0 - 3, dy0 - 3, dx1 + 3, dy1], fill=WOOD_FRAME_DARK, outline=STONE_BASE_DARK, width=1)
    draw.rectangle([dx0, dy0, dx1, dy1], fill=WOOD_PLANK_DARK, outline=WOOD_FRAME_DARK, width=2)
    
    mid_dx = (dx0 + dx1) // 2
    if is_double:
        draw.line([(mid_dx, dy0), (mid_dx, dy1)], fill=WOOD_FRAME_DARK, width=2)
        doors = [(dx0 + 2, dy0 + 2, mid_dx - 2, dy1 - 2), (mid_dx + 2, dy0 + 2, dx1 - 2, dy1 - 2)]
    else:
        doors = [(dx0 + 2, dy0 + 2, dx1 - 2, dy1 - 2)]
        
    for (x_a, y_a, x_b, y_b) in doors:
        draw.rectangle([x_a, y_a + 8, x_b, y_a + 13], fill=IRON_STEEL_DARK, outline=IRON_STEEL_LIGHT, width=1)
        draw.rectangle([x_a, y_b - 14, x_b, y_b - 9], fill=IRON_STEEL_DARK, outline=IRON_STEEL_LIGHT, width=1)
        draw.ellipse([(x_a + x_b)//2 - 3, (y_a + y_b)//2 - 3, (x_a + x_b)//2 + 3, (y_a + y_b)//2 + 3], 
                     outline=IRON_STEEL_LIGHT, width=1)

def draw_detailed_window(draw, wx0, wy0, wx1, wy1):
    draw.rectangle([wx0 - 2, wy0 - 2, wx1 + 2, wy1 + 2], fill=WOOD_FRAME_DARK, outline=STONE_BASE_DARK)
    draw.rectangle([wx0, wy0, wx1, wy1], fill=(255, 195, 65, 230), outline=WOOD_FRAME_DARK, width=1)
    mid_x = (wx0 + wx1) // 2
    mid_y = (wy0 + wy1) // 2
    draw.line([(mid_x, wy0), (mid_x, wy1)], fill=WOOD_FRAME_DARK, width=1)
    draw.line([(wx0, mid_y), (wx1, mid_y)], fill=WOOD_FRAME_DARK, width=1)
    draw.rectangle([wx0 - 3, wy1, wx1 + 3, wy1 + 3], fill=WOOD_FRAME_MID, outline=WOOD_FRAME_DARK)

def draw_3d_signboard(draw, bx, by, icon_type="beer"):
    draw.line([(bx - 18, by), (bx + 18, by)], fill=IRON_STEEL_DARK, width=3)
    draw.line([(bx - 16, by - 1), (bx + 16, by - 1)], fill=IRON_STEEL_LIGHT, width=1)
    draw.line([(bx - 14, by + 12), (bx - 2, by)], fill=IRON_STEEL_DARK, width=2)
    draw.line([(bx + 14, by + 12), (bx + 2, by)], fill=IRON_STEEL_DARK, width=2)
    draw.line([(bx - 10, by), (bx - 10, by + 8)], fill=IRON_STEEL_MID, width=2)
    draw.line([(bx + 10, by), (bx + 10, by + 8)], fill=IRON_STEEL_MID, width=2)
    
    draw.rectangle([bx - 16, by + 6, bx + 16, by + 30], fill=WOOD_FRAME_DARK, outline=GOLD_METALLIC, width=2)
    draw.rectangle([bx - 14, by + 8, bx + 14, by + 28], fill=WOOD_PLANK_DARK)
    
    if icon_type == "beer":
        draw.rectangle([bx - 7, by + 13, bx + 4, by + 25], fill=GOLD_METALLIC, outline=GOLD_SHADOW, width=1)
        draw.rectangle([bx + 4, by + 16, bx + 8, by + 22], fill=GOLD_SHADOW, outline=GOLD_METALLIC, width=1)
        draw.ellipse([bx - 8, by + 10, bx + 5, by + 15], fill=BEER_FOAM)
    elif icon_type == "hammer":
        draw.line([(bx - 7, by + 24), (bx + 5, by + 12)], fill=WOOD_HIGHLIGHT, width=2)
        draw.rectangle([bx + 2, by + 10, bx + 9, by + 16], fill=IRON_STEEL_LIGHT, outline=IRON_STEEL_DARK, width=1)
        draw.polygon([(bx - 8, by + 23), (bx + 2, by + 23), (bx - 1, by + 26), (bx - 5, by + 26)], fill=FIRE_ORANGE)
    elif icon_type == "potion":
        draw.ellipse([bx - 8, by + 14, bx + 2, by + 24], fill=POTION_RUBY, outline=GLASS_HIGHLIGHT, width=1)
        draw.rectangle([bx - 5, by + 11, bx - 1, by + 14], fill=WOOD_PLANK_LIGHT)
        draw.ellipse([bx + 1, by + 16, bx + 8, by + 25], fill=GOLD_METALLIC, outline=GOLD_SHADOW, width=1)

# ==============================================================================
# 2. 滿格渲染建築 (酒館 8x6, 鐵匠 6x5, 雜貨 6x5)
# ==============================================================================

# 🍺 2.1 邊境大酒館 (256x192 px = 8x6)
img_tav_int = Image.new("RGBA", (256, 192), (0, 0, 0, 0))
d_ti = ImageDraw.Draw(img_tav_int)

d_ti.ellipse([4, 168, 252, 192], fill=(30, 22, 15, 130))
d_ti.rectangle([4, 36, 252, 184], fill=STONE_BASE_MID, outline=STONE_BASE_DARK, width=2)
for sy in range(40, 184, 12): d_ti.line([(4, sy), (252, sy)], fill=STONE_BASE_DARK, width=1)
d_ti.rectangle([104, 172, 152, 188], fill=STONE_BASE_LIGHT, outline=STONE_BASE_DARK, width=1)

for fy in range(40, 172, 6):
    for fx in range(8, 248, 12):
        c = FLOOR_PARQUET_1 if ((fx // 12) + (fy // 6)) % 2 == 0 else FLOOR_PARQUET_2
        d_ti.rectangle([fx, fy, fx + 11, fy + 5], fill=c, outline=WOOD_FRAME_DARK, width=1)

d_ti.rectangle([64, 88, 192, 152], fill=RUG_BURGUNDY, outline=RUG_GOLD_FRINGE, width=3)
d_ti.rectangle([72, 96, 184, 144], outline=RUG_PATTERN, width=2)
d_ti.polygon([(128, 104), (144, 120), (128, 136), (112, 120)], fill=RUG_PATTERN, outline=RUG_GOLD_FRINGE)

d_ti.rectangle([196, 44, 244, 108], fill=STONE_BASE_MID, outline=STONE_BASE_DARK, width=2)
d_ti.rectangle([204, 60, 236, 108], fill=(25, 18, 15, 255))
d_ti.ellipse([208, 76, 232, 104], fill=FIRE_RED)
d_ti.ellipse([212, 82, 228, 100], fill=FIRE_ORANGE)
d_ti.ellipse([216, 88, 224, 96], fill=FIRE_CORE)
d_ti.line([(204, 100), (236, 100)], fill=IRON_STEEL_DARK, width=2)
d_ti.line([(212, 92), (212, 106)], fill=IRON_STEEL_DARK, width=1)
d_ti.line([(220, 92), (220, 106)], fill=IRON_STEEL_DARK, width=1)
d_ti.line([(228, 92), (228, 106)], fill=IRON_STEEL_DARK, width=1)

d_ti.rectangle([12, 42, 116, 56], fill=WOOD_FRAME_DARK, outline=WOOD_HIGHLIGHT, width=1)
for bx in range(16, 112, 8):
    bottle_col = [POTION_RUBY, POTION_SAPPHIRE, GOLD_METALLIC, POTION_EMERALD][(bx // 8) % 4]
    d_ti.rectangle([bx, 44, bx + 4, 54], fill=bottle_col)
for kx in range(16, 56, 14):
    d_ti.ellipse([kx, 60, kx + 12, 74], fill=WOOD_PLANK_DARK, outline=IRON_STEEL_DARK, width=1)
d_ti.rectangle([16, 68, 116, 80], fill=WOOD_FRAME_MID, outline=WOOD_HIGHLIGHT, width=2)
d_ti.rectangle([16, 80, 32, 136], fill=WOOD_FRAME_MID, outline=WOOD_HIGHLIGHT, width=2)
d_ti.rectangle([70, 64, 76, 68], fill=GOLD_METALLIC)
d_ti.ellipse([88, 70, 94, 76], fill=GOLD_SHADOW)
d_ti.ellipse([100, 70, 106, 76], fill=GOLD_SHADOW)
for st_y in range(86, 132, 16):
    d_ti.ellipse([36, st_y, 48, st_y + 12], fill=RUG_BURGUNDY, outline=WOOD_FRAME_DARK, width=2)

d_ti.rectangle([96, 108, 160, 128], fill=WOOD_PLANK_LIGHT, outline=WOOD_FRAME_DARK, width=2)
d_ti.ellipse([118, 112, 138, 124], fill=STONE_BASE_LIGHT, outline=STONE_BASE_DARK)
d_ti.ellipse([122, 115, 134, 121], fill=WOOD_FRAME_DARK)
d_ti.ellipse([104, 114, 110, 122], fill=GOLD_METALLIC)
d_ti.ellipse([146, 114, 152, 122], fill=GOLD_METALLIC)
d_ti.rectangle([98, 100, 158, 105], fill=WOOD_PLANK_DARK, outline=WOOD_FRAME_DARK)
d_ti.rectangle([98, 131, 158, 136], fill=WOOD_PLANK_DARK, outline=WOOD_FRAME_DARK)

img_tav_int.save(asset_dir / "interior_tavern_256x192.png")

img_tav_ext = Image.new("RGBA", (256, 192), (0, 0, 0, 0))
d_te = ImageDraw.Draw(img_tav_ext)
d_te.ellipse([4, 168, 252, 192], fill=(30, 22, 15, 130))
d_te.rectangle([4, 36, 252, 184], fill=STONE_BASE_MID, outline=STONE_BASE_DARK, width=2)
for sy in range(40, 184, 12): d_te.line([(4, sy), (252, sy)], fill=STONE_BASE_DARK, width=1)
d_te.rectangle([104, 172, 152, 188], fill=STONE_BASE_LIGHT, outline=STONE_BASE_DARK, width=1)

# 正面立面牆 (Facade Wall)
draw_detailed_facade_wall(d_te, 8, 72, 248, 174)
draw_detailed_doors(d_te, 108, 104, 148, 174, is_double=True)
draw_detailed_window(d_te, 36, 108, 76, 144)
draw_detailed_window(d_te, 180, 108, 220, 144)

# 自然流暢 3/4 俯視人字山牆瓦頂 (無死板水平線！)
draw_organic_34_roof(d_te, 0, 4, 256, 192, ridge_y=6, eaves_y=76, roof_type="tavern")
draw_3d_signboard(d_te, 128, 80, icon_type="beer")
img_tav_ext.save(asset_dir / "exterior_tavern_256x192.png")

img_tav_roof = Image.new("RGBA", (256, 192), (0, 0, 0, 0))
d_tr = ImageDraw.Draw(img_tav_roof)
draw_organic_34_roof(d_tr, 0, 4, 256, 192, ridge_y=6, eaves_y=76, roof_type="tavern")
draw_3d_signboard(d_tr, 128, 80, icon_type="beer")
img_tav_roof.save(asset_dir / "fader_tavern_256x192.png")

# 🔨 2.2 鐵匠工坊 (192x160 px = 6x5)
img_smith_int = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_si = ImageDraw.Draw(img_smith_int)
d_si.ellipse([4, 138, 188, 160], fill=(30, 22, 15, 130))
d_si.rectangle([4, 32, 188, 150], fill=STONE_BASE_MID, outline=STONE_BASE_DARK, width=2)
for sy in range(36, 150, 12): d_si.line([(4, sy), (188, sy)], fill=STONE_BASE_DARK, width=1)
d_si.rectangle([76, 140, 116, 154], fill=STONE_BASE_LIGHT, outline=STONE_BASE_DARK, width=1)
for sy in range(36, 142, 8):
    for sx in range(8, 184, 12):
        d_si.rectangle([sx, sy, sx + 11, sy + 7], fill=STONE_BASE_MID, outline=STONE_BASE_DARK, width=1)
d_si.ellipse([14, 42, 34, 62], fill=WOOD_FRAME_DARK, outline=IRON_STEEL_DARK, width=2)
d_si.ellipse([18, 46, 30, 58], fill=POTION_SAPPHIRE)
d_si.ellipse([150, 42, 178, 64], fill=STONE_BASE_LIGHT, outline=STONE_BASE_DARK, width=2)
d_si.rectangle([14, 72, 60, 116], fill=WOOD_FRAME_MID, outline=WOOD_FRAME_DARK, width=2)
d_si.line([(22, 64), (22, 112)], fill=IRON_STEEL_LIGHT, width=2)
d_si.line([(34, 58), (34, 112)], fill=WOOD_HIGHLIGHT, width=2)
d_si.polygon([(32, 58), (36, 58), (34, 50)], fill=IRON_STEEL_LIGHT)
d_si.line([(48, 62), (48, 112)], fill=IRON_STEEL_LIGHT, width=2)
d_si.rectangle([138, 74, 166, 118], fill=WOOD_FRAME_DARK, outline=WOOD_FRAME_DARK)
d_si.ellipse([144, 66, 160, 80], fill=IRON_STEEL_LIGHT, outline=IRON_STEEL_DARK, width=1)
d_si.rectangle([142, 80, 162, 108], fill=IRON_STEEL_MID, outline=IRON_STEEL_LIGHT, width=1)
d_si.ellipse([140, 102, 164, 126], fill=IRON_STEEL_DARK)
d_si.ellipse([82, 92, 110, 112], fill=WOOD_FRAME_DARK)
d_si.polygon([(78, 86), (114, 86), (106, 100), (86, 100)], fill=IRON_STEEL_DARK, outline=IRON_STEEL_LIGHT, width=1)
d_si.rectangle([(74, 84), (118, 88)], fill=IRON_STEEL_LIGHT)
img_smith_int.save(asset_dir / "interior_blacksmith_192x160.png")

img_smith_ext = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_se = ImageDraw.Draw(img_smith_ext)
d_se.ellipse([4, 138, 188, 160], fill=(30, 22, 15, 130))
d_se.rectangle([4, 32, 188, 150], fill=STONE_BASE_MID, outline=STONE_BASE_DARK, width=2)
for sy in range(36, 150, 12): d_se.line([(4, sy), (188, sy)], fill=STONE_BASE_DARK, width=1)
d_se.rectangle([76, 140, 116, 154], fill=STONE_BASE_LIGHT, outline=STONE_BASE_DARK, width=1)
draw_detailed_facade_wall(d_se, 8, 64, 184, 142)
draw_detailed_doors(d_se, 78, 92, 114, 142, is_double=False)
draw_detailed_window(d_se, 28, 96, 56, 124)
draw_organic_34_roof(d_se, 0, 4, 192, 160, ridge_y=6, eaves_y=66, roof_type="smith")
draw_3d_signboard(d_se, 96, 70, icon_type="hammer")
img_smith_ext.save(asset_dir / "exterior_blacksmith_192x160.png")

img_smith_roof = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_sr = ImageDraw.Draw(img_smith_roof)
draw_organic_34_roof(d_sr, 0, 4, 192, 160, ridge_y=6, eaves_y=66, roof_type="smith")
draw_3d_signboard(d_sr, 96, 70, icon_type="hammer")
img_smith_roof.save(asset_dir / "fader_blacksmith_192x160.png")

# 🧪 2.3 道具雜貨鋪 (192x160 px = 6x5)
img_merch_int = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_mi = ImageDraw.Draw(img_merch_int)
d_mi.ellipse([4, 138, 188, 160], fill=(30, 22, 15, 130))
d_mi.rectangle([4, 32, 188, 150], fill=STONE_BASE_MID, outline=STONE_BASE_DARK, width=2)
for sy in range(36, 150, 12): d_mi.line([(4, sy), (188, sy)], fill=STONE_BASE_DARK, width=1)
d_mi.rectangle([76, 140, 116, 154], fill=STONE_BASE_LIGHT, outline=STONE_BASE_DARK, width=1)
for my in range(36, 142, 6):
    c = FLOOR_PARQUET_1 if (my // 6) % 2 == 0 else FLOOR_PARQUET_2
    d_mi.rectangle([8, my, 184, my + 5], fill=c, outline=WOOD_FRAME_DARK, width=1)
d_mi.rectangle([12, 42, 68, 122], fill=WOOD_FRAME_MID, outline=WOOD_FRAME_DARK, width=2)
for py in range(50, 120, 14):
    d_mi.line([(12, py), (68, py)], fill=WOOD_FRAME_DARK, width=2)
    d_mi.ellipse([16, py - 10, 26, py], fill=POTION_RUBY, outline=GLASS_HIGHLIGHT, width=1)
    d_mi.ellipse([30, py - 10, 40, py], fill=POTION_SAPPHIRE, outline=GLASS_HIGHLIGHT, width=1)
    d_mi.ellipse([44, py - 10, 54, py], fill=POTION_EMERALD, outline=GLASS_HIGHLIGHT, width=1)
    d_mi.ellipse([56, py - 10, 64, py], fill=POTION_AMETHYST, outline=GLASS_HIGHLIGHT, width=1)
d_mi.rectangle([112, 70, 176, 92], fill=WOOD_PLANK_LIGHT, outline=WOOD_FRAME_DARK, width=2)
d_mi.line([(144, 54), (144, 70)], fill=GOLD_METALLIC, width=2)
d_mi.line([(134, 56), (154, 56)], fill=GOLD_METALLIC, width=2)
d_mi.ellipse([131, 58, 137, 64], fill=GOLD_SHADOW, outline=GOLD_METALLIC)
d_mi.ellipse([151, 58, 157, 64], fill=GOLD_SHADOW, outline=GOLD_METALLIC)
d_mi.rectangle([118, 74, 130, 84], fill=BEER_FOAM, outline=WOOD_FRAME_DARK)
d_mi.line([(126, 72), (132, 66)], fill=BEER_FOAM, width=1)
d_mi.rectangle([124, 102, 164, 128], fill=WOOD_FRAME_DARK, outline=GOLD_METALLIC, width=2)
d_mi.ellipse([128, 106, 136, 114], fill=GOLD_METALLIC)
d_mi.ellipse([136, 108, 144, 116], fill=GOLD_METALLIC)
d_mi.ellipse([144, 105, 152, 113], fill=POTION_EMERALD, outline=GLASS_HIGHLIGHT)
d_mi.ellipse([152, 107, 160, 115], fill=POTION_RUBY, outline=GLASS_HIGHLIGHT)
img_merch_int.save(asset_dir / "interior_merchant_192x160.png")

img_merch_ext = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_me = ImageDraw.Draw(img_merch_ext)
d_me.ellipse([4, 138, 188, 160], fill=(30, 22, 15, 130))
d_me.rectangle([4, 32, 188, 150], fill=STONE_BASE_MID, outline=STONE_BASE_DARK, width=2)
for sy in range(36, 150, 12): d_me.line([(4, sy), (188, sy)], fill=STONE_BASE_DARK, width=1)
d_me.rectangle([76, 140, 116, 154], fill=STONE_BASE_LIGHT, outline=STONE_BASE_DARK, width=1)
draw_detailed_facade_wall(d_me, 8, 64, 184, 142)
draw_detailed_doors(d_me, 78, 92, 114, 142, is_double=False)
draw_detailed_window(d_me, 136, 96, 164, 124)
draw_organic_34_roof(d_me, 0, 4, 192, 160, ridge_y=6, eaves_y=66, roof_type="merch")
draw_3d_signboard(d_me, 96, 70, icon_type="potion")
img_merch_ext.save(asset_dir / "exterior_merchant_192x160.png")

img_merch_roof = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_mr = ImageDraw.Draw(img_merch_roof)
draw_organic_34_roof(d_mr, 0, 4, 192, 160, ridge_y=6, eaves_y=66, roof_type="merch")
draw_3d_signboard(d_mr, 96, 70, icon_type="potion")
img_merch_roof.save(asset_dir / "fader_merchant_192x160.png")

# ==============================================================================
# 3. 重新渲染四大分層與對比大圖
# ==============================================================================
cell = 32
w_px, h_px = 40 * cell, 40 * cell

img_l1 = Image.open(asset_dir / "layer_1_ground.png").convert("RGBA")
img_l2 = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))

def paste_bldg(target_img, sprite_img, bkey):
    b = BUILDINGS[bkey]
    px, py = b["gx"] * cell, b["gy"] * cell
    target_img.paste(sprite_img, (px, py), sprite_img)

tex_tower = Image.open(asset_dir / "prefab_watchtower_128x160.png").convert("RGBA")
tex_furnace = Image.open(asset_dir / "prefab_furnace_64x64.png").convert("RGBA")
tex_stall = Image.open(asset_dir / "prefab_market_stall_64x48.png").convert("RGBA")
tex_shack_ext = Image.open(asset_dir / "exterior_shack_128x96.png").convert("RGBA")

paste_bldg(img_l2, tex_tower, "WATCHTOWER")
paste_bldg(img_l2, img_merch_int, "MERCHANT")
paste_bldg(img_l2, tex_furnace, "FURNACE")
paste_bldg(img_l2, img_smith_int, "BLACKSMITH")
paste_bldg(img_l2, tex_stall, "MARKET_A")
paste_bldg(img_l2, tex_stall, "MARKET_B")
paste_bldg(img_l2, tex_shack_ext, "SHACK_W")
paste_bldg(img_l2, tex_shack_ext, "SHACK_E")
paste_bldg(img_l2, tex_shack_ext, "FARM_SHED")
paste_bldg(img_l2, img_tav_int, "TAVERN")

img_l25 = Image.open(asset_dir / "layer_2_5_clutter.png").convert("RGBA")

img_l3 = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
paste_bldg(img_l3, img_merch_roof, "MERCHANT")
paste_bldg(img_l3, img_smith_roof, "BLACKSMITH")
paste_bldg(img_l3, img_tav_roof, "TAVERN")

img_exterior_merged = img_l1.copy()
paste_bldg(img_exterior_merged, tex_tower, "WATCHTOWER")
paste_bldg(img_exterior_merged, img_merch_ext, "MERCHANT")
paste_bldg(img_exterior_merged, tex_furnace, "FURNACE")
paste_bldg(img_exterior_merged, img_smith_ext, "BLACKSMITH")
paste_bldg(img_exterior_merged, tex_stall, "MARKET_A")
paste_bldg(img_exterior_merged, tex_stall, "MARKET_B")
paste_bldg(img_exterior_merged, tex_shack_ext, "SHACK_W")
paste_bldg(img_exterior_merged, tex_shack_ext, "SHACK_E")
paste_bldg(img_exterior_merged, tex_shack_ext, "FARM_SHED")
paste_bldg(img_exterior_merged, img_tav_ext, "TAVERN")
img_exterior_merged.paste(img_l25, (0, 0), img_l25)

img_interior_merged = img_l1.copy()
img_interior_merged.paste(img_l2, (0, 0), img_l2)
img_interior_merged.paste(img_l25, (0, 0), img_l25)

img_l1.save(brain_dir / "layer_1_ground.png")
img_l2.save(brain_dir / "layer_2_structures.png")
img_l25.save(brain_dir / "layer_2_5_clutter.png")
img_l3.save(brain_dir / "layer_3_roofs.png")
img_exterior_merged.save(brain_dir / "view_exterior_merged.png")
img_interior_merged.save(brain_dir / "view_interior_merged.png")

img_exterior_merged.save(skill_assets_dir / "kenshi_village_exterior_1280.png")
img_interior_merged.save(skill_assets_dir / "kenshi_village_interior_1280.png")

# Base64
b64_ext = base64.b64encode((brain_dir / "view_exterior_merged.png").read_bytes()).decode("utf-8")
b64_int = base64.b64encode((brain_dir / "view_interior_merged.png").read_bytes()).decode("utf-8")
b64_l1 = base64.b64encode((brain_dir / "layer_1_ground.png").read_bytes()).decode("utf-8")
b64_l2 = base64.b64encode((brain_dir / "layer_2_structures.png").read_bytes()).decode("utf-8")
b64_l25 = base64.b64encode((brain_dir / "layer_2_5_clutter.png").read_bytes()).decode("utf-8")
b64_l3 = base64.b64encode((brain_dir / "layer_3_roofs.png").read_bytes()).decode("utf-8")

# ==============================================================================
# 4. 重新渲染五態視覺化語意圖 (嚴格分層空間分離！)
# ==============================================================================
TOKEN_COLORS = {
    "[沙]": ((215, 175, 115, 180), (70, 50, 25)),
    "[路]": ((180, 130, 85, 230), (255, 245, 225)),
    "[石]": ((145, 155, 175, 230), (20, 30, 45)),
    "[田]": ((125, 165, 75, 230), (20, 40, 10)),
    "[渠]": ((55, 125, 215, 230), (255, 255, 255)),
    "[酒]": ((175, 55, 45, 240), (255, 240, 200)),
    "[酒地]": ((195, 135, 90, 220), (50, 25, 15)),
    "[吧台]": ((125, 75, 40, 240), (255, 215, 80)),
    "[酒桶]": ((100, 60, 30, 240), (255, 200, 80)),
    "[酒架]": ((110, 65, 35, 240), (255, 220, 140)),
    "[壁爐]": ((225, 85, 30, 240), (255, 255, 200)),
    "[長桌]": ((150, 105, 65, 240), (255, 255, 255)),
    "[酒門]": ((140, 75, 45, 240), (255, 235, 180)),
    "[鐵]": ((70, 80, 105, 240), (255, 140, 40)),
    "[鐵地]": ((120, 125, 135, 220), (20, 25, 35)),
    "[武架]": ((140, 60, 40, 240), (255, 220, 180)),
    "[甲架]": ((80, 110, 145, 240), (255, 255, 255)),
    "[鐵砧]": ((45, 55, 70, 240), (220, 235, 255)),
    "[鐵門]": ((90, 75, 65, 240), (255, 235, 180)),
    "[熔爐]": ((235, 75, 25, 240), (255, 245, 180)),
    "[店]": ((55, 135, 105, 240), (255, 235, 150)),
    "[店地]": ((165, 130, 95, 220), (45, 30, 15)),
    "[藥架]": ((165, 45, 85, 240), (255, 225, 235)),
    "[櫃台]": ((135, 95, 55, 240), (255, 235, 180)),
    "[金箱]": ((215, 165, 35, 240), (40, 25, 5)),
    "[店門]": ((120, 85, 60, 240), (255, 235, 180)),
    "[石階]": ((160, 155, 145, 240), (30, 30, 30)),
    "[塔]": ((95, 105, 120, 240), (255, 255, 255)),
    "[哨塔]": ((95, 105, 120, 240), (255, 255, 255)),
    "[木棚]": ((130, 95, 65, 230), (255, 235, 205)),
    "[農棚]": ((130, 95, 65, 230), (255, 235, 205)),
    "[果攤]": ((185, 115, 45, 240), (255, 255, 255)),
    "[器攤]": ((75, 125, 145, 240), (255, 255, 255)),
    "[水井]": ((45, 145, 175, 240), (255, 255, 255)),
    "[碎石]": ((110, 115, 125, 230), (240, 245, 255)),
    "[枯草]": ((155, 145, 75, 230), (40, 40, 10)),
    "[木箱]": ((145, 100, 55, 240), (255, 235, 190)),
    "[木橋]": ((165, 120, 75, 240), (255, 255, 255)),
    "[▲店頂]": ((180, 80, 50, 240), (255, 240, 210)),
    "[▲鐵頂]": ((180, 80, 50, 240), (255, 240, 210)),
    "[▲酒頂]": ((180, 80, 50, 240), (255, 240, 210)),
    "[▲塔頂]": ((160, 70, 40, 240), (255, 240, 210)),
    "[▲棚頂]": ((160, 70, 40, 240), (255, 240, 210)),
    "[ · ]": ((15, 18, 24, 255), (45, 55, 70))
}

def render_semantic_grid_image(grid):
    img = Image.new("RGBA", (1280, 1280), (14, 17, 23, 255))
    d = ImageDraw.Draw(img)
    for y in range(40):
        for x in range(40):
            px, py = x * 32, y * 32
            tok = grid[y][x]
            bg_col, txt_col = TOKEN_COLORS.get(tok, ((30, 35, 45, 220), (150, 160, 175)))
            d.rectangle([px, py, px + 31, py + 31], fill=bg_col, outline=(25, 30, 40, 180), width=1)
            
            if tok != "[ · ]":
                short_txt = tok.replace("[", "").replace("]", "")
                if len(short_txt) > 2: short_txt = short_txt[:2]
                bbox = d.textbbox((0, 0), short_txt, font=font_cell)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                tx, ty = px + (32 - tw) // 2, py + (32 - th) // 2 - 2
                d.text((tx, ty), short_txt, fill=txt_col, font=font_cell)

    for i in range(0, 40, 5):
        d.text((i * 32 + 2, 2), f"{i}", fill=(255, 255, 255, 160), font=font_hdr)
        if i > 0: d.text((2, i * 32 + 2), f"{i}", fill=(255, 255, 255, 160), font=font_hdr)
    return img

img_sem_l1 = render_semantic_grid_image(grid_l1)
img_sem_l2 = render_semantic_grid_image(grid_l2)
img_sem_l25 = render_semantic_grid_image(grid_l25)
img_sem_l3 = render_semantic_grid_image(grid_l3)

grid_merged = [["[沙]" for _ in range(40)] for _ in range(40)]
for y in range(40):
    for x in range(40):
        grid_merged[y][x] = grid_l1[y][x]
        if grid_l2[y][x] != "[ · ]": grid_merged[y][x] = grid_l2[y][x]
        elif grid_l25[y][x] != "[ · ]": grid_merged[y][x] = grid_l25[y][x]
        if grid_l3[y][x] != "[ · ]": grid_merged[y][x] = grid_l3[y][x]

img_sem_mrg = render_semantic_grid_image(grid_merged)

img_sem_l1.save(brain_dir / "semantic_grid_l1.png")
img_sem_l2.save(brain_dir / "semantic_grid_l2.png")
img_sem_l25.save(brain_dir / "semantic_grid_l25.png")
img_sem_l3.save(brain_dir / "semantic_grid_l3.png")
img_sem_mrg.save(brain_dir / "semantic_grid_merged.png")
img_sem_mrg.save(skill_assets_dir / "kenshi_village_semantic_ssot_1280.png")

b64_sem_l1 = base64.b64encode((brain_dir / "semantic_grid_l1.png").read_bytes()).decode("utf-8")
b64_sem_l2 = base64.b64encode((brain_dir / "semantic_grid_l2.png").read_bytes()).decode("utf-8")
b64_sem_l25 = base64.b64encode((brain_dir / "semantic_grid_l25.png").read_bytes()).decode("utf-8")
b64_sem_l3 = base64.b64encode((brain_dir / "semantic_grid_l3.png").read_bytes()).decode("utf-8")
b64_sem_mrg = base64.b64encode((brain_dir / "semantic_grid_merged.png").read_bytes()).decode("utf-8")

# ==============================================================================
# 5. 更新全規格 HTML 報告
# ==============================================================================
html_content = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <title>🏰 戰術荒原 (0, 0) 邊境村落【全規格標準交付報告】</title>
    <style>
        :root {{
            --bg-dark: #0a0d12;
            --bg-card: #13171f;
            --text-main: #f0f6fc;
            --text-muted: #8b949e;
            --accent-gold: #f2c94c;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --border-color: #272f3d;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }}
        .container {{ max-width: 1440px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 24px; }}
        .badge {{
            background: rgba(242, 201, 76, 0.15);
            border: 1px solid var(--accent-gold);
            color: var(--accent-gold);
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        .tab-bar {{
            display: flex;
            justify-content: center;
            gap: 12px;
            margin: 18px 0;
        }}
        .tab-btn {{
            background: var(--bg-card);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            padding: 10px 22px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: 0.2s;
        }}
        .tab-btn.active {{
            background: var(--accent-gold);
            color: #000;
            border-color: var(--accent-gold);
        }}
        .grid-main {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 30px;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            margin-bottom: 24px;
        }}
        .card h3 {{ margin-top: 0; color: var(--accent-gold); font-size: 18px; }}
        
        .sandbox-container {{
            position: relative;
            width: 100%;
            aspect-ratio: 1 / 1;
            background: #080a0e;
            border-radius: 8px;
            border: 1px solid #333;
            overflow: hidden;
            cursor: zoom-in;
        }}
        .layer-canvas {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            transition: opacity 0.2s ease;
        }}
        .controls-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            background: #0d1117;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            margin-top: 14px;
            align-items: center;
        }}
        .control-label {{
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            user-select: none;
        }}
        
        .semantic-tabs {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }}
        .sem-tab-btn {{
            background: #1f242c;
            color: var(--text-muted);
            border: 1px solid var(--border-color);
            padding: 7px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s;
        }}
        .sem-tab-btn:hover {{ color: #fff; border-color: var(--accent-gold); }}
        .sem-tab-btn.active {{
            background: var(--accent-gold);
            color: #000;
            border-color: var(--accent-gold);
        }}
        
        .semantic-visual-container {{
            position: relative;
            width: 100%;
            aspect-ratio: 1 / 1;
            background: #080a0e;
            border-radius: 8px;
            border: 1px solid #333;
            overflow: hidden;
            cursor: zoom-in;
        }}
        .semantic-visual-img {{
            width: 100%;
            height: 100%;
            image-rendering: pixelated;
            image-rendering: crisp-edges;
        }}
        
        .tactical-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 12px;
        }}
        .tactical-table th, .tactical-table td {{
            padding: 8px 10px;
            border: 1px solid var(--border-color);
            text-align: left;
        }}
        .tactical-table th {{
            background: #1a202c;
            color: var(--accent-gold);
        }}
        .tactical-table tr:nth-child(even) {{ background: rgba(255, 255, 255, 0.02); }}
        
        .layers-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }}
        .layer-card {{
            background: #0d1117;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            cursor: zoom-in;
            transition: transform 0.2s, border-color 0.2s;
        }}
        .layer-card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent-gold);
        }}
        .layer-card img {{
            width: 100%;
            border-radius: 4px;
            background: #000;
            border: 1px solid #222;
            image-rendering: pixelated;
            image-rendering: crisp-edges;
        }}
        .layer-card-title {{
            font-size: 14px;
            font-weight: bold;
            color: var(--accent-gold);
            margin-bottom: 8px;
        }}
        
        .building-compare-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 14px;
        }}
        .bldg-box {{
            background: #0d1117;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            cursor: zoom-in;
        }}
        .bldg-box h4 {{ margin: 0 0 10px 0; color: var(--accent-blue); font-size: 15px; }}
        .bldg-box img {{
            width: 100%;
            border-radius: 6px;
            border: 1px solid #222;
            image-rendering: pixelated;
            image-rendering: crisp-edges;
        }}
        
        .lightbox-modal {{
            display: none;
            position: fixed;
            z-index: 9999;
            left: 0;
            top: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(0, 0, 0, 0.9);
            backdrop-filter: blur(8px);
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }}
        .lightbox-content {{
            position: relative;
            max-width: 90vw;
            max-height: 85vh;
            overflow: hidden;
            border: 2px solid var(--accent-gold);
            border-radius: 8px;
            background: #000;
            cursor: grab;
        }}
        .lightbox-content:active {{ cursor: grabbing; }}
        .lightbox-img {{
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            transform-origin: center center;
            transition: transform 0.05s ease-out;
            user-select: none;
            pointer-events: none;
        }}
        .lightbox-toolbar {{
            display: flex;
            gap: 14px;
            margin-top: 14px;
            background: #111;
            padding: 8px 18px;
            border-radius: 20px;
            border: 1px solid #333;
        }}
        .lb-btn {{
            background: #222;
            color: #fff;
            border: 1px solid #444;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }}
        .lb-btn:hover {{ background: var(--accent-gold); color: #000; }}
        .close-btn {{
            position: absolute;
            top: 20px;
            right: 24px;
            color: #fff;
            font-size: 32px;
            font-weight: bold;
            cursor: pointer;
        }}
        .close-btn:hover {{ color: var(--accent-gold); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏰 戰術荒原 (0, 0) 邊境村落【全規格標準交付報告】</h1>
            <p><span class="badge">Base64 100% 內嵌 • 屋頂與店內空間語意解耦 • 自然人字瓦簷 • Lightbox 800% 放大</span></p>
        </div>

        <!-- 頂部視圖切換 -->
        <div class="tab-bar">
            <button class="tab-btn active" onclick="switchMainState('ext')">🏠 【進去前·外觀層全景 (Roofs ON·人字瓦簷/半木外牆/加固大門/大招牌)】</button>
            <button class="tab-btn" onclick="switchMainState('int')">🚪 【進去後·店內層全景 (Roofs OFF·人字拼地板/流蘇地毯/吧台/壁爐)】</button>
        </div>

        <!-- 主體 1:1 雙沙盒對比 -->
        <div class="grid-main">
            <!-- 左側：即時圖層疊加檢驗沙盒 -->
            <div class="card">
                <h3>🎛️ 1. 遊戲視覺圖層疊加檢驗 (點擊進入 Lightbox 800% 像素放大)</h3>
                <div class="sandbox-container" onclick="openCurrentSandbox()">
                    <img id="layer1-img" class="layer-canvas" src="data:image/png;base64,{b64_l1}" alt="Layer 1">
                    <img id="layer2-img" class="layer-canvas" src="data:image/png;base64,{b64_l2}" alt="Layer 2">
                    <img id="layer25-img" class="layer-canvas" src="data:image/png;base64,{b64_l25}" alt="Layer 2.5">
                    <img id="layer3-img" class="layer-canvas" src="data:image/png;base64,{b64_l3}" alt="Layer 3">
                </div>

                <div class="controls-bar">
                    <span style="color: var(--accent-gold); font-size: 13px; font-weight: bold;">圖層開關：</span>
                    <label class="control-label"><input type="checkbox" id="chk-l1" checked onchange="toggleLayer('l1')"> 🏜️ Layer 1 自然底地</label>
                    <label class="control-label"><input type="checkbox" id="chk-l2" checked onchange="toggleLayer('l2')"> 🏬 Layer 2 建築店內地基層 (無死板橫線)</label>
                    <label class="control-label"><input type="checkbox" id="chk-l25" checked onchange="toggleLayer('l25')"> 🪵 Layer 2.5 環境雜物</label>
                    <label class="control-label"><input type="checkbox" id="chk-l3" checked onchange="toggleLayer('l3')"> 🛖 Layer 3 人字瓦簷屋頂 ＆ 3D 招牌</label>
                </div>
            </div>

            <!-- 右側：分層視覺化語意圖 -->
            <div class="card">
                <h3>📑 2. 每格文字標籤分層視覺化語意圖 (空間語意徹底解耦 SSOT)</h3>
                <div class="semantic-tabs">
                    <button class="sem-tab-btn active" onclick="switchSemView('mrg')">🌟 綜合全景語意 (SSOT)</button>
                    <button class="sem-tab-btn" onclick="switchSemView('l1')">Layer 1 底地語意</button>
                    <button class="sem-tab-btn" onclick="switchSemView('l2')">Layer 2 店內地基語意</button>
                    <button class="sem-tab-btn" onclick="switchSemView('l25')">Layer 2.5 雜物語意</button>
                    <button class="sem-tab-btn" onclick="switchSemView('l3')">Layer 3 屋頂懸垂語意</button>
                </div>
                <div class="semantic-visual-container" onclick="openCurrentSemLightbox()">
                    <img id="sem-visual-img" class="semantic-visual-img" src="data:image/png;base64,{b64_sem_mrg}" alt="Visual Semantic Grid">
                </div>
                <div style="font-size: 12px; color: var(--accent-gold); margin-top: 10px;">
                    🔍 <b>屋頂語意 [▲頂] 嚴格獨立於上部懸垂區，店內層 [店地]/[酒地]/[門口] 獨立於下方佔地區！</b>
                </div>
            </div>
        </div>

        <!-- 區塊二：語意文字標籤全索引與戰術屬性對照表 -->
        <div class="card">
            <h3>📊 3. 語意文字標籤全索引與戰術屬性對照表 (Tactical Custom Data Layer)</h3>
            <table class="tactical-table">
                <thead>
                    <tr>
                        <th>語意 Token</th>
                        <th>地形 / 建築名稱</th>
                        <th>AP 移動消耗</th>
                        <th>戰術掩體率 (Cover %)</th>
                        <th>通行規則 (Passability)</th>
                        <th>特殊戰術機制</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td><code>[沙]</code></td><td>自然沙質原野</td><td>1 AP</td><td>0% (無掩體)</td><td>全單位可通行</td><td>標準荒原地表</td></tr>
                    <tr><td><code>[路]</code></td><td>硬化黏土車轍小道</td><td>1 AP</td><td>0% (無掩體)</td><td>全單位可通行</td><td>輕微移動加成</td></tr>
                    <tr><td><code>[石]</code></td><td>中央生活石板廣場</td><td>1 AP</td><td>0% (無掩體)</td><td>全單位可通行</td><td>市集核心生活區</td></tr>
                    <tr><td><code>[田]</code></td><td>梯形農耕麥田</td><td>1.5 AP</td><td>20% (輕掩體)</td><td>全單位可通行</td><td>提供低矮遮蔽</td></tr>
                    <tr><td><code>[渠]</code></td><td>灌溉活水渠</td><td>不可通行</td><td>0%</td><td>僅飛行/浮空可跨</td><td>地面單位需繞行或走木橋</td></tr>
                    <tr><td><code>[酒地]</code> <code>[酒門]</code></td><td>西南大酒館店內層 (8x4 佔地)</td><td>1 AP (室內)</td><td>100% (實體掩體)</td><td>門口進出 / 室內可戰鬥</td><td>踏入門廊觸發 Roof_Fader 淡出屋頂</td></tr>
                    <tr><td><code>[▲酒頂]</code></td><td>酒館 3/4 俯視斜坡屋頂 (8x3 懸垂)</td><td>不可通行</td><td>100%</td><td>上方遮蔽層</td><td>進門時平滑淡出</td></tr>
                    <tr><td><code>[吧台]</code> <code>[壁爐]</code></td><td>酒館吧台與石壁爐</td><td>不可通行</td><td>75% (重掩體)</td><td>不可站立</td><td>可作為室內重掩體射擊</td></tr>
                    <tr><td><code>[鐵地]</code> <code>[鐵門]</code></td><td>東北鐵匠工坊店內層 (6x4 佔地)</td><td>1 AP (室內)</td><td>100% (實體掩體)</td><td>門口進出 / 室內可戰鬥</td><td>踏入門廊觸發 Roof_Fader 淡出屋頂</td></tr>
                    <tr><td><code>[▲鐵頂]</code></td><td>鐵匠 3/4 俯視斜坡屋頂 (6x2 懸垂)</td><td>不可通行</td><td>100%</td><td>上方遮蔽層</td><td>進門時平滑淡出</td></tr>
                    <tr><td><code>[武架]</code> <code>[鐵砧]</code></td><td>武器展示架與黑鋼砧</td><td>不可通行</td><td>75% (重掩體)</td><td>不可站立</td><td>提供近戰與射擊阻擋</td></tr>
                    <tr><td><code>[店地]</code> <code>[店門]</code></td><td>西北雜貨鋪店內層 (6x4 佔地)</td><td>1 AP (室內)</td><td>100% (實體掩體)</td><td>門口進出 / 室內可戰鬥</td><td>踏入門廊觸發 Roof_Fader 淡出屋頂</td></tr>
                    <tr><td><code>[▲店頂]</code></td><td>雜貨鋪 3/4 俯視屋頂 (6x2 懸垂)</td><td>不可通行</td><td>100%</td><td>上方遮蔽層</td><td>進門時平滑淡出</td></tr>
                    <tr><td><code>[藥架]</code> <code>[金箱]</code></td><td>藥水貨架與金庫箱</td><td>不可通行</td><td>50% (半掩體)</td><td>不可站立</td><td>提供半身掩護</td></tr>
                    <tr><td><code>[哨塔]</code> <code>[▲塔頂]</code></td><td>荒原守衛哨塔</td><td>不可通行</td><td>100%</td><td>阻擋通行</td><td>頂部提供 +2 射程視野優勢</td></tr>
                    <tr><td><code>[水井]</code></td><td>中央蓄水石井</td><td>不可通行</td><td>75% (重掩體)</td><td>不可站立</td><td>戰術掩體、水源互動點</td></tr>
                    <tr><td><code>[熔爐]</code></td><td>露天高溫鍛造爐</td><td>不可通行</td><td>75% (重掩體)</td><td>不可站立</td><td>高溫地形障礙</td></tr>
                    <tr><td><code>[果攤]</code> <code>[器攤]</code></td><td>市集帆布遮陽攤位</td><td>不可通行</td><td>50% (半掩體)</td><td>不可站立</td><td>集市遮蔽掩體</td></tr>
                </tbody>
            </table>
        </div>

        <!-- 區塊三：四大分層獨立分解圖 -->
        <div class="card">
            <h3>📐 4. 四大分層獨立分解圖 (Discrete Layer-by-Layer Views)</h3>
            <div class="layers-grid">
                <div class="layer-card" onclick="openLightboxImage('data:image/png;base64,{b64_l1}', 'Layer 1: 自然原野底地')">
                    <div class="layer-card-title">Layer 1: 自然原野底地</div>
                    <img src="data:image/png;base64,{b64_l1}" alt="Layer 1 Ground">
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">8 階沙地抖動、石板廣場、水渠、麥田</div>
                </div>

                <div class="layer-card" onclick="openLightboxImage('data:image/png;base64,{b64_l2}', 'Layer 2: 建築店內層 ＆ 本體')">
                    <div class="layer-card-title">Layer 2: 建築店內層 (佔地空間)</div>
                    <img src="data:image/png;base64,{b64_l2}" alt="Layer 2 Structures">
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">人字拼木地板、奢華紅地毯、炭火壁爐、多層兵器架</div>
                </div>

                <div class="layer-card" onclick="openLightboxImage('data:image/png;base64,{b64_l25}', 'Layer 2.5: 環境雜物佈置層')">
                    <div class="layer-card-title">Layer 2.5: 環境雜物佈置層</div>
                    <img src="data:image/png;base64,{b64_l25}" alt="Layer 2.5 Clutter">
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">碎石、乾草堆、木桶木箱、農莊雜物</div>
                </div>

                <div class="layer-card" onclick="openLightboxImage('data:image/png;base64,{b64_l3}', 'Layer 3: 自然人字瓦簷 ＆ 3D 招牌')">
                    <div class="layer-card-title">Layer 3: 人字瓦簷 ＆ 3D 招牌</div>
                    <img src="data:image/png;base64,{b64_l3}" alt="Layer 3 Roofs">
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">消除水平割線、自然人字瓦簷弧度、封簷木板</div>
                </div>
            </div>
        </div>

        <!-- 區塊四：建築「進去前 (外觀)」vs「進去後 (店內層)」1:1 對比 -->
        <div class="card">
            <h3>🚪 5. 建築「進去前 (完整外觀)」vs「進去後 (店內層)」屋頂透視對比</h3>
            <div class="building-compare-grid">
                <div class="bldg-box" onclick="openLightboxImage('data:image/png;base64,{b64_ext}', '進去前·全村落外觀層 (Roofs ON)')">
                    <h4>🏠 進去前狀態 (完整外觀層·Roofs ON)：</h4>
                    <img src="data:image/png;base64,{b64_ext}" alt="Exterior State">
                    <div style="font-size: 13px; color: var(--text-muted); margin-top: 8px;">
                        • <b>自然人字瓦簷 (無死板水平線！)</b>：屋簷中央微垂 ＋ 封簷板 ＋ 投影落影，消除生硬橫線！<br>
                        • <b>半木構造立面牆</b>：垂直主樑 ＋ 角石 ＋ 雙開加固厚木門 ＋ 鉛條格子窗！<br>
                        • <b>3D 立體雕花大招牌</b>：鍛鐵雕花懸臂支架 ＋ 鍍金邊框與金屬立體 Logo！
                    </div>
                </div>

                <div class="bldg-box" onclick="openLightboxImage('data:image/png;base64,{b64_int}', '進去後·店內層全景 (Roofs OFF)')">
                    <h4>🚪 進去後狀態 (店內層·Roofs OFF / Faded)：</h4>
                    <img src="data:image/png;base64,{b64_int}" alt="Interior State">
                    <div style="font-size: 13px; color: var(--text-muted); margin-top: 8px;">
                        • <b>佔地空間語意嚴格分離</b>：屋頂淡出後露出完整的室內戰鬥地磚！<br>
                        • <b>大酒館</b>：人字拼木地板 ＋ 奢華紅地毯 ＋ 石砌炭火壁爐 ＋ L型吧台 ＋ 宴席長桌！<br>
                        • <b>鐵匠鋪</b>：淬火水桶 ＋ 磨刀砂輪 ＋ 兵器展示架 ＋ 鎖子甲人偶 ＋ 黑鋼鐵砧！<br>
                        • <b>雜貨鋪</b>：五彩魔藥貨架 ＋ 黃金天秤櫃台 ＋ 寶石金幣藏寶箱！
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Lightbox 模態框 -->
    <div id="lightbox" class="lightbox-modal">
        <span class="close-btn" onclick="closeLightbox()">&times;</span>
        <div id="lb-container" class="lightbox-content" onwheel="onZoom(event)" onmousedown="onPanStart(event)">
            <img id="lb-image" class="lightbox-img" src="" alt="Lightbox View">
        </div>
        <div class="lightbox-toolbar">
            <button class="lb-btn" onclick="adjustZoom(0.25)">🔍 放大 (+)</button>
            <button class="lb-btn" onclick="adjustZoom(-0.25)">🔍 縮小 (-)</button>
            <button class="lb-btn" onclick="resetZoom()">🔄 重設 (100%)</button>
            <span id="zoom-text" style="color: var(--accent-gold); font-size: 13px; font-weight: bold; align-self: center;">100%</span>
        </div>
    </div>

    <script>
        const semImages = {{
            'mrg': "data:image/png;base64,{b64_sem_mrg}",
            'l1': "data:image/png;base64,{b64_sem_l1}",
            'l2': "data:image/png;base64,{b64_sem_l2}",
            'l25': "data:image/png;base64,{b64_sem_l25}",
            'l3': "data:image/png;base64,{b64_sem_l3}"
        }};

        let currentSemKey = 'mrg';

        function switchSemView(layerKey) {{
            currentSemKey = layerKey;
            document.getElementById('sem-visual-img').src = semImages[layerKey];
            const btns = document.querySelectorAll('.sem-tab-btn');
            btns.forEach(b => b.classList.remove('active'));
            if (layerKey === 'mrg') btns[0].classList.add('active');
            if (layerKey === 'l1') btns[1].classList.add('active');
            if (layerKey === 'l2') btns[2].classList.add('active');
            if (layerKey === 'l25') btns[3].classList.add('active');
            if (layerKey === 'l3') btns[4].classList.add('active');
        }}

        function openCurrentSemLightbox() {{
            openLightboxImage(semImages[currentSemKey], "視覺化語意圖 (" + currentSemKey + ")");
        }}

        function toggleLayer(layer) {{
            const el = document.getElementById(layer === 'l1' ? 'layer1-img' : layer === 'l2' ? 'layer2-img' : layer === 'l25' ? 'layer25-img' : 'layer3-img');
            const chk = document.getElementById(layer === 'l1' ? 'chk-l1' : layer === 'l2' ? 'chk-l2' : layer === 'l25' ? 'chk-l25' : 'chk-l3');
            el.style.opacity = chk.checked ? '1' : '0';
        }}

        function switchMainState(state) {{
            const chkRoof = document.getElementById('chk-l3');
            const btns = document.querySelectorAll('.tab-btn');
            btns.forEach(b => b.classList.remove('active'));
            if (state === 'ext') {{
                chkRoof.checked = true;
                toggleLayer('l3');
                btns[0].classList.add('active');
            }} else {{
                chkRoof.checked = false;
                toggleLayer('l3');
                btns[1].classList.add('active');
            }}
        }}

        let currentScale = 1;
        let isPanning = false;
        let startX, startY, translateX = 0, translateY = 0;

        function openCurrentSandbox() {{
            const chkRoof = document.getElementById('chk-l3');
            openLightboxImage(chkRoof.checked ? "data:image/png;base64,{b64_ext}" : "data:image/png;base64,{b64_int}", "沙盒當前視圖");
        }}

        function openLightboxImage(src, title) {{
            const lb = document.getElementById('lightbox');
            const img = document.getElementById('lb-image');
            img.src = src;
            resetZoom();
            lb.style.display = 'flex';
        }}

        function closeLightbox() {{
            document.getElementById('lightbox').style.display = 'none';
        }}

        function onZoom(e) {{
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.25 : -0.25;
            adjustZoom(delta);
        }}

        function adjustZoom(delta) {{
            currentScale = Math.max(0.5, Math.min(8.0, currentScale + delta));
            updateTransform();
        }}

        function resetZoom() {{
            currentScale = 1;
            translateX = 0;
            translateY = 0;
            updateTransform();
        }}

        function updateTransform() {{
            const img = document.getElementById('lb-image');
            img.style.transform = `scale(${{currentScale}}) translate(${{translateX}}px, ${{translateY}}px)`;
            document.getElementById('zoom-text').innerText = Math.round(currentScale * 100) + '%';
        }}

        function onPanStart(e) {{
            if (currentScale <= 1) return;
            isPanning = true;
            startX = e.clientX - translateX * currentScale;
            startY = e.clientY - translateY * currentScale;
            window.addEventListener('mousemove', onPanMove);
            window.addEventListener('mouseup', onPanEnd);
        }}

        function onPanMove(e) {{
            if (!isPanning) return;
            translateX = (e.clientX - startX) / currentScale;
            translateY = (e.clientY - startY) / currentScale;
            updateTransform();
        }}

        function onPanEnd() {{
            isPanning = false;
            window.removeEventListener('mousemove', onPanMove);
            window.removeEventListener('mouseup', onPanEnd);
        }}
    </script>
</body>
</html>
"""

report_file = brain_dir / "map_delivery_report_0_0.html"
report_file.write_text(html_content, encoding="utf-8")
shutil.copy2(report_file, reports_dir / "map_delivery_report_0_0_village.html")

print("Fixed roof semantics spatial decoupling and eliminated straight horizontal roof cut lines!")
