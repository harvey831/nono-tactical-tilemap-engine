#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_chunk_0_0_v2.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: 戶外地形、建築、道具與演員渲染器 (v2 - Round 10 水面高度定稿與剖面修訂版)，只用 Pillow 與標準庫。

============================================================
【Round 10 修訂要點】：
1. 水面高度定稿：
   - 水面＝H0（減 0.15），即 0 - 0.15 = -0.15。
   - 水方塊佔 [-1, 0]，河床在 -1（深處 -2）。
   - 水格 surface elevation ＝ 河床最高那級 + 1（通常 0）。
2. 剖面定稿（每層只顯示頂面高度 <= cut 的東西）：
   - cut >= 0 看得到水（v2_cut_H0.png 有水）；
   - cut = -1 水被切掉，看到河床（v2_cut_Hneg1.png：-1 的床畫泥地、-2 的床畫在 -2 並畫出 -1→-2 的水下岸壁，不畫水面）；
   - cut = -2 只剩 -2 的床，其餘是 -2 的 cut_plane 切面（v2_cut_Hneg2.png 沒水）。
3. 招牌元件確認：
   - 門面元件貼圖前先以 bbox 裁切透明邊，並裁在牆帶內；
   - HTML 交付報告 PLM_PROPS 注入所有 facade 影像，確保全景與報告皆能精準呈現。
4. 鐵匠鋪屋頂（H3）DECK 梯洞透視、R25 樓梯三階、R38 手繪 3/4 視角 sprite 等規範完整保持。
5. R41 修正：水面擁有的面一律使用土岸 tile（pit_wall / pit_wall_side），不用 face_water。
============================================================
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
# 基礎幾何常數與投影參數 (Presentation Constants)
# ---------------------------------------------------------------------------
COLS = 40
ROWS = 40
CELL = 32
ROW_H = 48  # atlas 中每列的高度

RISE = 23.04          # 垂直高度倍率: 32 * 0.72
SIDE_SHIFT = 3.84     # 水平錯位倍率: 32 * 0.12
SIDE_SPREAD = 192.0   # 鏡頭影響半徑: 32 * 6

MARGIN_X = 40
MARGIN_TOP = int(7 * RISE) + 40    # 確保最高 H6/H7 頂面與 H3 哨塔頂不破頂 (~201 px)
MARGIN_BOTTOM = int(2 * RISE) + 24 # 確保負高程 (~70 px)

WORLD_W = COLS * CELL # 1280
WORLD_H = ROWS * CELL # 1280
CANVAS_W = WORLD_W + 2 * MARGIN_X
CANVAS_H = WORLD_H + MARGIN_TOP + MARGIN_BOTTOM
OX = MARGIN_X
OY = MARGIN_TOP
BG = (15, 17, 26, 255)

ACTOR_W = 24
ACTOR_H = 30

# ---------------------------------------------------------------------------
# 頂點投影與可見性 (R19, R29)
# ---------------------------------------------------------------------------
def side_at(world_x, cam_x):
    """計算 world_x 處相對於鏡頭中心的側向因子，範圍限制在 [-1, 1]。"""
    return max(-1.0, min(1.0, (world_x - cam_x) / SIDE_SPREAD))

def PV(x, y, h, cam_x):
    """
    R19 頂點投影：同一個 3D 頂點經由連續 side(x) 映射到螢幕 2D 像素座標。
    sy = y - h * 23.04
    sx = x + h * 3.84 * side(x)
    """
    sd = side_at(x, cam_x)
    return (x + sd * h * SIDE_SHIFT, y - h * RISE)

def face_visible(which, x_edge, cam_x):
    """
    R29 側面可見性判定：
    - left: 法線向西 (-x)，鏡頭在左側 (side > 0.03) 時可見
    - right: 法線向東 (+x)，鏡頭在右側 (side < -0.03) 時可見
    """
    sd = side_at(x_edge, cam_x)
    return sd > 0.03 if which == "left" else sd < -0.03

# ---------------------------------------------------------------------------
# 平行四邊形仿射變換與光柵化 (Affine Warp & Conservative Rasterization, R23)
# ---------------------------------------------------------------------------
def expand_source_clamp(src):
    """
    將 src 四周邊緣延伸 1 px (clamp)，確保保守光柵化在 1 px 膨脹採樣時
    取得邊緣材質真實顏色，而非被裁切為透明 (0, 0, 0, 0)。
    """
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
    """
    將矩形材質 src 貼為平行四邊形：
    dst(u, v) = p0 + (u / w) * vec_u + (v / h) * vec_v
    - conservative=True: 使用 MaxFilter(3) 保守光柵化消弭邊緣接縫（不透明幾何專用）。
    - conservative=False: 原尺寸精確光柵化，不膨脹、不畫邊線（半透明水面專用，避免相鄰水格重疊產生深色方框線）。
    """
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
# 材質快取與處理 (Tile Helpers)
# ---------------------------------------------------------------------------
def force_opaque(img):
    """確保地面頂部 tile 不透明，避免透出底色。"""
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
        """R14: 水平平鋪 n 格，垂直沿投影高度向量 BOX 壓縮並微壓暗。"""
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
        """依 [atlas, col, row, w, h] 裁切任意尺寸的 sprite。若無指定 w,h 則預設 CELL×CELL。"""
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
        """
        R28 & R30 & R32: 一層樓 3 個高度單位 = 69 px 立面帶。
        牆面 tile 由底向上鋪滿 69 px；二樓以上底部加深色接縫。
        """
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

# ---------------------------------------------------------------------------
# 道具圖庫管理 (R38 手繪 3/4 視角 Sprite Manager)
# ---------------------------------------------------------------------------
class PropsManager:
    def __init__(self, props_atlas_img, props_coords_dict, props_boxes_dict=None):
        self.atlas = props_atlas_img
        self.coords = props_coords_dict
        self.cache = {}
        self.missing_sprites = set()

    def get_prop_sprite(self, name):
        """依據 keluo_props_sprites.json 裁切對應 2D sprite。無對應圖檔不硬湊。"""
        if name not in self.coords:
            if name not in self.missing_sprites:
                self.missing_sprites.add(name)
            return None
        if name not in self.cache:
            x, y, w, h = self.coords[name]
            self.cache[name] = self.atlas.crop((x, y, x + w, y + h))
        return self.cache[name]

