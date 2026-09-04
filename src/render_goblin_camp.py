#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_goblin_camp.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: 蠻荒峽谷哥布林巢穴 (The Savage Canyon Goblin Camp) 40×40 全套視圖與互動報告渲染器。
100% 繼承奴隸礦坑與荒野十字路口黃金渲染管線：
  - 仿射投影與 Conservative 幾何防漏底
  - 自然岩壁 (cliff_face) 與側壁立面
  - 建築實體立面、門窗、實心屋頂 (0 黑洞)
  - 雙端接地置中錨點
  - 完整 Keluo Viewer HTML 骨架與 Prop 獨立 Base64 切片
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
    resample_bilinear = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR

    patch = src_transformed.transform((bw, bh), affine_mode, coeffs, resample=resample_bilinear)
    canvas.alpha_composite(patch, (int(ox_base + bx), int(oy_base + by)))

def render_view(cam_x, tm, pm, actor_sprites, context, cut=None, grid_overlay=False, elevation_labels=False, edge_labels=False):
    cols = context["cols"]
    rows = context["rows"]
    elevation_rows = context["elevation_rows"]
    surfaces = context["surfaces"]
    edges = context["edges"]
    buildings = context["buildings"]
    props = context["props"]
    actors_fixture = context.get("actors_fixture", [])

    world_w = cols * CELL
    world_h = rows * CELL

    canvas_w = int(world_w + 2 * MARGIN_X)
    canvas_h = int(world_h + MARGIN_TOP + MARGIN_BOTTOM)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(canvas)

    ox_base = MARGIN_X
    oy_base = MARGIN_TOP

    # 1. 建築腳印排除
    bld_cells = {}
    for b in buildings:
        ox, oy = b["footprint"]["origin"]
        bw = b["footprint"]["cols"]
        bh = b["footprint"]["rows"]
        for r in range(oy, oy + bh):
            for c in range(ox, ox + bw):
                bld_cells[(c, r)] = b

    # 2. 地形 surfaces 繪製（由北到南 row 由小到大）
    cell_to_surface = {}
    for sf in surfaces:
        for c, r in sf["cells"]:
            cell_to_surface[(c, r)] = sf

    for r in range(rows):
        for c in range(cols):
            if (c, r) in bld_cells:
                continue

            sf = cell_to_surface.get((c, r))
            if not sf:
                continue

            h = sf["elevation"]
            if cut is not None and h > cut:
                h = cut

            # 南立面 (South face)
            if r < rows - 1 and (c, r + 1) not in bld_cells:
                h_south = elevation_rows[r + 1][c]
                if cut is not None and h_south > cut:
                    h_south = cut
                if h > h_south:
                    p0 = PV(c * CELL, (r + 1) * CELL, h, cam_x)
                    vec_u = (CELL, 0)
                    vec_v = (0, (h - h_south) * RISE)
                    # 依材質選擇立面貼圖 (stone 使用 face_stone，其他使用 cliff_face)
                    face_mat = "face_stone" if sf["material"] == "plaza" else "cliff_face"
                    paste_parallelogram(canvas, tm.get_tile(face_mat), p0, vec_u, vec_v, ox_base, oy_base)

            # 東西向立面 (East / West side faces)
            if c < cols - 1 and (c + 1, r) not in bld_cells:
                h_east = elevation_rows[r][c + 1]
                if cut is not None and h_east > cut:
                    h_east = cut
                if h > h_east and face_visible("right", (c + 1) * CELL, cam_x):
                    x_edge = (c + 1) * CELL
                    p0 = PV(x_edge, r * CELL, h, cam_x)
                    p_y = PV(x_edge, (r + 1) * CELL, h, cam_x)
                    p_bot = PV(x_edge, r * CELL, h_east, cam_x)
                    vec_u = (p_y[0] - p0[0], p_y[1] - p0[1])
                    vec_v = (p_bot[0] - p0[0], p_bot[1] - p0[1])
                    face_mat = "face_stone" if sf["material"] == "plaza" else "cliff_face"
                    paste_parallelogram(canvas, tm.get_tile(face_mat), p0, vec_u, vec_v, ox_base, oy_base)

            if c > 0 and (c - 1, r) not in bld_cells:
                h_west = elevation_rows[r][c - 1]
                if cut is not None and h_west > cut:
                    h_west = cut
                if h > h_west and face_visible("left", c * CELL, cam_x):
                    x_edge = c * CELL
                    p0 = PV(x_edge, r * CELL, h, cam_x)
                    p_y = PV(x_edge, (r + 1) * CELL, h, cam_x)
                    p_bot = PV(x_edge, r * CELL, h_west, cam_x)
                    vec_u = (p_y[0] - p0[0], p_y[1] - p0[1])
                    vec_v = (p_bot[0] - p0[0], p_bot[1] - p0[1])
                    face_mat = "face_stone" if sf["material"] == "plaza" else "cliff_face"
                    paste_parallelogram(canvas, tm.get_tile(face_mat), p0, vec_u, vec_v, ox_base, oy_base)

            # 頂面
            tile_img = tm.get_surface_tile(sf["material"], c, r)
            p0 = PV(c * CELL, r * CELL, h, cam_x)
            p_east = PV((c + 1) * CELL, r * CELL, h, cam_x)
            vec_u = (p_east[0] - p0[0], p_east[1] - p0[1])
            vec_v = (0, CELL)
            paste_parallelogram(canvas, tile_img, p0, vec_u, vec_v, ox_base, oy_base)

    # 3. 建築物繪製 (Solid Roof, Facade, Floor)
    for b in buildings:
        ox, oy = b["footprint"]["origin"]
        bw = b["footprint"]["cols"]
        bh = b["footprint"]["rows"]
        base_h = b["base_elevation"]
        height_u = b["height_units"]
        top_h = base_h + height_u

        # 剖面處理
        is_cut = (cut is not None and cut >= base_h and cut < top_h)
        disp_h = cut if is_cut else top_h

        # (A) 室內地板
        floor_tile = tm.get_tile("wooden_floor")
        for r in range(oy, oy + bh):
            for c in range(ox, ox + bw):
                p0 = PV(c * CELL, r * CELL, base_h, cam_x)
                p_e = PV((c + 1) * CELL, r * CELL, base_h, cam_x)
                paste_parallelogram(canvas, floor_tile, p0, (p_e[0] - p0[0], p_e[1] - p0[1]), (0, CELL), ox_base, oy_base)

        # (B) 南立面 (含門窗)
        door_cells = set(tuple(d) for d in b.get("doors_local", []))
        for c_idx in range(bw):
            c_world = ox + c_idx
            r_world = oy + bh - 1
            wall_h_disp = disp_h - base_h
            if wall_h_disp > 0:
                p0 = PV(c_world * CELL, (r_world + 1) * CELL, disp_h, cam_x)
                vec_u = (CELL, 0)
                vec_v = (0, wall_h_disp * RISE)
                if (c_idx, bh - 1) in door_cells and not is_cut:
                    wall_tile = tm.get_tile("arch_door")
                elif c_idx == 0 and not is_cut:
                    wall_tile = tm.get_tile("barred_window")
                else:
                    wall_tile = tm.get_tile("stone_facade")
                paste_parallelogram(canvas, wall_tile, p0, vec_u, vec_v, ox_base, oy_base)

        # (C) 屋頂覆蓋 (若未被剖面截開)
        if not is_cut:
            roof_tile = tm.get_tile("slate_roof")
            for r in range(oy, oy + bh):
                for c in range(ox, ox + bw):
                    p0 = PV(c * CELL, r * CELL, top_h, cam_x)
                    p_e = PV((c + 1) * CELL, r * CELL, top_h, cam_x)
                    paste_parallelogram(canvas, roof_tile, p0, (p_e[0] - p0[0], p_e[1] - p0[1]), (0, CELL), ox_base, oy_base)

    # 4. 道具與演員深度排序繪製 (Y-Sort)
    render_items = []

    for p in props:
        c, r = p["cell"]
        h = p["elevation"]
        if cut is not None and h > cut:
            continue
        p_id = p["sprite"]
        img = pm.get_prop_sprite(p_id)
        if img:
            fw, fh = p.get("footprint", (1, 1))
            depth = (r + fh) * CELL + c * 0.1
            render_items.append({
                "depth": depth,
                "cell": (c, r),
                "elevation": h,
                "img": img,
                "footprint": (fw, fh),
                "id": p["id"]
            })

    for a in actors_fixture:
        c, r = a["cell"]
        h = a["elevation"]
        if cut is not None and h > cut:
            continue
        a_id = a["actor_id"]
        img = actor_sprites.get(a_id)
        if img:
            depth = (r + 1) * CELL + c * 0.1
            render_items.append({
                "depth": depth,
                "cell": (c, r),
                "elevation": h,
                "img": img,
                "footprint": (1, 1),
                "id": a_id
            })

    render_items.sort(key=lambda item: item["depth"])

    for item in render_items:
        c, r = item["cell"]
        h = item["elevation"]
        img = item["img"]
        fw, fh = item.get("footprint", (1, 1))
        wx = c * CELL
        wy = (r + fh) * CELL
        p_base = PV(wx, wy, h, cam_x)

        px = int(ox_base + p_base[0] + fw * CELL / 2 - img.width / 2)
        py = int(oy_base + p_base[1] - img.height)
        canvas.alpha_composite(img, (px, py))

    # 5. 標籤與輔助圖層
    if grid_overlay:
        for r in range(rows):
            for c in range(cols):
                h = elevation_rows[r][c]
                wx = c * CELL
                wy = r * CELL
                p0 = PV(wx, wy, h, cam_x)
                p_e = PV(wx + CELL, wy, h, cam_x)
                p_s = PV(wx, wy + CELL, h, cam_x)
                p_se = PV(wx + CELL, wy + CELL, h, cam_x)
                pts = [
                    (ox_base + p0[0], oy_base + p0[1]),
                    (ox_base + p_e[0], oy_base + p_e[1]),
                    (ox_base + p_se[0], oy_base + p_se[1]),
                    (ox_base + p_s[0], oy_base + p_s[1]),
                ]
                draw.polygon(pts, outline=(255, 255, 255, 40))

    if elevation_labels:
        for r in range(0, rows, 2):
            for c in range(0, cols, 2):
                h = elevation_rows[r][c]
                wx = c * CELL
                wy = r * CELL
                pt = PV(wx + CELL / 2, wy + CELL / 2, h, cam_x)
                draw.text((ox_base + pt[0] - 6, oy_base + pt[1] - 5), f"H{h}", fill=(255, 255, 255, 180))

    if edge_labels:
        for e in edges:
            c1, r1 = e["cell_high"]
            c2, r2 = e["cell_low"]
            h_high = e["h_high"]
            h_low = e["h_low"]
            if e["dir"] == "EAST":
                pt = PV((max(c1, c2)) * CELL, r1 * CELL + CELL / 2, h_high, cam_x)
                draw.line([(ox_base + pt[0], oy_base + pt[1] - 4), (ox_base + pt[0], oy_base + pt[1] + 4)], fill=(255, 60, 60, 200), width=2)
            else:
                pt = PV(c1 * CELL + CELL / 2, (max(r1, r2)) * CELL, h_high, cam_x)
                draw.line([(ox_base + pt[0] - 4, oy_base + pt[1]), (ox_base + pt[0] + 4, oy_base + pt[1])], fill=(60, 120, 255, 200), width=2)

    return canvas

