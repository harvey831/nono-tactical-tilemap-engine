import math
import random
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

brain_dir = Path(r"C:\Users\ihate\.gemini\antigravity\brain\522dd70e-62d4-4f27-893e-70f3ade173ca")
skill_repo = Path(__file__).resolve().parent.parent
godot_base = Path(r"C:\GPTfile\godot\adventure-of-self-realization-v-0.5")
slave_camp_godot_dir = godot_base / "圖片" / "地圖" / "荒原九大戰區_正式資產" / "01_西方奴隸營"
slave_camp_godot_dir.mkdir(parents=True, exist_ok=True)

assets_dir = skill_repo / "assets"
reports_dir = skill_repo / "reports"
assets_dir.mkdir(parents=True, exist_ok=True)
reports_dir.mkdir(parents=True, exist_ok=True)

font_path = Path(r"C:\Windows\Fonts\msyh.ttc")
if not font_path.exists(): font_path = Path(r"C:\Windows\Fonts\simsun.ttc")
font_cell = ImageFont.truetype(str(font_path), 10)
font_hdr = ImageFont.truetype(str(font_path), 12)

# ==============================================================================
# 🎨 1. 3/4 俯視角調色盤
# ==============================================================================
SAND_LIGHT = (236, 215, 178, 255)
SAND_MID = (215, 186, 142, 255)
SAND_DARK = (185, 150, 108, 255)
SAND_TRACK = (165, 130, 90, 255)

ROCK_T1_SURF = (198, 160, 120, 255)
ROCK_T1_WALL = (145, 105, 72, 255)
ROCK_T2_SURF = (172, 130, 92, 255)
ROCK_T2_WALL = (120, 80, 50, 255)
ROCK_T3_SURF = (142, 98, 68, 255)
ROCK_T3_WALL = (92, 58, 35, 255)
CLIFF_EDGE_LIGHT = (248, 228, 198, 255)
CLIFF_SHADOW = (55, 35, 22, 255)

# 巨型開採石條塊 (Megaslab)
MEGABLOCK_TOP = (215, 208, 198, 255)
MEGABLOCK_FRONT = (168, 158, 148, 255)
MEGABLOCK_SIDE = (135, 126, 116, 255)
MEGABLOCK_OUTLINE = (78, 72, 65, 255)
ROPE_BROWN = (155, 110, 60, 255)

# 木構造與腳手架
WOOD_PLANK_L = (158, 125, 90, 255)
WOOD_PLANK_D = (125, 92, 62, 255)
WOOD_BEAM_MID = (92, 68, 48, 255)
WOOD_BEAM_DARK = (52, 38, 26, 255)

# 奴隸主帳篷
CANVAS_TOP = (235, 218, 190, 255)
CANVAS_SLOPE = (205, 182, 148, 255)
CANVAS_FRONT = (175, 148, 115, 255)
CANVAS_SHADOW = (135, 110, 80, 255)
CRIMSON_VALANCE = (158, 32, 28, 255)
CRIMSON_SHADOW = (112, 20, 16, 255)
GOLD_TRIM = (238, 198, 55, 255)

# 鐵器、熔爐與刑具
IRON_STEEL_L = (175, 188, 205, 255)
IRON_STEEL_M = (88, 98, 112, 255)
IRON_STEEL_D = (42, 48, 56, 255)
FIRE_ORANGE = (255, 125, 30, 255)
FIRE_CORE = (255, 245, 175, 255)
RUST_RED = (168, 72, 38, 255)

# 室內裝飾
FLOOR_PARQUET_1 = (175, 135, 95, 255)
FLOOR_PARQUET_2 = (152, 115, 78, 255)
RUG_RED = (142, 25, 25, 255)
RUG_BORDER = (235, 195, 65, 255)
GOLD_COINS = (255, 215, 45, 255)

# ==============================================================================
# 📐 2. 嚴密純語意矩陣定義 (4-Layer SSOT: 40x40 @ 32px)
# ==============================================================================
gw, gh = 40, 40

# --- Layer 1: 自然底地與階梯採石坑 ---
grid_l1 = [["[沙地]" for _ in range(gw)] for _ in range(gh)]

for y in range(0, 12):
    grid_l1[y][19] = "[土路]"; grid_l1[y][20] = "[土路]"
for y in range(36, 40):
    grid_l1[y][19] = "[土路]"; grid_l1[y][20] = "[土路]"

for y in range(12, 36):
    for x in range(4, 36): grid_l1[y][x] = "[岩層1]"
for y in range(19, 35):
    for x in range(10, 33): grid_l1[y][x] = "[岩層2]"
for y in range(26, 34):
    for x in range(15, 29): grid_l1[y][x] = "[岩層3]"

for y in range(12, 36):
    grid_l1[y][19] = "[石路]"; grid_l1[y][20] = "[石路]"
for x in range(8, 33): grid_l1[18][x] = "[石路]"
for x in range(14, 29): grid_l1[25][x] = "[石路]"

# --- Layer 2: 建築本體、奴隸鐵籠、腳手架與室內層 ---
grid_l2 = [["[ · ]" for _ in range(gw)] for _ in range(gh)]

for y in range(7, 11):
    for x in range(6, 14): grid_l2[y][x] = "[帳地]"
grid_l2[7][8] = "[皮椅]"; grid_l2[7][9] = "[皮椅]"
grid_l2[7][11] = "[戰圖]"; grid_l2[7][12] = "[戰圖]"
grid_l2[8][6] = "[金箱]"; grid_l2[8][7] = "[金箱]"
grid_l2[8][9] = "[地毯]"; grid_l2[8][10] = "[地毯]"
grid_l2[9][9] = "[地毯]"; grid_l2[9][10] = "[地毯]"
grid_l2[10][9] = "[帳門]"; grid_l2[10][10] = "[帳門]"

for y in range(7, 11):
    for x in range(26, 32): grid_l2[y][x] = "[鍛地]"