# ---------------------------------------------------------------------------
# 演員與字型管理 (Actors Fixture Helpers)
# ---------------------------------------------------------------------------
def load_actor_font(font_size=12):
    """載入支援中文與標準字符的 TrueType 字型，若無則降級至預設字型。"""
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
    """
    建立 24×30 的演員 fixture 色塊加代表字 sprite。
    底部帶影子，主體為 20×20 圓形色塊，置中標示身分首字。
    """
    img = Image.new("RGBA", (ACTOR_W, ACTOR_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    color_rgb = tuple(actor_def.get("color", [56, 189, 248]))
    fill_col = color_rgb + (240,)
    outline_col = (18, 22, 30, 255)

    # 1. 底部接地陰影
    d.ellipse([(2, ACTOR_H - 6), (ACTOR_W - 3, ACTOR_H - 1)], fill=(0, 0, 0, 90))

    # 2. 身體下擺底座
    d.rounded_rectangle([(3, 14), (ACTOR_W - 4, ACTOR_H - 4)], radius=3, fill=fill_col, outline=outline_col, width=1)

    # 3. 頭部主色塊圓形 (直徑 20)
    d.ellipse([(2, 1), (ACTOR_W - 3, 20)], fill=fill_col, outline=outline_col, width=2)

    # 4. 身分文字 (label)
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
# Round 10 水體連通與有效高度判定 (Water Levels & Effective Elevation Helpers)
# ---------------------------------------------------------------------------
def compute_water_levels(elevation_rows, water_cells_set):
    """
    Round 10 定稿: flood fill 每個連通水體 (4-鄰、只走 water_cells)，
    水格 surface elevation ＝ 水體最高河床 + 1 (通常 H0)。
    水面畫在 0 - 0.15 級 (即 surface elevation - 0.15)。
    回傳字典:
      cell_water_level: (col, row) -> 水面高度 (surface elevation - 0.15, 通常 -0.15)
      cell_water_layer: (col, row) -> 水格 surface elevation (最高河床 + 1, 通常 0)
    """
    cell_water_level = {}
    cell_water_layer = {}
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
            max_bed = max(elevation_rows[br][bc] for bc, br in body)
            w_surf = int(max_bed + 1)
            wl = w_surf - 0.15
            for pt in body:
                cell_water_layer[pt] = w_surf
                cell_water_level[pt] = wl
    return cell_water_level, cell_water_layer

def cell_draw_height(raw_h, cut=None):
    """計算格點的實際繪製高度。若高於 cut，截斷到 cut。"""
    if cut is not None and raw_h > cut:
        return cut
    return raw_h

def neighbor_elev(c, r, dx, dy, elevation_rows, cut=None):
    """
    取得鄰格有效高程。
    R40: chunk 外視為 H0。若受 cut 限制，鄰格高度亦截斷至 cut。
    """
    nc, nr = c + dx, r + dy
    if 0 <= nc < COLS and 0 <= nr < ROWS:
        v = elevation_rows[nr][nc]
    else:
        v = 0
    if cut is not None and v > cut:
        return cut
    return v

def effective_neighbor_elev(c, r, dx, dy, context, cut=None):
    """
    Round 10: 取得 (c, r) 向 (c+dx, r+dy) 暴露時的鄰格有效高度。
    - chunk 外視為 H0 (R40)。
    - 水格在 cut >= 0 時具有頂面水面高度 (通常 0)；在 cut < 0 水被切掉時暴露其河床高度。
    - 橋面鄰格照舊 (依 elevation_rows)。
    """
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
    """
    計算當前格向 which 側暴露的垂直級數集合 {k : nb < k <= h}。
    水格側面由 draw_outdoor_cell 水下岸壁專屬繪製，常規側面回傳空集合。
    """
    elevation_rows = context["elevation_rows"]
    water_cells = context.get("water_cells", set())

    pt = (c, r)
    if pt in water_cells:
        return set()

    raw_h = elevation_rows[r][c]
    h = cell_draw_height(raw_h, cut)

    dx = -1 if which == "left" else 1
    nb = effective_neighbor_elev(c, r, dx, 0, context, cut)
    if nb < h:
        return set(range(nb + 1, h + 1))
    return set()

# ---------------------------------------------------------------------------
# R41 面的材質動態對齊 (Material Selection by Higher Cell Top Surface)
# ---------------------------------------------------------------------------
def front_tile_for(c, r, k, context, h_bottom=None):
    """
    新規則 R41：面的材質由擁有該面的較高格 (c, r) 的頂面材質決定。
    - 木橋 -> 木板側 (bridge_face / face_bridge)
    - 水面 -> 土岸 (pit_wall / pit_wall_side，不用 face_water，顏色由半透明水去變)
    - 石板廣場 -> 石砌 (face_stone / stone wall)
    - 田 -> 土坎 (adobe wall)
    - 沙地/泥灘地形 -> 沙崖 tile (cliff_face / cliff_face_base) 或 pit_wall (負高程非水面)
    """
    presentation = context["presentation"]
    tiles = presentation.get("tiles", {})
    styles = presentation.get("styles", {})
    pt = (c, r)

    if pt in context.get("bridge_cells", set()):
        return tiles.get("bridge_face") or tiles.get("face_bridge")
    if pt in context.get("water_cells", set()):
        return tiles.get("pit_wall") or tiles.get("pit_wall_side")
    if pt in context.get("plaza_cells", set()):
        return tiles.get("face_stone", styles.get("stone", {}).get("wall"))
    if pt in context.get("field_cells", set()):
        return styles.get("adobe", {}).get("wall")
    if pt in context.get("mud_cells", set()):
        return tiles.get("pit_wall")

    # 預設沙地 / 泥灘地形
    elevation_rows = context.get("elevation_rows")
    elev = elevation_rows[r][c] if (elevation_rows and 0 <= c < COLS and 0 <= r < ROWS) else 0
    if elev < 0:
        return tiles.get("pit_wall")

    if h_bottom is not None and k == max(h_bottom, 0) + 1:
        return tiles.get("cliff_face_base")
    return tiles.get("cliff_face")

# ---------------------------------------------------------------------------
# 面繪製函數 (Draw Front, Side, Top, Transition)
# ---------------------------------------------------------------------------
def draw_front_faces(canvas, c, r, h_top, h_bottom, cam_x, tm, context):
    """南向正面：每級一片 32×23，從 h_top 遞減落到 h_bottom。依 R41 依附頂面材質。"""
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
    """R13 / R41: 連續 n_rows 格的側面作為單一四邊形整段一次貼。側面先取頂面同材質正面 tile 再 BOX 壓縮。"""
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
    """頂面 tile 四角投影張成，統一走 paste_parallelogram。水面可傳入 conservative=False。"""
    p0 = PV(x, y, h, cam_x)
    p1 = PV(x + img.width, y, h, cam_x)
    paste_parallelogram(canvas, img, p0, (p1[0] - p0[0], 0), (0, img.height), conservative=conservative)

def draw_transition(canvas, c, r, h, cam_x, context, cut=None):
    """
    R35 / R44: 平面與垂直面的幾何過渡。
    水格不畫線；南鄰較低時畫受光線與稜線；北/西/東鄰較高且可見時畫接觸漸層陰影。
    """
    pt = (c, r)
    water_cells = context.get("water_cells", set())
    if pt in water_cells:
        return

    x = c * CELL
    y = r * CELL
    layer = Image.new("RGBA", (CELL + 2, CELL + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # 南鄰
    south = effective_neighbor_elev(c, r, 0, 1, context, cut)
    if south < h:
        d.line([(0, CELL - 2), (CELL + 1, CELL - 2)], fill=(255, 236, 190, 70))
        d.line([(0, CELL - 1), (CELL + 1, CELL - 1)], fill=(60, 40, 20, 120))

    # 北鄰
    north = effective_neighbor_elev(c, r, 0, -1, context, cut)
    if north > h:
        for k in range(4):
            d.line([(0, k), (CELL + 1, k)], fill=(40, 26, 14, 110 - k * 26))

    # 西鄰
    west = effective_neighbor_elev(c, r, -1, 0, context, cut)
    if west > h and face_visible("right", x, cam_x):
        for k in range(3):
            d.line([(k, 0), (k, CELL + 1)], fill=(40, 26, 14, 100 - k * 30))

    # 東鄰
    east = effective_neighbor_elev(c, r, 1, 0, context, cut)
    if east > h and face_visible("left", x + CELL, cam_x):
        for k in range(3):
            d.line([(CELL - 1 - k, 0), (CELL - 1 - k, CELL + 1)], fill=(40, 26, 14, 100 - k * 30))

    p0 = PV(x, y, h, cam_x)
    p1 = PV(x + CELL, y, h, cam_x)
    paste_parallelogram(canvas, layer.crop((0, 0, CELL, CELL)), p0, (p1[0] - p0[0], 0), (0, CELL))

# ---------------------------------------------------------------------------
# 地表頂面材質判定 (R45 溝 16 向 autotile)
# ---------------------------------------------------------------------------
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
        # R45: 溝 16 向 autotile (N=1, E=2, S=4, W=8，鄰是溝或水就算相連)
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            npt = (c + dx, r + dy)
            if npt in ditch_cells or npt in water_cells:
                m |= bit

        ditch_autotile = presentation.get("ditch_autotile", {})
        tile_spec = ditch_autotile.get(str(m))
        if tile_spec:
            if isinstance(tile_spec, list) and len(tile_spec) == 2 and isinstance(tile_spec[0], int):
                ref = ["kenshi", tile_spec[0], tile_spec[1]]
            elif isinstance(tile_spec, list) and len(tile_spec) >= 3 and isinstance(tile_spec[0], str):
                ref = tile_spec
            else:
                ref = ["kenshi", tile_spec[0], tile_spec[1]]
            img = tm.get_top_tile(ref)
        else:
            ditch_ref = presentation.get("tiles", {}).get("ditch", ["kenshi", 12, 3])
            img = tm.get_top_tile(ditch_ref)
    elif pt in water_cells:
        img = tm.get_top_tile(presentation["tiles"]["water"])
    elif pt in mud_cells:
        img = tm.get_top_tile(presentation["tiles"]["pit_floor"])
    elif h < 0:
        img = tm.get_top_tile(presentation["tiles"]["pit_floor"])
    elif pt in road_cells:
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            if (c + dx, r + dy) in road_cells:
                m |= bit
        tc, tr = presentation["road_autotile"][str(m)]
        img = tm.get_top_tile(["kenshi", tc, tr])
    elif pt in plaza_cells:
        img = tm.get_top_tile(presentation["tiles"]["plaza"])
    elif pt in field_cells:
        sand_variants = presentation["tiles"]["sand"]
        sand_idx = (((c * 73856093) ^ (r * 19349663)) & 0xffff) % len(sand_variants)
        sand_ref = sand_variants[sand_idx]
        base = tm.get_top_tile(sand_ref).copy()
        base.alpha_composite(tm.get_top_tile(presentation["tiles"]["field"]))
        img = base
    else:
        sand_variants = presentation["tiles"]["sand"]
        sand_idx = (((c * 73856093) ^ (r * 19349663)) & 0xffff) % len(sand_variants)
        sand_ref = sand_variants[sand_idx]
        img = tm.get_top_tile(sand_ref)

    if h > 0:
        tint_info = presentation.get("plateau_tint", {})
        color = tuple(tint_info.get("color", [118, 92, 52]))
        alpha_dict = tint_info.get("alpha", {})
        a = alpha_dict.get(str(h), 0.38 if h >= 3 else 0.0)
        if a > 0:
            img = Image.blend(img, Image.new("RGBA", img.size, color + (255,)), a)

    return img

# ---------------------------------------------------------------------------
# 單一戶外格繪製流程 (Draw Outdoor Cell with Round 10 水面高度與剖面)
# ---------------------------------------------------------------------------
def draw_outdoor_cell(canvas, c, r, cam_x, tm, context, cut=None):
    elevation_rows = context["elevation_rows"]
    water_cells = context.get("water_cells", set())
    cell_water_layer = context.get("cell_water_layer", {})
    building_footprint_cells = context.get("building_footprint_cells", set())
    buildings = context.get("buildings", [])
    presentation = context["presentation"]

    pt = (c, r)
    is_water = pt in water_cells
    is_building_cell = pt in building_footprint_cells

    if is_building_cell:
        if cut is not None:
            for b in buildings:
                ox, oy = b["footprint"]["origin"]
                bw, bh = b["footprint"]["cols"], b["footprint"]["rows"]
                if ox <= c < ox + bw and oy <= r < oy + bh:
                    if cut <= b.get("base_elevation", 0):
                        cut_tile = tm.get_top_tile(presentation["tiles"]["cut_plane"])
                        paste_top(canvas, cut_tile, c * CELL, r * CELL, cut, cam_x)
                    break
        return

    # -----------------------------------------------------------------------
    # Round 10 水格專用渲染流程：
    # - 水面＝H0（減 0.15），水方塊佔 [-1, 0]，河床在 -1（深處 -2）。
    # - 水格 surface elevation ＝ 最高河床 + 1（通常 0）。
    # - 剖面：cut >= 0 看得到水；cut = -1 切掉水，看到河床（-1 畫泥地、-2 畫深色泥地並畫出 -1→-2 水下岸壁，不畫水面）；
    #   cut = -2 只剩 -2 的床，其餘 -1 河床被 cut 截斷成 -2 切面。
    # -----------------------------------------------------------------------
    if is_water:
        bed_h = elevation_rows[r][c]
        water_surface = cell_water_layer.get(pt, 0)
        wl = water_surface - 0.15

        # 1. 剖面判斷：當 cut 比河床還要低時（例如 cut = -2，而 -1 的河床高於 -2），河床被切掉，畫 cut_plane
        if cut is not None and bed_h > cut:
            h = cut
            south = effective_neighbor_elev(c, r, 0, 1, context, cut)
            if south < h:
                draw_front_faces(canvas, c, r, h, south, cam_x, tm, context)
            for which in ("left", "right"):
                xe = c * CELL + (CELL if which == "right" else 0)
                if not face_visible(which, xe, cam_x):
                    continue
                dx = -1 if which == "left" else 1
                nb = effective_neighbor_elev(c, r, dx, 0, context, cut)
                if nb < h:
                    for k in range(h, nb, -1):
                        draw_side_run(canvas, c, r, 1, k, which, cam_x, tm, context)
            cut_tile = tm.get_top_tile(presentation["tiles"]["cut_plane"])
            paste_top(canvas, cut_tile, c * CELL, r * CELL, h, cam_x)
            return

        bed_draw_h = cell_draw_height(bed_h, cut)

        # 2. 河床頂面在河床高度 (cut >= bed_h 時畫河床，-1 畫泥地，-2 畫深色泥地)
        if cut is None or bed_h <= cut:
            bed_img = tm.get_top_tile(presentation["tiles"]["pit_floor"]).copy()
            if bed_h <= -2:
                bed_img = Image.blend(bed_img, Image.new("RGBA", bed_img.size, (0, 0, 0, 255)), 0.43)
            paste_top(canvas, bed_img, c * CELL, r * CELL, bed_draw_h, cam_x)

        # 3. 只有鄰格比自己河床高的地方畫水下岸壁（鄰是水→比它的河床；鄰是地→比它的高度）
        # Round 12 規則：切水後代畫的岸壁「頂端不得高於 cut」（鄰格高度先跟 cut 取 min）。
        pit_wall_ref = presentation["tiles"].get("pit_wall", ["kenshi", 0, 3])
        pit_wall_src = tm.get_face_src(pit_wall_ref)
        water_ceiling = water_surface
        if cut is not None and water_ceiling > cut:
            water_ceiling = cut

        # 北面 (y = r * CELL)
        nb_h = elevation_rows[r - 1][c] if (0 <= r - 1 < ROWS) else 0
        if cut is not None:
            nb_h = min(nb_h, cut)
        if nb_h > bed_h:
            wall_top = min(nb_h, water_ceiling)
            if cut is not None and wall_top > cut:
                wall_top = cut
            wall_bot = bed_h
            for k in range(wall_top, wall_bot, -1):
                p0 = PV(c * CELL, r * CELL, k, cam_x)
                p1 = PV((c + 1) * CELL, r * CELL, k, cam_x)
                p2 = PV(c * CELL, r * CELL, k - 1, cam_x)
                paste_parallelogram(canvas, pit_wall_src, p0, (p1[0] - p0[0], p1[1] - p0[1]), (p2[0] - p0[0], p2[1] - p0[1]))

        # 西側側面 (x = c * CELL, 法線向東，side > 0.03 時可見)
        if face_visible("right", c * CELL, cam_x):
            wb_h = elevation_rows[r][c - 1] if (0 <= c - 1 < COLS) else 0
            if cut is not None:
                wb_h = min(wb_h, cut)
            if wb_h > bed_h:
                wall_top = min(wb_h, water_ceiling)
                if cut is not None and wall_top > cut:
                    wall_top = cut
                wall_bot = bed_h
                for k in range(wall_top, wall_bot, -1):
                    p0 = PV(c * CELL, r * CELL, k, cam_x)
                    p1 = PV(c * CELL, r * CELL, k - 1, cam_x)
                    v_vec = (p1[0] - p0[0], p1[1] - p0[1])
                    v_len = math.hypot(*v_vec)
                    if v_len >= 0.5:
                        side_img = tm.get_side_source(pit_wall_src, 1, v_len, 0.10)
                        paste_parallelogram(canvas, side_img, p0, (0, CELL), v_vec)

        # 東側側面 (x = (c + 1) * CELL, 法線向西，side < -0.03 時可見)
        if face_visible("left", (c + 1) * CELL, cam_x):
            eb_h = elevation_rows[r][c + 1] if (0 <= c + 1 < COLS) else 0
            if cut is not None:
                eb_h = min(eb_h, cut)
            if eb_h > bed_h:
                wall_top = min(eb_h, water_ceiling)
                if cut is not None and wall_top > cut:
                    wall_top = cut
                wall_bot = bed_h
                for k in range(wall_top, wall_bot, -1):
                    p0 = PV((c + 1) * CELL, r * CELL, k, cam_x)
                    p1 = PV((c + 1) * CELL, r * CELL, k - 1, cam_x)
                    v_vec = (p1[0] - p0[0], p1[1] - p0[1])
                    v_len = math.hypot(*v_vec)
                    if v_len >= 0.5:
                        side_img = tm.get_side_source(pit_wall_src, 1, v_len, 0.10)
                        paste_parallelogram(canvas, side_img, p0, (0, CELL), v_vec)

        # 4. 水面貼半透明水（alpha 0.7，原尺寸不膨脹）
        # 剖面規則：每層只顯示頂面高度 <= cut 的東西。
        # 水面頂面在 water_surface (0)，所以 cut >= 0 (或 cut is None) 時畫水面；
        # cut < 0 時切掉水，只畫河床與水下岸壁，不畫水面！
        if cut is None or water_surface <= cut:
            water_tile = tm.get_top_tile(presentation["tiles"]["water"]).copy()
            r_ch, g_ch, b_ch, a_ch = water_tile.split()
            a_ch = a_ch.point(lambda v: int(v * 0.70) if v > 0 else 0)
            water_tile = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
            paste_top(canvas, water_tile, c * CELL, r * CELL, wl, cam_x, conservative=False)

        return

    # -----------------------------------------------------------------------
    # 常規陸地/溝渠格繪製
    # -----------------------------------------------------------------------
    raw_h = elevation_rows[r][c]
    h = cell_draw_height(raw_h, cut)
    is_cut_cell = (cut is not None and raw_h > cut)

    # 1. 南向正面 (R15 / R22 截斷柱子照樣畫到 cut，依 R41 依附較高格頂面材質)
    south = effective_neighbor_elev(c, r, 0, 1, context, cut)
    if south < h:
        draw_front_faces(canvas, c, r, h, south, cam_x, tm, context)

    # 2. 東西側面 run (R13, R14, R29, R41)
    for which in ("left", "right"):
        xe = c * CELL + (CELL if which == "right" else 0)
        if not face_visible(which, xe, cam_x):
            continue
        levels = side_levels(c, r, which, context, cut)
        above = side_levels(c, r - 1, which, context, cut) if r > 0 else set()
        for k in sorted(levels - above, reverse=True):
            n = 1
            while (r + n < ROWS) and ((c, r + n) not in building_footprint_cells) and (k in side_levels(c, r + n, which, context, cut)):
                n += 1
            draw_side_run(canvas, c, r, n, k, which, cam_x, tm, context)

    # 3. R40 代畫：chunk 外視為 H0，若較高鄰格在 chunk 外由自己代畫
    def absent(cc, rr):
        return not (0 <= cc < COLS and 0 <= rr < ROWS) or ((cc, rr) in building_footprint_cells)

    # 北鄰代畫
    nb = effective_neighbor_elev(c, r, 0, -1, context, cut)
    if absent(c, r - 1) and nb > h:
        draw_front_faces(canvas, c, r - 1, nb, h, cam_x, tm, context)

    # 西鄰代畫
    wb = effective_neighbor_elev(c, r, -1, 0, context, cut)
    if absent(c - 1, r) and wb > h and face_visible("right", c * CELL, cam_x):
        for k in range(wb, h, -1):
            draw_side_run(canvas, c - 1, r, 1, k, "right", cam_x, tm, context)

    # 東鄰代畫
    eb = effective_neighbor_elev(c, r, 1, 0, context, cut)
    if absent(c + 1, r) and eb > h and face_visible("left", (c + 1) * CELL, cam_x):
        for k in range(eb, h, -1):
            draw_side_run(canvas, c + 1, r, 1, k, "left", cam_x, tm, context)

    # 4. 頂面 tile (被截斷格貼 cut_plane，其餘貼正常地表)
    if is_cut_cell:
        cut_img = tm.get_top_tile(presentation["tiles"]["cut_plane"])
        paste_top(canvas, cut_img, c * CELL, r * CELL, h, cam_x)
    else:
        top_img = get_ground_tile(c, r, h, tm, context)
        paste_top(canvas, top_img, c * CELL, r * CELL, h, cam_x)

    # 5. 過渡線條 (R35, R44)
    draw_transition(canvas, c, r, h, cam_x, context, cut)

# ---------------------------------------------------------------------------
# R33 / R34 Facade 素材取得與輔助生成 (先 bbox 裁透明邊)
# ---------------------------------------------------------------------------
def create_fallback_sign(text_label, bg_color=(90, 60, 30, 255), fg_color=(255, 255, 255, 255)):
    """建立優雅的 32×32 告示牌/懸掛裝飾 fallback 影像。"""
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 6, 27, 26], fill=bg_color, outline=(40, 25, 10, 255), width=1)
    d.line([(8, 0), (8, 6)], fill=(30, 20, 10, 255), width=1)
    d.line([(23, 0), (23, 6)], fill=(30, 20, 10, 255), width=1)
    f = load_actor_font(10)
    if f:
        try:
            d.text((16, 16), text_label, fill=fg_color, font=f, anchor="mm")
        except Exception:
            pass
    return img

def get_facade_image(item, tm, pm, presentation):
    """
    依 R33/R34 取得外牆立面掛件素材。
    確保 sign_beer、sign_hammer、sign_potion、sack 等皆能精準取得材質。
    依珂洛規範：先 bbox 裁掉透明邊後再回傳。
    """
    tile_ref = item.get("tile")
    sprite_name = item.get("sprite", "")

    img = None
    if not tile_ref:
        if sprite_name == "awning":
            tile_ref = ["kenshi", 0, 3, 32, 32]
        elif sprite_name == "lantern":
            tile_ref = ["kenshi", 1, 3, 32, 32]
        elif sprite_name == "chimney":
            tile_ref = ["kenshi", 2, 3, 32, 32]
        elif sprite_name in presentation.get("tiles", {}):
            tile_ref = presentation["tiles"][sprite_name]

    if tile_ref:
        img = tm.get_sprite(tile_ref)
    elif sprite_name:
        prop_img = pm.get_prop_sprite(sprite_name)
        if prop_img is not None:
            img = prop_img
        else:
            fallbacks = {
                "sign_beer": ("酒", (180, 120, 40, 255), (255, 240, 180, 255)),
                "sign_hammer": ("鐵", (100, 105, 115, 255), (240, 240, 250, 255)),
                "sign_potion": ("藥", (60, 130, 90, 255), (200, 255, 220, 255)),
                "sacks": ("糧", (150, 120, 80, 255), (250, 235, 200, 255)),
                "sack": ("糧", (150, 120, 80, 255), (250, 235, 200, 255))
            }
            if sprite_name in fallbacks:
                lbl, bg, fg = fallbacks[sprite_name]
                img = create_fallback_sign(lbl, bg, fg)

    if img is not None:
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        return img

    return None

# ---------------------------------------------------------------------------
# R25 樓梯＝一格三階繪製 (Stair Cell Rendering: Riser 8 px + 踏面 32/3 深)
# ---------------------------------------------------------------------------
def draw_stair_cell(canvas, sc, sr, hh, ox_b, oy_b, cam_x, tm, style_info, presentation, cut=None):
    """
    R25: 每格梯級從南到北分三階：
    riser 8 px（牆 tile 上緣 32×8）＋踏面 32/3 深（step tile 切三段），
    第 k 階高 hh−1+(k+1)/3，南緣 row r+1−k/3。
    依 y-sort 自北向南 (k = 2, 1, 0) 依次繪製踏面與南緣立面。
    """
    stair_tile_ref = presentation["tiles"].get("step") or style_info.get("floor") or presentation["tiles"]["wood_floor"]
    stair_tile = tm.get_top_tile(stair_tile_ref)
    wall_ref = style_info.get("wall", ["kenshi", 1, 1])
    wall_tile = tm.get_top_tile(wall_ref)
    riser_src = wall_tile.crop((0, 0, CELL, 8))

    cx = (ox_b + sc) * CELL
    step_slice_ranges = [
        (21, 32),  # k = 0 (南階)
        (11, 21),  # k = 1 (中階)
        (0, 11)    # k = 2 (北階)
    ]

    for k in (2, 1, 0):
        h_k = hh - 1.0 + (k + 1) / 3.0
        h_prev = hh - 1.0 + k / 3.0

        if cut is not None and h_prev >= cut:
            continue

        h_k_draw = min(cut, h_k) if cut is not None else h_k
        h_prev_draw = min(cut, h_prev) if cut is not None else h_prev

        r_south = sr + 1.0 - k / 3.0
        r_north = r_south - 1.0 / 3.0

        cy_south = (oy_b + r_south) * CELL
        cy_north = (oy_b + r_north) * CELL

        # 1. 踏面 (水平頂面)
        y0_s, y1_s = step_slice_ranges[k]
        step_slice = stair_tile.crop((0, y0_s, CELL, y1_s))
        p0 = PV(cx, cy_north, h_k_draw, cam_x)
        p1 = PV(cx + CELL, cy_north, h_k_draw, cam_x)
        paste_parallelogram(canvas, step_slice, p0, (p1[0] - p0[0], p1[1] - p0[1]), (0, cy_south - cy_north))

        # 2. 南緣立面 (riser 8 px)
        if h_k_draw > h_prev_draw:
            rp0 = PV(cx, cy_south, h_k_draw, cam_x)
            rp1 = PV(cx + CELL, cy_south, h_k_draw, cam_x)
            rp2 = PV(cx, cy_south, h_prev_draw, cam_x)
            paste_parallelogram(canvas, riser_src, rp0, (rp1[0] - rp0[0], rp1[1] - rp0[1]), (rp2[0] - rp0[0], rp2[1] - rp0[1]))

# ---------------------------------------------------------------------------
# 樓梯開口/豎井與踏面繪製 (Stair Opening Shaft & Steps Rendering)
# ---------------------------------------------------------------------------
def draw_stair_opening(canvas, opening_cells, floor_level_h, lower_floor_h, flight_by_cell,
                       ox_b, oy_b, cam_x, tm, style_info, presentation, cut=None):
    """
    繪製樓板/DECK 梯洞開口 (opening)：
    每個 opening 格要畫：
    1. 豎井內牆（從樓板高度落到該格梯級頂）
    2. 該格梯級三階；若該格沒有梯級則畫下一層地板。
    """
    if not opening_cells:
        return

    opening_set = set(tuple(p) for p in opening_cells)
    wall_ref = style_info.get("wall", ["kenshi", 1, 1])
    wall_src = tm.get_face_src(wall_ref)
    floor_tile_ref = style_info.get("floor") or presentation["tiles"]["wood_floor"]
    floor_img = tm.get_top_tile(floor_tile_ref)

    # 依 y-sort (北到南，即 row 遞增) 排序
    sorted_cells = sorted(opening_set, key=lambda pt: (pt[1], pt[0]))

    for vc, vr in sorted_cells:
        wx = (ox_b + vc) * CELL
        wy = (oy_b + vr) * CELL

        has_step = (vc, vr) in flight_by_cell
        if has_step:
            step_top_h = flight_by_cell[(vc, vr)]
            target_bot_h = int(round(step_top_h))
        else:
            step_top_h = None
            target_bot_h = int(round(lower_floor_h))

        h_wall_top = int(round(floor_level_h))
        if cut is not None and h_wall_top > cut:
            h_wall_top = int(cut)

        # 1. 豎井內牆 (從樓板高度落到該格梯級頂)
        # 北側內壁 (面向南，永遠可見)
        if (vc, vr - 1) not in opening_set and h_wall_top > target_bot_h:
            for k in range(h_wall_top, target_bot_h, -1):
                p0 = PV(wx, wy, k, cam_x)
                p1 = PV(wx + CELL, wy, k, cam_x)
                p2 = PV(wx, wy, k - 1, cam_x)
                paste_parallelogram(canvas, wall_src, p0, (p1[0] - p0[0], p1[1] - p0[1]), (p2[0] - p0[0], p2[1] - p0[1]))

        # 西側內壁 (面向東，side > 0.03 時可見)
        if (vc - 1, vr) not in opening_set and face_visible("right", wx, cam_x) and h_wall_top > target_bot_h:
            for k in range(h_wall_top, target_bot_h, -1):
                p0 = PV(wx, wy, k, cam_x)
                p1 = PV(wx, wy, k - 1, cam_x)
                v_vec = (p1[0] - p0[0], p1[1] - p0[1])
                v_len = math.hypot(*v_vec)
                if v_len >= 0.5:
                    side_img = tm.get_side_source(wall_src, 1, v_len, 0.15)
                    paste_parallelogram(canvas, side_img, p0, (0, CELL), v_vec)

        # 東側內壁 (面向西，side < -0.03 時可見)
        if (vc + 1, vr) not in opening_set and face_visible("left", wx + CELL, cam_x) and h_wall_top > target_bot_h:
            for k in range(h_wall_top, target_bot_h, -1):
                p0 = PV(wx + CELL, wy, k, cam_x)
                p1 = PV(wx + CELL, wy, k - 1, cam_x)
                v_vec = (p1[0] - p0[0], p1[1] - p0[1])
                v_len = math.hypot(*v_vec)
                if v_len >= 0.5:
                    side_img = tm.get_side_source(wall_src, 1, v_len, 0.15)
                    paste_parallelogram(canvas, side_img, p0, (0, CELL), v_vec)

        # 2. 該格梯級三階 或 沒有梯級的洞格畫下一層地板
        if has_step:
            draw_stair_cell(canvas, vc, vr, step_top_h, ox_b, oy_b, cam_x, tm, style_info, presentation, cut=cut)
        else:
            if cut is None or lower_floor_h <= cut:
                p0 = PV(wx, wy, lower_floor_h, cam_x)
                p1 = PV(wx + CELL, wy, lower_floor_h, cam_x)
                paste_parallelogram(canvas, floor_img, p0, (p1[0] - p0[0], 0), (0, CELL))

# ---------------------------------------------------------------------------
# 建築繪製流程 (含 Facade 門面招牌保證繪製、R25 樓梯三階、DECK 梯洞垂直透視)
# ---------------------------------------------------------------------------
def draw_building(canvas, b, cam_x, tm, pm, context, cut=None, actor_sprites=None):
    base = b.get("base_elevation", 0)
    H = int(b.get("height_units", 3))
    top_h = base + H
    floors = b.get("floors", 1)
    units_per_floor = b.get("units_per_floor", 3.0)

    is_cut = (cut is not None and cut < top_h)
    disp = (cut - base) if is_cut else float(H)
    if disp <= 0:
        return

    ox_b, oy_b = b["footprint"]["origin"]
    cols, rows = b["footprint"]["cols"], b["footprint"]["rows"]
    style_name = b.get("style", "stone")
    style_info = context["presentation"]["styles"].get(style_name, {})
    presentation = context["presentation"]

    wall_cells = set()
    for r in range(rows):
        for c in range(cols):
            if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                wall_cells.add((c, r))

    doors_local_set = set(tuple(p) for p in b.get("doors_local", []))
    door_h_units = b.get("door_height_units", 2.0)
    windows_dict = b.get("windows_local", {})
    stair = b.get("stair")
    roof_info = b.get("roof", {})
    roof_kind = roof_info.get("kind", "ROOF_CAP")
    roof_walkable = roof_info.get("walkable", False)

    opening_cells = []
    if stair:
        opening_cells = (
            stair.get("opening")
            or stair.get("opening_local")
            or stair.get("void_cells_local")
            or stair.get("void_cells")
            or []
        )
    elif b.get("opening"):
        opening_cells = b.get("opening")
    elif b.get("void_cells_local"):
        opening_cells = b.get("void_cells_local")

    flight_by_cell = {}
    if stair:
        flight = stair.get("flight_local") or stair.get("flight") or []
        for step in flight:
            flight_by_cell[(step["col"], step["row"])] = base + step.get("step_offset", 0)

    if not opening_cells and flight_by_cell:
        opening_cells = list(flight_by_cell.keys())

    opening_cells = [tuple(p) for p in opening_cells]
    void_cells = set(opening_cells)

    # 1. 室內樓板
    visible_floor = 0
    while (visible_floor + 1) * units_per_floor <= disp and (visible_floor + 1) < floors:
        visible_floor += 1

    floor_h = base + int(visible_floor * units_per_floor)
    floor_tile_ref = style_info.get("floor") or presentation["tiles"]["wood_floor"]
    floor_img = tm.get_top_tile(floor_tile_ref)

    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if visible_floor > 0 and (c, r) in void_cells:
                continue
            cx = (ox_b + c) * CELL
            cy = (oy_b + r) * CELL
            p0 = PV(cx, cy, floor_h, cam_x)
            p1 = PV(cx + CELL, cy, floor_h, cam_x)
            paste_parallelogram(canvas, floor_img, p0, (p1[0] - p0[0], 0), (0, CELL))

    # 樓板梯洞 (cut 模式下 2F+ 梯洞垂直透視)
    if void_cells and visible_floor > 0:
        lower_floor_h = base + int((visible_floor - 1) * units_per_floor)
        draw_stair_opening(canvas, opening_cells, floor_h, lower_floor_h, flight_by_cell,
                           ox_b, oy_b, cam_x, tm, style_info, presentation, cut=cut)

    # 室內樓梯級 (cut 模式下 1F 可見)
    if stair and visible_floor == 0 and disp >= 1.0:
        flight = stair.get("flight_local", [])
        for step in flight:
            sc, sr, s_off = step["col"], step["row"], step["step_offset"]
            step_hh = base + s_off
            draw_stair_cell(canvas, sc, sr, step_hh, ox_b, oy_b, cam_x, tm, style_info, presentation, cut=cut)

    # 1.5 牆環內側面
    if is_cut and disp > visible_floor * units_per_floor:
        h_in_top = int(base + disp)
        h_in_bot = int(base + visible_floor * units_per_floor)

        # 北牆內側面 (面向南，永遠可見)
        wy_inner = (oy_b + 1) * CELL
        for c in range(1, cols - 1):
            wx = (ox_b + c) * CELL
            for k in range(h_in_top, h_in_bot, -1):
                p0 = PV(wx, wy_inner, k, cam_x)
                p1 = PV(wx + CELL, wy_inner, k, cam_x)
                p2 = PV(wx, wy_inner, k - 1, cam_x)
                ref = style_info.get("wall", ["kenshi", 1, 1])
                src = tm.get_face_src(ref)
                paste_parallelogram(canvas, src, p0, (p1[0] - p0[0], p1[1] - p0[1]), (p2[0] - p0[0], p2[1] - p0[1]))

        # 西牆內側面 (面向東)
        xe_inner_w = (ox_b + 1) * CELL
        if face_visible("right", xe_inner_w, cam_x):
            ref = style_info.get("wall", ["kenshi", 1, 1])
            src = tm.get_face_src(ref)
            n_inner_rows = rows - 2
            v_vec = (PV(xe_inner_w, oy_b * CELL, h_in_bot, cam_x)[0] - PV(xe_inner_w, oy_b * CELL, h_in_top, cam_x)[0],
                     PV(xe_inner_w, oy_b * CELL, h_in_bot, cam_x)[1] - PV(xe_inner_w, oy_b * CELL, h_in_top, cam_x)[1])
            v_len = math.hypot(*v_vec)
            if v_len >= 0.5:
                side_img = tm.get_side_source(src, n_inner_rows, v_len, 0.15)
                p0 = PV(xe_inner_w, (oy_b + 1) * CELL, h_in_top, cam_x)
                paste_parallelogram(canvas, side_img, p0, (0, n_inner_rows * CELL), v_vec)

        # 東牆內側面 (面向西)
        xe_inner_e = (ox_b + cols - 1) * CELL
        if face_visible("left", xe_inner_e, cam_x):
            ref = style_info.get("wall", ["kenshi", 1, 1])
            src = tm.get_face_src(ref)
            n_inner_rows = rows - 2
            v_vec = (PV(xe_inner_e, oy_b * CELL, h_in_bot, cam_x)[0] - PV(xe_inner_e, oy_b * CELL, h_in_top, cam_x)[0],
                     PV(xe_inner_e, oy_b * CELL, h_in_bot, cam_x)[1] - PV(xe_inner_e, oy_b * CELL, h_in_top, cam_x)[1])
            v_len = math.hypot(*v_vec)
            if v_len >= 0.5:
                side_img = tm.get_side_source(src, n_inner_rows, v_len, 0.15)
                p0 = PV(xe_inner_e, (oy_b + 1) * CELL, h_in_top, cam_x)
                paste_parallelogram(canvas, side_img, p0, (0, n_inner_rows * CELL), v_vec)

    # 1.8 cut H1 專項修復：門楣兩側角 56 px 垂直側面閉合
    if is_cut and disp <= door_h_units and doors_local_set:
        door_cols = [dc for dc, dr in doors_local_set if dr == rows - 1]
        if door_cols:
            min_dc = min(door_cols)
            max_dc = max(door_cols)
            h_jamb_top = int(base + disp)
            h_jamb_bot = base
            wall_ref = style_info.get("wall", ["kenshi", 1, 1])
            wall_face_src = tm.get_face_src(wall_ref)

            # 門洞西側內壁
            xe_jamb_w = (ox_b + min_dc) * CELL
            if face_visible("right", xe_jamb_w, cam_x):
                p0 = PV(xe_jamb_w, (oy_b + rows - 1) * CELL, h_jamb_top, cam_x)
                p1 = PV(xe_jamb_w, (oy_b + rows - 1) * CELL, h_jamb_bot, cam_x)
                v_vec = (p1[0] - p0[0], p1[1] - p0[1])
                v_len = math.hypot(*v_vec)
                if v_len >= 0.5:
                    side_img = tm.get_side_source(wall_face_src, 1, v_len, 0.12)
                    paste_parallelogram(canvas, side_img, p0, (0, CELL), v_vec)

            # 門洞東側內壁
            xe_jamb_e = (ox_b + max_dc + 1) * CELL
            if face_visible("left", xe_jamb_e, cam_x):
                p0 = PV(xe_jamb_e, (oy_b + rows - 1) * CELL, h_jamb_top, cam_x)
                p1 = PV(xe_jamb_e, (oy_b + rows - 1) * CELL, h_jamb_bot, cam_x)
                v_vec = (p1[0] - p0[0], p1[1] - p0[1])
                v_len = math.hypot(*v_vec)
                if v_len >= 0.5:
                    side_img = tm.get_side_source(wall_face_src, 1, v_len, 0.12)
                    paste_parallelogram(canvas, side_img, p0, (0, CELL), v_vec)

    # 2. 外牆立面帶與外側面
    wall_ref = style_info.get("wall", ["kenshi", 1, 1])
    door_tile_ref = style_info.get("door") or presentation["tiles"].get("door_2u")
    door_src = tm.get_sprite(door_tile_ref) if door_tile_ref else None
    win_tile_ref = style_info.get("window") or presentation["tiles"].get("window")
    window_src = tm.get_sprite(win_tile_ref) if win_tile_ref else None

    yb_south = (oy_b + rows) * CELL
    for f_idx in range(floors):
        f_bot_h = base + int(f_idx * units_per_floor)
        f_top_h = base + int((f_idx + 1) * units_per_floor)
        if is_cut and f_bot_h >= cut:
            break

        draw_top_h = min(cut, f_top_h) if is_cut else f_top_h
        band_img = tm.get_wall_band(style_name, style_info, f_idx)

        for c in range(cols):
            x = (ox_b + c) * CELL
            is_door = (f_idx == 0 and (c, rows - 1) in doors_local_set)
            is_win = (c in windows_dict.get(str(f_idx), []))

            if is_door and is_cut and cut <= f_bot_h + door_h_units:
                continue

            p0 = PV(x, yb_south, draw_top_h, cam_x)
            p1 = PV(x + CELL, yb_south, draw_top_h, cam_x)
            p2 = PV(x, yb_south, f_bot_h, cam_x)
            u_vec = (p1[0] - p0[0], p1[1] - p0[1])
            v_vec = (p2[0] - p0[0], p2[1] - p0[1])

            band_h_actual = int(round((draw_top_h - f_bot_h) * RISE))
            if band_h_actual < band_img.height:
                band_slice = band_img.crop((0, band_img.height - band_h_actual, CELL, band_img.height))
            else:
                band_slice = band_img

            paste_parallelogram(canvas, band_slice, p0, u_vec, v_vec)

            if is_door and door_src:
                if not is_cut or cut >= f_bot_h + door_h_units:
                    dp0 = PV(x, yb_south, f_bot_h + door_h_units, cam_x)
                    dp1 = PV(x + CELL, yb_south, f_bot_h + door_h_units, cam_x)
                    dp2 = PV(x, yb_south, f_bot_h, cam_x)
                    paste_parallelogram(canvas, door_src, dp0, (dp1[0] - dp0[0], dp1[1] - dp0[1]), (dp2[0] - dp0[0], dp2[1] - dp0[1]))

            if is_win and window_src:
                win_bot = f_bot_h + 1.0
                win_top = f_bot_h + 2.0
                if not is_cut or cut >= win_top:
                    wp0 = PV(x, yb_south, win_top, cam_x)
                    wp1 = PV(x + CELL, yb_south, win_top, cam_x)
                    wp2 = PV(x, yb_south, win_bot, cam_x)
                    paste_parallelogram(canvas, window_src, wp0, (wp1[0] - wp0[0], wp1[1] - wp0[1]), (wp2[0] - wp0[0], wp2[1] - wp0[1]))

    # 西外側面 run
    xe_west = ox_b * CELL
    if face_visible("left", xe_west, cam_x):
        h_side_top = int(base + disp)
        h_side_bot = base
        src = tm.get_face_src(wall_ref)
        for k in range(h_side_top, h_side_bot, -1):
            p0 = PV(xe_west, oy_b * CELL, k, cam_x)
            p1 = PV(xe_west, oy_b * CELL, k - 1, cam_x)
            v_vec = (p1[0] - p0[0], p1[1] - p0[1])
            v_len = math.hypot(*v_vec)
            if v_len >= 0.5:
                side_img = tm.get_side_source(src, rows, v_len, 0.10)
                paste_parallelogram(canvas, side_img, p0, (0, rows * CELL), v_vec)

    # 東外側面 run
    xe_east = (ox_b + cols) * CELL
    if face_visible("right", xe_east, cam_x):
        h_side_top = int(base + disp)
        h_side_bot = base
        src = tm.get_face_src(wall_ref)
        for k in range(h_side_top, h_side_bot, -1):
            p0 = PV(xe_east, oy_b * CELL, k, cam_x)
            p1 = PV(xe_east, oy_b * CELL, k - 1, cam_x)
            v_vec = (p1[0] - p0[0], p1[1] - p0[1])
            v_len = math.hypot(*v_vec)
            if v_len >= 0.5:
                side_img = tm.get_side_source(src, rows, v_len, 0.10)
                paste_parallelogram(canvas, side_img, p0, (0, rows * CELL), v_vec)

    # 2.5 Facade 立面掛件 (確認門面元件皆繪製，先 bbox 裁透明邊並裁在牆帶內)
    for f_item in b.get("facade", []):
        fc = f_item.get("col", 0)
        fh = float(f_item.get("h", 2.0))

        f_img = get_facade_image(f_item, tm, pm, presentation)
        if f_img is None:
            continue

        # 元件底與頂高度 (h 為元件底高程，高為 f_img.height / RISE)
        f_bot_h = base + fh
        item_h_units = f_img.height / RISE
        f_top_h = f_bot_h + item_h_units

        # 牆帶有效高程範圍：[base, wall_visible_top]
        wall_visible_top = min(cut, base + H) if is_cut else (base + H)
        wall_visible_bot = base

        # 完全在可見牆帶之外則不畫
        if f_bot_h >= wall_visible_top or f_top_h <= wall_visible_bot:
            continue

        # 裁在牆帶內 (截斷至可見牆帶)
        eff_top_h = min(f_top_h, wall_visible_top)
        eff_bot_h = max(f_bot_h, wall_visible_bot)

        # 依截斷範圍垂直裁切素材
        orig_h = f_img.height
        span = f_top_h - f_bot_h
        if span > 1e-4:
            crop_top = int(round((f_top_h - eff_top_h) / span * orig_h))
            crop_bot = int(round((eff_bot_h - f_bot_h) / span * orig_h))
            y0 = max(0, crop_top)
            y1 = min(orig_h, orig_h - crop_bot)
            if y1 <= y0:
                continue
            f_slice = f_img.crop((0, y0, f_img.width, y1))
        else:
            f_slice = f_img

        # 水平置中於該 col 格點
        x_center = (ox_b + fc + 0.5) * CELL
        x_left = x_center - f_slice.width / 2.0
        x_right = x_center + f_slice.width / 2.0

        fp0 = PV(x_left, yb_south, eff_top_h, cam_x)
        fp1 = PV(x_right, yb_south, eff_top_h, cam_x)
        fp2 = PV(x_left, yb_south, eff_bot_h, cam_x)
        u_vec = (fp1[0] - fp0[0], fp1[1] - fp0[1])
        v_vec = (fp2[0] - fp0[0], fp2[1] - fp0[1])
        paste_parallelogram(canvas, f_slice, fp0, u_vec, v_vec)

    # 3. 牆頂 cap
    cap_ref = style_info.get("cap") or presentation["tiles"]["cap"]
    cap_img = tm.get_top_tile(cap_ref)
    cap_h = base + disp
    for c, r in wall_cells:
        if is_cut and (c, r) in doors_local_set and disp <= door_h_units:
            cx = (ox_b + c) * CELL
            cy = (oy_b + r) * CELL
            p0 = PV(cx, cy, floor_h, cam_x)
            p1 = PV(cx + CELL, cy, floor_h, cam_x)
            paste_parallelogram(canvas, floor_img, p0, (p1[0] - p0[0], 0), (0, CELL))
            continue
        cx = (ox_b + c) * CELL
        cy = (oy_b + r) * CELL
        p0 = PV(cx, cy, cap_h, cam_x)
        p1 = PV(cx + CELL, cy, cap_h, cam_x)
        paste_parallelogram(canvas, cap_img, p0, (p1[0] - p0[0], 0), (0, CELL))

    # 4. 屋頂
    if not is_cut:
        if roof_kind == "ROOF_CAP" and not roof_walkable:
            roof_ref = style_info["roof"]["all"]
            roof_img = tm.get_top_tile(roof_ref)
            for r in range(rows):
                for c in range(cols):
                    paste_top(canvas, roof_img, (ox_b + c) * CELL, (oy_b + r) * CELL, top_h, cam_x)

            if "eave" in style_info:
                eave_col = tuple(style_info["eave"]) + (255,)
                d = ImageDraw.Draw(canvas)
                p_sw = PV(ox_b * CELL, (oy_b + rows) * CELL, top_h, cam_x)
                p_se = PV((ox_b + cols) * CELL, (oy_b + rows) * CELL, top_h, cam_x)
                d.line([(OX + p_sw[0], OY + p_sw[1]), (OX + p_se[0], OY + p_se[1])], fill=eave_col, width=2)
                p_nw = PV(ox_b * CELL, oy_b * CELL, top_h, cam_x)
                p_ne = PV((ox_b + cols) * CELL, oy_b * CELL, top_h, cam_x)
                d.line([(OX + p_nw[0], OY + p_nw[1]), (OX + p_ne[0], OY + p_ne[1])], fill=eave_col, width=1)
        else:
            # DECK 梯洞垂直透視 (畫序 豎井側面與踏面 → 屋頂，洞內不填沙、不貼屋頂 tile、不填底色)
            if void_cells:
                draw_stair_opening(canvas, opening_cells, top_h, base, flight_by_cell,
                                   ox_b, oy_b, cam_x, tm, style_info, presentation, cut=cut)

            # 3. DECK 可站屋頂 (洞格 void_cells 不貼屋頂)
            deck_ref = style_info.get("deck") or presentation["tiles"]["deck"]
            deck_img = tm.get_top_tile(deck_ref)
            for r in range(rows):
                for c in range(cols):
                    if (c, r) in void_cells:
                        continue
                    paste_top(canvas, deck_img, (ox_b + c) * CELL, (oy_b + r) * CELL, top_h, cam_x)

            # 站在屋頂上的演員
            if cut is None or cut >= 3:
                b_id = b.get("building_id")
                actors = context.get("actors_fixture", [])
                sprites = actor_sprites or context.get("actor_sprites", {})
                for a in actors:
                    if a.get("on_building") == b_id:
                        cells_list = a.get("cells", [])
                        if not cells_list and "cell" in a:
                            cells_list = [a["cell"]]
                        for c_info in cells_list:
                            ac, ar = c_info[0], c_info[1]
                            ae = c_info[2] if len(c_info) > 2 else top_h
                            draw_actor(canvas, a, ac, ar, ae, cam_x, sprites, cut=None)

# ---------------------------------------------------------------------------
# 道具與演員繪製流程 (R38 手繪 3/4 視角 Sprite 貼法 & Actors)
# ---------------------------------------------------------------------------
def draw_prop(canvas, p, cam_x, pm, context, parent=None, cut=None):
    """
    R38 改回手繪 3/4 視角 sprite (billboard 貼法)：
    貼法回到「底邊貼腳印南緣、水平置中」。
    錨點設於 PV(center_x, south_y, elev)，底邊對齊南緣，水平置中於腳印寬度。
    剖面規則：基準 elevation > cut 不畫。
    """
    c, r = p.get("cell", parent.get("cell") if parent else [0, 0])
    elev = p.get("elevation", parent.get("elevation", 0) if parent else 0)

    if cut is not None and elev > cut:
        return

    sprite_name = p.get("sprite", p.get("id"))
    sprite_img = pm.get_prop_sprite(sprite_name)
    if sprite_img is None:
        return

    fp = p.get("footprint", [1, 1])
    w, d = fp[0], fp[1]

    center_x = (c + w / 2.0) * CELL
    south_y = (r + d) * CELL
    pv_x, pv_y = PV(center_x, south_y, elev, cam_x)

    sw, sh = sprite_img.size
    dst_x = int(round(OX + pv_x - sw / 2.0))
    dst_y = int(round(OY + pv_y - sh))

    canvas.alpha_composite(sprite_img, (dst_x, dst_y))

def draw_prop_and_children(canvas, p, cam_x, pm, context, child_props_by_parent, parent=None, cut=None):
    """繪製道具本體；若有 on 綁定於此道具的子道具，在父道具畫完立刻畫。"""
    draw_prop(canvas, p, cam_x, pm, context, parent=parent, cut=cut)
    p_id = p.get("id")
    if p_id in child_props_by_parent:
        for child in child_props_by_parent[p_id]:
            draw_prop_and_children(canvas, child, cam_x, pm, context, child_props_by_parent, parent=p, cut=cut)

def draw_actor(canvas, actor_def, col, row, elev, cam_x, actor_sprites, cut=None):
    """
    演員 fixture 繪製：
    24×30 色塊加一個字，底邊貼格南緣、水平置中於格點，錨點設於 PV(cx, (row + 1) * 32, elev)。
    剖面規則：elev >= cut 不畫。
    """
    if cut is not None and elev >= cut:
        return

    actor_id = actor_def.get("id", "actor")
    sprite = actor_sprites.get(actor_id)
    if sprite is None:
        return

    cx = (col + 0.5) * CELL
    south_y = (row + 1) * CELL
    pv_x, pv_y = PV(cx, south_y, elev, cam_x)

    dst_x = int(round(OX + pv_x - ACTOR_W / 2.0))
    dst_y = int(round(OY + pv_y - ACTOR_H))

    canvas.alpha_composite(sprite, (dst_x, dst_y))

# ---------------------------------------------------------------------------
# 高程色彩與邊界常數 (Elevation Color & Edge Color Constants)
# ---------------------------------------------------------------------------
def get_elev_color(elev):
    """依高度分級提供清晰高對比色相。"""
    if elev <= -2:
        return (147, 197, 253, 255)
    elif elev == -1:
        return (56, 189, 248, 255)
    elif elev == 0:
        return (245, 245, 245, 255)
    elif elev == 1:
        return (134, 239, 172, 255)
    elif elev == 2:
        return (253, 224, 71, 255)
    elif elev == 3:
        return (251, 146, 60, 255)
    elif elev == 6:
        return (236, 72, 153, 255)
    else:
        return (248, 113, 113, 255)

EDGE_COLORS = {
    "WALK": None,
    "WALK_SLOPE": (250, 204, 21, 255),
    "CLIFF": (239, 68, 68, 255),
    "WATER": (59, 130, 246, 255),
    "DITCH": (45, 212, 191, 255),
    "WALL": (255, 255, 255, 255),
    "DOOR": (34, 197, 94, 255),
    "PIT_RIM": (249, 115, 22, 255),
    "PIT_WALL": (249, 115, 22, 255),
}

def compute_surfaces(elevation_rows, building_footprint_cells, water_cells=None, water_bodies=None):
    """R42 / Round 10: surfaces 涵蓋所有非建築格 (含水面與泥灘)。水格 surface elevation 為該水體 level (最高河床 + 1, 通常 0)。"""
    water_cells = water_cells or set()
    water_level_map = {}
    if water_bodies:
        for wb in water_bodies:
            lvl = wb.get("level", 0)
            for pt in wb.get("cells", []):
                water_level_map[(pt[0], pt[1])] = lvl

    seen, surfaces = set(), []
    for r in range(ROWS):
        for c in range(COLS):
            if (c, r) in seen or (c, r) in building_footprint_cells:
                continue
            is_w = (c, r) in water_cells
            if is_w:
                h = water_level_map.get((c, r), 0)
            else:
                h = elevation_rows[r][c]
            q, cells = deque([(c, r)]), []
            seen.add((c, r))
            while q:
                x, y = q.popleft()
                cells.append([x, y])
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc, nr = x + dx, y + dy
                    if not (0 <= nc < COLS and 0 <= nr < ROWS):
                        continue
                    if (nc, nr) in seen or (nc, nr) in building_footprint_cells:
                        continue
                    nb_is_w = (nc, nr) in water_cells
                    if nb_is_w != is_w:
                        continue
                    nb_h = water_level_map.get((nc, nr), 0) if nb_is_w else elevation_rows[nr][nc]
                    if nb_h != h:
                        continue
                    seen.add((nc, nr))
                    q.append((nc, nr))
            if is_w:
                kind = "WATER"
            elif h == 0:
                kind = "GROUND"
            elif h > 0:
                kind = "PLATEAU"
            else:
                kind = "PIT"
            surfaces.append({"surface_id": f"S{len(surfaces) + 1:02d}", "elevation": h, "kind": kind, "cells": cells})
    return surfaces

def compute_edges(elevation_rows, buildings, building_footprint_cells, water_cells, ditch_cells=None):
    edges = []
    ditch_cells = ditch_cells or set()
    wall_cells, door_cells = set(), set()
    for b in buildings:
        ox, oy = b["footprint"]["origin"]
        cols, rows = b["footprint"]["cols"], b["footprint"]["rows"]
        door_cells |= {(ox + dc, oy + dr) for dc, dr in b.get("doors_local", [])}
        b_cells = {(ox + c, oy + r) for r in range(rows) for c in range(cols)}
        wall_cells |= {cell for cell in b_cells if any((cell[0] + dx, cell[1] + dy) not in b_cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}

    for r in range(ROWS):
        for c in range(COLS):
            for dx, dy in ((1, 0), (0, 1)):
                bc, br = c + dx, r + dy
                if not (0 <= bc < COLS and 0 <= br < ROWS):
                    continue
                a, b_pt = (c, r), (bc, br)
                a_in, b_in = a in building_footprint_cells, b_pt in building_footprint_cells
                if a_in or b_in:
                    if a_in and b_in:
                        if a in wall_cells and b_pt in wall_cells:
                            continue
                        t = "WALL" if (a in wall_cells or b_pt in wall_cells) else "WALK"
                    else:
                        inner = a if a_in else b_pt
                        t = "DOOR" if (inner in door_cells and dy == 1) else "WALL"
                    edges.append({"from": [a[0], a[1]], "to": [b_pt[0], b_pt[1]], "type": t})
                    continue

                ha, hb = elevation_rows[r][c], elevation_rows[br][bc]
                diff = abs(ha - hb)
                if a in water_cells or b_pt in water_cells:
                    t = "WATER"
                elif a in ditch_cells or b_pt in ditch_cells:
                    t = "DITCH"
                elif diff == 0:
                    t = "WALK"
                elif diff == 1:
                    t = "WALK_SLOPE"
                else:
                    t = "CLIFF"
                edges.append({"from": [a[0], a[1]], "to": [b_pt[0], b_pt[1]], "type": t})
    return edges

# ---------------------------------------------------------------------------
# 單一視角渲染 (Render Frame, 統一 y-sort 整合建築、道具與演員)
# ---------------------------------------------------------------------------
def render_view(cam_x, tm, pm, actor_sprites, context, cut=None,
                grid_overlay=False, elevation_labels=False, edge_labels=False,
                only_surface_id=None):
    canvas_bg = (0, 0, 0, 0) if only_surface_id is not None else BG
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), canvas_bg)

    target_cells = None
    if only_surface_id is not None:
        surfaces = context.get("surfaces", [])
        for s in surfaces:
            if s["surface_id"] == only_surface_id:
                target_cells = set((pt[0], pt[1]) for pt in s["cells"])
                break
        if target_cells is None:
            target_cells = set()

    # 1. 建築依腳印底邊 row 分組
    buildings = context.get("buildings", []) if only_surface_id is None else []
    b_by_bottom_row = {}
    for b in buildings:
        bot_row = b["footprint"]["origin"][1] + b["footprint"]["rows"] - 1
        b_by_bottom_row.setdefault(bot_row, []).append(b)

    # 2. 道具提取與子道具分流
    props = context.get("props", []) if only_surface_id is None else []
    child_props_by_parent = {}
    root_props = []
    for p in props:
        parent_id = p.get("on")
        if parent_id:
            child_props_by_parent.setdefault(parent_id, []).append(p)
        else:
            root_props.append(p)

    props_by_bottom_row = {}
    for p in root_props:
        c, r = p.get("cell", [0, 0])
        fp = p.get("footprint", [1, 1])
        bot_row = r + fp[1] - 1
        props_by_bottom_row.setdefault(bot_row, []).append(p)

    # 3. 演員依所在 row 分組
    actors = context.get("actors_fixture", []) if only_surface_id is None else []
    actors_by_row = {}
    for a in actors:
        if a.get("on_building"):
            continue
        cells_list = a.get("cells", [])
        if not cells_list and "cell" in a:
            cells_list = [a["cell"]]
        for c_info in cells_list:
            c, r = c_info[0], c_info[1]
            elev = c_info[2] if len(c_info) > 2 else 0
            actors_by_row.setdefault(r, []).append((a, c, r, elev))

    # R7 & R24 畫序：
    cam_col = cam_x / CELL
    col_order = [c for c in range(COLS) if c + 0.5 <= cam_col] + sorted(
        [c for c in range(COLS) if c + 0.5 > cam_col], reverse=True
    )

    for r in range(ROWS):
        # 1. 該 row 的戶外地形格
        for c in col_order:
            if only_surface_id is not None and (c, r) not in target_cells:
                continue
            draw_outdoor_cell(canvas, c, r, cam_x, tm, context, cut=cut)

        # 2. 該 row 底邊的建築
        if r in b_by_bottom_row:
            for b in b_by_bottom_row[r]:
                draw_building(canvas, b, cam_x, tm, pm, context, cut=cut, actor_sprites=actor_sprites)

        # 3. 該 row 底邊的道具
        if r in props_by_bottom_row:
            for p in props_by_bottom_row[r]:
                draw_prop_and_children(canvas, p, cam_x, pm, context, child_props_by_parent, parent=None, cut=cut)

        # 4. 該 row 的演員 fixture
        if r in actors_by_row:
            for item in actors_by_row[r]:
                a_def, ac, ar, ae = item
                draw_actor(canvas, a_def, ac, ar, ae, cam_x, actor_sprites, cut=cut)

    # -----------------------------------------------------------------------
    # 交付模式疊加層 (Overlays)
    # -----------------------------------------------------------------------
    elevation_rows = context["elevation_rows"]
    building_footprint_cells = context.get("building_footprint_cells", set())
    buildings_list = context.get("buildings", [])

    # 1. Grid Overlay
    if grid_overlay:
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        d_grid = ImageDraw.Draw(overlay)
        font_grid = load_actor_font(9)

        for r in range(ROWS):
            for c in range(COLS):
                pt = (c, r)
                if pt in building_footprint_cells:
                    h = 0
                    for b in buildings_list:
                        ox, oy = b["footprint"]["origin"]
                        bw, bh = b["footprint"]["cols"], b["footprint"]["rows"]
                        if ox <= c < ox + bw and oy <= r < oy + bh:
                            h = b.get("base_elevation", 0)
                            break
                elif pt in context.get("water_cells", set()):
                    if cut is not None and cut < 0:
                        bed_h = elevation_rows[r][c]
                        h = cell_draw_height(bed_h, cut)
                    else:
                        wl = context.get("cell_water_level", {}).get(pt, -0.15)
                        h = cell_draw_height(wl, cut)
                else:
                    h = cell_draw_height(elevation_rows[r][c], cut)

                p0 = PV(c * CELL, r * CELL, h, cam_x)
                p1 = PV((c + 1) * CELL, r * CELL, h, cam_x)
                p2 = PV((c + 1) * CELL, (r + 1) * CELL, h, cam_x)
                p3 = PV(c * CELL, (r + 1) * CELL, h, cam_x)

                poly = [
                    (OX + p0[0], OY + p0[1]),
                    (OX + p1[0], OY + p1[1]),
                    (OX + p2[0], OY + p2[1]),
                    (OX + p3[0], OY + p3[1])
                ]
                d_grid.polygon(poly, outline=(255, 255, 255, 75))
                if font_grid:
                    try:
                        d_grid.text((OX + p0[0] + 2, OY + p0[1] + 1), f"{c},{r}", fill=(255, 255, 255, 180), font=font_grid)
                    except Exception:
                        pass

        canvas.alpha_composite(overlay)

    # 2. Elevation Labels
    if elevation_labels:
        d_elev = ImageDraw.Draw(canvas)
        font_elev = load_actor_font(10)

        for r in range(ROWS):
            for c in range(COLS):
                pt = (c, r)
                if pt in building_footprint_cells:
                    elev = 0
                    for b in buildings_list:
                        ox, oy = b["footprint"]["origin"]
                        bw, bh = b["footprint"]["cols"], b["footprint"]["rows"]
                        if ox <= c < ox + bw and oy <= r < oy + bh:
                            elev = b.get("base_elevation", 0) + int(b.get("height_units", 3))
                            break
                    draw_h = cell_draw_height(elev, cut)
                elif pt in context.get("water_cells", set()):
                    elev = elevation_rows[r][c]  # 數值顯示河床高程
                    if cut is not None and cut < 0:
                        draw_h = cell_draw_height(elev, cut)
                    else:
                        wl = context.get("cell_water_level", {}).get(pt, -0.15)
                        draw_h = cell_draw_height(wl, cut)
                else:
                    elev = elevation_rows[r][c]
                    draw_h = cell_draw_height(elev, cut)

                cx = (c + 0.5) * CELL
                cy = (r + 0.5) * CELL
                pv_x, pv_y = PV(cx, cy, draw_h, cam_x)

                col = get_elev_color(elev)
                txt = f"{elev:>2}"
                if font_elev:
                    try:
                        d_elev.text(
                            (OX + pv_x, OY + pv_y),
                            txt,
                            fill=col,
                            font=font_elev,
                            anchor="mm",
                            stroke_width=2,
                            stroke_fill=(0, 0, 0, 220)
                        )
                    except Exception:
                        d_elev.text((OX + pv_x - 6, OY + pv_y - 5), txt, fill=col, font=font_elev)

    # 3. Edge Labels
    if edge_labels:
        d_edge = ImageDraw.Draw(canvas)
        edges = context.get("edges", [])
        water_cells = context.get("water_cells", set())
        cell_water_level = context.get("cell_water_level", {})
        for e in edges:
            etype = e.get("type")
            col = EDGE_COLORS.get(etype)
            if col is None:
                continue

            (ac, ar) = e["from"]
            (bc, br) = e["to"]

            pt_a = (ac, ar)
            pt_b = (bc, br)

            ha_raw = cell_water_level.get(pt_a, -0.15) if (pt_a in water_cells and (cut is None or cut >= 0)) else elevation_rows[ar][ac]
            hb_raw = cell_water_level.get(pt_b, -0.15) if (pt_b in water_cells and (cut is None or cut >= 0)) else elevation_rows[br][bc]

            ha = cell_draw_height(ha_raw if pt_a not in building_footprint_cells else 0, cut)
            hb = cell_draw_height(hb_raw if pt_b not in building_footprint_cells else 0, cut)
            h = max(ha, hb)

            if bc == ac + 1:
                p_start = PV(bc * CELL, ar * CELL, h, cam_x)
                p_end = PV(bc * CELL, (ar + 1) * CELL, h, cam_x)
            else:
                p_start = PV(ac * CELL, br * CELL, h, cam_x)
                p_end = PV((ac + 1) * CELL, br * CELL, h, cam_x)

            d_edge.line(
                [(OX + p_start[0], OY + p_start[1]), (OX + p_end[0], OY + p_end[1])],
                fill=col,
                width=3
            )

    return canvas

# ---------------------------------------------------------------------------
# 交付報告生成 (Build HTML Report)
# ---------------------------------------------------------------------------
def build_report(spec, presentation, props_coords, tileset_path, props_png_path, out_dir):
    """產出 reports/v2_report.html"""
    plm_spec = dict(spec)
    plm_spec.update(presentation)

    with open(tileset_path, "rb") as f:
        tileset_b64 = base64.b64encode(f.read()).decode("ascii")
    plm_atlases = {
        "kenshi": f"data:image/png;base64,{tileset_b64}"
    }

    props_atlas_img = Image.open(props_png_path).convert("RGBA")
    pm = PropsManager(props_atlas_img, props_coords)
    atlas_img = Image.open(tileset_path).convert("RGBA")
    tm = TileManager(atlas_img, presentation.get("face_crop_y0", {}))

    plm_props = {}
    for p in spec.get("props", []):
        p_id = p.get("id")
        if not p_id:
            continue
        sprite_name = p.get("sprite", p_id)
        if sprite_name in props_coords:
            x, y, w, h = props_coords[sprite_name]
            sprite_img = props_atlas_img.crop((x, y, x + w, y + h))
            buf = io.BytesIO()
            sprite_img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            plm_props[p_id] = f"data:image/png;base64,{b64}"

    # facade 招牌保證全部注入 PLM_PROPS (先 bbox 裁切透明邊，sign_beer, sign_hammer, sign_potion 等)
    for b in spec.get("buildings", []):
        b_id = b.get("building_id", "")
        for idx, f_item in enumerate(b.get("facade", [])):
            img_id = f_item.get("img_id", f"{b_id}_facade_{idx}")
            f_img = get_facade_image(f_item, tm, pm, presentation)
            if f_img is not None:
                buf = io.BytesIO()
                f_img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                plm_props[img_id] = f"data:image/png;base64,{b64}"

    static_images = [
        {"title": "全場景俯視透視 (v2_all.png, cam_x = 640)", "src": "v2_all.png"},
        {"title": "鏡頭左偏透視 (v2_cam_left.png, cam_x = 0)", "src": "v2_cam_left.png"},
        {"title": "鏡頭右偏透視 (v2_cam_right.png, cam_x = 1280)", "src": "v2_cam_right.png"},
        {"title": "建築特寫 (v2_buildings_crop.png, 酒館 2x)", "src": "v2_buildings_crop.png"},
        {"title": "道具與演員特寫 (v2_props_crop.png, 廣場 2x)", "src": "v2_props_crop.png"},
        {"title": "順序四 a - 02 網格與座標標註 (v2_02_grid_overlay.png)", "src": "v2_02_grid_overlay.png"},
        {"title": "順序四 a - 03 頂面高程數字標註 (v2_03_elevation_labels.png)", "src": "v2_03_elevation_labels.png"},
        {"title": "順序四 a - 04 邊界與特徵線標註 (v2_04_edge_labels.png)", "src": "v2_04_edge_labels.png"},
    ]

    diff_points = [
        "Round 10 水面高度定稿：水面＝H0（減 0.15），即水面畫在 0 - 0.15 = -0.15 級。水方塊佔 [-1, 0]，河床在 -1（深處 -2）。水格 surface elevation ＝ 最高河床 + 1（通常 0）。",
        "剖面定稿（每層只顯示頂面高度 <= cut 的東西）：cut >= 0 看得到水（v2_cut_H0.png 有水）；cut = -1 水被切掉，看到河床（v2_cut_Hneg1.png：-1 的床畫泥地、-2 的床畫在 -2 並畫出 -1→-2 的水下岸壁，不畫水面）；cut = -2 只剩 -2 的床，其餘 -1 的河床被截斷為 -2 的切面（v2_cut_Hneg2.png 沒水）。",
        "門面 facade 元件先 bbox 裁切透明邊，並裁在牆帶內：西南酒館 (sign_beer 啤酒招牌)、東北鐵匠鋪 (sign_hammer 鐵匠招牌)、西北雜貨鋪 (sign_potion 藥水招牌)，田舍 sack 移至 props 地面，全景 v2_all.png 與互動報告 PLM_PROPS 皆精準呈現。",
        "R44 補：岸就是 H0 的地，水體旁不可有低於地面又不是水的格。5 格泥灘 (mud_cells) 高程為 0，頂面貼 pit_floor 泥地 tile（可走），漁夫站位調整至 H0。",
        "鐵匠鋪屋頂（H3）DECK 與酒館 2F 梯洞透視修復：梯洞開口 opening 每格由樓板高度落至該格梯級頂繪製豎井內牆，梯級繪製三階踏面（R25）；無梯級格繪製下一層地板，徹底消弭切面破洞；畫序：豎井內牆 → 梯級/底板 → 屋頂/樓板。",
        "水面方框線消除：半透明水面 tile (alpha 0.7) 採原尺寸不膨脹貼圖 (conservative=False)，消弭接縫重疊線。",
        "R38 手繪 3/4 視角 sprite billboard 貼法：底邊貼腳印南緣、水平置中。",
        "R45 溝 16 向 autotile：東西向田間支渠透過 4 鄰 bitmask 正確選取連通 tile。",
        "R25 樓梯一格三階：每格梯級從南到北精準劃分三階，8 px riser 加上 32/3 踏面。",
        "cut H1 門角 56 px 專項修復：四棟建築門洞兩側暴露的垂直斷面完整補齊。",
        "R41 水面擁有的面材質修正：水面擁有的面（淺床落到深床、岸落到床）一律使用土岸 tile（pit_wall / pit_wall_side），不用 face_water。"
    ]

    skeleton_path = os.path.join(out_dir, "keluo_viewer_skeleton.html")
    if not os.path.exists(skeleton_path):
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "reports", "keluo_viewer_skeleton.html"),
            "C:/GPTfile/godot/Nono's Little Base/nono_google_cloud/nono-tactical-tilemap-engine/reports/keluo_viewer_skeleton.html"
        ]
        for c_path in candidates:
            if os.path.exists(c_path):
                skeleton_path = c_path
                break
    with open(skeleton_path, "r", encoding="utf-8") as f:
        skeleton_content = f.read()

    if 'id="plm-root"' in skeleton_content or "id='plm-root'" in skeleton_content:
        plm_root_block = skeleton_content
    else:
        plm_root_block = f'  <div id="plm-root">\n{skeleton_content}\n  </div>'

    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-TW">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <title>諾諾戰術地圖渲染器 (v2 - Round 10) 交付報告</title>',
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
        '  <h1>諾諾戰術地圖渲染器 (v2) 交付報告 (Round 10 水面定稿版)</h1>',
        '  <div class="diff-box">',
        '    <h3>Round 10 水面高度定稿與剖面要點</h3>',
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

    report_path = os.path.join(out_dir, "v2_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))
    print(f"已生成互動檢視報告：{report_path}")

# ---------------------------------------------------------------------------
# 主執行管線 (Pipeline)
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

    spec_path = locate_file("reports/chunk_0_0_spec_v2.json", script_dir)
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

    actor_ids = {a.get("id") for a in actors}
    if "arya" not in actor_ids and "hero" not in actor_ids:
        actors.append({
            "id": "arya",
            "label": "主",
            "color": [56, 189, 248],
            "cells": [[18, 20, 0]]
        })
    if "guard" not in actor_ids:
        actors.append({
            "id": "guard",
            "label": "衛",
            "color": [234, 179, 8],
            "cells": [[24, 5, 3]]
        })
    if "fisherman" not in actor_ids:
        actors.append({
            "id": "fisherman",
            "label": "漁",
            "color": [34, 197, 94],
            "cells": [[30, 16, 0]]
        })

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

    surfaces = spec.get("surfaces")
    if not surfaces:
        surfaces = compute_surfaces(spec["elevation_rows"], building_footprint_cells, spec.get("water_cells"), spec.get("water_bodies"))

    ditch_cells_set = set(tuple(p) for p in spec.get("ditch_cells", []))
    water_cells_set = set(tuple(p) for p in spec.get("water_cells", []))

    edges = spec.get("edges")
    if not edges:
        edges = compute_edges(spec["elevation_rows"], buildings, building_footprint_cells, water_cells_set, ditch_cells_set)

    cell_water_level, cell_water_layer = compute_water_levels(spec["elevation_rows"], water_cells_set)

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

    cam_center = WORLD_W / 2  # 640

    # 1. 基礎視角輸出 (全景、鏡頭左移、鏡頭右移)
    tasks = [
        ("v2_all.png", cam_center),
        ("v2_cam_left.png", 0),
        ("v2_cam_right.png", WORLD_W)
    ]

    frame_center = None
    for filename, cam_x in tasks:
        print(f"正在渲染 {filename} (cam_x = {cam_x})...")
        frame = render_view(cam_x, tm, pm, actor_sprites, context, cut=None)
        out_path = os.path.join(out_dir, filename)
        frame.save(out_path)
        print(f"已輸出：{out_path}")
        if filename == "v2_all.png":
            frame_center = frame

    resample_nearest = Image.Resampling.NEAREST if hasattr(Image, "Resampling") else Image.NEAREST

    # 2. 輸出酒館與道具演員特寫裁切圖
    if frame_center is not None:
        crop_box = (
            int(OX + 6 * CELL),
            int(OY + 20 * CELL),
            int(OX + 18 * CELL),
            int(OY + 32 * CELL)
        )
        crop_img = frame_center.crop(crop_box)
        crop_scaled = crop_img.resize((crop_img.width * 2, crop_img.height * 2), resample=resample_nearest)
        crop_path = os.path.join(out_dir, "v2_buildings_crop.png")
        crop_scaled.save(crop_path)
        print(f"已輸出酒館裁切放大圖：{crop_path}")

        props_crop_box = (
            int(OX + 14 * CELL),
            int(OY - 2 * CELL),
            int(OX + 32 * CELL),
            int(OY + 24 * CELL)
        )
        props_crop_img = frame_center.crop(props_crop_box)
        props_crop_scaled = props_crop_img.resize(
            (props_crop_img.width * 2, props_crop_img.height * 2),
            resample=resample_nearest
        )
        props_crop_path = os.path.join(out_dir, "v2_props_crop.png")
        props_crop_scaled.save(props_crop_path)
        print(f"已輸出道具與演員裁切放大圖：{props_crop_path}")

    # 3. 11 張剖面圖輸出
    cut_jobs = [
        ("v2_cut_H8.png", 8),
        ("v2_cut_H7.png", 7),
        ("v2_cut_H6.png", 6),
        ("v2_cut_H5.png", 5),
        ("v2_cut_H4.png", 4),
        ("v2_cut_H3.png", 3),
        ("v2_cut_H2.png", 2),
        ("v2_cut_H1.png", 1),
        ("v2_cut_H0.png", 0),
        ("v2_cut_Hneg1.png", -1),
        ("v2_cut_Hneg2.png", -2),
    ]

    for filename, cut_val in cut_jobs:
        print(f"正在渲染剖面圖 {filename} (cut = {cut_val}, cam_x = {cam_center})...")
        cut_frame = render_view(cam_center, tm, pm, actor_sprites, context, cut=cut_val)
        cut_out_path = os.path.join(out_dir, filename)
        cut_frame.save(cut_out_path)
        print(f"已輸出剖面圖：{cut_out_path}")

    frame_center.save(os.path.join(out_dir, "v2_cut_all.png"))

    # 4. 順序四 a：四種交付圖
    print("正在渲染交付圖：v2_02_grid_overlay.png...")
    frame_grid = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, grid_overlay=True)
    frame_grid.save(os.path.join(out_dir, "v2_02_grid_overlay.png"))
    print(f"已輸出：{os.path.join(out_dir, 'v2_02_grid_overlay.png')}")

    print("正在渲染交付圖：v2_03_elevation_labels.png...")
    frame_elev = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, elevation_labels=True)
    frame_elev.save(os.path.join(out_dir, "v2_03_elevation_labels.png"))
    print(f"已輸出：{os.path.join(out_dir, 'v2_03_elevation_labels.png')}")

    print("正在渲染交付圖：v2_04_edge_labels.png...")
    frame_edge = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, edge_labels=True)
    frame_edge.save(os.path.join(out_dir, "v2_04_edge_labels.png"))
    print(f"已輸出：{os.path.join(out_dir, 'v2_04_edge_labels.png')}")

    slices_dir = os.path.join(out_dir, "v2_slices")
    os.makedirs(slices_dir, exist_ok=True)
    print(f"正在渲染交付圖切片集：v2_slices/ (共 {len(surfaces)} 個 surface)...")
    for s in surfaces:
        s_id = s["surface_id"]
        frame_slice = render_view(cam_center, tm, pm, actor_sprites, context, cut=None, only_surface_id=s_id)
        slice_path = os.path.join(slices_dir, f"{s_id}.png")
        frame_slice.save(slice_path)
    print(f"已輸出切片至：{slices_dir}")

    # 5. 輸出整合式 HTML 報告與 Viewer 規格注入
    print("正在生成交付報告 reports/v2_report.html...")
    build_report(spec, presentation, props_coords, tileset_path, props_png_path, out_dir)

if __name__ == "__main__":
    main()