class TileManager:
    def __init__(self, tileset_path):
        self.atlas = Image.open(tileset_path).convert("RGBA")
        self.cache = {}

    def get_tile(self, name):
        if name in self.cache:
            return self.cache[name]

        mapping = {
            "sand": (0, 0),
            "sand_var1": (1, 0),
            "sand_var2": (2, 0),
            "plaza": (4, 0),
            "field": (5, 0),
            "pit_floor": (9, 3),
            "cliff_face": (6, 0),
            "face_stone": (1, 2),
            "road": (0, 1),
            "wooden_floor": (2, 1),
            "stone_facade": (1, 2),
            "arch_door": (4, 2),
            "barred_window": (5, 2),
            "slate_roof": (7, 2),
        }
        col, row = mapping.get(name, (0, 0))
        img = self.atlas.crop((col * CELL, row * ROW_H, (col + 1) * CELL, (row + 1) * ROW_H))
        img = img.crop((0, 0, CELL, CELL))
        self.cache[name] = img
        return img

    def get_surface_tile(self, material, c, r):
        if material == "road":
            return self.get_tile("road")
        elif material == "plaza":
            return self.get_tile("plaza")
        elif material == "pit_floor":
            return self.get_tile("pit_floor")
        elif material == "field":
            return self.get_tile("field")
        else:
            h = ((c * 73856093) ^ (r * 19349663)) & 0xffff
            mod = h % 3
            if mod == 1:
                return self.get_tile("sand_var1")
            elif mod == 2:
                return self.get_tile("sand_var2")
            else:
                return self.get_tile("sand")

