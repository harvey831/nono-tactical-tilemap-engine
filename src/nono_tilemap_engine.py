import math
import random
import base64
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# 專案路徑
repo_root = Path(__file__).resolve().parent.parent
assets_dir = repo_root / "assets"
reports_dir = repo_root / "reports"
assets_dir.mkdir(parents=True, exist_ok=True)
reports_dir.mkdir(parents=True, exist_ok=True)

# 顏色定義
SAND_BASE = (218, 178, 122, 255)
SAND_LIGHT = (235, 198, 145, 255)
SAND_DARK = (195, 152, 98, 255)
SAND_GRAIN = (168, 128, 78, 255)

CLAY_ROAD_BASE = (175, 122, 75, 255)
CLAY_ROAD_DARK = (142, 95, 52, 255)
CLAY_ROAD_LIGHT = (198, 145, 95, 255)
CLAY_RUT = (125, 80, 42, 255)

STONE_PLAZA_BASE = (135, 142, 155, 255)
STONE_PLAZA_DARK = (95, 102, 115, 255)
STONE_PLAZA_LIGHT = (172, 180, 195, 255)

FARM_EARTH_BASE = (118, 82, 48, 255)
FARM_CROP_GREEN = (145, 175, 55, 255)
FARM_CROP_GOLD = (215, 185, 45, 255)
FARM_FURROW = (88, 58, 32, 255)

WATER_DEEP = (45, 105, 185, 255)
WATER_SHALLOW = (65, 145, 225, 255)
WATER_FOAM = (195, 235, 255, 255)
WATER_BANK_STONE = (110, 115, 125, 255)

