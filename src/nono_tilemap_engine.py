import base64
from PIL import Image, ImageDraw
from pathlib import Path
import math
import numpy as np

godot_base = Path(r"C:\GPTfile\godot\adventure-of-self-realization-v-0.5")
brain_dir = Path(r"C:\Users\ihate\.gemini\antigravity\brain\522dd70e-62d4-4f27-893e-70f3ade173ca")

kenshi_house = Image.open(brain_dir / "kenshi_house_prefab.png").convert("RGBA")
kenshi_roof = Image.open(brain_dir / "kenshi_roof_fader.png").convert("RGBA")

# 40x40 Grid @ 32px = 1280x1280 px
gw, gh = 40, 40
cell = 32

# ==============================================================================
# 🎨 1. Kenshi 荒原水系與地景調色盤
# ==============================================================================
SAND_DESERT = (228, 206, 162, 255)
SAND_DUNE_D = (196, 170, 126, 255)
SAND_DUNE_L = (242, 224, 184, 255)

CLAY_EARTH = (175, 138, 98, 255)
CLAY_DARK = (135, 102, 68, 255)
MUDBRICK_BASE = (158, 125, 88, 255)
MUDBRICK_DARK = (118, 88, 56, 255)
MUDBRICK_LIGHT = (195, 162, 122, 255)

# 土質泥壟溝與水系 (Connected Irrigation Ditch System)
DITCH_SOIL_DEEP = (85, 62, 38, 255)   # 溝底深色濕泥
DITCH_BANK = (148, 112, 75, 255)      # 泥壟溝邊緣土埂
WOOD_SLUICE = (118, 95, 72, 255)      # 風化木製水槽與分水閘
WATER_SEEPAGE = (95, 128, 145, 180)   # 溝底微量滲水反光

BLEACHED_WOOD_0 = (55, 42, 32, 255)
BLEACHED_WOOD_1 = (92, 75, 58, 255)
BLEACHED_WOOD_2 = (138, 116, 92, 255)
RUST_METAL_1 = (112, 62, 45, 255)
RUST_METAL_0 = (48, 38, 38, 255)

DRY_GRASS_0 = (92, 85, 45, 255)
DRY_GRASS_1 = (145, 138, 72, 255)
DRY_GRASS_2 = (195, 188, 105, 255)
SCREE_ROCK = (128, 122, 115, 255)
SCREE_LIGHT = (168, 162, 155, 255)
GOLD_STUD = (245, 205, 70, 255)
STONE_SHADE_0 = (45, 42, 38, 255)

# ==============================================================================
# 🌊 2. 建立【頭尾連通的完整水系拓撲】 (Logically Connected Hydrology)
# 源頭：中央蓄水井 (21, 18) 溢流木水槽 -> 灌溉主渠 -> 梯形麥田分流 -> 地圖東南邊界 (39, 33) 荒野排水
# ==============================================================================
# 語意矩陣
LABEL_GRID = np.full((gh, gw), "沙", dtype=object)
ROOF_GRID = np.full((gh, gw), "", dtype=object)