grid_l2[7][27] = "[風箱]"
grid_l2[7][28] = "[熔爐]"; grid_l2[7][29] = "[熔爐]"
grid_l2[8][28] = "[鐵砧]"
grid_l2[8][30] = "[鐐架]"; grid_l2[8][31] = "[鐐架]"
grid_l2[10][28] = "[鍛門]"; grid_l2[10][29] = "[鍛門]"

for y in range(14, 19):
    for x in range(6, 14): grid_l2[y][x] = "[鐵籠]"
grid_l2[16][9] = "[牢門]"; grid_l2[16][10] = "[牢門]"
grid_l2[18][9] = "[牢門]"; grid_l2[18][10] = "[牢門]"

for y in range(14, 19):
    for x in range(24, 33): grid_l2[y][x] = "[棧台]"
grid_l2[15][28] = "[絞盤]"; grid_l2[15][29] = "[絞盤]"
grid_l2[16][28] = "[吊臂]"; grid_l2[16][29] = "[吊臂]"

for y in range(27, 31):
    for x in range(14, 19): grid_l2[y][x] = "[巨石條]"

grid_l2[27][25] = "[碎石機]"; grid_l2[27][26] = "[碎石機]"
grid_l2[28][25] = "[石堆]"; grid_l2[28][26] = "[石堆]"
grid_l2[29][25] = "[石堆]"; grid_l2[29][26] = "[石堆]"

for (sx, sy) in [(3, 3), (33, 3), (3, 33), (33, 33)]:
    for dy in range(3):
        for dx in range(3):
            grid_l2[sy + dy][sx + dx] = "[哨塔]"

for x in range(0, 18): grid_l2[2][x] = "[拒馬]"
for x in range(22, 40): grid_l2[2][x] = "[拒馬]"

# --- Layer 2.5: 環境雜物 ---
grid_l25 = [["[ · ]" for _ in range(gw)] for _ in range(gh)]
for y in range(gh):
    for x in range(gw):
        if (x * 13 + y * 17) % 23 == 0 and grid_l2[y][x] == "[ · ]": grid_l25[y][x] = "[碎石]"
        if (x * 7 + y * 19) % 29 == 0 and grid_l1[y][x] in ["[岩層2]", "[岩層3]"] and grid_l2[y][x] == "[ · ]":
            grid_l25[y][x] = "[十字鎬]"

grid_l25[12][20] = "[刑柱]"
grid_l25[13][20] = "[鎖鏈]"
grid_l25[20][20] = "[礦車]"
grid_l25[21][20] = "[礦車]"
grid_l25[13][10] = "[水槽]"
grid_l25[13][27] = "[木桶]"
grid_l25[29][18] = "[鐵撬]"

# --- Layer 3: 屋頂與遮陽帆布 ---
grid_l3 = [["[ · ]" for _ in range(gw)] for _ in range(gh)]

for y in range(5, 7):
    for x in range(6, 14): grid_l3[y][x] = "[▲帳頂]"

for y in range(5, 7):
    for x in range(26, 32): grid_l3[y][x] = "[▲鍛頂]"

for (sx, sy) in [(3, 2), (33, 2), (3, 32), (33, 32)]:
    for dy in range(2):
        for dx in range(3): grid_l3[sy + dy][sx + dx] = "[▲塔頂]"

for y in range(13, 15):
    for x in range(24, 33): grid_l3[y][x] = "[▲遮陽]"

# ==============================================================================
# 🏠 3. 繪製獨立 3/4 俯視角大作建築 Prefabs
# ==============================================================================
img_tent_roof = Image.new("RGBA", (256, 192), (0, 0, 0, 0))
d_tr = ImageDraw.Draw(img_tent_roof)

roof_main_poly = [(128, 8), (240, 72), (240, 88), (128, 108), (16, 88), (16, 72)]
d_tr.polygon(roof_main_poly, fill=CANVAS_SLOPE, outline=CANVAS_SHADOW)
d_tr.polygon([(128, 8), (128, 108), (16, 88), (16, 72)], fill=CANVAS_TOP)
d_tr.polygon([(128, 8), (240, 72), (240, 88), (128, 108)], fill=CANVAS_SLOPE)
d_tr.polygon([(128, 8), (144, 104), (128, 108), (112, 104)], fill=CRIMSON_VALANCE, outline=GOLD_TRIM)
d_tr.polygon([(16, 80), (128, 100), (240, 80), (240, 88), (128, 108), (16, 88)], fill=CRIMSON_VALANCE, outline=GOLD_TRIM)

img_tent_facade = Image.new("RGBA", (256, 192), (0, 0, 0, 0))
d_tf = ImageDraw.Draw(img_tent_facade)
d_tf.rectangle([20, 88, 236, 176], fill=CANVAS_FRONT, outline=CANVAS_SHADOW, width=2)
for vx in range(36, 236, 24):
    d_tf.line([(vx, 88), (vx, 176)], fill=CANVAS_SHADOW, width=2)
    d_tf.line([(vx + 1, 88), (vx + 1, 176)], fill=CANVAS_TOP, width=1)
d_tf.rectangle([18, 166, 238, 178], fill=ROCK_T1_WALL, outline=WOOD_BEAM_DARK, width=1)
d_tf.rectangle([96, 104, 160, 176], fill=CRIMSON_SHADOW, outline=GOLD_TRIM, width=2)
d_tf.line([(128, 104), (128, 176)], fill=GOLD_TRIM, width=2)
d_tf.rectangle([88, 92, 168, 114], fill=WOOD_BEAM_DARK, outline=GOLD_TRIM, width=2)
d_tf.text((98, 96), "奴隸主大帳", fill=GOLD_TRIM, font=font_hdr)
for bx in (32, 216):
    d_tf.rectangle([bx, 140, bx + 12, 172], fill=IRON_STEEL_D, outline=IRON_STEEL_M, width=1)
    d_tf.ellipse([bx - 2, 132, bx + 14, 144], fill=FIRE_ORANGE)
    d_tf.ellipse([bx + 2, 135, bx + 10, 141], fill=FIRE_CORE)

