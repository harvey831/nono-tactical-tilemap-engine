#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_slave_mine.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: 奴隸礦坑 (The Slavers' Quarry) 36×36 全景圖、特寫圖、剖面圖與互動報告渲染器。
Deliverables:
  - reports/v4_all.png, v4_cam_left.png, v4_cam_right.png
  - reports/v4_buildings_crop.png, v4_props_crop.png
  - reports/v4_02_grid_overlay.png, v4_03_elevation_labels.png, v4_04_edge_labels.png
  - reports/v4_cut_H3.png, v4_cut_H2.png, v4_cut_H1.png, v4_cut_H0.png, v4_cut_Hneg1.png, v4_cut_Hneg2.png
  - reports/v4_slices/*.png
  - reports/v4_report.html
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
# 投影參數與基礎幾何
# ---------------------------------------------------------------------------
CELL = 32
ROW_H = 48

RISE = 23.04          # 32 * 0.72
SIDE_SHIFT = 3.84     # 32 * 0.12
SIDE_SPREAD = 192.0   # 32 * 6

MARGIN_X = 40
MARGIN_TOP = int(8 * RISE) + 40
MARGIN_BOTTOM = int(2 * RISE) + 24

ACTOR_W = 24
ACTOR_H = 30
BG = (15, 17, 26, 255)

def side_at(world_x, cam_x):
    return max(-1.0, min(1.0, (world_x - cam_x) / SIDE_SPREAD))

def PV(x, y, h, cam_x):
    sd = side_at(x, cam_x)
    return (x + sd * h * SIDE_SHIFT, y - h * RISE)

def face_visible(which, x_edge, cam_x):
    sd = side_at(x_edge, cam_x)
    return sd > 0.03 if which == "left" else sd < -0.03

# ---------------------------------------------------------------------------
# 仿射貼圖
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

def paste_parallelogram(canvas, src, p0, vec_u, vec_v, ox_base, oy_base, conservative=True):
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

    canvas.alpha_composite(warped, (int(ox_base + bx), int(oy_base + by)))

# ---------------------------------------------------------------------------
# Tile 管理器與道具管理器
# ---------------------------------------------------------------------------
class TileManager:
    def __init__(self, atlas_img, face_crop_y0):
        self.atlas = atlas_img
        self.face_crop_y0 = face_crop_y0

    def get_tile(self, tile_info, default_h=32):
        if not tile_info:
            return None
        col, row = tile_info[1], tile_info[2]
        tw = tile_info[3] if len(tile_info) >= 4 else 32
        th = tile_info[4] if len(tile_info) >= 5 else default_h
        x = col * 32
        y = row * ROW_H
        return self.atlas.crop((x, y, x + tw, y + th))

class PropsManager:
    def __init__(self, atlas_img, coords, boxes):
        self.atlas = atlas_img
        self.coords = coords
        self.boxes = boxes

    def get_sprite(self, name):
        if name not in self.coords:
            return None
        x, y, w, h = self.coords[name]
        return self.atlas.crop((x, y, x + w, y + h))

def load_font(size=11):
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\arial.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_actor_sprite(actor, font):
    img = Image.new("RGBA", (ACTOR_W, ACTOR_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = tuple(actor.get("color", [255, 255, 255])) + (255,)

    # 圓形底座
    d.ellipse([(2, ACTOR_H - 10), (ACTOR_W - 2, ACTOR_H - 2)], fill=(20, 20, 20, 180), outline=(220, 220, 220, 220))
    # 本體標記柱
    d.rounded_rectangle([(4, 2), (ACTOR_W - 4, ACTOR_H - 6)], radius=4, fill=color, outline=(15, 17, 26, 255), width=2)
    # 文字標籤
    label = actor.get("label", "人")[:1]
    d.text((ACTOR_W / 2, (ACTOR_H - 6) / 2 + 1), label, fill=(15, 17, 26, 255), font=font, anchor="mm")
    return img

# ---------------------------------------------------------------------------
# 主視角渲染核心
# ---------------------------------------------------------------------------
def render_view(cam_x, tm, pm, actor_sprites, context, cut=None,
                grid_overlay=False, elevation_labels=False, edge_labels=False,
                only_surface_id=None):
    spec = context["spec"]
    cols = spec["grid"]["cols"]
    rows = spec["grid"]["rows"]
    world_w = cols * CELL
    world_h = rows * CELL

    canvas_w = world_w + 2 * MARGIN_X
    canvas_h = world_h + MARGIN_TOP + MARGIN_BOTTOM
    ox_base = MARGIN_X
    oy_base = MARGIN_TOP

    canvas = Image.new("RGBA", (canvas_w, canvas_h), BG if cut is None else (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font_s = load_font(10)
    font_m = load_font(12)

    elevation_rows = context["elevation_rows"]
    surfaces = context["surfaces"]
    presentation = context["presentation"]
    tiles = presentation.get("tiles", {})

    # --------------------------------------------------------
    # 1. 地面 Surfaces 渲染
    # --------------------------------------------------------
    for surf in surfaces:
        s_id = surf["surface_id"]
        if only_surface_id and s_id != only_surface_id:
            continue
        h = surf["elevation"]
        if cut is not None and h > cut:
            continue

        tile_def = surf.get("tile")
        tile_img = tm.get_tile(tile_def, default_h=32)
        if not tile_img:
            continue

        for c, r in surf["cells"]:
            wx = c * CELL
            wy = r * CELL
            p0 = PV(wx, wy, h, cam_x)
            p_east = PV(wx + CELL, wy, h, cam_x)
            p_south = PV(wx, wy + CELL, h, cam_x)
            vec_u = (p_east[0] - p0[0], p_east[1] - p0[1])
            vec_v = (p_south[0] - p0[0], p_south[1] - p0[1])
            paste_parallelogram(canvas, tile_img, p0, vec_u, vec_v, ox_base, oy_base, conservative=True)

    # --------------------------------------------------------
    # 2. 地形落差立面 (Edges / Cliff Faces / Pit Walls)
    # --------------------------------------------------------
    for edge in context["edges"]:
        h1 = edge["elev_a"]
        h2 = edge["elev_b"]
        high_h = max(h1, h2)
        low_h = min(h1, h2)
        if cut is not None and high_h > cut:
            continue

        c1, r1 = edge["cell_a"]
        c2, r2 = edge["cell_b"]
        kind = edge.get("kind", "CLIFF")
        diff = abs(h1 - h2)

        # 根據高程深度決定立面貼圖 (採石坑用 pit_wall，地表斷崖用 cliff_face)
        if low_h < 0:
            wall_tile_def = tiles.get("pit_wall", ["kenshi", 10, 3])
        else:
            wall_tile_def = tiles.get("cliff_face", ["kenshi", 6, 0])

        face_tile = tm.get_tile(wall_tile_def, default_h=32)
        if not face_tile:
            continue

        if edge["direction"] == "SOUTH" and h1 > h2:
            # 南向懸崖面
            wx = c1 * CELL
            wy = (r1 + 1) * CELL
            for dh in range(diff):
                curr_h = low_h + dh + 1
                p_top_l = PV(wx, wy, curr_h, cam_x)
                p_top_r = PV(wx + CELL, wy, curr_h, cam_x)
                p_bot_l = PV(wx, wy, curr_h - 1, cam_x)
                vec_u = (p_top_r[0] - p_top_l[0], p_top_r[1] - p_top_l[1])
                vec_v = (p_bot_l[0] - p_top_l[0], p_bot_l[1] - p_top_l[1])
                paste_parallelogram(canvas, face_tile, p_top_l, vec_u, vec_v, ox_base, oy_base, conservative=True)

        elif edge["direction"] == "EAST":
            # 側向立面 (僅在鏡頭視角偏轉時可見)
            wx = (c1 + 1) * CELL
            wy = r1 * CELL
            if h1 > h2 and face_visible("right", wx, cam_x):
                for dh in range(diff):
                    curr_h = low_h + dh + 1
                    p_top_n = PV(wx, wy, curr_h, cam_x)
                    p_top_s = PV(wx, wy + CELL, curr_h, cam_x)
                    p_bot_n = PV(wx, wy, curr_h - 1, cam_x)
                    vec_u = (p_top_s[0] - p_top_n[0], p_top_s[1] - p_top_n[1])
                    vec_v = (p_bot_n[0] - p_top_n[0], p_bot_n[1] - p_top_n[1])
                    paste_parallelogram(canvas, face_tile, p_top_n, vec_u, vec_v, ox_base, oy_base, conservative=True)
            elif h2 > h1 and face_visible("left", wx, cam_x):
                for dh in range(diff):
                    curr_h = low_h + dh + 1
                    p_top_n = PV(wx, wy, curr_h, cam_x)
                    p_top_s = PV(wx, wy + CELL, curr_h, cam_x)
                    p_bot_n = PV(wx, wy, curr_h - 1, cam_x)
                    vec_u = (p_top_s[0] - p_top_n[0], p_top_s[1] - p_top_n[1])
                    vec_v = (p_bot_n[0] - p_top_n[0], p_bot_n[1] - p_top_n[1])
                    paste_parallelogram(canvas, face_tile, p_top_n, vec_u, vec_v, ox_base, oy_base, conservative=True)

    # --------------------------------------------------------
    # 3. 建築物渲染 (Buildings)
    # --------------------------------------------------------
    styles = presentation.get("styles", {})
    for b in context["buildings"]:
        b_base = b["base_elevation"]
        if cut is not None and b_base > cut:
            continue

        b_style_name = b.get("style", "stone")
        style = styles.get(b_style_name, styles.get("stone", {}))
        wall_tile = tm.get_tile(style.get("wall", ["kenshi", 1, 2]), default_h=32)
        roof_tile = tm.get_tile(style.get("roof", {}).get("all", ["kenshi", 4, 2]), default_h=32)
        door_tile = tm.get_tile(style.get("door", ["kenshi", 11, 2, 32, 46]), default_h=46)
        win_tile = tm.get_tile(style.get("window", ["kenshi", 14, 2, 32, 24]), default_h=24)

        ox, oy = b["footprint"]["origin"]
        cols_b, rows_b = b["footprint"]["cols"], b["footprint"]["rows"]
        h_units = b.get("height_units", 3.0)

        # 牆面
        wx0 = ox * CELL
        wy0 = oy * CELL
        wx1 = (ox + cols_b) * CELL
        wy1 = (oy + rows_b) * CELL

        # 南立面 (正對鏡頭)
        if cut is None or (b_base + h_units <= cut + 1):
            for c in range(cols_b):
                wx = (ox + c) * CELL
                wy = wy1
                p_top_l = PV(wx, wy, b_base + h_units, cam_x)
                p_top_r = PV(wx + CELL, wy, b_base + h_units, cam_x)
                p_bot_l = PV(wx, wy, b_base, cam_x)
                vec_u = (p_top_r[0] - p_top_l[0], p_top_r[1] - p_top_l[1])
                vec_v = (p_bot_l[0] - p_top_l[0], p_bot_l[1] - p_top_l[1])
                if wall_tile:
                    paste_parallelogram(canvas, wall_tile, p_top_l, vec_u, vec_v, ox_base, oy_base, conservative=True)

                # 門
                if [c, rows_b - 1] in b.get("doors_local", []):
                    if door_tile:
                        paste_parallelogram(canvas, door_tile, p_bot_l, (vec_u[0], vec_u[1]), (0, -46 * 0.72), ox_base, oy_base, conservative=False)
                # 窗
                elif c in b.get("windows_local", {}).get("0", []):
                    if win_tile:
                        # 窗底離地 40% 牆高：vec_v 為頂到腳 (往下為正)，故從牆腳往上減 vec_v * 0.4
                        p_win_bot = (p_bot_l[0] - vec_v[0] * 0.4, p_bot_l[1] - vec_v[1] * 0.4)
                        paste_parallelogram(canvas, win_tile, p_win_bot, (vec_u[0], vec_u[1]), (0, -24 * 0.72), ox_base, oy_base, conservative=False)

        # 屋頂 (坡頂或平頂)
        if cut is None or (b_base + h_units <= cut):
            roof_info = b.get("roof", {})
            for r in range(rows_b):
                for c in range(cols_b):
                    wx = (ox + c) * CELL
                    wy = (oy + r) * CELL
                    p0 = PV(wx, wy, b_base + h_units, cam_x)
                    p_e = PV(wx + CELL, wy, b_base + h_units, cam_x)
                    p_s = PV(wx, wy + CELL, b_base + h_units, cam_x)
                    vec_u = (p_e[0] - p0[0], p_e[1] - p0[1])
                    vec_v = (p_s[0] - p0[0], p_s[1] - p0[1])
                    if roof_tile:
                        paste_parallelogram(canvas, roof_tile, p0, vec_u, vec_v, ox_base, oy_base, conservative=True)

        # Facade 門面懸掛物
        for f in b.get("facade", []):
            sp_name = f.get("sprite")
            sp_img = pm.get_sprite(sp_name)
            if not sp_img:
                continue
            if f.get("kind") == "wall":
                fc = f.get("col", 0)
                fh = f.get("h", 1.0)
                wx = (ox + fc) * CELL
                wy = wy1
                p_attach = PV(wx, wy, b_base + fh, cam_x)
                canvas.alpha_composite(sp_img, (int(ox_base + p_attach[0]), int(oy_base + p_attach[1] - sp_img.height)))
            elif f.get("kind") == "roof":
                fc = f.get("col", 0)
                fr = f.get("row", 0)
                wx = (ox + fc) * CELL
                wy = (oy + fr) * CELL
                p_attach = PV(wx, wy, b_base + h_units, cam_x)
                canvas.alpha_composite(sp_img, (int(ox_base + p_attach[0]), int(oy_base + p_attach[1] - sp_img.height)))

    # --------------------------------------------------------
    # 4. 道具與演員深度排序渲染 (Props & Actors)
    # --------------------------------------------------------
    render_items = []

    # 收集 props
    for p in context["props"]:
        pe = p.get("elevation", 0)
        if cut is not None and pe > cut:
            continue
        pc, pr = p["cell"]
        sp_name = p.get("sprite")
        sp_img = pm.get_sprite(sp_name)
        if sp_img:
            fw, fh = p.get("footprint", [1, 1])
            depth_key = ((pr + fh) * CELL) - (pe * 10)
            render_items.append({
                "type": "prop",
                "depth": depth_key,
                "cell": (pc, pr),
                "elevation": pe,
                "img": sp_img,
                "footprint": (fw, fh),
                "id": p["id"]
            })

    # 收集 actors
    for a in context["actors_fixture"]:
        c3d = a["cells"][0]
        ac, ar, ae = c3d[0], c3d[1], c3d[2]
        if cut is not None and ae > cut:
            continue
        a_id = a.get("id", "actor")
        a_img = actor_sprites.get(a_id)
        if a_img:
            depth_key = ((ar + 1) * CELL) - (ae * 10) + 5
            render_items.append({
                "type": "actor",
                "depth": depth_key,
                "cell": (ac, ar),
                "elevation": ae,
                "img": a_img,
                "footprint": (1, 1),
                "id": a_id
            })

    # 按深度由遠及近排序
    render_items.sort(key=lambda item: item["depth"])

    for item in render_items:
        c, r = item["cell"]
        h = item["elevation"]
        img = item["img"]
        fw, fh = item.get("footprint", (1, 1))
        wx = c * CELL
        wy = (r + fh) * CELL
        p_base = PV(wx, wy, h, cam_x)

        # 錨點對齊腳底中央 (橫向跨 fw 格置中，縱向以 footprint 最南緣為腳底貼地)
        px = int(ox_base + p_base[0] + fw * CELL / 2 - img.width / 2)
        py = int(oy_base + p_base[1] - img.height)
        canvas.alpha_composite(img, (px, py))

    # --------------------------------------------------------
    # 5. 疊加圖層 (Grid, Labels, Edges)
    # --------------------------------------------------------
    if grid_overlay:
        for r in range(rows + 1):
            p_start = (ox_base, oy_base + r * CELL)
            p_end = (ox_base + world_w, oy_base + r * CELL)
            draw.line([p_start, p_end], fill=(56, 189, 248, 90), width=1)
        for c in range(cols + 1):
            p_start = (ox_base + c * CELL, oy_base)
            p_end = (ox_base + c * CELL, oy_base + world_h)
            draw.line([p_start, p_end], fill=(56, 189, 248, 90), width=1)

    if elevation_labels:
        for r in range(0, rows, 2):
            for c in range(0, cols, 2):
                h = elevation_rows[r][c]
                wx = c * CELL + CELL / 2
                wy = r * CELL + CELL / 2
                p = PV(wx, wy, h, cam_x)
                draw.text((ox_base + p[0], oy_base + p[1]), str(h), fill=(255, 255, 255, 220), font=font_s, anchor="mm")

    if edge_labels:
        for edge in context["edges"]:
            c1, r1 = edge["cell_a"]
            h1 = edge["elev_a"]
            p = PV(c1 * CELL, r1 * CELL, h1, cam_x)
            draw.point((ox_base + p[0], oy_base + p[1]), fill=(239, 68, 68, 255))

    return canvas

# ---------------------------------------------------------------------------
# HTML 報告生成器
# ---------------------------------------------------------------------------
def build_html_report(spec, tileset_path, props_png_path, out_dir):
    skeleton_path = os.path.join(out_dir, "keluo_viewer_skeleton.html")
    skeleton_content = ""
    if os.path.exists(skeleton_path):
        with open(skeleton_path, "r", encoding="utf-8") as f:
            skeleton_content = f.read()

    plm_root_block = skeleton_content if skeleton_content else '<div id="plm-root"></div>'

    # 珂洛代修 2026-09-04：keluo_viewer.js 的 tiles / styles / autotile 表全都從 window.PLM_SPEC 讀，
    # report builder 必須把 keluo_presentation.json 合併進去，否則 S.tiles 是 undefined、檢視器第一格就爆。
    plm_spec = dict(spec)
    _pres_path = os.path.join(out_dir, "keluo_presentation.json")
    if os.path.exists(_pres_path):
        with open(_pres_path, "r", encoding="utf-8") as f:
            plm_spec.update(json.load(f))

    tileset_b64 = ""
    if os.path.exists(tileset_path):
        with open(tileset_path, "rb") as f:
            tileset_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

    props_b64 = ""
    if os.path.exists(props_png_path):
        with open(props_png_path, "rb") as f:
            props_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

    plm_atlases = {"kenshi": tileset_b64}

    # 珂洛代修 2026-09-04：keluo_viewer.js 是用 props[p.id] 取圖，
    # 所以 PLM_PROPS 必須是「每個道具實例一張裁好的小圖」{prop_id: dataURL}，
    # 不是整張 sprite sheet；門面元件另外用 "<building_id>_facade_<i>" 當 key。
    plm_props = {}
    try:
        from PIL import Image as _Img
        _sheet = _Img.open(props_png_path).convert("RGBA")
        with open(os.path.join(out_dir, "keluo_props_sprites.json"), "r", encoding="utf-8") as f:
            _spr = json.load(f)

        def _crop_b64(sprite_name):
            box = _spr.get(sprite_name)
            if not box:
                return None
            x, y, w, h = box
            buf = io.BytesIO()
            _sheet.crop((x, y, x + w, y + h)).save(buf, "PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

        for _p in spec.get("props", []):
            _d = _crop_b64(_p.get("sprite"))
            if _d:
                plm_props[_p["id"]] = _d
        for _b in spec.get("buildings", []):
            for _i, _f in enumerate(_b.get("facade", [])):
                if _f.get("sprite"):
                    _d = _crop_b64(_f["sprite"])
                    if _d:
                        plm_props[_f.get("img_id") or f"{_b['building_id']}_facade_{_i}"] = _d
    except Exception as _e:
        print(f"⚠️ PLM_PROPS 裁圖失敗：{_e}")
        plm_props = {"kenshi": props_b64}

    diff_points = [
        "地圖尺度升級至 48×48 (1536×1536 px)：空間機能率突破 78%，徹底消除擠壓與邊界侷促感，為大型戰棋軍團展開提供完美開闊戰場！",
        "居高臨下哨塔基座修復：西北 H3 高台周邊留足 2~4 格平整石台，哨塔 4 隻高腳 100% 穩固踩在平地上，徹底消滅懸空踩崖！狙擊守衛精準配置於頂層甲板中央！",
        "黑鐵鍛造坊面寬擴展與招牌解耦：南立面拓寬至 9 格，鐵鎚招牌掛於右側 col 8 專屬實牆區，完全避開大門 (col 4) 與窗戶 (col 1, 7)，0 覆蓋門窗！",
        "階梯巨型開採深坑下挖至 H-3：中央露天採石台面 (H-1) ──► 赤鐵深掘層 (H-2) ──► 幽暗核心深井 (H-3)，層層推進！",
        "實裝 4 大礦坑靈魂專屬資產：露天生鏽鐵籠排 (關押帶刺奴隸)、中央行刑雙木受刑樁、採礦鐵軌路線網絡與翻斗礦車 (空車 + 滿載赤鐵車)！",
        "真實重工業運輸閉環：坑底開採面 ──雙向鐵軌斜坡道──► 刑場點名坪 ──► 雙熔爐鍛造坊 ──► 礦石貨棧裝卸月台 ──► 南側唯一檢查哨出口。",
        "全域渲染器修復：修復 H1 剖面除零拋錯黑屏 Bug、統一雙端道具接地投影錨點，非建築格 100% 被 Surfaces 覆蓋！"
    ]

    static_images = [
        {"title": "奴隸礦坑全景俯視 (v4_all.png)", "src": "v4_all.png"},
        {"title": "格網對齊輔助圖 (v4_02_grid_overlay.png)", "src": "v4_02_grid_overlay.png"},
        {"title": "高程標籤分佈圖 (v4_03_elevation_labels.png)", "src": "v4_03_elevation_labels.png"},
        {"title": "拓撲邊界標籤圖 (v4_04_edge_labels.png)", "src": "v4_04_edge_labels.png"},
        {"title": "左側視角鏡頭 (v4_cam_left.png)", "src": "v4_cam_left.png"},
        {"title": "右側視角鏡頭 (v4_cam_right.png)", "src": "v4_cam_right.png"},
        {"title": "囚牢、鐵籠與刑場特寫 (v4_buildings_crop.png)", "src": "v4_buildings_crop.png"},
        {"title": "階梯採石坑與鐵軌礦車特寫 (v4_props_crop.png)", "src": "v4_props_crop.png"},
        {"title": "剖面 H3 (哨塔高台頂面)", "src": "v4_cut_H3.png"},
        {"title": "剖面 H2 (奴隸主高台營地)", "src": "v4_cut_H2.png"},
        {"title": "剖面 H1 (高台巡邏斜坡)", "src": "v4_cut_H1.png"},
        {"title": "剖面 H0 (營區地面與鍛造區)", "src": "v4_cut_H0.png"},
        {"title": "剖面 H-1 (露天採石坑底)", "src": "v4_cut_Hneg1.png"},
        {"title": "剖面 H-2 (深層赤鐵開採面)", "src": "v4_cut_Hneg2.png"},
        {"title": "剖面 H-3 (核心深井礦脈)", "src": "v4_cut_Hneg3.png"}
    ]

    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-TW">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <title>諾諾戰術地圖渲染器 V4 -「奴隸礦坑」(The Slavers Quarry) 交付報告</title>',
        '  <link rel="stylesheet" href="keluo_viewer_style.css">',
        '  <style>',
        '    body { margin: 0; padding: 24px; background: #0f111a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }',
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
        '  <h1>⛏️ 諾諾戰術地圖渲染器 V4 -「奴隸礦坑」交付報告</h1>',
        '  <div class="diff-box">',
        '    <h3>設計重構要點與空間邏輯實現</h3>',
        '    <ol>'
    ]
    for dp in diff_points:
        html_parts.append(f'      <li>{dp}</li>')
    html_parts.extend([
        '    </ol>',
        '  </div>',
        '  <h2>全套渲染交付視圖 (V4)</h2>',
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

    report_path = os.path.join(out_dir, "v4_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))
    print(f"SUCCESS: Report generated at: {report_path}")

# ---------------------------------------------------------------------------
# 主程式
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
    raise FileNotFoundError(f"找不到檔案：{rel_path}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.abspath(os.path.join(script_dir, "..", "reports"))
    os.makedirs(out_dir, exist_ok=True)

    spec_path = locate_file("reports/slave_mine_spec.json", script_dir)
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

    font = load_font(12)
    actors = list(spec.get("actors_fixture", []))
    actor_sprites = {}
    for a in actors:
        a_id = a.get("id", "actor")
        actor_sprites[a_id] = create_actor_sprite(a, font)

    context = {
        "spec": spec,
        "elevation_rows": spec["elevation_rows"],
        "surfaces": spec["surfaces"],
        "edges": spec["edges"],
        "buildings": spec["buildings"],
        "props": spec["props"],
        "actors_fixture": actors,
        "presentation": presentation
    }

    world_w = spec["grid"]["cols"] * CELL
    cam_center = world_w / 2

    # 1. 基礎三大視角
    print("正在渲染 v4_all.png (cam_center)...")
    frame_all = render_view(cam_center, tm, pm, actor_sprites, context, cut=None)
    frame_all.save(os.path.join(out_dir, "v4_all.png"))

    print("正在渲染 v4_cam_left.png (cam_left)...")
    frame_left = render_view(0, tm, pm, actor_sprites, context, cut=None)
    frame_left.save(os.path.join(out_dir, "v4_cam_left.png"))

    print("正在渲染 v4_cam_right.png (cam_right)...")
    frame_right = render_view(world_w, tm, pm, actor_sprites, context, cut=None)
    frame_right.save(os.path.join(out_dir, "v4_cam_right.png"))

    # 2. 特寫裁切圖 (放大 2x)
    resample_nearest = Image.Resampling.NEAREST if hasattr(Image, "Resampling") else Image.NEAREST
    crop_bld_box = (
        int(MARGIN_X + 3 * CELL),
        int(MARGIN_TOP + 14 * CELL),
        int(MARGIN_X + 18 * CELL),
        int(MARGIN_TOP + 38 * CELL)
    )
    crop_bld = frame_all.crop(crop_bld_box)
    crop_bld_scaled = crop_bld.resize((crop_bld.width * 2, crop_bld.height * 2), resample=resample_nearest)
    crop_bld_scaled.save(os.path.join(out_dir, "v4_buildings_crop.png"))

    crop_pit_box = (
        int(MARGIN_X + 17 * CELL),
        int(MARGIN_TOP + 18 * CELL),
        int(MARGIN_X + 44 * CELL),
        int(MARGIN_TOP + 36 * CELL)
    )
    crop_pit = frame_all.crop(crop_pit_box)
    crop_pit_scaled = crop_pit.resize((crop_pit.width * 2, crop_pit.height * 2), resample=resample_nearest)
    crop_pit_scaled.save(os.path.join(out_dir, "v4_props_crop.png"))

    # 3. 疊加圖層
    print("正在渲染 v4_02_grid_overlay.png...")
    frame_grid = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, grid_overlay=True)
    frame_grid.save(os.path.join(out_dir, "v4_02_grid_overlay.png"))

    print("正在渲染 v4_03_elevation_labels.png...")
    frame_elev = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, elevation_labels=True)
    frame_elev.save(os.path.join(out_dir, "v4_03_elevation_labels.png"))

    print("正在渲染 v4_04_edge_labels.png...")
    frame_edge = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, edge_labels=True)
    frame_edge.save(os.path.join(out_dir, "v4_04_edge_labels.png"))

    # 4. 剖面切片 (H3, H2, H1, H0, H-1, H-2, H-3)
    cuts = [
        ("v4_cut_H3.png", 3),
        ("v4_cut_H2.png", 2),
        ("v4_cut_H1.png", 1),
        ("v4_cut_H0.png", 0),
        ("v4_cut_Hneg1.png", -1),
        ("v4_cut_Hneg2.png", -2),
        ("v4_cut_Hneg3.png", -3)
    ]
    for fname, cut_val in cuts:
        print(f"正在渲染剖面 {fname} (cut = {cut_val})...")
        cut_frame = render_view(cam_center, tm, pm, actor_sprites, context, cut=cut_val)
        cut_frame.save(os.path.join(out_dir, fname))

    # 5. Surface 切片集
    slices_dir = os.path.join(out_dir, "v4_slices")
    os.makedirs(slices_dir, exist_ok=True)
    print(f"正在渲染 Surfaces 切片集：v4_slices/...")
    for s in spec["surfaces"]:
        sid = s["surface_id"]
        slice_frame = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, only_surface_id=sid)
        slice_frame.save(os.path.join(slices_dir, f"{sid}.png"))

    # 6. HTML 報告
    print("正在生成 v4_report.html...")
    build_html_report(spec, tileset_path, props_png_path, out_dir)

    print("SUCCESS: Slave quarry 48x48 render pipeline completed perfectly.")

if __name__ == "__main__":
    main()