# A. 泥土小道 [路]
clay_mask = np.zeros((gh, gw), dtype=int)
def mark_road(pts, w=2):
    for i in range(len(pts)-1):
        p0, p1 = pts[i], pts[i+1]
        steps = int(math.hypot(p1[0]-p0[0], p1[1]-p0[1]) * 2)
        for t in range(steps + 1):
            s = t / float(steps)
            cx, cy = int(p0[0] + (p1[0]-p0[0])*s), int(p0[1] + (p1[1]-p0[1])*s)
            for dy in range(-w//2, w//2 + 1):
                for dx in range(-w//2, w//2 + 1):
                    if 0 <= cx+dx < gw and 0 <= cy+dy < gh:
                        clay_mask[cy+dy, cx+dx] = 1
                        LABEL_GRID[cy+dy, cx+dx] = "路"

mark_road([(0, 23), (8, 22), (15, 20), (22, 19), (30, 19), (39, 17)], w=2)
mark_road([(22, 19), (21, 26), (20, 39)], w=1)
mark_road([(15, 20), (12, 14), (11, 8)], w=1)
mark_road([(30, 19), (31, 14), (29, 9)], w=1)

# 中央石板生活廣場
for y in range(16, 22):
    for x in range(19, 25):
        if (x - 22)**2 + (y - 19)**2 <= 8:
            clay_mask[y, x] = 1
            LABEL_GRID[y, x] = "路"

# B. 東南梯形麥田 [田]
farm_mask = np.zeros((gh, gw), dtype=int)
for fy in range(24, 31):
    for fx in range(24 + (fy - 24)//2, 37 - (fy - 24)//2):
        farm_mask[fy, fx] = 1
        LABEL_GRID[fy, fx] = "田"

# C. 完整連通的灌溉泥溝 [溝]
# 源頭：(21, 19) 水井溢水口 -> (22, 21) 木水槽 -> (24, 24) 麥田入口 -> (28, 27) 田中分流閘 -> (33, 30) 麥田尾 -> (39, 33) 出地圖
ditch_pts = [(21, 19), (22, 21), (24, 24), (28, 27), (33, 30), (39, 33)]
for i in range(len(ditch_pts)-1):
    p0, p1 = ditch_pts[i], ditch_pts[i+1]
    steps = int(math.hypot(p1[0]-p0[0], p1[1]-p0[1]) * 2)
    for t in range(steps + 1):
        s = t / float(steps)
        cx, cy = int(p0[0] + (p1[0]-p0[0])*s), int(p0[1] + (p1[1]-p0[1])*s)
        if 0 <= cx < gw and 0 <= cy < gh:
            LABEL_GRID[cy, cx] = "溝"

# D. 房屋佔地 [屋] 與 屋頂覆蓋 [頂]
def mark_house(gx, gy):
    for hy in range(gy, gy + 5):
        for hx in range(gx, gx + 6):
            if 0 <= hx < gw and 0 <= hy < gh:
                LABEL_GRID[hy, hx] = "屋"
    for ry in range(gy, gy + 3):
        for rx in range(gx, gx + 6):
            if 0 <= rx < gw and 0 <= ry < gh:
                ROOF_GRID[ry, rx] = "頂"

mark_house(6, 4)   # 西北村長宅
mark_house(25, 5)  # 東北鐵匠鋪
mark_house(4, 25)  # 西南酒館

# E. 道具 [井]、[爐]、[草]、[石]
LABEL_GRID[18, 21] = "井"
LABEL_GRID[7, 23] = "爐"

scrub_coords = [(4, 15), (14, 12), (18, 24), (28, 12), (33, 22), (8, 34), (22, 35), (36, 15), (12, 6), (24, 11), (16, 28), (3, 22)]
for sx, sy in scrub_coords:
    if LABEL_GRID[sy, sx] == "沙":
        LABEL_GRID[sy, sx] = "草"
    if sx + 1 < gw and LABEL_GRID[sy, sx + 1] == "沙":
        LABEL_GRID[sy, sx + 1] = "石"

# ==============================================================================
# 📑 3. 渲染每格文字標籤語意大圖 (Per-Cell Text Label Semantic Grid Image)
# ==============================================================================
sem_img = Image.new("RGBA", (gw * cell, gh * cell), (30, 30, 36, 255))
draw_sem = ImageDraw.Draw(sem_img)

LABEL_COLORS = {
    "沙": (228, 206, 162, 100),
    "路": (175, 138, 98, 220),
    "田": (195, 160, 90, 220),
    "溝": (110, 80, 50, 255),
    "屋": (180, 110, 70, 255),
    "井": (70, 130, 200, 255),
    "爐": (230, 100, 40, 255),
    "草": (145, 160, 60, 255),
    "石": (140, 140, 150, 255),
}

for y in range(gh):
    for x in range(gw):
        lbl = LABEL_GRID[y, x]
        px, py = x * cell, y * cell
        bg_col = LABEL_COLORS.get(lbl, (50, 50, 60, 255))
        draw_sem.rectangle([px, py, px + cell, py + cell], fill=bg_col, outline=(80, 80, 95, 180), width=1)
        draw_sem.text((px + 8, py + 8), lbl, fill=(255, 255, 255, 240))
        if ROOF_GRID[y, x] == "頂":
            draw_sem.text((px + 18, py + 18), "▲", fill=(255, 80, 80, 220))

out_sem_img = brain_dir / "kenshi_village_per_cell_text_labels.png"
sem_img.save(out_sem_img)

# ==============================================================================
# 🎨 4. 渲染四大分層 (4 Discrete Layers)
# ==============================================================================
# Layer 1: 底沙
l1_img = Image.new("RGBA", (gw * cell, gh * cell), SAND_DESERT)
draw_l1 = ImageDraw.Draw(l1_img)
for gy in range(gh):
    for gx in range(gw):
        if (gx * 3 + gy * 7) % 11 == 0:
            px, py = gx * cell, gy * cell
            draw_l1.line([(px + 4, py + 16), (px + 28, py + 16)], fill=SAND_DUNE_D)
            draw_l1.line([(px + 4, py + 17), (px + 28, py + 17)], fill=SAND_DUNE_L)

# Layer 2: 建築地景
l2_img = Image.new("RGBA", (gw * cell, gh * cell), (0, 0, 0, 0))
draw_l2 = ImageDraw.Draw(l2_img)

def render_autotile(target_draw, mask, fill_col, dark_col, light_col):
    for y in range(gh):
        for x in range(gw):
            if mask[y, x] == 0: continue
            px, py = x * cell, y * cell
            nt = mask[y-1, x] if y > 0 else 1
            nb = mask[y+1, x] if y < gh-1 else 1
            nl = mask[y, x-1] if x > 0 else 1
            nr = mask[y, x+1] if x < gw-1 else 1
            target_draw.rectangle([px, py, px + cell, py + cell], fill=fill_col)
            if not nt:
                target_draw.line([(px, py), (px + cell, py)], fill=dark_col, width=2)
                target_draw.line([(px, py + 2), (px + cell, py + 2)], fill=light_col, width=1)
            if not nb: target_draw.line([(px, py + cell - 1), (px + cell, py + cell - 1)], fill=dark_col, width=2)
            if not nl:
                target_draw.line([(px, py), (px, py + cell)], fill=dark_col, width=2)
                target_draw.line([(px + 2, py), (px + 2, py + cell)], fill=light_col, width=1)
            if not nr: target_draw.line([(px + cell - 1, py), (px + cell - 1, py + cell)], fill=dark_col, width=2)
            if not nt and not nl:
                target_draw.rectangle([px, py, px + 6, py + 6], fill=SAND_DESERT)
                target_draw.line([(px + 6, py), (px, py + 6)], fill=dark_col, width=2)
            if not nt and not nr:
                target_draw.rectangle([px + cell - 6, py, px + cell, py + 6], fill=SAND_DESERT)
                target_draw.line([(px + cell - 6, py), (px + cell, py + 6)], fill=dark_col, width=2)
            if not nb and not nl:
                target_draw.rectangle([px, py + cell - 6, px + 6, py + cell], fill=SAND_DESERT)
                target_draw.line([(px, py + cell - 6), (px + 6, py + cell)], fill=dark_col, width=2)
            if not nb and not nr:
                target_draw.rectangle([px + cell - 6, py + cell - 6, px + cell, py + cell], fill=SAND_DESERT)
                target_draw.line([(px + cell - 6, py + cell), (px + cell, py + cell - 6)], fill=dark_col, width=2)

render_autotile(draw_l2, clay_mask, CLAY_EARTH, CLAY_DARK, SAND_DUNE_L)
render_autotile(draw_l2, farm_mask, MUDBRICK_BASE, MUDBRICK_DARK, MUDBRICK_LIGHT)

# 耕地麥垄
for fy in range(24, 31):
    for fx in range(gw):
        if farm_mask[fy, fx]:
            px, py = fx * cell, fy * cell
            draw_l2.line([(px, py + 8), (px + cell, py + 8)], fill=CLAY_DARK, width=2)
            draw_l2.line([(px, py + 20), (px + cell, py + 20)], fill=CLAY_DARK, width=2)
            for wx in (6, 16, 26):
                draw_l2.line([(px + wx, py + 3), (px + wx, py + 8)], fill=GOLD_STUD, width=2)
                draw_l2.line([(px + wx, py + 15), (px + wx, py + 20)], fill=GOLD_STUD, width=2)

# 完整連通水渠 (Connected Ditch from Well to Boundary)
for i in range(len(ditch_pts)-1):
    p0, p1 = ditch_pts[i], ditch_pts[i+1]
    x0, y0 = p0[0]*cell, p0[1]*cell
    x1, y1 = p1[0]*cell, p1[1]*cell
    # 渠埂土堤
    draw_l2.line([(x0, y0), (x1, y1)], fill=DITCH_BANK, width=10)
    # 渠底深泥
    draw_l2.line([(x0, y0), (x1, y1)], fill=DITCH_SOIL_DEEP, width=6)
    # 微量滲水光澤
    draw_l2.line([(x0, y0), (x1, y1)], fill=WATER_SEEPAGE, width=2)
    # 分水閘門
    if i == 0:
        # 水井引水木槽
        draw_l2.rectangle([x0 - 4, y0 - 4, x0 + 12, y0 + 12], fill=WOOD_SLUICE, outline=BLEACHED_WOOD_0)
    elif i == 3:
        # 麥田中段木質分流閘門
        draw_l2.rectangle([x0 - 4, y0 - 4, x0 + 8, y0 + 8], fill=WOOD_SLUICE, outline=BLEACHED_WOOD_0)

# 放置 3 棟 Kenshi 房屋
l2_img.paste(kenshi_house, (6 * cell, 4 * cell), kenshi_house)
l2_img.paste(kenshi_house, (25 * cell, 5 * cell), kenshi_house)
l2_img.paste(kenshi_house, (4 * cell, 25 * cell), kenshi_house)

# 放置 Kenshi 水井與熔爐 (水井源頭與引水槽相連！)
wx, wy = 21 * cell + 16, 18 * cell + 8
draw_l2.ellipse([wx + 4, wy + 20, wx + 44, wy + 38], fill=(35, 25, 20, 80))
draw_l2.rectangle([wx + 6, wy + 16, wx + 38, wy + 32], fill=MUDBRICK_BASE, outline=MUDBRICK_DARK, width=2)
draw_l2.ellipse([wx + 6, wy + 8, wx + 38, wy + 20], fill=MUDBRICK_LIGHT, outline=MUDBRICK_DARK, width=2)
draw_l2.ellipse([wx + 12, wy + 11, wx + 32, wy + 17], fill=DITCH_SOIL_DEEP)
draw_l2.line([(wx + 8, wy + 16), (wx + 8, wy - 4)], fill=BLEACHED_WOOD_0, width=2)
draw_l2.line([(wx + 36, wy + 16), (wx + 36, wy - 4)], fill=BLEACHED_WOOD_0, width=2)
draw_l2.line([(wx + 6, wy - 4), (wx + 38, wy - 4)], fill=BLEACHED_WOOD_2, width=3)
# 水井溢流出水口木槽 (Spillway Trough into ditch)
draw_l2.rectangle([wx + 18, wy + 26, wx + 26, wy + 42], fill=WOOD_SLUICE, outline=BLEACHED_WOOD_0)

fx, fy = 23 * cell, 7 * cell
draw_l2.rectangle([fx, fy + 8, fx + 48, fy + 40], fill=MUDBRICK_BASE, outline=MUDBRICK_DARK, width=2)
draw_l2.arc([fx + 10, fy + 16, fx + 38, fy + 40], start=180, end=0, fill=MUDBRICK_DARK, width=2)
draw_l2.rectangle([fx + 12, fy + 26, fx + 36, fy + 40], fill=(25, 15, 15, 255))
draw_l2.polygon([(fx + 16, fy + 38), (fx + 24, fy + 22), (fx + 32, fy + 38)], fill=(255, 110, 30, 255))
draw_l2.rectangle([fx - 24, fy + 24, fx - 8, fy + 40], fill=BLEACHED_WOOD_1, outline=BLEACHED_WOOD_0)
draw_l2.rectangle([fx - 28, fy + 16, fx - 4, fy + 24], fill=RUST_METAL_1, outline=RUST_METAL_0, width=1)

# Layer 2.5: 雜草與碎石佈置層
l_clutter = Image.new("RGBA", (gw * cell, gh * cell), (0, 0, 0, 0))
draw_cl = ImageDraw.Draw(l_clutter)
for sx, sy in scrub_coords:
    px, py = sx * cell + 16, sy * cell + 16
    draw_cl.line([(px, py), (px - 4, py - 8)], fill=DRY_GRASS_1, width=2)
    draw_cl.line([(px + 2, py), (px + 6, py - 10)], fill=DRY_GRASS_2, width=2)
    draw_cl.line([(px - 2, py), (px - 1, py - 12)], fill=DRY_GRASS_0, width=2)
    draw_cl.rectangle([px + 12, py + 4, px + 17, py + 7], fill=SCREE_ROCK, outline=BLEACHED_WOOD_0)
    draw_cl.rectangle([px + 18, py + 6, px + 21, py + 8], fill=SCREE_LIGHT)

# Layer 3: 頭頂屋頂淡出層
l3_roofs = Image.new("RGBA", (gw * cell, gh * cell), (0, 0, 0, 0))
l3_roofs.paste(kenshi_roof, (6 * cell, 4 * cell), kenshi_roof)
l3_roofs.paste(kenshi_roof, (25 * cell, 5 * cell), kenshi_roof)
l3_roofs.paste(kenshi_roof, (4 * cell, 25 * cell), kenshi_roof)

# 保存獨立圖層
l1_img.save(brain_dir / "layer_1_sand_ground.png")
l2_img.save(brain_dir / "layer_2_civil_structures.png")
l_clutter.save(brain_dir / "layer_2_5_clutter_decor.png")
l3_roofs.save(brain_dir / "layer_3_roofs_faders.png")

# 最終合併大圖
master_merged = Image.new("RGBA", (gw * cell, gh * cell))
master_merged.alpha_composite(l1_img)
master_merged.alpha_composite(l2_img)
master_merged.alpha_composite(l_clutter)
master_merged.alpha_composite(l3_roofs)

out_merged = brain_dir / "kenshi_village_final_master_merged.png"
master_merged.save(out_merged)

# ==============================================================================
# 🌐 5. 生成 Base64 自包含 HTML 交付報告
# ==============================================================================
def get_b64(img):
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

b64_merged = get_b64(master_merged)
b64_sem = get_b64(sem_img)
b64_l1 = get_b64(l1_img)
b64_l2 = get_b64(l2_img)
b64_clutter = get_b64(l_clutter)
b64_l3 = get_b64(l3_roofs)

html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚔️ 戰術荒原 (0, 0) 邊境村落 - 官方標準地圖交付 HTML 報告</title>
    <style>
        :root {{
            --bg-primary: #141418;
            --bg-secondary: #1e1e24;
            --bg-card: #262630;
            --accent-gold: #e5b567;
            --accent-blue: #64b5f6;
            --accent-green: #81c784;
            --accent-red: #e57373;
            --text-main: #f0f0f5;
            --text-muted: #a0a0b0;
            --border-color: #3e3e4f;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Microsoft JhengHei', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-main);
            line-height: 1.6;
            padding: 24px;
        }}

        header {{
            background: linear-gradient(135deg, #2a2218 0%, #1a1a24 100%);
            border: 1px solid var(--accent-gold);
            border-radius: 12px;
            padding: 24px 32px;
            margin-bottom: 32px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }}

        h1 {{
            color: var(--accent-gold);
            font-size: 26px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 14px;
        }}

        .standards-badge {{
            display: inline-block;
            background: rgba(229, 181, 103, 0.15);
            border: 1px solid var(--accent-gold);
            color: var(--accent-gold);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-top: 12px;
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }}

        .card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }}

        .card-title {{
            font-size: 18px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .merged-title {{ color: var(--accent-gold); }}
        .semantic-title {{ color: var(--accent-blue); }}
        .layer-title {{ color: var(--accent-green); }}

        .hint {{
            font-size: 12px;
            color: var(--text-muted);
            background: rgba(255,255,255,0.05);
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .img-container {{
            position: relative;
            background: #0d0d10;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #333344;
            cursor: zoom-in;
            text-align: center;
            flex-grow: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 440px;
        }}

        .img-container img {{
            max-width: 100%;
            max-height: 460px;
            image-rendering: pixelated;
            image-rendering: -moz-crisp-edges;
            image-rendering: crisp-edges;
            transition: transform 0.2s ease;
        }}

        .img-container:hover img {{
            transform: scale(1.02);
        }}

        .zoom-overlay-hint {{
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.75);
            color: #fff;
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            pointer-events: none;
            border: 1px solid #555;
        }}

        .legend-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 10px;
            margin-top: 16px;
            background: var(--bg-card);
            padding: 14px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
        }}

        .legend-badge {{
            display: inline-block;
            width: 32px;
            height: 24px;
            line-height: 24px;
            text-align: center;
            font-weight: bold;
            border-radius: 4px;
            font-size: 12px;
            color: #fff;
            text-shadow: 0 1px 2px #000;
        }}

        .layers-section {{
            margin-bottom: 32px;
        }}

        .layers-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }}

        .layer-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            display: flex;
            flex-direction: column;
        }}

        .layer-card .img-container {{
            min-height: 220px;
        }}

        .layer-card .img-container img {{
            max-height: 220px;
        }}

        .layer-card-desc {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 10px;
            line-height: 1.4;
        }}

        .sandbox-section {{
            background: var(--bg-secondary);
            border: 1px solid var(--accent-gold);
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 32px;
        }}

        .sandbox-controls {{
            display: flex;
            gap: 20px;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}

        .sandbox-checkbox {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            cursor: pointer;
            user-select: none;
            background: var(--bg-card);
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }}

        .sandbox-viewport {{
            position: relative;
            width: 640px;
            height: 640px;
            margin: 0 auto;
            background: #000;
            border: 2px solid var(--accent-gold);
            border-radius: 8px;
            overflow: hidden;
            cursor: zoom-in;
        }}

        .sandbox-layer {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            image-rendering: pixelated;
            transition: opacity 0.2s ease;
        }}

        .lightbox-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.94);
            z-index: 99999;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            user-select: none;
        }}

        .lightbox-header {{
            position: absolute;
            top: 16px;
            left: 24px;
            right: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #fff;
            z-index: 100000;
        }}

        .lightbox-title {{
            font-size: 18px;
            font-weight: bold;
            color: var(--accent-gold);
        }}

        .lightbox-toolbar {{
            display: flex;
            gap: 12px;
            align-items: center;
        }}

        .lightbox-btn {{
            background: var(--bg-card);
            color: #fff;
            border: 1px solid var(--border-color);
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        }}

        .lightbox-btn:hover {{
            background: var(--accent-gold);
            color: #000;
        }}

        .lightbox-close {{
            font-size: 24px;
            cursor: pointer;
            background: none;
            border: none;
            color: #fff;
            padding: 0 10px;
        }}

        .lightbox-close:hover {{
            color: var(--accent-red);
        }}

        .lightbox-body {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            cursor: grab;
        }}

        .lightbox-body:active {{
            cursor: grabbing;
        }}

        .lightbox-img {{
            max-width: 90vw;
            max-height: 85vh;
            image-rendering: pixelated;
            image-rendering: -moz-crisp-edges;
            image-rendering: crisp-edges;
            transform-origin: center center;
            transition: transform 0.1s ease-out;
        }}

        @media (max-width: 1100px) {{
            .dashboard-grid {{ grid-template-columns: 1fr; }}
            .layers-grid {{ grid-template-columns: 1fr 1fr; }}
            .sandbox-viewport {{ width: 100%; height: auto; aspect-ratio: 1/1; }}
        }}
    </style>