img_tent_interior = Image.new("RGBA", (256, 192), (0, 0, 0, 0))
d_ti = ImageDraw.Draw(img_tent_interior)
d_ti.rectangle([20, 88, 236, 176], fill=WOOD_BEAM_DARK, outline=WOOD_BEAM_MID, width=2)
for fy in range(92, 174, 8):
    c = FLOOR_PARQUET_1 if (fy // 8) % 2 == 0 else FLOOR_PARQUET_2
    d_ti.rectangle([24, fy, 232, fy + 7], fill=c, outline=WOOD_BEAM_DARK, width=1)
d_ti.rectangle([48, 108, 208, 166], fill=RUG_RED, outline=RUG_BORDER, width=2)
for rx in range(56, 200, 16): d_ti.line([(rx, 112), (rx + 8, 162)], fill=(175, 45, 45, 255), width=1)
d_ti.rectangle([104, 96, 152, 128], fill=CRIMSON_VALANCE, outline=GOLD_TRIM, width=2)
d_ti.ellipse([112, 102, 144, 120], fill=GOLD_TRIM)
d_ti.rectangle([168, 108, 224, 148], fill=WOOD_PLANK_L, outline=WOOD_BEAM_DARK, width=2)
d_ti.text((176, 122), "作戰地圖", fill=WOOD_BEAM_DARK, font=font_cell)
d_ti.rectangle([32, 116, 56, 144], fill=GOLD_COINS, outline=WOOD_BEAM_DARK, width=2)
d_ti.rectangle([32, 146, 56, 170], fill=GOLD_COINS, outline=WOOD_BEAM_DARK, width=2)

img_forge_roof = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_fr = ImageDraw.Draw(img_forge_roof)
forge_roof_poly = [(96, 12), (180, 68), (180, 80), (96, 92), (12, 80), (12, 68)]
d_fr.polygon(forge_roof_poly, fill=WOOD_PLANK_D, outline=WOOD_BEAM_DARK)
d_fr.polygon([(96, 12), (96, 92), (12, 80), (12, 68)], fill=WOOD_PLANK_L)
d_fr.polygon([(96, 12), (180, 68), (180, 80), (96, 92)], fill=WOOD_PLANK_D)
for r in range(4):
    t = (r + 1) / 5.0
    ry_mid = int(12 + (92 - 12) * t)
    ry_side = int(68 + (80 - 68) * t)
    d_fr.line([(int(96 - 84 * t), ry_side), (96, ry_mid)], fill=WOOD_BEAM_DARK, width=1)
    d_fr.line([(96, ry_mid), (int(96 + 84 * t), ry_side)], fill=WOOD_BEAM_DARK, width=1)
d_fr.rectangle([140, 8, 160, 44], fill=ROCK_T1_WALL, outline=WOOD_BEAM_DARK, width=2)

img_forge_facade = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_ff = ImageDraw.Draw(img_forge_facade)
d_ff.rectangle([16, 78, 176, 148], fill=WOOD_PLANK_D, outline=WOOD_BEAM_DARK, width=2)
for hx in (16, 56, 136, 176): d_ff.rectangle([hx - 2, 78, hx + 4, 148], fill=WOOD_BEAM_DARK)
d_ff.rectangle([72, 96, 120, 148], fill=IRON_STEEL_D, outline=IRON_STEEL_M, width=2)
d_ff.line([(96, 96), (96, 148)], fill=IRON_STEEL_M, width=1)
d_ff.ellipse([86, 120, 92, 126], fill=IRON_STEEL_L)
d_ff.ellipse([100, 120, 106, 126], fill=IRON_STEEL_L)
d_ff.rectangle([60, 80, 132, 98], fill=WOOD_BEAM_DARK, outline=IRON_STEEL_L, width=1)
d_ff.text((68, 82), "刑具鍛造", fill=IRON_STEEL_L, font=font_cell)

img_forge_interior = Image.new("RGBA", (192, 160), (0, 0, 0, 0))
d_fi = ImageDraw.Draw(img_forge_interior)
d_fi.rectangle([16, 78, 176, 148], fill=ROCK_T3_WALL, outline=WOOD_BEAM_DARK, width=2)
for sy in range(82, 146, 8):
    for sx in range(20, 172, 16):
        d_fi.rectangle([sx, sy, sx + 14, sy + 6], fill=ROCK_T2_SURF, outline=ROCK_T3_WALL, width=1)
d_fi.rectangle([24, 86, 72, 132], fill=ROCK_T1_WALL, outline=WOOD_BEAM_DARK, width=2)
d_fi.ellipse([34, 98, 62, 124], fill=FIRE_ORANGE)
d_fi.ellipse([42, 106, 54, 118], fill=FIRE_CORE)
d_fi.rectangle([88, 102, 116, 132], fill=IRON_STEEL_D, outline=IRON_STEEL_L, width=2)
d_fi.polygon([(84, 102), (88, 102), (88, 110), (84, 106)], fill=IRON_STEEL_L)
d_fi.rectangle([132, 86, 168, 122], fill=WOOD_BEAM_DARK, outline=WOOD_BEAM_MID, width=1)
for chx in (140, 150, 160): d_fi.line([(chx, 88), (chx, 116)], fill=IRON_STEEL_L, width=2)

# ==============================================================================
# 📐 4. 組裝大作世界地圖 (1280x1280 px)
# ==============================================================================
img_l1 = Image.new("RGBA", (1280, 1280), SAND_LIGHT)
d_l1 = ImageDraw.Draw(img_l1)

for y in range(0, 1280, 4):
    for x in range(0, 1280, 8):
        wave = int(math.sin(x * 0.02 + y * 0.015) * 3)
        c = SAND_MID if (y // 4 + wave) % 3 == 0 else SAND_LIGHT
        d_l1.rectangle([x, y, x + 7, y + 3], fill=c)

# Tier 1 (中層採石平台)
d_l1.rectangle([128, 384, 1152, 1152], fill=ROCK_T1_SURF)
d_l1.rectangle([128, 384, 1152, 398], fill=ROCK_T1_WALL)
d_l1.rectangle([128, 384, 142, 1152], fill=ROCK_T1_WALL)
d_l1.line([(128, 384), (1152, 384)], fill=CLIFF_EDGE_LIGHT, width=2)
d_l1.line([(128, 384), (128, 1152)], fill=CLIFF_EDGE_LIGHT, width=2)
d_l1.line([(128, 398), (1152, 398)], fill=CLIFF_SHADOW, width=2)

# Tier 2 (深層採石坑)
d_l1.rectangle([320, 608, 1056, 1120], fill=ROCK_T2_SURF)
d_l1.rectangle([320, 608, 1056, 622], fill=ROCK_T2_WALL)
d_l1.rectangle([320, 608, 334, 1120], fill=ROCK_T2_WALL)
d_l1.line([(320, 608), (1056, 608)], fill=CLIFF_EDGE_LIGHT, width=2)
d_l1.line([(320, 608), (320, 1120)], fill=CLIFF_EDGE_LIGHT, width=2)
d_l1.line([(320, 622), (1056, 622)], fill=CLIFF_SHADOW, width=2)

# Tier 3 (最深岩心)
d_l1.rectangle([480, 832, 928, 1088], fill=ROCK_T3_SURF)
d_l1.rectangle([480, 832, 928, 846], fill=ROCK_T3_WALL)
d_l1.rectangle([480, 832, 494, 1088], fill=ROCK_T3_WALL)
d_l1.line([(480, 832), (928, 832)], fill=CLIFF_EDGE_LIGHT, width=2)

for gy in range(40):
    py = gy * 32
    d_l1.rectangle([608, py, 672, py + 31], fill=SAND_TRACK)
    for sy in range(0, 32, 8):
        d_l1.rectangle([612, py + sy, 668, py + sy + 4], fill=WOOD_PLANK_D, outline=WOOD_BEAM_DARK, width=1)
    d_l1.line([(620, py), (620, py + 31)], fill=IRON_STEEL_L, width=2)
    d_l1.line([(660, py), (660, py + 31)], fill=IRON_STEEL_L, width=2)

img_l2_common = Image.new("RGBA", (1280, 1280), (0, 0, 0, 0))
d_l2c = ImageDraw.Draw(img_l2_common)

c_px, c_py = 6 * 32, 14 * 32
d_l2c.rectangle([c_px + 8, c_py + 12, c_px + 248, c_py + 152], fill=WOOD_BEAM_DARK, outline=IRON_STEEL_D, width=2)
for bx in range(c_px + 16, c_px + 248, 16): d_l2c.line([(bx, c_py + 12), (bx, c_py + 152)], fill=IRON_STEEL_L, width=2)
for by in range(c_py + 28, c_py + 152, 32): d_l2c.line([(c_px + 8, by), (c_px + 248, by)], fill=IRON_STEEL_D, width=2)
d_l2c.rectangle([c_px + 88, c_py + 32, c_px + 168, c_py + 152], fill=IRON_STEEL_D, outline=RUST_RED, width=2)

s_px, s_py = 24 * 32, 14 * 32
d_l2c.rectangle([s_px + 8, s_py + 12, s_px + 280, s_py + 152], fill=WOOD_PLANK_L, outline=WOOD_BEAM_DARK, width=2)
for bx in range(s_px + 8, s_px + 280 - 32, 32):
    d_l2c.line([(bx, s_py + 12), (bx + 32, s_py + 152)], fill=WOOD_BEAM_MID, width=2)
    d_l2c.line([(bx, s_py + 152), (bx + 32, s_py + 12)], fill=WOOD_BEAM_MID, width=2)
d_l2c.line([(s_px + 90, s_py + 60), (s_px + 180, s_py - 28)], fill=WOOD_BEAM_DARK, width=6)
d_l2c.line([(s_px + 180, s_py - 28), (s_px + 180, s_py + 80)], fill=IRON_STEEL_D, width=2)
d_l2c.ellipse([s_px + 172, s_py - 34, s_px + 188, s_py - 18], fill=IRON_STEEL_L, outline=WOOD_BEAM_DARK)

m_px, m_py = 14 * 32, 27 * 32
for row in range(4):
    for col in range(3):
        bx = m_px + col * 52
        by = m_py + row * 30
        d_l2c.rectangle([bx + 2, by + 2, bx + 48, by + 12], fill=MEGABLOCK_TOP)
        d_l2c.rectangle([bx + 2, by + 12, bx + 48, by + 26], fill=MEGABLOCK_FRONT, outline=MEGABLOCK_OUTLINE, width=1)
        d_l2c.polygon([(bx + 48, by + 2), (bx + 52, by + 6), (bx + 52, by + 22), (bx + 48, by + 26)], fill=MEGABLOCK_SIDE)
        d_l2c.line([(bx + 14, by + 2), (bx + 14, by + 26)], fill=ROPE_BROWN, width=2)
        d_l2c.line([(bx + 36, by + 2), (bx + 36, by + 26)], fill=ROPE_BROWN, width=2)

for (sx, sy) in [(3, 3), (33, 3), (3, 33), (33, 33)]:
    px, py = sx * 32, sy * 32
    d_l2c.rectangle([px + 8, py + 16, px + 88, py + 88], fill=WOOD_PLANK_D, outline=WOOD_BEAM_DARK, width=2)
    d_l2c.rectangle([px + 8, py + 16, px + 16, py + 88], fill=WOOD_BEAM_DARK)
    d_l2c.rectangle([px + 80, py + 16, px + 88, py + 88], fill=WOOD_BEAM_DARK)

for x in range(0, 18):
    px, py = x * 32, 2 * 32
    d_l2c.line([(px, py + 24), (px + 32, py + 8)], fill=WOOD_BEAM_DARK, width=3)
    d_l2c.line([(px, py + 8), (px + 32, py + 24)], fill=WOOD_BEAM_DARK, width=3)
for x in range(22, 40):
    px, py = x * 32, 2 * 32
    d_l2c.line([(px, py + 24), (px + 32, py + 8)], fill=WOOD_BEAM_DARK, width=3)
    d_l2c.line([(px, py + 8), (px + 32, py + 24)], fill=WOOD_BEAM_DARK, width=3)

img_l25 = Image.new("RGBA", (1280, 1280), (0, 0, 0, 0))
d_l25 = ImageDraw.Draw(img_l25)

for gy in range(40):
    for gx in range(40):
        tok = grid_l25[gy][gx]
        px, py = gx * 32, gy * 32
        if tok == "[碎石]":
            d_l25.polygon([(px+8, py+24), (px+14, py+16), (px+22, py+20), (px+24, py+28)], fill=MEGABLOCK_TOP, outline=MEGABLOCK_OUTLINE)
        elif tok == "[十字鎬]":
            d_l25.line([(px+6, py+26), (px+24, py+8)], fill=WOOD_BEAM_MID, width=2)
            d_l25.polygon([(px+20, py+6), (px+26, py+4), (px+28, py+12), (px+22, py+14)], fill=IRON_STEEL_L, outline=IRON_STEEL_D)
        elif tok == "[刑柱]":
            d_l25.rectangle([px+12, py+4, px+20, py+30], fill=WOOD_BEAM_MID, outline=WOOD_BEAM_DARK, width=1)
            d_l25.rectangle([px+4, py+10, px+28, py+16], fill=WOOD_BEAM_MID, outline=WOOD_BEAM_DARK, width=1)
            d_l25.line([(px+6, py+16), (px+6, py+26)], fill=IRON_STEEL_D, width=2)
            d_l25.line([(px+26, py+16), (px+26, py+26)], fill=IRON_STEEL_D, width=2)
        elif tok == "[礦車]":
            d_l25.rectangle([px+4, py+8, px+28, py+26], fill=WOOD_BEAM_DARK, outline=IRON_STEEL_D, width=2)
            d_l25.ellipse([px+6, py+24, px+14, py+30], fill=IRON_STEEL_D)
            d_l25.ellipse([px+18, py+24, px+26, py+30], fill=IRON_STEEL_D)
            d_l25.polygon([(px+6, py+8), (px+12, py+2), (px+20, py+4), (px+26, py+8)], fill=MEGABLOCK_TOP)
        elif tok == "[水槽]":
            d_l25.rectangle([px+4, py+8, px+28, py+24], fill=WOOD_BEAM_MID, outline=WOOD_BEAM_DARK, width=2)
            d_l25.rectangle([px+8, py+12, px+24, py+20], fill=(85, 128, 145, 255))
        elif tok == "[木桶]":
            d_l25.ellipse([px+8, py+8, px+24, py+24], fill=WOOD_PLANK_L, outline=WOOD_BEAM_DARK, width=2)

# ==============================================================================
# 🖼️ 5. 合成外觀層 (Exterior) 與店內層 (Interior)
# ==============================================================================
view_ext = Image.new("RGBA", (1280, 1280), (0, 0, 0, 0))
view_ext = Image.alpha_composite(view_ext, img_l1)
view_ext = Image.alpha_composite(view_ext, img_l2_common)

view_ext.paste(img_tent_facade, (6 * 32, 5 * 32), img_tent_facade)
view_ext.paste(img_forge_facade, (26 * 32, 5 * 32), img_forge_facade)
view_ext.paste(img_tent_roof, (6 * 32, 5 * 32), img_tent_roof)
view_ext.paste(img_forge_roof, (26 * 32, 5 * 32), img_forge_roof)

d_ve = ImageDraw.Draw(view_ext)
for (sx, sy) in [(3, 3), (33, 3), (3, 33), (33, 33)]:
    px, py = sx * 32, sy * 32
    d_ve.polygon([(px + 48, py - 12), (px + 96, py + 24), (px, py + 24)], fill=CRIMSON_VALANCE, outline=WOOD_BEAM_DARK)

view_ext = Image.alpha_composite(view_ext, img_l25)

view_int = Image.new("RGBA", (1280, 1280), (0, 0, 0, 0))
view_int = Image.alpha_composite(view_int, img_l1)
view_int = Image.alpha_composite(view_int, img_l2_common)

view_int.paste(img_tent_interior, (6 * 32, 5 * 32), img_tent_interior)
view_int.paste(img_forge_interior, (26 * 32, 5 * 32), img_forge_interior)

view_int = Image.alpha_composite(view_int, img_l25)

# 儲存奴隸營專屬檔案到 brain (加上 slave_camp_ 前綴，避免覆蓋村落！)
img_l1.save(brain_dir / "slave_camp_layer_1_ground.png")
img_l2_common.save(brain_dir / "slave_camp_layer_2_structures.png")
img_l25.save(brain_dir / "slave_camp_layer_2_5_clutter.png")
view_ext.save(brain_dir / "slave_camp_view_exterior_merged.png")
view_int.save(brain_dir / "slave_camp_view_interior_merged.png")

# 同步至 Godot 專屬 01_西方奴隸營 目錄
img_l1.save(slave_camp_godot_dir / "layer_1_ground.png")
img_l2_common.save(slave_camp_godot_dir / "layer_2_structures.png")
img_l25.save(slave_camp_godot_dir / "layer_2_5_clutter.png")
view_ext.save(slave_camp_godot_dir / "map_0_1_slave_camp_exterior_1280.png")
view_int.save(slave_camp_godot_dir / "map_0_1_slave_camp_interior_1280.png")

# 同步至倉庫 assets
view_ext.save(assets_dir / "kenshi_slave_camp_exterior_1280.png")
view_int.save(assets_dir / "kenshi_slave_camp_interior_1280.png")

# ==============================================================================
# 📑 6. 渲染 5 態視覺化語意矩陣大圖
# ==============================================================================
TOKEN_COLORS = {
    "[沙地]": (236, 215, 178), "[土路]": (185, 150, 108), "[石路]": (92, 58, 35),
    "[岩層1]": (198, 160, 120), "[岩層2]": (172, 130, 92), "[岩層3]": (142, 98, 68),
    "[帳地]": (158, 125, 90), "[皮椅]": (158, 32, 28), "[戰圖]": (235, 218, 190),
    "[金箱]": (255, 215, 45), "[地毯]": (142, 25, 25), "[帳門]": (205, 182, 148),
    "[鍛地]": (92, 58, 35), "[風箱]": (158, 125, 90), "[熔爐]": (255, 125, 30),
    "[鐵砧]": (42, 48, 56), "[鐐架]": (175, 188, 205), "[鍛門]": (92, 68, 48),
    "[鐵籠]": (58, 65, 78), "[牢門]": (168, 72, 38),
    "[棧台]": (158, 125, 90), "[絞盤]": (92, 68, 48), "[吊臂]": (52, 38, 26),
    "[巨石條]": (215, 208, 198), "[碎石機]": (92, 58, 35), "[石堆]": (215, 208, 198),
    "[哨塔]": (92, 68, 48), "[拒馬]": (52, 38, 26),
    "[碎石]": (215, 208, 198), "[十字鎬]": (175, 188, 205),
    "[刑柱]": (158, 125, 90), "[鎖鏈]": (42, 48, 56), "[礦車]": (92, 68, 48),
    "[水槽]": (85, 128, 145), "[木桶]": (158, 125, 90), "[鐵撬]": (175, 188, 205),
    "[▲帳頂]": (235, 218, 190), "[▲鍛頂]": (158, 125, 90),
    "[▲塔頂]": (158, 32, 28), "[▲遮陽]": (235, 218, 190),
    "[ · ]": (25, 25, 28)
}

def render_visual_semantic_grid(grid_data, title=""):
    img = Image.new("RGBA", (1280, 1280), (20, 20, 24, 255))
    draw = ImageDraw.Draw(img)
    for gy in range(40):
        for gx in range(40):
            tok = grid_data[gy][gx]
            px, py = gx * 32, gy * 32
            bg_c = TOKEN_COLORS.get(tok, (40, 40, 45))
            draw.rectangle([px, py, px + 31, py + 31], fill=bg_c, outline=(15, 15, 18, 180), width=1)
            txt = tok.strip("[]▲")
            if txt != "·":
                txt_c = (15, 15, 18) if sum(bg_c) > 380 else (245, 245, 250)
                draw.text((px + 2, py + 8), txt[:3], fill=txt_c, font=font_cell)
    return img

sem_l1 = render_visual_semantic_grid(grid_l1, "Layer 1")
sem_l2 = render_visual_semantic_grid(grid_l2, "Layer 2")
sem_l25 = render_visual_semantic_grid(grid_l25, "Layer 2.5")
sem_l3 = render_visual_semantic_grid(grid_l3, "Layer 3")

grid_merged = [["[ · ]" for _ in range(40)] for _ in range(40)]
for gy in range(40):
    for gx in range(40):
        if grid_l3[gy][gx] != "[ · ]": grid_merged[gy][gx] = grid_l3[gy][gx]
        elif grid_l2[gy][gx] != "[ · ]": grid_merged[gy][gx] = grid_l2[gy][gx]
        elif grid_l25[gy][gx] != "[ · ]": grid_merged[gy][gx] = grid_l25[gy][gx]
        else: grid_merged[gy][gx] = grid_l1[gy][gx]

sem_merged = render_visual_semantic_grid(grid_merged, "Merged SSOT")

sem_merged.save(assets_dir / "kenshi_slave_camp_semantic_ssot_1280.png")
sem_merged.save(slave_camp_godot_dir / "semantic_grid_merged.png")

# ==============================================================================
# 📑 7. 100% 完整 Lightbox 縮放拖拽互動式 HTML 交付報告
# ==============================================================================
def img_to_b64(img):
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')

b64_ext = img_to_b64(view_ext)
b64_int = img_to_b64(view_int)
b64_sem_m = img_to_b64(sem_merged)
b64_sem_l1 = img_to_b64(sem_l1)
b64_sem_l2 = img_to_b64(sem_l2)
b64_sem_l25 = img_to_b64(sem_l25)
b64_sem_l3 = img_to_b64(sem_l3)

html_report = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>戰術荒原 (0, 1) 西方奴隸營 · 階梯採石場 - 官方標準交付報告</title>
    <style>
        :root {{
            --bg-primary: #0f1013;
            --bg-card: #181a20;
            --bg-card-inner: #21242c;
            --accent: #e59844;
            --accent-crimson: #d44238;
            --accent-cyan: #3db8c2;
            --text-primary: #f0f2f5;
            --text-secondary: #9da5b4;
            --border-color: #2e3340;
        }}
        body {{
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            margin: 0; padding: 24px;
            line-height: 1.6;
        }}
        header {{
            border-bottom: 2px solid var(--accent);
            padding-bottom: 16px; margin-bottom: 24px;
            display: flex; justify-content: space-between; align-items: flex-end;
        }}
        h1 {{ margin: 0; font-size: 26px; color: var(--accent); }}
        .badge {{
            background: rgba(229, 152, 68, 0.15);
            color: var(--accent);
            padding: 4px 12px; border-radius: 4px;
            font-size: 13px; font-weight: 600; border: 1px solid var(--accent);
        }}
        .section {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px; padding: 20px; margin-bottom: 24px;
        }}
        h2 {{ margin-top: 0; font-size: 18px; color: var(--accent-cyan); border-left: 4px solid var(--accent-cyan); padding-left: 10px; }}
        .view-toggle-bar {{
            display: flex; gap: 12px; margin-bottom: 16px;
        }}
        .btn-toggle {{
            background: var(--bg-card-inner); color: #fff; border: 1px solid var(--border-color);
            padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600;
            transition: all 0.2s;
        }}
        .btn-toggle.active {{
            background: var(--accent); color: #121316; border-color: var(--accent);
        }}
        .map-stage {{
            display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
        }}
        .map-box {{
            background: var(--bg-card-inner); border: 1px solid var(--border-color);
            border-radius: 6px; padding: 14px; text-align: center;
        }}
        .map-box h3 {{ margin: 0 0 10px 0; font-size: 15px; color: var(--text-secondary); }}
        .map-img {{
            width: 100%; max-width: 580px; height: auto;
            image-rendering: pixelated; border-radius: 4px;
            cursor: zoom-in; transition: transform 0.2s; border: 1px solid var(--border-color);
        }}
        .map-img:hover {{ transform: scale(1.01); border-color: var(--accent); }}
        table {{
            width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px;
        }}
        th, td {{
            padding: 10px 12px; text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{ background: var(--bg-card-inner); color: var(--accent); }}
        
        /* 800% 完整 Lightbox 縮放與拖拽模態框 */
        .lightbox-modal {{
            display: none; position: fixed; top: 0; left: 0;
            width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.95);
            z-index: 99999; flex-direction: column;
            align-items: center; justify-content: center;
            user-select: none;
        }}
        .lightbox-header {{
            position: absolute; top: 16px; left: 24px; right: 24px;
            display: flex; justify-content: space-between; align-items: center;
            color: #fff; z-index: 100000;
        }}
        .lightbox-title {{ font-size: 18px; font-weight: bold; color: var(--accent); }}
        .lightbox-toolbar {{ display: flex; gap: 12px; align-items: center; }}
        .lightbox-btn {{
            background: var(--bg-card-inner); color: #fff; border: 1px solid var(--border-color);
            padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px;
        }}
        .lightbox-btn:hover {{ background: var(--accent); color: #000; }}
        .lightbox-close {{
            font-size: 24px; cursor: pointer; background: none; border: none; color: #fff;
        }}
        .lightbox-close:hover {{ color: var(--accent-crimson); }}
        .lightbox-body {{
            width: 100%; height: 100%; display: flex;
            align-items: center; justify-content: center;
            overflow: hidden; cursor: grab;
        }}
        .lightbox-body:active {{ cursor: grabbing; }}
        .lightbox-img {{
            max-width: 90vw; max-height: 85vh;
            image-rendering: pixelated;
            transform-origin: center center;
            transition: transform 0.05s ease-out;
        }}
    </style>
</head>
<body>
    <header>
        <div>
            <h1>🗺️ 戰術荒原 (0, 1) · 西方奴隸營 ＆ 階梯採石場</h1>
            <div style="color: var(--text-secondary); margin-top: 4px;">4-Layer 語意 SSOT • 40×40 網格 (1280×1280 px) • 3 階立體階梯採石坑 • 3/4 俯視角大作建築</div>
        </div>
        <div class="badge">Godot 4.3+ 戰術地圖架構</div>
    </header>

    <!-- 1. 核心大圖驗收視圖 -->
    <div class="section">
        <h2>🖼️ 一、遊戲大圖雙態驗收 (Roofs ON vs Roofs OFF)</h2>
        <div class="view-toggle-bar">
            <button class="btn-toggle active" id="btn-ext" onclick="switchMainView('ext')">🏠 進去前·外觀層全景 (Roofs ON)</button>
            <button class="btn-toggle" id="btn-int" onclick="switchMainView('int')">🚪 進去後·店內層全景 (Roofs OFF)</button>
        </div>
        <div class="map-stage">
            <div class="map-box">
                <h3 id="main-view-title">進去前·外觀層全景 (map_0_1_slave_camp_exterior_1280.png)</h3>
                <img id="main-img" class="map-img" src="{b64_ext}" onclick="openLightbox(this.src, '【西方奴隸營·外觀全景 1280x1280】')" alt="Map View">
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 6px;">💡 點擊大圖開啟 800% 像素級平移/滾輪縮放 Lightbox</div>
            </div>
            <div class="map-box">
                <h3>五態視覺化純語意矩陣 SSOT (semantic_grid_merged.png)</h3>
                <img id="sem-img" class="map-img" src="{b64_sem_m}" onclick="openLightbox(this.src, '【五態視覺語意 SSOT 矩陣 - 1600 格全標註】')" alt="Semantic SSOT">
                <div class="view-toggle-bar" style="justify-content: center; margin-top: 8px;">
                    <button class="btn-toggle active" style="padding: 4px 8px; font-size: 11px;" onclick="switchSemView('merged')">綜合 SSOT</button>
                    <button class="btn-toggle" style="padding: 4px 8px; font-size: 11px;" onclick="switchSemView('l1')">L1 底地</button>
                    <button class="btn-toggle" style="padding: 4px 8px; font-size: 11px;" onclick="switchSemView('l2')">L2 建築</button>
                    <button class="btn-toggle" style="padding: 4px 8px; font-size: 11px;" onclick="switchSemView('l25')">L2.5 雜物</button>
                    <button class="btn-toggle" style="padding: 4px 8px; font-size: 11px;" onclick="switchSemView('l3')">L3 屋頂</button>
                </div>
            </div>
        </div>
    </div>

    <!-- 2. 戰術 Custom Data Layer 對照表 -->
    <div class="section">
        <h2>📊 二、戰術自定義數據層 (Tactical Custom Data Layer)</h2>
        <table>
            <thead>
                <tr>
                    <th>語意 Token</th>
                    <th>分層 Layer</th>
                    <th>AP 移動消耗</th>
                    <th>掩體率 (Cover %)</th>
                    <th>戰術機制與效果</th>
                </tr>
            </thead>
            <tbody>
                <tr><td><code>[沙地]</code></td><td>Layer 1</td><td>1.0</td><td>0%</td><td>標準原野地面</td></tr>
                <tr><td><code>[土路] / [石路]</code></td><td>Layer 1</td><td>0.8</td><td>0%</td><td>行軍與採石滑軌加速通道</td></tr>
                <tr><td><code>[岩層1] / [岩層2] / [岩層3]</code></td><td>Layer 1</td><td>1.2 ~ 1.5</td><td>25%</td><td>3 階立體階梯採石坑，低窪受制</td></tr>
                <tr><td><code>[帳地] / [鍛地]</code></td><td>Layer 2</td><td>1.0</td><td>0%</td><td>建築室內戰鬥平地</td></tr>
                <tr><td><code>[皮椅] / [戰圖]</code></td><td>Layer 2</td><td>不可通行</td><td>50% (半掩體)</td><td>奴隸主作戰指揮中心</td></tr>
                <tr><td><code>[鐵籠] / [牢門]</code></td><td>Layer 2</td><td>1.5</td><td>75% (重掩體)</td><td>奴隸囚禁區，提供高額掩護</td></tr>
                <tr><td><code>[棧台] / [吊臂]</code></td><td>Layer 2</td><td>1.0</td><td>40%</td><td>高空採石升降平台，居高臨下</td></tr>
                <tr><td><code>[巨石條] / [碎石機]</code></td><td>Layer 2</td><td>不可通行</td><td>80% (巨型重掩體)</td><td>開採出來的巨型原石條塊</td></tr>
                <tr><td><code>[哨塔]</code></td><td>Layer 2</td><td>不可通行</td><td>100% (全掩體)</td><td>制高點狙擊警戒哨塔</td></tr>
                <tr><td><code>[拒馬]</code></td><td>Layer 2</td><td>不可通行</td><td>60%</td><td>刺樁阻絕陣地，近戰阻擋</td></tr>
                <tr><td><code>[刑柱] / [鎖鏈]</code></td><td>Layer 2.5</td><td>1.0</td><td>25% (輕掩體)</td><td>行刑威嚇地標</td></tr>
            </tbody>
        </table>
    </div>

    <!-- 3. Lightbox 模態框 (支援 800% 縮放與平移) -->
    <div id="lightbox-modal" class="lightbox-modal">
        <div class="lightbox-header">
            <div class="lightbox-title" id="lightbox-title">圖片檢視器</div>
            <div class="lightbox-toolbar">
                <span id="zoom-text" style="font-size: 13px; color: var(--text-secondary);">100%</span>
                <button class="lightbox-btn" onclick="zoomLightbox(0.5)">🔍 放大 (+)</button>
                <button class="lightbox-btn" onclick="zoomLightbox(-0.5)">🔍 縮小 (-)</button>
                <button class="lightbox-btn" onclick="resetLightboxZoom()">🔄 重置</button>
                <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
            </div>
        </div>
        <div class="lightbox-body" id="lightbox-body" onwheel="handleLightboxWheel(event)">
            <img id="lightbox-img" class="lightbox-img" src="" alt="Zoomable Image">
        </div>
    </div>

    <script>
        const b64Ext = "{b64_ext}";
        const b64Int = "{b64_int}";
        const semImgs = {{
            'merged': "{b64_sem_m}",
            'l1': "{b64_sem_l1}",
            'l2': "{b64_sem_l2}",
            'l25': "{b64_sem_l25}",
            'l3': "{b64_sem_l3}"
        }};

        function switchMainView(type) {{
            document.getElementById('btn-ext').classList.toggle('active', type === 'ext');
            document.getElementById('btn-int').classList.toggle('active', type === 'int');
            document.getElementById('main-img').src = type === 'ext' ? b64Ext : b64Int;
            document.getElementById('main-view-title').innerText = type === 'ext' 
                ? '進去前·外觀層全景 (view_exterior_merged.png)' 
                : '進去後·店內層全景 (view_interior_merged.png)';
        }}

        function switchSemView(key) {{
            document.querySelectorAll('.map-box .btn-toggle').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('sem-img').src = semImgs[key];
        }}

        let currentScale = 1;
        let translateX = 0;
        let translateY = 0;
        let isDragging = false;
        let startX, startY;

        function openLightbox(src, title) {{
            const modal = document.getElementById('lightbox-modal');
            const img = document.getElementById('lightbox-img');
            document.getElementById('lightbox-title').innerText = title || '像素級大圖放大檢驗';
            img.src = src;
            currentScale = 1;
            translateX = 0;
            translateY = 0;
            updateTransform();
            modal.style.display = 'flex';
        }}

        function closeLightbox() {{
            document.getElementById('lightbox-modal').style.display = 'none';
        }}

        function zoomLightbox(delta) {{
            currentScale = Math.max(0.5, Math.min(8.0, currentScale + delta));
            updateTransform();
        }}

        function resetLightboxZoom() {{
            currentScale = 1;
            translateX = 0;
            translateY = 0;
            updateTransform();
        }}

        function updateTransform() {{
            const img = document.getElementById('lightbox-img');
            img.style.transform = `scale(${{currentScale}}) translate(${{translateX}}px, ${{translateY}}px)`;
            document.getElementById('zoom-text').innerText = Math.round(currentScale * 100) + '%';
        }}

        function handleLightboxWheel(e) {{
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.3 : -0.3;
            zoomLightbox(delta);
        }}

        const body = document.getElementById('lightbox-body');
        body.addEventListener('mousedown', (e) => {{
            if (currentScale <= 1) return;
            isDragging = true;
            startX = e.clientX - translateX * currentScale;
            startY = e.clientY - translateY * currentScale;
        }});
        window.addEventListener('mousemove', (e) => {{
            if (!isDragging) return;
            translateX = (e.clientX - startX) / currentScale;
            translateY = (e.clientY - startY) / currentScale;
            updateTransform();
        }});
        window.addEventListener('mouseup', () => {{
            isDragging = false;
        }});
    </script>
</body>
</html>
"""

(brain_dir / "map_delivery_report_0_1.html").write_text(html_report, encoding="utf-8")
(reports_dir / "map_delivery_report_0_1_slave_camp.html").write_text(html_report, encoding="utf-8")

print("Generated and Isolated Western Slave Camp (0, 1) to its own directory successfully!")