class PropManager:
    def __init__(self, props_png_path, props_json_path):
        self.props_atlas = Image.open(props_png_path).convert("RGBA")
        with open(props_json_path, "r", encoding="utf-8") as f:
            self.sprites_dict = json.load(f)
        self.cache = {}

    def get_prop_sprite(self, sprite_id):
        if sprite_id in self.cache:
            return self.cache[sprite_id]

        rect = self.sprites_dict.get(sprite_id)
        if not rect:
            return None
        x, y, w, h = rect
        img = self.props_atlas.crop((x, y, x + w, y + h))
        self.cache[sprite_id] = img
        return img

def create_actor_sprite(actor_id, color_hex):
    im = Image.new("RGBA", (ACTOR_W, ACTOR_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    def parse_hex(c):
        c = c.lstrip("#")
        return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)

    col = parse_hex(color_hex)
    draw.ellipse([(2, ACTOR_H - 8), (ACTOR_W - 2, ACTOR_H - 1)], fill=(0, 0, 0, 80))
    draw.ellipse([(4, 2), (ACTOR_W - 4, ACTOR_W - 6)], fill=col)
    draw.ellipse([(6, 4), (ACTOR_W - 6, ACTOR_W - 8)], fill=(255, 255, 255, 120))
    draw.rectangle([(8, ACTOR_W - 4), (ACTOR_W - 8, ACTOR_H - 6)], fill=col)
    return im

def build_html_report(spec, tileset_path, props_png_path, out_dir):
    with open(tileset_path, "rb") as f:
        tileset_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

    # 讀取 presentation 與 viewer skeleton
    pres_path = os.path.join(out_dir, "keluo_presentation.json")
    with open(pres_path, "r", encoding="utf-8") as f:
        pres = json.load(f)

    # 深度合併 presentation 到 spec
    full_spec = dict(spec)
    for k, v in pres.items():
        if k not in full_spec:
            full_spec[k] = v

    props_atlas = Image.open(props_png_path).convert("RGBA")
    with open(os.path.join(out_dir, "keluo_props_sprites.json"), "r", encoding="utf-8") as f:
        props_sprites = json.load(f)

    props_b64_dict = {}
    for p in spec.get("props", []):
        p_id = p["id"]
        spr = p["sprite"]
        if spr in props_sprites and p_id not in props_b64_dict:
            x, y, w, h = props_sprites[spr]
            crop_im = props_atlas.crop((x, y, x + w, y + h))
            buf = io.BytesIO()
            crop_im.save(buf, format="PNG")
            props_b64_dict[p_id] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    skeleton_path = os.path.join(out_dir, "keluo_viewer_skeleton.html")
    if os.path.exists(skeleton_path):
        with open(skeleton_path, "r", encoding="utf-8") as f:
            viewer_html = f.read()
    else:
        viewer_html = '<div style="position:relative; width:100%; height:640px; background:#0f111a;"><canvas id="plm-canvas" style="width:100%; height:100%;"></canvas></div>'

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>蠻荒峽谷哥布林巢穴 40×40 戰術地圖報告 (The Savage Canyon Goblin Camp)</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0b0c10; color: #c5c6c7; margin: 0; padding: 24px; }}
h1, h2, h3 {{ color: #66fcf1; }}
.card {{ background: #1f2833; border-radius: 8px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
img.preview {{ width: 100%; height: auto; border-radius: 4px; border: 1px solid #45a29e; }}
.tag {{ display: inline-block; padding: 4px 8px; background: #45a29e; color: #0b0c10; font-weight: bold; border-radius: 4px; font-size: 12px; margin-right: 8px; }}
</style>
</head>
<body>
<h1>👺 蠻荒峽谷哥布林巢穴 40×40 戰術地圖報告 (The Savage Canyon Goblin Camp)</h1>
<p>由 <strong>諾諾 (Nono)</strong> 架構之 2.5D 真高程拓撲戰術地圖模組，具備環形峽谷險峻幾何、骷髏王座、綠沸大鐵鍋、骨頭圖騰、粗木拒馬隘口與俘虜深坑。</p>

<div class="card">
  <h2>🎮 互動式檢視器 (Keluo Interactive Viewer)</h2>
  <p>支援即時縮放 (Mouse Wheel)、拖拽平移 (Drag)、相機角度切換與 H2/H1/H0 剖面即時切片。</p>
  {viewer_html}
</div>

<div class="card">
  <h2>📸 核心視圖預覽</h2>
  <div class="grid-2">
    <div>
      <h3>40×40 全景俯視圖 (1280×1280 px)</h3>
      <img class="preview" src="goblin_camp_all.png" alt="全景">
    </div>
    <div>
      <h3>左斜 15° 側向投影視圖</h3>
      <img class="preview" src="goblin_camp_cam_left.png" alt="左視角">
    </div>
  </div>
</div>

<div class="card">
  <h2>🔍 四大功能象限特寫</h2>
  <div class="grid-2">
    <div>
      <h3>👑 西北酋長石台與骨骸要塞</h3>
      <img class="preview" src="goblin_camp_chieftain_crop.png" alt="酋長大帳">
    </div>
    <div>
      <h3>🍲 東北薩滿沸騰大鐵鍋與骨塚祭壇</h3>
      <img class="preview" src="goblin_camp_shaman_crop.png" alt="薩滿祭壇">
    </div>
    <div>
      <h3>🪵 東南入谷峽谷通道與尖刺拒馬防線</h3>
      <img class="preview" src="goblin_camp_chokepoint_crop.png" alt="入谷隘口">
    </div>
    <div>
      <h3>⛓️ 西南俘虜泥坑與掠奪贓物寶箱</h3>
      <img class="preview" src="goblin_camp_loot_crop.png" alt="俘虜坑">
    </div>
  </div>
</div>

<script>
window.PLM_SPEC = {json.dumps(full_spec, ensure_ascii=False)};
window.PLM_ATLASES = {{ "kenshi": "{tileset_b64}" }};
window.PLM_PROPS = {json.dumps(props_b64_dict)};
</script>
<script src="keluo_viewer.js"></script>
</body>
</html>
"""

    report_path = os.path.join(out_dir, "goblin_camp_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"SUCCESS: Report generated at: {report_path}")

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root_dir, "reports")
    spec_path = os.path.join(out_dir, "goblin_camp_spec.json")

    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    tileset_path = os.path.join(out_dir, "keluo_kenshi_tileset.png")
    props_png_path = os.path.join(out_dir, "keluo_kenshi_props.png")
    props_json_path = os.path.join(out_dir, "keluo_props_sprites.json")
    presentation_path = os.path.join(out_dir, "keluo_presentation.json")

    with open(presentation_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)

    tm = TileManager(tileset_path)
    pm = PropManager(props_png_path, props_json_path)

    actor_sprites = {}
    for a in spec.get("actors_fixture", []):
        actor_sprites[a["actor_id"]] = create_actor_sprite(a["actor_id"], a["color"])

    context = {
        "cols": spec["grid"]["cols"],
        "rows": spec["grid"]["rows"],
        "elevation_rows": spec["elevation_rows"],
        "surfaces": spec["surfaces"],
        "edges": spec["edges"],
        "buildings": spec["buildings"],
        "props": spec["props"],
        "actors_fixture": spec.get("actors_fixture", []),
        "presentation": presentation
    }

    world_w = spec["grid"]["cols"] * CELL
    cam_center = world_w / 2

    # 1. 核心視圖
    print("正在渲染 goblin_camp_all.png...")
    render_view(cam_center, tm, pm, actor_sprites, context, cut=None).save(os.path.join(out_dir, "goblin_camp_all.png"))

    print("正在渲染 goblin_camp_cam_left.png...")
    render_view(0, tm, pm, actor_sprites, context, cut=None).save(os.path.join(out_dir, "goblin_camp_cam_left.png"))

    print("正在渲染 goblin_camp_cam_right.png...")
    render_view(world_w, tm, pm, actor_sprites, context, cut=None).save(os.path.join(out_dir, "goblin_camp_cam_right.png"))

    # 2. POI 特寫裁切
    resample_nearest = Image.Resampling.NEAREST if hasattr(Image, "Resampling") else Image.NEAREST
    frame_all = Image.open(os.path.join(out_dir, "goblin_camp_all.png"))

    # 西北酋長高台
    crop_chief_box = (
        int(MARGIN_X + 4 * CELL),
        int(MARGIN_TOP + 4 * CELL),
        int(MARGIN_X + 18 * CELL),
        int(MARGIN_TOP + 14 * CELL)
    )
    frame_all.crop(crop_chief_box).resize(((crop_chief_box[2] - crop_chief_box[0]) * 2, (crop_chief_box[3] - crop_chief_box[1]) * 2), resample=resample_nearest).save(os.path.join(out_dir, "goblin_camp_chieftain_crop.png"))

    # 東北薩滿祭壇
    crop_shaman_box = (
        int(MARGIN_X + 24 * CELL),
        int(MARGIN_TOP + 4 * CELL),
        int(MARGIN_X + 36 * CELL),
        int(MARGIN_TOP + 14 * CELL)
    )
    frame_all.crop(crop_shaman_box).resize(((crop_shaman_box[2] - crop_shaman_box[0]) * 2, (crop_shaman_box[3] - crop_shaman_box[1]) * 2), resample=resample_nearest).save(os.path.join(out_dir, "goblin_camp_shaman_crop.png"))

    # 東南入谷隘口
    crop_gorge_box = (
        int(MARGIN_X + 19 * CELL),
        int(MARGIN_TOP + 25 * CELL),
        int(MARGIN_X + 35 * CELL),
        int(MARGIN_TOP + 38 * CELL)
    )
    frame_all.crop(crop_gorge_box).resize(((crop_gorge_box[2] - crop_gorge_box[0]) * 2, (crop_gorge_box[3] - crop_gorge_box[1]) * 2), resample=resample_nearest).save(os.path.join(out_dir, "goblin_camp_chokepoint_crop.png"))

    # 西南俘虜深坑
    crop_loot_box = (
        int(MARGIN_X + 6 * CELL),
        int(MARGIN_TOP + 18 * CELL),
        int(MARGIN_X + 18 * CELL),
        int(MARGIN_TOP + 27 * CELL)
    )
    frame_all.crop(crop_loot_box).resize(((crop_loot_box[2] - crop_loot_box[0]) * 2, (crop_loot_box[3] - crop_loot_box[1]) * 2), resample=resample_nearest).save(os.path.join(out_dir, "goblin_camp_loot_crop.png"))

    # 3. 疊加圖層
    print("正在渲染 goblin_camp_02_grid_overlay.png...")
    render_view(cam_center, tm, pm, actor_sprites, context, cut=None, grid_overlay=True).save(os.path.join(out_dir, "goblin_camp_02_grid_overlay.png"))

    print("正在渲染 goblin_camp_03_elevation_labels.png...")
    render_view(cam_center, tm, pm, actor_sprites, context, cut=None, elevation_labels=True).save(os.path.join(out_dir, "goblin_camp_03_elevation_labels.png"))

    print("正在渲染 goblin_camp_04_edge_labels.png...")
    render_view(cam_center, tm, pm, actor_sprites, context, cut=None, edge_labels=True).save(os.path.join(out_dir, "goblin_camp_04_edge_labels.png"))

    # 4. 剖面切片
    cuts = [
        ("goblin_camp_cut_H2.png", 2),
        ("goblin_camp_cut_H1.png", 1),
        ("goblin_camp_cut_H0.png", 0),
    ]
    for fname, cut_val in cuts:
        print(f"正在渲染剖面 {fname} (cut = {cut_val})...")
        render_view(cam_center, tm, pm, actor_sprites, context, cut=cut_val).save(os.path.join(out_dir, fname))

    # 5. HTML 報告
    print("正在生成 goblin_camp_report.html...")
    build_html_report(spec, tileset_path, props_png_path, out_dir)
    print("SUCCESS: Goblin Camp render pipeline completed with 0 errors!")

if __name__ == "__main__":
    main()