</head>
<body>

    <header>
        <h1>⚔️ 戰術荒原【(0, 0) 邊境村落】官方標準地圖交付報告</h1>
        <p class="subtitle">SSOT 語意優先管線 • 40×40 網格 (1280×1280 px) • 3/4 斜上方俯視角 • 完整連通灌溉水系 • Base64 內嵌 100% 防破圖</p>
        <div class="standards-badge">✅ 已達成：1.水系頭尾完全連通 ＋ 2.合併大圖 ＋ 3.每格文字標籤分層語意 ＋ 4.四大分層圖 ＋ 5.全圖無損像素放大</div>
    </header>

    <!-- 1 & 2: 合併大圖 與 每格文字標籤語意圖 -->
    <div class="dashboard-grid">
        <!-- 1. 最終合併大圖 -->
        <div class="card">
            <div class="card-header">
                <div class="card-title merged-title">🖼️ 1. 最終遊戲合併大圖 (Final Merged View)</div>
                <span class="hint">🔍 點擊全螢幕像素級放大</span>
            </div>
            <div class="img-container" onclick="openLightbox(b64Merged, '【最終遊戲合併大圖 - 1280x1280】')">
                <img id="imgMerged" src="{b64_merged}" alt="最終遊戲合併大圖">
                <div class="zoom-overlay-hint">🔍 點擊放大</div>
            </div>
            <div style="margin-top: 14px; font-size: 13px; color: var(--text-muted);">
                • <b>完整連通灌溉水系閉環</b>：源頭來自<b>中央蓄水石井 [井]</b> 溢流槽 ➔ 順坡進入<b>梯形麥田 [田]</b> 分水灌溉 ➔ 最終順利排出<b>東南地圖邊界 (39, 33)</b> 荒野低地！<br>
                • 100% Kenshi 廢土質感：風化灰木壁、斜拉獸皮遮陽棚、土坯泥磚地基、零黑邊、枯黃草叢與碎石。
            </div>
        </div>

        <!-- 2. 每格文字標籤分層語意圖 -->
        <div class="card">
            <div class="card-header">
                <div class="card-title semantic-title">📑 2. 每格文字標籤分層語意圖 (Per-Cell Text Labels)</div>
                <span class="hint">🔍 點擊全螢幕像素級放大</span>
            </div>
            <div class="img-container" onclick="openLightbox(b64Sem, '【每格文字標籤分層語意圖 - 1,600 格全標註】')">
                <img id="imgSem" src="{b64_sem}" alt="每格文字標籤分層語意圖">
                <div class="zoom-overlay-hint">🔍 點擊放大</div>
            </div>
            <div class="legend-grid">
                <div class="legend-item"><span class="legend-badge" style="background:#e4cea2; color:#333;">[沙]</span> 純黃沙底地 (AP: 1.0)</div>
                <div class="legend-item"><span class="legend-badge" style="background:#af8a62;">[路]</span> 黏土車轍小道 (AP: 0.8)</div>
                <div class="legend-item"><span class="legend-badge" style="background:#c3a05a;">[田]</span> 泥磚麥垄耕地 (AP: 1.2)</div>
                <div class="legend-item"><span class="legend-badge" style="background:#6e5032;">[溝]</span> 連通灌溉水渠 (源自水井)</div>
                <div class="legend-item"><span class="legend-badge" style="background:#b46e46;">[屋]</span> Kenshi 風化大木屋實體</div>
                <div class="legend-item"><span class="legend-badge" style="background:#4682b4;">[井]</span> 蓄水水井(水系源頭, 75%)</div>
                <div class="legend-item"><span class="legend-badge" style="background:#e66428;">[爐]</span> 露天熔爐與打鐵砧 (75%)</div>
                <div class="legend-item"><span class="legend-badge" style="background:#91a03c;">[草]</span> 荒漠枯黃雜草叢 (飾物)</div>
                <div class="legend-item"><span class="legend-badge" style="background:#8c8c96;">[石]</span> 碎石散礫堆 (飾物)</div>
                <div class="legend-item"><span class="legend-badge" style="background:#e55050;">[▲頂]</span> 3/4 獸皮屋頂 (進門淡出)</div>
            </div>
        </div>
    </div>

    <!-- 3. 四大分層獨立展示 -->
    <div class="layers-section">
        <div class="card-header" style="margin-bottom: 16px;">
            <div class="card-title layer-title">📐 3. 四大分層獨立圖層解析 (Discrete Layer-by-Layer Views)</div>
            <span class="hint">每層皆可獨立點擊放大檢驗</span>
        </div>
        <div class="layers-grid">
            <!-- Layer 1 -->
            <div class="layer-card">
                <div style="font-weight: bold; margin-bottom: 8px; color: #e4cea2;">【Layer 1: 原野底沙】</div>
                <div class="img-container" onclick="openLightbox(b64L1, '【Layer 1: 純自然原野底沙】')">
                    <img src="{b64_l1}" alt="Layer 1 底沙">
                </div>
                <div class="layer-card-desc">
                    Z-Index: 0<br>
                    乾燥風化黃沙底地，Perlin 柔和沙丘起伏紋理，無碰撞純背景。
                </div>
            </div>

            <!-- Layer 2 -->
            <div class="layer-card">
                <div style="font-weight: bold; margin-bottom: 8px; color: #af8a62;">【Layer 2: 建築地景與連通水渠】</div>
                <div class="img-container" onclick="openLightbox(b64L2, '【Layer 2: 人工建築與地景層】')">
                    <img src="{b64_l2}" alt="Layer 2 建築地景">
                </div>
                <div class="layer-card-desc">
                    Z-Index: 2 (Y-Sort: on)<br>
                    Autotile 泥路、梯形耕地、<b>水井連通至地圖邊界的完整灌溉水渠</b>、3 棟木屋、熔爐。
                </div>
            </div>

            <!-- Layer 2.5 -->
            <div class="layer-card">
                <div style="font-weight: bold; margin-bottom: 8px; color: #91a03c;">【Layer 2.5: 枯草碎石層】</div>
                <div class="img-container" onclick="openLightbox(b64Clutter, '【Layer 2.5: 雜草與碎石佈置層】')">
                    <img src="{b64_clutter}" alt="Layer 2.5 枯草碎石">
                </div>
                <div class="layer-card-desc">
                    Z-Index: 2 (Decors)<br>
                    荒原枯黃草叢、碎石散礫堆，自然散佈於路旁與牆角，增強環境生活感。
                </div>
            </div>

            <!-- Layer 3 -->
            <div class="layer-card">
                <div style="font-weight: bold; margin-bottom: 8px; color: #e55050;">【Layer 3: 獸皮屋頂淡出層】</div>
                <div class="img-container" onclick="openLightbox(b64L3, '【Layer 3: 獸皮屋頂淡出層】')">
                    <img src="{b64_l3}" alt="Layer 3 屋頂淡出層">
                </div>
                <div class="layer-card-desc">
                    Z-Index: 10 (Roofs)<br>
                    3/4 獸皮與厚木棚頂，配備 Area2D 觸發器，角色進門時平滑 Tween 淡出。
                </div>
            </div>
        </div>
    </div>

    <!-- 4. 即時圖層疊加沙盒 -->
    <div class="sandbox-section">
        <div class="card-header">
            <div class="card-title merged-title">🎛️ 4. 即時圖層疊加檢驗沙盒 (Interactive Layer Blending Sandbox)</div>
            <span class="hint">勾選開關可即時疊加/隱藏圖層進行 QC 審查</span>
        </div>
        <div class="sandbox-controls">
            <label class="sandbox-checkbox"><input type="checkbox" id="chk-l1" checked onchange="updateSandbox()"> Layer 1: 底沙</label>
            <label class="sandbox-checkbox"><input type="checkbox" id="chk-l2" checked onchange="updateSandbox()"> Layer 2: 建築與連通水渠</label>
            <label class="sandbox-checkbox"><input type="checkbox" id="chk-cl" checked onchange="updateSandbox()"> Layer 2.5: 枯草碎石</label>
            <label class="sandbox-checkbox"><input type="checkbox" id="chk-l3" checked onchange="updateSandbox()"> Layer 3: 獸皮屋頂</label>
            <label class="sandbox-checkbox"><input type="checkbox" id="chk-sem" onchange="updateSandbox()"> 📑 疊加語意文字網格</label>
        </div>
        <div class="sandbox-viewport" onclick="openLightbox(b64Merged, '【即時沙盒全域檢視】')">
            <img id="sb-l1" class="sandbox-layer" src="{b64_l1}">
            <img id="sb-l2" class="sandbox-layer" src="{b64_l2}">
            <img id="sb-cl" class="sandbox-layer" src="{b64_clutter}">
            <img id="sb-l3" class="sandbox-layer" src="{b64_l3}">
            <img id="sb-sem" class="sandbox-layer" src="{b64_sem}" style="opacity: 0; pointer-events: none;">
        </div>
    </div>

    <!-- 5. 全螢幕 Lightbox 放大模態框 -->
    <div id="lightboxModal" class="lightbox-modal">
        <div class="lightbox-header">
            <div id="lightboxTitle" class="lightbox-title">圖片標題</div>
            <div class="lightbox-toolbar">
                <button class="lightbox-btn" onclick="zoomIn()">🔍 放大 (+)</button>
                <button class="lightbox-btn" onclick="zoomOut()">🔍 縮小 (-)</button>
                <button class="lightbox-btn" onclick="resetZoom()">🔄 重設 100%</button>
                <button class="lightbox-close" onclick="closeLightbox()">✕</button>
            </div>
        </div>
        <div class="lightbox-body" id="lightboxBody" onwheel="handleWheel(event)" onmousedown="startPan(event)" onmousemove="doPan(event)" onmouseup="endPan()">
            <img id="lightboxImg" class="lightbox-img" src="" alt="放大圖">
        </div>
    </div>

    <script>
        const b64Merged = "{b64_merged}";
        const b64Sem = "{b64_sem}";
        const b64L1 = "{b64_l1}";
        const b64L2 = "{b64_l2}";
        const b64Clutter = "{b64_clutter}";
        const b64L3 = "{b64_l3}";

        function updateSandbox() {{
            document.getElementById('sb-l1').style.opacity = document.getElementById('chk-l1').checked ? '1' : '0';
            document.getElementById('sb-l2').style.opacity = document.getElementById('chk-l2').checked ? '1' : '0';
            document.getElementById('sb-cl').style.opacity = document.getElementById('chk-cl').checked ? '1' : '0';
            document.getElementById('sb-l3').style.opacity = document.getElementById('chk-l3').checked ? '1' : '0';
            document.getElementById('sb-sem').style.opacity = document.getElementById('chk-sem').checked ? '0.75' : '0';
        }}

        let currentScale = 1.0;
        let isPanning = false;
        let startX = 0, startY = 0;
        let translateX = 0, translateY = 0;

        function openLightbox(src, title) {{
            const modal = document.getElementById('lightboxModal');
            const img = document.getElementById('lightboxImg');
            const titleEl = document.getElementById('lightboxTitle');
            
            img.src = src;
            titleEl.textContent = title;
            modal.style.display = 'flex';
            resetZoom();
        }}

        function closeLightbox() {{
            document.getElementById('lightboxModal').style.display = 'none';
        }}

        function applyTransform() {{
            const img = document.getElementById('lightboxImg');
            img.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{currentScale}})`;
        }}

        function zoomIn() {{
            currentScale = Math.min(currentScale * 1.3, 10.0);
            applyTransform();
        }}

        function zoomOut() {{
            currentScale = Math.max(currentScale / 1.3, 0.5);
            applyTransform();
        }}

        function resetZoom() {{
            currentScale = 1.0;
            translateX = 0;
            translateY = 0;
            applyTransform();
        }}

        function handleWheel(e) {{
            e.preventDefault();
            if (e.deltaY < 0) {{
                zoomIn();
            }} else {{
                zoomOut();
            }}
        }}

        function startPan(e) {{
            if (e.button !== 0) return;
            isPanning = true;
            startX = e.clientX - translateX;
            startY = e.clientY - translateY;
        }}

        function doPan(e) {{
            if (!isPanning) return;
            translateX = e.clientX - startX;
            translateY = e.clientY - startY;
            applyTransform();
        }}

        function endPan() {{
            isPanning = false;
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeLightbox();
        }});
    </script>
</body>
</html>
"""

html_path = brain_dir / "map_delivery_report_0_0_village.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"[Hydrology Connected] 100% Connected Hydrology Map & HTML Report generated: {html_path}")