def draw_subtile(draw, px, py, sub_type, quadrant, terrain_type="clay"):
    base_col = CLAY_ROAD_BASE
    dark_col = CLAY_ROAD_DARK
    light_col = CLAY_ROAD_LIGHT
    
    if terrain_type == "stone":
        base_col, dark_col, light_col = STONE_PLAZA_BASE, STONE_PLAZA_DARK, STONE_PLAZA_LIGHT
    elif terrain_type == "farm":
        base_col, dark_col, light_col = FARM_EARTH_BASE, FARM_FURROW, FARM_CROP_GREEN
    elif terrain_type == "water":
        base_col, dark_col, light_col = WATER_DEEP, WATER_SHALLOW, WATER_BANK_STONE

    if sub_type == "SOLID":
        draw.rectangle([px, py, px + 15, py + 15], fill=base_col)
        if terrain_type == "clay":
            for _ in range(4):
                rx, ry = px + random.randint(1, 14), py + random.randint(1, 14)
                draw.point((rx, ry), fill=dark_col)
            draw.line([(px, py + 7), (px + 15, py + 7)], fill=CLAY_RUT, width=1)
        elif terrain_type == "stone":
            draw.rectangle([px + 1, py + 1, px + 14, py + 14], fill=base_col, outline=dark_col)
            draw.line([(px + 1, py + 1), (px + 14, py + 1)], fill=light_col)
        elif terrain_type == "farm":
            for fy in range(py + 2, py + 16, 4):
                draw.line([(px, fy), (px + 15, fy)], fill=FARM_FURROW, width=1)
                draw.line([(px, fy + 1), (px + 15, fy + 1)], fill=FARM_CROP_GOLD, width=1)
        elif terrain_type == "water":
            draw.rectangle([px, py, px + 15, py + 15], fill=WATER_DEEP)
            draw.line([(px + 2, py + 5), (px + 13, py + 5)], fill=WATER_SHALLOW, width=1)
            draw.line([(px + 4, py + 11), (px + 11, py + 11)], fill=WATER_FOAM, width=1)

    elif sub_type == "OUTER":
        if quadrant == "TL":
            draw.pieslice([px - 14, py - 14, px + 18, py + 18], 0, 90, fill=base_col, outline=dark_col)
            draw.point((px + 4, py + 1), fill=dark_col)
            draw.point((px + 1, py + 4), fill=dark_col)
        elif quadrant == "TR":
            draw.pieslice([px - 4, py - 14, px + 28, py + 18], 90, 180, fill=base_col, outline=dark_col)
            draw.point((px + 11, py + 1), fill=dark_col)
            draw.point((px + 14, py + 4), fill=dark_col)
        elif quadrant == "BL":
            draw.pieslice([px - 14, py - 4, px + 18, py + 28], 270, 360, fill=base_col, outline=dark_col)
            draw.point((px + 4, py + 14), fill=dark_col)
            draw.point((px + 1, py + 11), fill=dark_col)
        elif quadrant == "BR":
            draw.pieslice([px - 4, py - 4, px + 28, py + 28], 180, 270, fill=base_col, outline=dark_col)
            draw.point((px + 11, py + 14), fill=dark_col)
            draw.point((px + 14, py + 11), fill=dark_col)

    elif sub_type == "INNER":
        draw.rectangle([px, py, px + 15, py + 15], fill=base_col)
        if quadrant == "TL":
            draw.polygon([(px, py), (px + 6, py), (px, py + 6)], fill=SAND_BASE, outline=dark_col)
        elif quadrant == "TR":
            draw.polygon([(px + 15, py), (px + 9, py), (px + 15, py + 6)], fill=SAND_BASE, outline=dark_col)
        elif quadrant == "BL":
            draw.polygon([(px, py + 15), (px + 6, py + 15), (px, py + 9)], fill=SAND_BASE, outline=dark_col)
        elif quadrant == "BR":
            draw.polygon([(px + 15, py + 15), (px + 9, py + 15), (px + 15, py + 9)], fill=SAND_BASE, outline=dark_col)

    elif sub_type == "EDGE_V":
        draw.rectangle([px, py, px + 15, py + 15], fill=base_col)
        if quadrant in ("TL", "BL"):
            draw.rectangle([px, py, px + 3, py + 15], fill=SAND_BASE)
            for sy in range(py, py + 16, 3):
                draw.point((px + 4, sy), fill=dark_col)
                if sy % 6 == 0: draw.point((px + 2, sy), fill=base_col)
        else:
            draw.rectangle([px + 12, py, px + 15, py + 15], fill=SAND_BASE)
            for sy in range(py, py + 16, 3):
                draw.point((px + 11, sy), fill=dark_col)
                if sy % 6 == 0: draw.point((px + 13, sy), fill=base_col)

    elif sub_type == "EDGE_H":
        draw.rectangle([px, py, px + 15, py + 15], fill=base_col)
        if quadrant in ("TL", "TR"):
            draw.rectangle([px, py, px + 15, py + 3], fill=SAND_BASE)
            for sx in range(px, px + 16, 3):
                draw.point((sx, py + 4), fill=dark_col)
                if sx % 6 == 0: draw.point((sx, py + 2), fill=base_col)
        else:
            draw.rectangle([px, py + 12, px + 15, py + 15], fill=SAND_BASE)
            for sx in range(px, px + 16, 3):
                draw.point((sx, py + 11), fill=dark_col)
                if sx % 6 == 0: draw.point((sx, py + 13), fill=base_col)

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
    print("Executing nono_tilemap_engine: 12~47 Autotile topological transitions & 4-Layer SSOT pipeline...")
    img_clay_47t = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d_47 = ImageDraw.Draw(img_clay_47t)
    for ty in range(4):
        for tx in range(4):
            cpx, cpy = tx * 32, ty * 32
            draw_subtile(d_47, cpx, cpy, "SOLID", "TL", "clay")
            draw_subtile(d_47, cpx + 16, cpy, "EDGE_H", "TR", "clay")
            draw_subtile(d_47, cpx, cpy + 16, "EDGE_V", "BL", "clay")
            draw_subtile(d_47, cpx + 16, cpy + 16, "OUTER", "BR", "clay")
    img_clay_47t.save(assets_dir / "autotile_clay_sand_32px_47t.png")
    print(f"Generated {assets_dir / 'autotile_clay_sand_32px_47t.png'}")
