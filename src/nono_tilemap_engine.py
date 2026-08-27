import math
import random
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 顏色定義 - 荒原極致美學調色盤
SAND_BASE = (226, 192, 142, 255)
SAND_LIGHT = (242, 214, 168, 255)
SAND_DARK = (204, 166, 114, 255)
SAND_GRAIN = (165, 126, 78, 255)

CLAY_BASE = (176, 126, 76, 255)
CLAY_LIGHT = (198, 148, 96, 255)
CLAY_DARK = (144, 96, 52, 255)
CLAY_RUT = (118, 74, 36, 255)
CLAY_PEBBLE = (160, 165, 175, 255)

STONE_BASE = (142, 148, 158, 255)
STONE_LIGHT = (178, 186, 198, 255)
STONE_DARK = (102, 108, 118, 255)
STONE_MORTAR = (74, 78, 86, 255)
STONE_WARM = (152, 144, 138, 255)

FARM_BASE = (124, 88, 52, 255)
FARM_FURROW = (82, 54, 28, 255)
FARM_GREEN = (152, 178, 62, 255)
FARM_GOLD = (224, 192, 54, 255)

WATER_DEEP = (48, 108, 188, 255)
WATER_MID = (72, 148, 226, 255)
WATER_RIPPLE = (175, 225, 255, 255)
WATER_BANK = (112, 118, 128, 255)

# ==============================================================================
# 0. 構建四層純語意 40x40 矩陣 (SSOT)
# ==============================================================================
grid_l1 = [["[沙]" for _ in range(40)] for _ in range(40)]
grid_l2 = [["[ · ]" for _ in range(40)] for _ in range(40)]
grid_l25 = [["[ · ]" for _ in range(40)] for _ in range(40)]
grid_l3 = [["[ · ]" for _ in range(40)] for _ in range(40)]

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

# 1. 大酒館 (西南: gx=4..11, gy=25..30)
for gx in range(4, 12):
    for gy in range(25, 28): grid_l3[gy][gx] = "[▲酒頂]"
    for gy in range(28, 31): grid_l2[gy][gx] = "[酒地]"
grid_l2[28][5] = "[吧台]"; grid_l2[28][6] = "[吧台]"
grid_l2[28][10] = "[壁爐]"; grid_l2[30][7] = "[酒門]"

# 2. 鐵匠鋪 (東北: gx=26..31, gy=5..10)
for gx in range(26, 32):
    for gy in range(5, 7): grid_l3[gy][gx] = "[▲鐵頂]"
    for gy in range(7, 11): grid_l2[gy][gx] = "[鐵地]"
grid_l2[7][27] = "[武架]"; grid_l2[8][30] = "[鐵砧]"; grid_l2[10][28] = "[鐵門]"

# 3. 雜貨鋪 (西北: gx=8..13, gy=5..10)
for gx in range(8, 14):
    for gy in range(5, 7): grid_l3[gy][gx] = "[▲店頂]"
    for gy in range(7, 11): grid_l2[gy][gx] = "[店地]"
grid_l2[7][9] = "[藥架]"; grid_l2[8][12] = "[金箱]"; grid_l2[10][10] = "[店門]"

grid_l2[19][22] = "[水井]"
grid_l2[9][33] = "[熔爐]"
grid_l2[4][3] = "[哨塔]"; grid_l3[3][3] = "[▲塔頂]"
grid_l2[18][17] = "[果攤]"; grid_l2[18][26] = "[器攤]"

random.seed(99)
for _ in range(35):
    rx, ry = random.randint(1, 38), random.randint(1, 38)
    if grid_l1[ry][rx] == "[沙]" and grid_l2[ry][rx] == "[ · ]":
        grid_l25[ry][rx] = random.choice(["[碎石]", "[枯草]", "[木箱]", "[木桶]"])

# ==============================================================================
# 1. 8 鄰居二進制遮罩計算函數 (8-Neighbor Autotile Bitmask Resolver)
# ==============================================================================
def resolve_tile_autotile(grid, x, y, terrain_token):
    def match(gx, gy):
        if 0 <= gx < 40 and 0 <= gy < 40:
            return grid[gy][gx] == terrain_token
        return False

    n  = match(x, y - 1)
    s  = match(x, y + 1)
    w  = match(x - 1, y)
    e  = match(x + 1, y)
    nw = match(x - 1, y - 1) and n and w
    ne = match(x + 1, y - 1) and n and e
    sw = match(x - 1, y + 1) and s and w
    se = match(x + 1, y + 1) and s and e

    if not n and not w: st_tl = "OUTER"
    elif n and not w:   st_tl = "EDGE_V"
    elif not n and w:   st_tl = "EDGE_H"
    elif n and w and not nw: st_tl = "INNER"
    else: st_tl = "SOLID"

    if not n and not e: st_tr = "OUTER"
    elif n and not e:   st_tr = "EDGE_V"
    elif not n and e:   st_tr = "EDGE_H"
    elif n and e and not ne: st_tr = "INNER"
    else: st_tr = "SOLID"

    if not s and not w: st_bl = "OUTER"
    elif s and not w:   st_bl = "EDGE_V"
    elif not s and w:   st_bl = "EDGE_H"
    elif s and w and not sw: st_bl = "INNER"
    else: st_bl = "SOLID"

    if not s and not e: st_br = "OUTER"
    elif s and not e:   st_br = "EDGE_V"
    elif not s and e:   st_br = "EDGE_H"
    elif s and e and not se: st_br = "INNER"
    else: st_br = "SOLID"

    return st_tl, st_tr, st_bl, st_br

if __name__ == "__main__":
    print("Executing standalone nono_tilemap_engine pipeline...")
