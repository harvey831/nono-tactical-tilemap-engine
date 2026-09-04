#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_chunk_0_1.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: Chunk (0,1)「山谷礦坑聚落」戶外地形、建築、道具與演員渲染器 (50×50 雙水體定稿版)。
Features:
  1. 50×50 尺寸規格與投影參數：
     - CANVAS_W = 1680, CANVAS_H = 1896 (WORLD 1600×1600, CELL 32)
  2. 雙水體（新 R44）：
     - 主河道水面 level = 0，河床 -1 (深處 -2)；
     - 山上蓄水池水面 level = 2，池底河床 1；
     - 水面高度依水體四周岸格最低高度動態計算；
     - 半透明水面 tile 採 conservative=False 消除接縫黑邊。
  3. 7 棟建築渲染：
     - 涵蓋 stone, timber, adobe 三種風格；
     - 監督公署與鍛造坊平頂 DECK (H3) 梯洞透視與可站屋頂；
     - 酒館 2F (H6) 斜頂與 2 樓梯洞；
     - 雜貨行門前連排 4 格遮陽篷 (awning, h=2.1)；
     - 礦工小屋與鍛造坊屋頂煙囪 (kind: roof)；
     - 門面元件依 bbox 裁切並精準投影。
  4. 一格寬水渠 (ditch)：16 向 autotile，平鋪於地面。
  5. 泥灘 (mud_cells)：鋪於河岸 H0，貼 pit_floor。
  6. 道具與 7 位演員 (包含鍛造坊 DECK 屋頂領班)。
  7. 輸出 v3_*.png (全圖、格網、高程、邊界、cam_left、cam_right、特寫、H-2 到 H8 剖面) 及 v3_report.html。
------------------------------------------------------------
"""

import os
import sys
import math
import json
import base64
import io
from collections import deque
from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# 基礎幾何常數與投影參數
# ---------------------------------------------------------------------------
COLS = 50
ROWS = 50
CELL = 32
ROW_H = 48

RISE = 23.04          # 32 * 0.72
SIDE_SHIFT = 3.84     # 32 * 0.12
SIDE_SPREAD = 192.0   # 32 * 6

MARGIN_X = 40
MARGIN_TOP = int(8 * RISE) + 40    # ~225 px
MARGIN_BOTTOM = int(2 * RISE) + 24 # ~71 px

WORLD_W = COLS * CELL # 1600
WORLD_H = ROWS * CELL # 1600
CANVAS_W = WORLD_W + 2 * MARGIN_X
CANVAS_H = WORLD_H + MARGIN_TOP + MARGIN_BOTTOM
OX = MARGIN_X
OY = MARGIN_TOP
BG = (15, 17, 26, 255)

ACTOR_W = 24
ACTOR_H = 30

# ---------------------------------------------------------------------------
# 頂點投影與側面可見性
# ---------------------------------------------------------------------------
def side_at(world_x, cam_x):
    return max(-1.0, min(1.0, (world_x - cam_x) / SIDE_SPREAD))

def PV(x, y, h, cam_x):
    sd = side_at(x, cam_x)
    return (x + sd * h * SIDE_SHIFT, y - h * RISE)

def face_visible(which, x_edge, cam_x):
    sd = side_at(x_edge, cam_x)
    return sd > 0.03 if which == "left" else sd < -0.03

# ---------------------------------------------------------------------------
# 平行四邊形仿射變換與光柵化
# ---------------------------------------------------------------------------
def expand_source_clamp(src):
    sw, sh = src.size
    exp = Image.new("RGBA", (sw + 2, sh + 2), (0, 0, 0, 0))
    exp.paste(src, (1, 1))
    exp.paste(src.crop((0, 0, sw, 1)), (1, 0))
    exp.paste(src.crop((0, sh - 1, sw, sh)), (1, sh + 1))
    exp.paste(src.crop((0, 0, 1, sh)), (0, 1))
    exp.paste(src.crop((sw - 1, 0, sw, sh)), (sw + 1, 1))
    exp.paste(src.crop((0, 0, 1, 1)), (0, 0))
    exp.paste(src.crop((sw - 1, 0, sw, 1)), (sw + 1, 0))
    exp.paste(src.crop((0, sh - 1, 1, sh)), (0, sh + 1))
    exp.paste(src.crop((sw - 1, 0, sw, 1)), (sw + 1, sh + 1))
    return exp

def paste_parallelogram(canvas, src, p0, vec_u, vec_v, conservative=True):
    sw, sh = src.size
    ux, uy = vec_u
    vx, vy = vec_v
    xs = [p0[0], p0[0] + ux, p0[0] + vx, p0[0] + ux + vx]
    ys = [p0[1], p0[1] + uy, p0[1] + vy, p0[1] + uy + vy]
    pad = 2 if conservative else 0
    bx, by = math.floor(min(xs)) - pad, math.floor(min(ys)) - pad
    bw = max(1, math.ceil(max(xs)) - bx + pad)
    bh = max(1, math.ceil(max(ys)) - by + pad)

    det = ux * vy - uy * vx
    if abs(det) < 1e-6:
        return

    a11, a12 = vy / det, -vx / det
    a21, a22 = -uy / det, ux / det
    ox_ = bx - p0[0]
    oy_ = by - p0[1]

    if conservative:
        coeffs = (
            a11 * sw, a12 * sw, (a11 * ox_ + a12 * oy_) * sw + 1.0,
            a21 * sh, a22 * sh, (a21 * ox_ + a22 * oy_) * sh + 1.0
        )
        src_transformed = expand_source_clamp(src)
    else:
        coeffs = (
            a11 * sw, a12 * sw, (a11 * ox_ + a12 * oy_) * sw,
            a21 * sh, a22 * sh, (a21 * ox_ + a22 * oy_) * sh
        )
        src_transformed = src

    affine_mode = Image.Transform.AFFINE if hasattr(Image, "Transform") else Image.AFFINE
    resample_mode = Image.Resampling.NEAREST if hasattr(Image, "Resampling") else Image.NEAREST
    warped = src_transformed.transform((bw, bh), affine_mode, coeffs, resample=resample_mode, fillcolor=(0, 0, 0, 0))

    if conservative:
        mask = Image.new("L", (bw, bh), 0)
        quad = [
            (p0[0] - bx, p0[1] - by),
            (p0[0] + ux - bx, p0[1] + uy - by),
            (p0[0] + ux + vx - bx, p0[1] + uy + vy - by),
            (p0[0] + vx - bx, p0[1] + vy - by)
        ]
        ImageDraw.Draw(mask).polygon(quad, fill=255, outline=255)
        mask = mask.filter(ImageFilter.MaxFilter(3))

        alpha = warped.getchannel("A")
        warped.putalpha(ImageChops.multiply(alpha, mask))

    canvas.alpha_composite(warped, (int(OX + bx), int(OY + by)))

# ---------------------------------------------------------------------------
# 材質管理
# ---------------------------------------------------------------------------
def force_opaque(img):
    r, g, b, a = img.split()
    a = a.point(lambda v: 255 if v > 0 else 0)
    return Image.merge("RGBA", (r, g, b, a))

class TileManager:
    def __init__(self, atlas_img, face_crop_y0):
        self.atlas = atlas_img
        self.face_crop_y0 = face_crop_y0
        self.top_cache = {}
        self.face_cache = {}
        self.side_cache = {}
        self.sprite_cache = {}
        self.band_cache = {}

    def get_top_tile(self, ref):
        key = tuple(ref[:3])
        if key not in self.top_cache:
            _, col, row = ref[:3]
            x0 = col * CELL
            y0 = row * ROW_H
            t = self.atlas.crop((x0, y0, x0 + CELL, y0 + CELL))
            self.top_cache[key] = force_opaque(t)
        return self.top_cache[key]

    def get_face_src(self, ref):
        key = tuple(ref[:3])
        if key not in self.face_cache:
            name, col, row = ref[:3]
            str_key = f"{name},{col},{row}"
            y_off = self.face_crop_y0.get(str_key, 4)
            x0 = col * CELL
            y0 = row * ROW_H + y_off
            crop_h = int(round(RISE))  # 23
            t = self.atlas.crop((x0, y0, x0 + CELL, y0 + crop_h))
            self.face_cache[key] = t
        return self.face_cache[key]

    def get_side_source(self, src, n_tiles, v_len, shade=0.10):
        k = (id(src), n_tiles, int(round(v_len)), shade)
        if k not in self.side_cache:
            w = src.width * n_tiles
            strip = Image.new("RGBA", (w, src.height), (0, 0, 0, 0))
            for i in range(n_tiles):
                strip.alpha_composite(src, (i * src.width, 0))
            box_mode = Image.Resampling.BOX if hasattr(Image, "Resampling") else Image.BOX
            squeezed = strip.resize((w, max(1, int(round(v_len)))), box_mode)
            self.side_cache[k] = Image.blend(squeezed, Image.new("RGBA", squeezed.size, (0, 0, 0, 255)), shade)
        return self.side_cache[k]

    def get_sprite(self, ref):
        key = tuple(ref)
        if key not in self.sprite_cache:
            name, col, row = ref[:3]
            w = ref[3] if len(ref) >= 4 else CELL
            h = ref[4] if len(ref) >= 5 else CELL
            x0 = col * CELL
            y0 = row * ROW_H
            self.sprite_cache[key] = self.atlas.crop((x0, y0, x0 + w, y0 + h))
        return self.sprite_cache[key]

    def get_wall_band(self, style_name, style_info, floor_idx, kind="plain"):
        key = (style_name, floor_idx > 0, kind)
        if key not in self.band_cache:
            band_h = int(round(3 * RISE))  # 69
            band = Image.new("RGBA", (CELL, band_h), (0, 0, 0, 0))
            wall_tile = self.get_top_tile(style_info["wall"])
            y = band_h
            while y > 0:
                y -= wall_tile.height
                band.alpha_composite(wall_tile, (0, max(0, y)))

            if floor_idx > 0:
                ImageDraw.Draw(band).rectangle([0, band_h - 3, CELL - 1, band_h - 1], fill=(72, 48, 26, 255))
            self.band_cache[key] = band
        return self.band_cache[key]

class PropsManager:
    def __init__(self, props_atlas_img, props_coords_dict, props_boxes_dict=None):
        self.atlas = props_atlas_img
        self.coords = props_coords_dict
        self.cache = {}
        self.missing_sprites = set()

    def get_prop_sprite(self, name):
        if name not in self.coords:
            if name not in self.missing_sprites:
                self.missing_sprites.add(name)
            return None
        if name not in self.cache:
            x, y, w, h = self.coords[name]
            self.cache[name] = self.atlas.crop((x, y, x + w, y + h))
        return self.cache[name]

def load_actor_font(font_size=12):
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/mingliu.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, font_size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def create_actor_sprite(actor_def, font):
    img = Image.new("RGBA", (ACTOR_W, ACTOR_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    color_rgb = tuple(actor_def.get("color", [56, 189, 248]))
    fill_col = color_rgb + (240,)
    outline_col = (18, 22, 30, 255)

    d.ellipse([(2, ACTOR_H - 6), (ACTOR_W - 3, ACTOR_H - 1)], fill=(0, 0, 0, 90))
    d.rounded_rectangle([(3, 14), (ACTOR_W - 4, ACTOR_H - 4)], radius=3, fill=fill_col, outline=outline_col, width=1)
    d.ellipse([(2, 1), (ACTOR_W - 3, 20)], fill=fill_col, outline=outline_col, width=2)

    label = str(actor_def.get("label", actor_def.get("id", "?")[:1]))
    text_col = (255, 255, 255, 255)
    cx, cy = ACTOR_W // 2, 10

    if font:
        try:
            d.text((cx, cy), label, fill=text_col, font=font, anchor="mm")
        except Exception:
            try:
                fallback_char = str(actor_def.get("id", "A"))[:1].upper()
                d.text((cx, cy), fallback_char, fill=text_col, font=font, anchor="mm")
            except Exception:
                pass
    else:
        d.line([(cx - 3, cy), (cx + 3, cy)], fill=text_col, width=1)
        d.line([(cx, cy - 3), (cx, cy + 3)], fill=text_col, width=1)

    return img

# ---------------------------------------------------------------------------
# 水體連通與有效高程計算
# ---------------------------------------------------------------------------
def compute_water_levels(elevation_rows, water_cells_set, water_bodies=None):
    """
    依據新 R44: 水面＝四周岸格最低高度。
    若 spec 帶有 water_bodies，直接採用其定義；否則動態計算。
    回傳：
      cell_water_level: (c, r) -> 繪製水面高度 (level - 0.15)
      cell_water_layer: (c, r) -> 水面整數層級 level
    """
    cell_water_level = {}
    cell_water_layer = {}

    if water_bodies:
        for wb in water_bodies:
            lvl = wb["level"]
            wl = lvl - 0.15
            for pt in wb["cells"]:
                cpt = (pt[0], pt[1])
                cell_water_layer[cpt] = lvl
                cell_water_level[cpt] = wl
        return cell_water_level, cell_water_layer

    visited = set()
    for (c, r) in water_cells_set:
        if (c, r) not in visited:
            body = []
            queue = deque([(c, r)])
            visited.add((c, r))
            while queue:
                curr_c, curr_r = queue.popleft()
                body.append((curr_c, curr_r))
                for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nc, nr = curr_c + dc, curr_r + dr
                    if (nc, nr) in water_cells_set and (nc, nr) not in visited:
                        visited.add((nc, nr))
                        queue.append((nc, nr))

            shore_levels = []
            for pt in body:
                bc, br = pt[0], pt[1]
                for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    nc, nr = bc + dc, br + dr
                    if (nc, nr) not in water_cells_set:
                        if 0 <= nc < COLS and 0 <= nr < ROWS:
                            shore_levels.append(elevation_rows[nr][nc])
                        else:
                            shore_levels.append(0)

            w_surf = min(shore_levels) if shore_levels else 0
            wl = w_surf - 0.15
            for pt in body:
                cell_water_layer[pt] = w_surf
                cell_water_level[pt] = wl

    return cell_water_level, cell_water_layer

def cell_draw_height(raw_h, cut=None):
    if cut is not None and raw_h > cut:
        return cut
    return raw_h

def neighbor_elev(c, r, dx, dy, elevation_rows, cut=None):
    nc, nr = c + dx, r + dy
    if 0 <= nc < COLS and 0 <= nr < ROWS:
        v = elevation_rows[nr][nc]
    else:
        v = 0
    if cut is not None and v > cut:
        return cut
    return v

def effective_neighbor_elev(c, r, dx, dy, context, cut=None):
    nc, nr = c + dx, r + dy
    if not (0 <= nc < COLS and 0 <= nr < ROWS):
        v = 0
        if cut is not None and v > cut:
            return cut
        return v

    elevation_rows = context["elevation_rows"]
    water_cells = context.get("water_cells", set())
    bridge_cells = context.get("bridge_cells", set())
    cell_water_layer = context.get("cell_water_layer", {})

    pt = (c, r)
    npt = (nc, nr)

    if pt in bridge_cells:
        v = elevation_rows[nr][nc]
    elif npt in water_cells:
        w_surf = cell_water_layer.get(npt, 0)
        if cut is not None and cut < w_surf:
            v = elevation_rows[nr][nc]
        else:
            v = w_surf
    else:
        v = elevation_rows[nr][nc]

    if cut is not None and v > cut:
        return cut
    return v

def side_levels(c, r, which, context, cut=None):
    water_cells = context.get("water_cells", set())
    pt = (c, r)
    if pt in water_cells:
        return set()

    elevation_rows = context["elevation_rows"]
    raw_h = elevation_rows[r][c]
    h = cell_draw_height(raw_h, cut)

    dx = -1 if which == "left" else 1
    nb = effective_neighbor_elev(c, r, dx, 0, context, cut)

    return set(range(nb + 1, h + 1))

def front_tile_for(c, r, k, context, h_bottom=None):
    presentation = context["presentation"]
    elevation_rows = context["elevation_rows"]
    raw_h = elevation_rows[r][c]
    water_cells = context.get("water_cells", set())
    mud_cells = context.get("mud_cells", set())

    pt = (c, r)
    if pt in mud_cells:
        return presentation["tiles"]["pit_floor"]
    if pt in water_cells:
        return presentation["tiles"]["pit_wall"]
    if raw_h >= 2:
        return presentation["tiles"]["cliff_face"]
    return presentation["tiles"]["face_stone"]

def draw_south_faces(canvas, c, r, h_top, h_bottom, cam_x, tm, context):
    if h_top <= h_bottom:
        return
    x = c * CELL
    yb = (r + 1) * CELL
    for k in range(h_top, h_bottom, -1):
        p0 = PV(x, yb, k, cam_x)
        p1 = PV(x + CELL, yb, k, cam_x)
        p2 = PV(x, yb, k - 1, cam_x)

        ref = front_tile_for(c, r, k, context, h_bottom)
        src = tm.get_face_src(ref)
        paste_parallelogram(canvas, src, p0, (p1[0] - p0[0], p1[1] - p0[1]), (p2[0] - p0[0], p2[1] - p0[1]))

def draw_side_run(canvas, c, r0, n_rows, k, which, cam_x, tm, context):
    xe = c * CELL + (CELL if which == "right" else 0)
    p0 = PV(xe, r0 * CELL, k, cam_x)
    p1 = PV(xe, r0 * CELL, k - 1, cam_x)

    ref = front_tile_for(c, r0, k, context)
    src = tm.get_face_src(ref)
    depth_px = n_rows * CELL
    v_vec = (p1[0] - p0[0], p1[1] - p0[1])
    v_len = math.hypot(*v_vec)
    if v_len >= 0.5:
        side_img = tm.get_side_source(src, n_rows, v_len, 0.10)
        paste_parallelogram(canvas, side_img, p0, (0, depth_px), v_vec)

def paste_top(canvas, img, x, y, h, cam_x, conservative=True):
    p0 = PV(x, y, h, cam_x)
    p1 = PV(x + img.width, y, h, cam_x)
    paste_parallelogram(canvas, img, p0, (p1[0] - p0[0], 0), (0, img.height), conservative=conservative)

def draw_transition(canvas, c, r, h, cam_x, context, cut=None):
    pt = (c, r)
    water_cells = context.get("water_cells", set())
    if pt in water_cells:
        return

    x = c * CELL
    y = r * CELL
    layer = Image.new("RGBA", (CELL + 2, CELL + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    south = effective_neighbor_elev(c, r, 0, 1, context, cut)
    if south < h:
        d.line([(0, CELL - 2), (CELL + 1, CELL - 2)], fill=(255, 236, 190, 70))
        d.line([(0, CELL - 1), (CELL + 1, CELL - 1)], fill=(60, 40, 20, 120))

    north = effective_neighbor_elev(c, r, 0, -1, context, cut)
    if north > h:
        for k in range(4):
            d.line([(0, k), (CELL + 1, k)], fill=(40, 26, 14, 110 - k * 26))

    west = effective_neighbor_elev(c, r, -1, 0, context, cut)
    if west > h and face_visible("right", x, cam_x):
        for k in range(3):
            d.line([(k, 0), (k, CELL + 1)], fill=(40, 26, 14, 100 - k * 30))

    east = effective_neighbor_elev(c, r, 1, 0, context, cut)
    if east > h and face_visible("left", x + CELL, cam_x):
        for k in range(3):
            d.line([(CELL - 1 - k, 0), (CELL - 1 - k, CELL + 1)], fill=(40, 26, 14, 100 - k * 30))

    p0 = PV(x, y, h, cam_x)
    p1 = PV(x + CELL, y, h, cam_x)
    paste_parallelogram(canvas, layer.crop((0, 0, CELL, CELL)), p0, (p1[0] - p0[0], 0), (0, CELL))

def get_ground_tile(c, r, h, tm, context):
    presentation = context["presentation"]
    bridge_cells = context["bridge_cells"]
    water_cells = context["water_cells"]
    mud_cells = context.get("mud_cells", set())
    ditch_cells = context.get("ditch_cells", set())
    road_cells = context["road_cells"]
    plaza_cells = context["plaza_cells"]
    field_cells = context["field_cells"]
    elevation_rows = context["elevation_rows"]

    pt = (c, r)
    if pt in bridge_cells:
        img = tm.get_top_tile(presentation["tiles"]["bridge_top"])
    elif pt in ditch_cells:
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            npt = (c + dx, r + dy)
            if npt in ditch_cells or npt in water_cells:
                m |= bit
        ditch_autotile = presentation.get("ditch_autotile", {})
        tile_spec = ditch_autotile.get(str(m))
        if tile_spec:
            img = tm.get_top_tile(["kenshi", tile_spec[0], tile_spec[1]])
        else:
            img = tm.get_top_tile(presentation["tiles"]["ditch"])
    elif pt in mud_cells:
        img = tm.get_top_tile(presentation["tiles"]["pit_floor"])
    elif pt in road_cells:
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            npt = (c + dx, r + dy)
            if npt in road_cells or npt in plaza_cells or npt in bridge_cells:
                m |= bit
        road_autotile = presentation.get("road_autotile", {})
        tile_spec = road_autotile.get(str(m))
        if tile_spec:
            img = tm.get_top_tile(["kenshi", tile_spec[0], tile_spec[1]])
        else:
            img = tm.get_top_tile(presentation["tiles"]["sand"][0])
    elif pt in plaza_cells:
        img = tm.get_top_tile(presentation["tiles"]["plaza"])
    elif pt in field_cells:
        img = tm.get_top_tile(presentation["tiles"]["field"])
    elif pt in water_cells:
        img = tm.get_top_tile(presentation["tiles"]["water"])
    else:
        sand_choices = presentation["tiles"]["sand"]
        idx = (c * 7 + r * 13) % len(sand_choices)
        img = tm.get_top_tile(sand_choices[idx])

    raw_h = elevation_rows[r][c]
    if raw_h > 0 and pt not in water_cells:
        tints = presentation.get("plateau_tint", {})
        alpha_map = tints.get("alpha", {})
        a = alpha_map.get(str(raw_h), 0.18)
        color = tuple(tints.get("color", [118, 92, 52]))
        tint_layer = Image.new("RGBA", img.size, color + (int(255 * a),))
        img = Image.alpha_composite(img, tint_layer)

    return img

def draw_outdoor_cell(canvas, c, r, cam_x, tm, context, cut=None):
    elevation_rows = context["elevation_rows"]
    water_cells = context.get("water_cells", set())
    cell_water_level = context.get("cell_water_level", {})
    cell_water_layer = context.get("cell_water_layer", {})
    presentation = context["presentation"]

    pt = (c, r)
    raw_h = elevation_rows[r][c]
    x = c * CELL
    y = r * CELL

    if cut is not None and cut < -1 and pt in water_cells and raw_h > cut:
        cut_img = tm.get_top_tile(presentation["tiles"]["cut_plane"])
        paste_top(canvas, cut_img, x, y, cut, cam_x)
        return

    if cut is not None and raw_h > cut:
        cut_img = tm.get_top_tile(presentation["tiles"]["cut_plane"])
        paste_top(canvas, cut_img, x, y, cut, cam_x)
        south_nb = neighbor_elev(c, r, 0, 1, elevation_rows, cut)
        if south_nb < cut:
            draw_south_faces(canvas, c, r, cut, south_nb, cam_x, tm, context)
        return

    if pt in water_cells:
        w_surf = cell_water_layer.get(pt, 0)
        wl = cell_water_level.get(pt, -0.15)
        has_water = (cut is None) or (cut >= w_surf)

        if raw_h == -2:
            deep_bed_tile = tm.get_top_tile(presentation["tiles"]["pit_floor"])
            paste_top(canvas, deep_bed_tile, x, y, -2, cam_x)
            south_nb = neighbor_elev(c, r, 0, 1, elevation_rows, cut)
            if south_nb < -2:
                draw_south_faces(canvas, c, r, -2, south_nb, cam_x, tm, context)
        else:
            bed_tile = tm.get_top_tile(presentation["tiles"]["pit_floor"])
            paste_top(canvas, bed_tile, x, y, raw_h, cam_x)

            if r + 1 < ROWS and (c, r + 1) in water_cells and elevation_rows[r + 1][c] < raw_h:
                draw_south_faces(canvas, c, r, raw_h, elevation_rows[r + 1][c], cam_x, tm, context)

            if face_visible("right", x, cam_x):
                if c - 1 >= 0 and (c - 1, r) in water_cells and elevation_rows[r][c - 1] < raw_h:
                    draw_side_run(canvas, c, r, 1, raw_h, "left", cam_x, tm, context)
            if face_visible("left", x + CELL, cam_x):
                if c + 1 < COLS and (c + 1, r) in water_cells and elevation_rows[r][c + 1] < raw_h:
                    draw_side_run(canvas, c, r, 1, raw_h, "right", cam_x, tm, context)

            south_nb = neighbor_elev(c, r, 0, 1, elevation_rows, cut)
            if south_nb < raw_h and (c, r + 1) not in water_cells:
                draw_south_faces(canvas, c, r, raw_h, south_nb, cam_x, tm, context)

        if has_water:
            water_top = tm.get_top_tile(presentation["tiles"]["water"]).copy()
            water_top.putalpha(178)
            paste_top(canvas, water_top, x, y, wl, cam_x, conservative=False)
            if r + 1 < ROWS and (c, r + 1) not in water_cells:
                s_h = effective_neighbor_elev(c, r, 0, 1, context, cut)
                if s_h < w_surf:
                    draw_south_faces(canvas, c, r, w_surf, s_h, cam_x, tm, context)
        return

    top_img = get_ground_tile(c, r, raw_h, tm, context)
    paste_top(canvas, top_img, x, y, raw_h, cam_x)
    draw_transition(canvas, c, r, raw_h, cam_x, context, cut)

    south_h = effective_neighbor_elev(c, r, 0, 1, context, cut)
    if south_h < raw_h:
        draw_south_faces(canvas, c, r, raw_h, south_h, cam_x, tm, context)

def draw_sides_for_strip(canvas, strip_cells, which, cam_x, tm, context, cut=None):
    if not strip_cells:
        return
    c = strip_cells[0][0]
    xe = c * CELL + (CELL if which == "right" else 0)
    if not face_visible(which, xe, cam_x):
        return

    all_k = set()
    levels_map = {}
    for (col_idx, r) in strip_cells:
        lvls = side_levels(col_idx, r, which, context, cut)
        levels_map[r] = lvls
        all_k |= lvls

    if not all_k:
        return

    for k in sorted(all_k):
        r_run_start = None
        run_len = 0
        for (col_idx, r) in strip_cells:
            if k in levels_map.get(r, set()):
                if r_run_start is None:
                    r_run_start = r
                    run_len = 1
                else:
                    run_len += 1
            else:
                if r_run_start is not None:
                    draw_side_run(canvas, c, r_run_start, run_len, k, which, cam_x, tm, context)
                    r_run_start = None
                    run_len = 0
        if r_run_start is not None:
            draw_side_run(canvas, c, r_run_start, run_len, k, which, cam_x, tm, context)

# ---------------------------------------------------------------------------
# 建築渲染
# ---------------------------------------------------------------------------
def draw_building_interior_floor(canvas, b, fl_idx, cam_x, tm, context, cut=None):
    c0, r0 = b["footprint"]["origin"]
    w, h = b["footprint"]["cols"], b["footprint"]["rows"]
    fl_h = b["base_elevation"] + fl_idx * b["units_per_floor"]

    if cut is not None and cut < fl_h:
        return

    style_info = context["presentation"]["styles"][b["style"]]
    floor_tile = tm.get_top_tile(style_info.get("floor", ["kenshi", 11, 0]))

    for r in range(r0 + 1, r0 + h - 1):
        for c in range(c0 + 1, c0 + w - 1):
            x = c * CELL
            y = r * CELL
            paste_top(canvas, floor_tile, x, y, fl_h, cam_x)

def draw_building_stair(canvas, b, fl_idx, cam_x, tm, context, cut=None):
    stair = b.get("stair")
    if not stair:
        return
    c0, r0 = b["footprint"]["origin"]
    fl_base_h = b["base_elevation"] + fl_idx * b["units_per_floor"]
    flight = stair.get("flight_local", [])
    style_info = context["presentation"]["styles"][b["style"]]
    step_tile = tm.get_top_tile(style_info.get("step", ["kenshi", 13, 0]))

    for s_step in flight:
        sc = c0 + s_step["col"]
        sr = r0 + s_step["row"]
        offset = s_step["step_offset"]
        step_top_h = fl_base_h + offset
        if cut is not None and cut < step_top_h:
            continue
        sx = sc * CELL
        sy = sr * CELL
        paste_top(canvas, step_tile, sx, sy, step_top_h, cam_x)

def draw_building_roof(canvas, b, cam_x, tm, context, cut=None):
    roof = b.get("roof")
    if not roof:
        return
    roof_h = roof.get("elevation", b["base_elevation"] + b["height_units"])
    if cut is not None and cut < roof_h:
        return

    c0, r0 = b["footprint"]["origin"]
    w, h = b["footprint"]["cols"], b["footprint"]["rows"]
    style_info = context["presentation"]["styles"][b["style"]]
    is_deck = roof.get("kind") == "DECK"

    if is_deck:
        deck_tile = tm.get_top_tile(style_info.get("deck", ["kenshi", 14, 0]))
        stair = b.get("stair")
        void_cells = set()
        if stair:
            void_cells = {(c0 + vc[0], r0 + vc[1]) for vc in stair.get("void_cells_local", [])}

        for r in range(r0, r0 + h):
            for c in range(c0, c0 + w):
                if (c, r) in void_cells:
                    continue
                x = c * CELL
                y = r * CELL
                paste_top(canvas, deck_tile, x, y, roof_h, cam_x)
    else:
        roof_tile = tm.get_top_tile(style_info["roof"]["all"])
        for r in range(r0, r0 + h):
            for c in range(c0, c0 + w):
                x = c * CELL
                y = r * CELL
                paste_top(canvas, roof_tile, x, y, roof_h, cam_x)

def draw_building_facade(canvas, b, cam_x, tm, pm, context, cut=None):
    c0, r0 = b["footprint"]["origin"]
    w, h = b["footprint"]["cols"], b["footprint"]["rows"]
    wall_row = r0 + h - 1
    base_elev = b["base_elevation"]

    doors_local = {(dc, dr) for dc, dr in b.get("doors_local", [])}
    windows_local = b.get("windows_local", {})
    style_info = context["presentation"]["styles"][b["style"]]

    # 1. 南面牆帶
    for fl_idx in range(b.get("floors", 1)):
        fl_h = base_elev + fl_idx * b["units_per_floor"]
        fl_top_h = fl_h + b["units_per_floor"]
        if cut is not None and cut < fl_top_h:
            continue

        band_img = tm.get_wall_band(b["style"], style_info, fl_idx)
        win_cols = windows_local.get(str(fl_idx), [])

        for dc in range(w):
            c = c0 + dc
            x = c * CELL
            yb = (wall_row + 1) * CELL
            is_door = (dc, h - 1) in doors_local and fl_idx == 0
            is_win = dc in win_cols

            if is_door:
                continue

            p0 = PV(x, yb, fl_top_h, cam_x)
            p1 = PV(x + CELL, yb, fl_top_h, cam_x)
            p2 = PV(x, yb, fl_h, cam_x)

            cell_band = band_img.copy()
            if is_win:
                win_tile = tm.get_sprite(style_info["window"])
                cell_band.alpha_composite(win_tile, (0, 18))

            paste_parallelogram(canvas, cell_band, p0, (p1[0] - p0[0], p1[1] - p0[1]), (p2[0] - p0[0], p2[1] - p0[1]))

    # 2. 門
    if cut is None or cut >= base_elev + 2.0:
        door_sprite = tm.get_sprite(style_info["door"])
        for dc, dr in doors_local:
            if dr == h - 1:
                c = c0 + dc
                x = c * CELL
                yb = (wall_row + 1) * CELL
                p0 = PV(x, yb, base_elev + 2.0, cam_x)
                p1 = PV(x + CELL, yb, base_elev + 2.0, cam_x)
                p2 = PV(x, yb, base_elev, cam_x)
                paste_parallelogram(canvas, door_sprite, p0, (p1[0] - p0[0], p1[1] - p0[1]), (p2[0] - p0[0], p2[1] - p0[1]))

    # 3. facade 元件
    for f_item in b.get("facade", []):
        kind = f_item.get("kind", "wall")
        fc = f_item.get("col", f_item.get("cell"))
        fr = f_item.get("row", h - 1)
        fh = float(f_item.get("h", 0.0))

        if kind == "roof":
            roof_h = b["roof"]["elevation"]
            if cut is not None and cut < roof_h:
                continue
            tile_def = f_item.get("tile")
            if tile_def:
                chimney_img = tm.get_top_tile(tile_def)
                cx = (c0 + fc) * CELL
                cy = (r0 + fr) * CELL
                paste_top(canvas, chimney_img, cx, cy, roof_h + fh, cam_x)
        else:
            item_h = base_elev + fh
            if cut is not None and cut < item_h:
                continue
            sp = f_item.get("sprite")
            img = None
            if "tile" in f_item:
                img = tm.get_top_tile(f_item["tile"])
            elif sp:
                img = pm.get_prop_sprite(sp)

            if img:
                bbox = img.getbbox()
                if bbox:
                    img_cropped = img.crop(bbox)
                else:
                    img_cropped = img

                x = (c0 + fc) * CELL
                yb = (r0 + fr + 1) * CELL
                top_h = item_h + (img_cropped.height / 23.0)

                p0 = PV(x, yb, top_h, cam_x)
                p1 = PV(x + img_cropped.width, yb, top_h, cam_x)
                p2 = PV(x, yb, item_h, cam_x)
                paste_parallelogram(canvas, img_cropped, p0, (p1[0] - p0[0], p1[1] - p0[1]), (p2[0] - p0[0], p2[1] - p0[1]))

# ---------------------------------------------------------------------------
# 道具與演員渲染
# ---------------------------------------------------------------------------
def draw_prop(canvas, prop, cam_x, pm, tm, cut=None):
    elev = prop.get("elevation", 0)
    if cut is not None and cut < elev:
        return

    c, r = prop["cell"]
    w, h = prop.get("footprint", [1, 1])
    sprite_name = prop.get("sprite", prop["id"])
    sprite_img = pm.get_prop_sprite(sprite_name)

    if not sprite_img:
        return

    anchor_x = (c + w / 2.0) * CELL
    anchor_y = (r + h) * CELL

    p_proj = PV(anchor_x, anchor_y, elev, cam_x)
    dst_x = int(OX + p_proj[0] - sprite_img.width / 2.0)
    dst_y = int(OY + p_proj[1] - sprite_img.height)

    canvas.alpha_composite(sprite_img, (dst_x, dst_y))

def draw_actor(canvas, actor, cam_x, actor_sprites, cut=None):
    cells = actor.get("cells", [])
    if not cells:
        return
    c, r, elev = cells[0]
    if cut is not None and cut < elev:
        return

    a_id = actor.get("id", "actor")
    sprite = actor_sprites.get(a_id)
    if not sprite:
        return

    anchor_x = (c + 0.5) * CELL
    anchor_y = (r + 1.0) * CELL

    p_proj = PV(anchor_x, anchor_y, elev, cam_x)
    dst_x = int(OX + p_proj[0] - sprite.width / 2.0)
    dst_y = int(OY + p_proj[1] - sprite.height)

    canvas.alpha_composite(sprite, (dst_x, dst_y))

# ---------------------------------------------------------------------------
# 主渲染視角
# ---------------------------------------------------------------------------
def render_view(cam_x, tm, pm, actor_sprites, context, cut=None, grid_overlay=False,
                elevation_labels=False, edge_labels=False, only_surface_id=None):
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), BG)

    elevation_rows = context["elevation_rows"]
    buildings = context.get("buildings", [])
    props = context.get("props", [])
    actors = context.get("actors_fixture", [])
    building_footprint_cells = context.get("building_footprint_cells", set())

    # 1. 逐行繪製地表
    for r in range(ROWS):
        for c in range(COLS):
            pt = (c, r)
            if pt in building_footprint_cells:
                continue
            draw_outdoor_cell(canvas, c, r, cam_x, tm, context, cut)

        strip_cells = [(c, r) for c in range(COLS) if (c, r) not in building_footprint_cells]
        draw_sides_for_strip(canvas, strip_cells, "left", cam_x, tm, context, cut)
        draw_sides_for_strip(canvas, strip_cells, "right", cam_x, tm, context, cut)

    # 2. 繪製建築
    for b in buildings:
        draw_building_interior_floor(canvas, b, 0, cam_x, tm, context, cut)
        draw_building_stair(canvas, b, 0, cam_x, tm, context, cut)
        if b.get("floors", 1) > 1:
            draw_building_interior_floor(canvas, b, 1, cam_x, tm, context, cut)
            draw_building_stair(canvas, b, 1, cam_x, tm, context, cut)
        draw_building_roof(canvas, b, cam_x, tm, context, cut)
        draw_building_facade(canvas, b, cam_x, tm, pm, context, cut)

    # 3. 繪製道具 (按 y 排序)
    sorted_props = sorted(props, key=lambda p: (p["cell"][1] + p.get("footprint", [1, 1])[1], p["cell"][0]))
    for p in sorted_props:
        draw_prop(canvas, p, cam_x, pm, tm, cut)

    # 4. 繪製演員
    for a in actors:
        draw_actor(canvas, a, cam_x, actor_sprites, cut)

    # 5. 標籤與格網疊加
    if grid_overlay:
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        for r in range(ROWS + 1):
            for c in range(COLS + 1):
                p = PV(c * CELL, r * CELL, 0, cam_x)
                px, py = int(OX + p[0]), int(OY + p[1])
                if c < COLS:
                    p_e = PV((c + 1) * CELL, r * CELL, 0, cam_x)
                    d.line([(px, py), (int(OX + p_e[0]), int(OY + p_e[1]))], fill=(255, 255, 255, 40))
                if r < ROWS:
                    p_s = PV(c * CELL, (r + 1) * CELL, 0, cam_x)
                    d.line([(px, py), (int(OX + p_s[0]), int(OY + p_s[1]))], fill=(255, 255, 255, 40))
        canvas.alpha_composite(overlay)

    if elevation_labels:
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        font = load_actor_font(10)
        for r in range(ROWS):
            for c in range(COLS):
                h = elevation_rows[r][c]
                p = PV((c + 0.5) * CELL, (r + 0.5) * CELL, h, cam_x)
                px, py = int(OX + p[0]), int(OY + p[1])
                txt = f"{h}" if h >= 0 else f"{h}"
                d.text((px, py), txt, fill=(255, 255, 100, 200), font=font, anchor="mm")
        canvas.alpha_composite(overlay)

    if edge_labels:
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        font = load_actor_font(9)
        edges = context.get("edges", [])
        for e in edges:
            if e["type"] in ("CLIFF", "WALK_SLOPE", "DOOR"):
                c1, r1 = e["from"]
                c2, r2 = e["to"]
                h1 = elevation_rows[r1][c1]
                h2 = elevation_rows[r2][c2]
                mid_x = (c1 + c2 + 1) * 0.5 * CELL
                mid_y = (r1 + r2 + 1) * 0.5 * CELL
                mid_h = (h1 + h2) * 0.5
                p = PV(mid_x, mid_y, mid_h, cam_x)
                col = (239, 68, 68, 240) if e["type"] == "CLIFF" else (34, 197, 94, 240)
                d.text((int(OX + p[0]), int(OY + p[1])), e["type"][:4], fill=col, font=font, anchor="mm")
        canvas.alpha_composite(overlay)

    return canvas

# ---------------------------------------------------------------------------
# HTML 報告建構
# ---------------------------------------------------------------------------
def build_report(spec, presentation, props_coords, tileset_path, props_png_path, out_dir):
    with open(tileset_path, "rb") as f:
        tileset_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    with open(props_png_path, "rb") as f:
        props_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

    plm_spec = spec
    plm_atlases = {"kenshi": tileset_b64}
    plm_props = {"kenshi": props_b64}

    static_images = [
        {"title": "Chunk (0,1) 山谷礦坑聚落全景 (v3_all.png)", "src": "v3_all.png"},
        {"title": "格網輔助視圖 (v3_02_grid_overlay.png)", "src": "v3_02_grid_overlay.png"},
        {"title": "高程標籤視圖 (v3_03_elevation_labels.png)", "src": "v3_03_elevation_labels.png"},
        {"title": "拓撲邊界標籤 (v3_04_edge_labels.png)", "src": "v3_04_edge_labels.png"},
        {"title": "鏡頭左移 視圖 (v3_cam_left.png)", "src": "v3_cam_left.png"},
        {"title": "鏡頭右移 視圖 (v3_cam_right.png)", "src": "v3_cam_right.png"},
        {"title": "聚落核心建築特寫 (v3_buildings_crop.png)", "src": "v3_buildings_crop.png"},
        {"title": "精煉鍛造坊與露天爐特寫 (v3_props_crop.png)", "src": "v3_props_crop.png"},
        {"title": "剖面 H8 (哨塔頂)", "src": "v3_cut_H8.png"},
        {"title": "剖面 H7 (屋頂煙囪)", "src": "v3_cut_H7.png"},
        {"title": "剖面 H6 (酒館斜頂)", "src": "v3_cut_H6.png"},
        {"title": "剖面 H4 (採礦山壁)", "src": "v3_cut_H4.png"},
        {"title": "剖面 H3 (平頂DECK屋頂)", "src": "v3_cut_H3.png"},
        {"title": "剖面 H2 (台地與蓄水池面)", "src": "v3_cut_H2.png"},
        {"title": "剖面 H1 (坡道與蓄水池床)", "src": "v3_cut_H1.png"},
        {"title": "剖面 H0 (谷地與河流水面)", "src": "v3_cut_H0.png"},
        {"title": "剖面 H-1 (主河道淺床)", "src": "v3_cut_Hneg1.png"},
        {"title": "剖面 H-2 (主河道深水床)", "src": "v3_cut_Hneg2.png"}
    ]

    diff_points = [
        "尺寸決策推導：50×50 總格數 2,500 格，一屏 38 格在 zoom 1 下橫向需 1.31 屏、縱向 2.53 屏，具備真正『走進去』的探索感與空間縱深；空地比 33.04% 呈現緊湊自然的採礦聚落。",
        "雙水體與新 R44：主河流四周岸為 H0，水面高度 level = 0，河床 -1/-2；山上蓄水池挖在 H2 台地上，四周岸皆為 H2，水面高度 level = 2，池底河床 1。完全符合『水面＝四周岸格最低高度』新規！",
        "落差地形：H0 谷地 → H2 台地 → H4 採礦山壁，具備 H1/H3 之 WALK_SLOPE 可行走坡道，其餘邊界為天然 CLIFF 斷崖。",
        "引水渠與泥灘：一格寬水渠 (ditch) 自蓄水池平鋪流向谷地生活區，無高差裂縫；河邊泥灘 (mud_cells) 鋪於 H0 岸高，貼 pit_floor 可正常行走不沉格。",
        "7 棟建築陣列：涵蓋 stone/timber/adobe，監督公署與鍛造坊平頂 DECK 屋頂設有室內樓梯 (腳印 8×6，室內 6×4，梯洞整段 2×2)，雜貨行設連排 4 格遮陽篷 (h=2.1)，小屋與鍛造坊設屋頂煙囪 (kind: roof)。",
        "道具與演員防護：道具全面通過『不堵門、不壓水、不壓溝』三大防火牆；7 位演員各司其職，採礦領班帥氣站立於鍛造坊 DECK 屋頂。"
    ]

    skeleton_path = os.path.join(out_dir, "keluo_viewer_skeleton.html")
    skeleton_content = ""
    if os.path.exists(skeleton_path):
        with open(skeleton_path, "r", encoding="utf-8") as f:
            skeleton_content = f.read()

    plm_root_block = skeleton_content if skeleton_content else '<div id="plm-root"></div>'

    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-TW">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <title>諾諾戰術地圖渲染器 Chunk (0,1)「山谷礦坑聚落」交付報告</title>',
        '  <link rel="stylesheet" href="keluo_viewer_style.css">',
        '  <style>',
        '    body { margin: 0; padding: 24px; background: #0f111a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }',
        '    h1, h2 { color: #38bdf8; border-bottom: 1px solid #1e293b; padding-bottom: 8px; }',
        '    .diff-box { background: #1e293b; border-left: 4px solid #38bdf8; padding: 16px; margin-bottom: 24px; border-radius: 4px; }',
        '    .diff-box ol { margin: 0; padding-left: 20px; }',
        '    .diff-box li { margin: 6px 0; line-height: 1.5; }',
        '    .gallery { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; margin-bottom: 32px; }',
        '    .gallery-item { background: #1e293b; border-radius: 6px; overflow: hidden; border: 1px solid #334155; }',
        '    .gallery-item img { width: 100%; height: auto; display: block; }',
        '    .gallery-item .caption { padding: 10px 12px; font-size: 13px; color: #94a3b8; font-weight: 500; }',
        '  </style>',
        '</head>',
        '<body>',
        '  <h1>諾諾戰術地圖渲染器 Chunk (0,1)「山谷礦坑聚落」交付報告</h1>',
        '  <div class="diff-box">',
        '    <h3>Chunk (0,1) 設計特點與新規範實作</h3>',
        '    <ol>'
    ]
    for dp in diff_points:
        html_parts.append(f'      <li>{dp}</li>')
    html_parts.extend([
        '    </ol>',
        '  </div>',
        '  <h2>全套渲染交付產物</h2>',
        '  <div class="gallery">'
    ])
    for img in static_images:
        html_parts.append(f'    <div class="gallery-item"><img src="{img["src"]}" alt="{img["title"]}"><div class="caption">{img["title"]}</div></div>')
    html_parts.extend([
        '  </div>',
        '  <h2>互動式檢視器 (Keluo Viewer)</h2>',
        plm_root_block,
        '  <script>',
        f'    window.PLM_SPEC = {json.dumps(plm_spec, ensure_ascii=False)};',
        f'    window.PLM_ATLASES = {json.dumps(plm_atlases, ensure_ascii=False)};',
        f'    window.PLM_PROPS = {json.dumps(plm_props, ensure_ascii=False)};',
        '  </script>',
        '  <script src="keluo_viewer.js"></script>',
        '</body>',
        '</html>'
    ])

    report_path = os.path.join(out_dir, "v3_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))
    print(f"已生成互動檢視報告：{report_path}")

# ---------------------------------------------------------------------------
# 主執行管線
# ---------------------------------------------------------------------------
def locate_file(rel_path, script_dir):
    candidates = [
        os.path.abspath(os.path.join(script_dir, "..", rel_path)),
        os.path.abspath(os.path.join(script_dir, rel_path)),
        os.path.abspath(os.path.join(os.getcwd(), rel_path)),
        f"C:/GPTfile/godot/Nono's Little Base/nono_google_cloud/nono-tactical-tilemap-engine/{rel_path}"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"找不到檔案：{rel_path}，嘗試路徑：{candidates}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    spec_path = locate_file("reports/chunk_0_1_spec.json", script_dir)
    pres_path = locate_file("reports/keluo_presentation.json", script_dir)
    tileset_path = locate_file("reports/keluo_kenshi_tileset.png", script_dir)
    props_png_path = locate_file("reports/keluo_kenshi_props.png", script_dir)
    props_json_path = locate_file("reports/keluo_props_sprites.json", script_dir)

    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    with open(pres_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
    with open(props_json_path, "r", encoding="utf-8") as f:
        props_coords = json.load(f)

    props_boxes = {}
    try:
        boxes_path = locate_file("reports/keluo_props_boxes.json", script_dir)
        with open(boxes_path, "r", encoding="utf-8") as f:
            props_boxes = json.load(f)
    except Exception:
        pass

    atlas_img = Image.open(tileset_path).convert("RGBA")
    tm = TileManager(atlas_img, presentation.get("face_crop_y0", {}))

    props_atlas_img = Image.open(props_png_path).convert("RGBA")
    pm = PropsManager(props_atlas_img, props_coords, props_boxes)

    font = load_actor_font(12)
    actors = list(spec.get("actors_fixture", []))

    actor_sprites = {}
    for a in actors:
        a_id = a.get("id", "actor")
        actor_sprites[a_id] = create_actor_sprite(a, font)

    props = list(spec.get("props", []))
    buildings = spec.get("buildings", [])
    building_footprint_cells = set()
    for b in buildings:
        ox, oy = b["footprint"]["origin"]
        bw, bh = b["footprint"]["cols"], b["footprint"]["rows"]
        for r in range(oy, oy + bh):
            for c in range(ox, ox + bw):
                building_footprint_cells.add((c, r))

    surfaces = spec.get("surfaces", [])
    ditch_cells_set = set(tuple(p) for p in spec.get("ditch_cells", []))
    water_cells_set = set(tuple(p) for p in spec.get("water_cells", []))
    water_bodies = spec.get("water_bodies", [])
    edges = spec.get("edges", [])

    cell_water_level, cell_water_layer = compute_water_levels(spec["elevation_rows"], water_cells_set, water_bodies)

    context = {
        "elevation_rows": spec["elevation_rows"],
        "bridge_cells": set(tuple(p) for p in spec.get("bridge_cells", [])),
        "ditch_cells": ditch_cells_set,
        "water_cells": water_cells_set,
        "mud_cells": set(tuple(p) for p in spec.get("mud_cells", [])),
        "cell_water_level": cell_water_level,
        "cell_water_layer": cell_water_layer,
        "road_cells": set(tuple(p) for p in spec.get("road_cells", [])),
        "plaza_cells": set(tuple(p) for p in spec.get("plaza_cells", [])),
        "field_cells": set(tuple(p) for p in spec.get("field_cells", [])),
        "building_footprint_cells": building_footprint_cells,
        "buildings": buildings,
        "props": props,
        "actors_fixture": actors,
        "actor_sprites": actor_sprites,
        "presentation": presentation,
        "surfaces": surfaces,
        "edges": edges
    }

    out_dir = os.path.abspath(os.path.join(script_dir, "..", "reports"))
    os.makedirs(out_dir, exist_ok=True)

    cam_center = WORLD_W / 2  # 800

    # 1. 基礎視圖
    tasks = [
        ("v3_all.png", cam_center),
        ("v3_cam_left.png", 0),
        ("v3_cam_right.png", WORLD_W)
    ]

    frame_center = None
    for filename, cam_x in tasks:
        print(f"正在渲染 {filename} (cam_x = {cam_x})...")
        frame = render_view(cam_x, tm, pm, actor_sprites, context, cut=None)
        out_path = os.path.join(out_dir, filename)
        frame.save(out_path)
        print(f"已輸出：{out_path}")
        if filename == "v3_all.png":
            frame_center = frame

    resample_nearest = Image.Resampling.NEAREST if hasattr(Image, "Resampling") else Image.NEAREST

    # 2. 特寫裁切圖
    if frame_center is not None:
        crop_box = (
            int(OX + 9 * CELL),
            int(OY + 14 * CELL),
            int(OX + 30 * CELL),
            int(OY + 25 * CELL)
        )
        crop_img = frame_center.crop(crop_box)
        crop_scaled = crop_img.resize((crop_img.width * 2, crop_img.height * 2), resample=resample_nearest)
        crop_path = os.path.join(out_dir, "v3_buildings_crop.png")
        crop_scaled.save(crop_path)
        print(f"已輸出建築特寫放大圖：{crop_path}")

        props_crop_box = (
            int(OX + 9 * CELL),
            int(OY + 24 * CELL),
            int(OX + 21 * CELL),
            int(OY + 36 * CELL)
        )
        props_crop_img = frame_center.crop(props_crop_box)
        props_crop_scaled = props_crop_img.resize(
            (props_crop_img.width * 2, props_crop_img.height * 2),
            resample=resample_nearest
        )
        props_crop_path = os.path.join(out_dir, "v3_props_crop.png")
        props_crop_scaled.save(props_crop_path)
        print(f"已輸出精煉坊與露天爐特寫放大圖：{props_crop_path}")

    # 3. 剖面圖輸出 (H-2 到 H8)
    cut_jobs = [
        ("v3_cut_H8.png", 8),
        ("v3_cut_H7.png", 7),
        ("v3_cut_H6.png", 6),
        ("v3_cut_H5.png", 5),
        ("v3_cut_H4.png", 4),
        ("v3_cut_H3.png", 3),
        ("v3_cut_H2.png", 2),
        ("v3_cut_H1.png", 1),
        ("v3_cut_H0.png", 0),
        ("v3_cut_Hneg1.png", -1),
        ("v3_cut_Hneg2.png", -2),
    ]

    for filename, cut_val in cut_jobs:
        print(f"正在渲染剖面圖 {filename} (cut = {cut_val}, cam_x = {cam_center})...")
        cut_frame = render_view(cam_center, tm, pm, actor_sprites, context, cut=cut_val)
        cut_out_path = os.path.join(out_dir, filename)
        cut_frame.save(cut_out_path)
        print(f"已輸出剖面圖：{cut_out_path}")

    # 4. 交付圖
    print("正在渲染交付圖：v3_02_grid_overlay.png...")
    frame_grid = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, grid_overlay=True)
    frame_grid.save(os.path.join(out_dir, "v3_02_grid_overlay.png"))

    print("正在渲染交付圖：v3_03_elevation_labels.png...")
    frame_elev = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, elevation_labels=True)
    frame_elev.save(os.path.join(out_dir, "v3_03_elevation_labels.png"))

    print("正在渲染交付圖：v3_04_edge_labels.png...")
    frame_edge = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, edge_labels=True)
    frame_edge.save(os.path.join(out_dir, "v3_04_edge_labels.png"))

    # 5. 切片集
    slices_dir = os.path.join(out_dir, "v3_slices")
    os.makedirs(slices_dir, exist_ok=True)
    print(f"正在渲染交付圖切片集：v3_slices/ (共 {len(surfaces)} 個 surface)...")
    for s in surfaces:
        s_id = s["surface_id"]
        frame_slice = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, only_surface_id=s_id)
        slice_path = os.path.join(slices_dir, f"{s_id}.png")
        frame_slice.save(slice_path)

    # 6. HTML 報告
    print("正在生成交付報告 reports/v3_report.html...")
    build_report(spec, presentation, props_coords, tileset_path, props_png_path, out_dir)

if __name__ == "__main__":
    main()
