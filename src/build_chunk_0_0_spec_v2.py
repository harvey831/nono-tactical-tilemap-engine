#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_chunk_0_0_spec_v2.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: 將 40×40 高程格網與村落配置生成為符合珂洛規範的機器可讀 chunk spec v2 (Round 13 煙囪屋頂化與門面遮陽篷連排版)。
Revision Highlights:
  1. 第十輪定稿：水面＝H0（減 0.15）。水方塊佔 [-1, 0]，河床在 -1（深處 -2）。
     水格 surface elevation ＝ 最高河床 + 1（通常 0）。
     spec 的 water_bodies[].level ＝ 最高河床 + 1，water_bodies[].bed ＝ 最高河床。
     surfaces 中水格的 elevation ＝ 0 (kind: WATER)。
  2. 剖面定稿：
     cut >= 0 看得到水（有水）；
     cut = -1 水被切掉，看到河床（-1 的床畫泥地、-2 的床畫在 -2 並畫出 -1→-2 的水下岸壁）；
     cut = -2 只剩 -2 的床，其餘是 -2 的切面。
  3. 第十二輪修訂：
     - sack 從 facade 移到 props（田舍 shed_sack_2 置於 cell(22, 29)，facade 只放掛在牆上的東西）。
     - facade 元件高度強制斷言防火牆：以 bbox 裁掉透明邊後的真實高度量測，h + sprite_bbox_h/23 <= 牆高。
     - 1 層樓建築招牌 h 設為 0.5（招牌實際約 46px＝2 級，0.5 + 2.0 = 2.5 落在 3 級牆內），煙囪/燈籠 h 調至 1.0，確保整張元件落在牆帶內。
  4. R44 補：泥灘 (mud_cells) 高程為 0，漁夫站位 H0。
  5. 座標系硬性收斂：全 spec 座標嚴格為 [col, row] = [x, y]，經唯一出口 cell() 產出。
  6. 梯洞規格修訂：opening_local_on_upper_floor / void_cells_local 涵蓋整段梯級 (2格寬 × 梯級長度)。
  7. 第十三輪修訂：
     - 鐵匠鋪煙囪修正：kind 改為 roof，置於屋頂靠後牆格 cell(7, 0)。
     - 雜貨鋪遮陽篷修正：於大門正上方 4 格連排 (cols 1..4, row 4, h=2.1)，南牆窗戶移至 col 5 避免撞窗。
------------------------------------------------------------
"""

import os
import sys
import json
import re
from collections import deque
from PIL import Image

def cell(col, row):
    """
    spec 座標唯一出口：所有輸出的 2D 格點一律為 [col, row] = [x, y]。
    """
    return [int(col), int(row)]

def cell_3d(col, row, elev):
    """
    3D 座標出口：[col, row, elevation]。
    """
    return [int(col), int(row), int(elev)]

def find_elevation_md():
    """尋找 nono_chunk_0_0_elevation_v3.md 的路徑 (優先 v3，降級 v2)"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(script_dir, "..", "..", "..", "nono_chunk_0_0_elevation_v3.md")),
        "C:/GPTfile/godot/Nono's Little Base/nono_chunk_0_0_elevation_v3.md",
        os.path.join(os.getcwd(), "nono_chunk_0_0_elevation_v3.md"),
        os.path.abspath(os.path.join(script_dir, "..", "..", "..", "nono_chunk_0_0_elevation_v2.md")),
        "C:/GPTfile/godot/Nono's Little Base/nono_chunk_0_0_elevation_v2.md"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"無法找到高程格網 Markdown，候選路徑：{candidates}")

def parse_elevation_grid(md_path):
    """解析 Markdown 內的 40×40 字串矩陣並轉為整數高程矩陣 (rows[y][x])"""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.findall(r"```(?:text)?\r?\n([\s\S]*?)```", content)
    grid_lines = None
    for b in blocks:
        lines = [line.strip() for line in b.splitlines() if line.strip()]
        if len(lines) == 40 and all(len(line) == 40 for line in lines):
            grid_lines = lines
            break

    if not grid_lines:
        raise ValueError("在 Markdown 中未找到符合 40×40 規範的高程代碼塊！")

    char_map = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        'a': -1, 'b': -2
    }
    elevation_rows = []
    for line in grid_lines:
        row = [char_map[c] for c in line]
        elevation_rows.append(row)

    return elevation_rows

def build_chunk_spec():
    md_path = find_elevation_md()
    elevation_rows = parse_elevation_grid(md_path)

    # 1. 指定泥灘岸格 (mud_cells / mudflat_cells): 規則 R44 補：岸就是 H0 的地；水體旁不可有低於地面又不是水的格。
    # 將 mudflat 格高程改為 0，頂面貼 pit_floor 泥地 tile（可走），並另出 mud_cells 給 renderer。
    mudflat_cells_coords = [
        (30, 14),
        (30, 15),
        (30, 16),
        (29, 17),
        (30, 17)
    ]
    mud_cells = [cell(c, r) for c, r in mudflat_cells_coords]
    mud_cells_set = set(mudflat_cells_coords)
    mudflat_cells_set = mud_cells_set

    # 將 mudflat 格高程改為 0
    for mc, mr in mudflat_cells_coords:
        elevation_rows[mr][mc] = 0

    # 2. 水面格 (water_cells): 所有 a (-1) / b (-2) 格扣掉指定泥灘岸格，格式為 [col, row]
    water_cells = []
    water_cells_set = set()
    for r in range(40):
        for c in range(40):
            if elevation_rows[r][c] in (-1, -2):
                if (c, r) not in mudflat_cells_set:
                    water_cells.append(cell(c, r))
                    water_cells_set.add((c, r))

    # 2.2 R45 田間支渠 (ditch_cells): 高程為 H0，頂面貼 ditch tile，edge 標 DITCH
    ditch_cells_coords = []
    for r in (24, 27, 30):
        for c in range(33, 38):
            ditch_cells_coords.append((c, r))
    ditch_cells = [cell(c, r) for c, r in ditch_cells_coords]
    ditch_cells_set = set(ditch_cells_coords)

    # 2.5 計算 water_bodies (Round 10 定稿: 水格 surface elevation ＝ 最高河床 + 1，通常 0)
    visited_water = set()
    water_bodies = []
    wb_idx = 0
    for r in range(40):
        for c in range(40):
            start_pt = (c, r)
            if start_pt in water_cells_set and start_pt not in visited_water:
                body_cells = []
                queue = deque([start_pt])
                visited_water.add(start_pt)
                while queue:
                    curr_c, curr_r = queue.popleft()
                    body_cells.append(cell(curr_c, curr_r))
                    for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nc, nr = curr_c + dc, curr_r + dr
                        ncell = (nc, nr)
                        if 0 <= nc < 40 and 0 <= nr < 40:
                            if ncell in water_cells_set and ncell not in visited_water:
                                visited_water.add(ncell)
                                queue.append(ncell)

                max_bed = max(elevation_rows[pt[1]][pt[0]] for pt in body_cells)
                water_bodies.append({
                    "id": f"wb_{wb_idx}",
                    "level": int(max_bed + 1),  # surface elevation = 最高河床 + 1
                    "bed": int(max_bed),
                    "cells": body_cells
                })
                wb_idx += 1

    # --------------------------------------------------------
    # R44 / Round 10 強制斷言防火牆：每個水格恰屬一個 water_body，無遺漏且無重複
    # --------------------------------------------------------
    all_body_cells = [tuple(pt) for wb in water_bodies for pt in wb["cells"]]
    all_body_set = set(all_body_cells)

    assert len(all_body_cells) == len(all_body_set), (
        f"斷言失敗！water_bodies 存在重複格點！總計 {len(all_body_cells)} 格，去重後 {len(all_body_set)} 格。"
    )
    assert all_body_set == water_cells_set, (
        f"斷言失敗！water_bodies 格點與 water_cells 不一致！"
        f"缺失水格：{len(water_cells_set - all_body_set)}，多餘水格：{len(all_body_set - water_cells_set)}。"
    )
    assert len(all_body_cells) == len(water_cells), (
        f"斷言失敗！water_bodies 總格數 {len(all_body_cells)} 不等於 water_cells 數 {len(water_cells)}！"
    )
    for wb in water_bodies:
        expected_bed = max(elevation_rows[pt[1]][pt[0]] for pt in wb["cells"])
        assert wb["level"] == expected_bed + 1, (
            f"斷言失敗！water_body '{wb['id']}' level={wb['level']} 不等於最高河床+1 {expected_bed + 1}！"
        )
        assert wb["bed"] == expected_bed, (
            f"斷言失敗！water_body '{wb['id']}' bed={wb['bed']} 不等於體內最高河床高度 {expected_bed}！"
        )

    # 3. 木橋格 (bridge_cells): rows 19..20 cols 29..32
    bridge_cells = []
    bridge_cells_set = set()
    for r in range(19, 21):
        for c in range(29, 33):
            bridge_cells.append(cell(c, r))
            bridge_cells_set.add((c, r))

    # 4. 十字幹道格 (road_cells): 南北向 Cols 18..20 Rows 0..39；東西向 Cols 0..39 Rows 19..20
    road_cells_set = set()
    for c in (18, 19, 20):
        for r in range(40):
            road_cells_set.add((c, r))
    for r in (19, 20):
        for c in range(40):
            road_cells_set.add((c, r))
    road_cells = sorted([cell(c, r) for c, r in road_cells_set])

    # 5. 中央廣場 (plaza_cells): Cols 16..22, Rows 16..22
    plaza_cells = []
    plaza_cells_set = set()
    for r in range(16, 23):
        for c in range(16, 23):
            plaza_cells.append(cell(c, r))
            plaza_cells_set.add((c, r))

    # 6. 建築列表 (buildings):
    # Round 12 修訂：
    # - 田舍 sack 從 facade 移到 props；
    # - 1 層樓建築招牌 h 設為 0.5 (實際約 46px＝2 級，0.5 + 2.0 = 2.5 落在 3 級牆內)，煙囪/燈籠 h 調至 1.0，滿足 h + 高/23 <= 牆高。
    # Round 13 修訂：
    # - 鐵匠鋪煙囪修正為 kind: roof，置於屋頂後牆格 cell(7, 0)。
    # - 雜貨鋪遮陽篷修正為門上方 4 格連排 (cols 1..4, row 4, h=2.1)，南牆窗戶移至 col 5。
    buildings = [
        {
            "building_id": "tavern",
            "label": "西南酒館",
            "style": "timber",
            "footprint": {
                "origin": cell(8, 24),
                "cols": 8,
                "rows": 6
            },
            "base_elevation": 0,
            "floors": 2,
            "units_per_floor": 3.0,
            "height_units": 6.0,
            "wall_ring_thickness": 1,
            # 南牆 (local row = 5)，沿 x 佔 2 格 (local col = 3, 4)
            "doors_local": [
                cell(3, 5),
                cell(4, 5)
            ],
            "door_height_units": 2.0,
            # R46: 室內 ≥ 6×4，梯級寬 2 格，前後各 1 格
            "stair": {
                "width": 2,
                "flight_local": [
                    {"col": 2, "row": 3, "step_offset": 1},
                    {"col": 3, "row": 3, "step_offset": 1},
                    {"col": 2, "row": 2, "step_offset": 2},
                    {"col": 3, "row": 2, "step_offset": 2}
                ],
                "void_cells_local": [
                    cell(2, 2),
                    cell(3, 2),
                    cell(2, 3),
                    cell(3, 3)
                ],
                "opening_local_on_upper_floor": [
                    cell(2, 2),
                    cell(3, 2),
                    cell(2, 3),
                    cell(3, 3)
                ]
            },
            "roof": {
                "walkable": False,
                "elevation": 6,
                "kind": "ROOF_CAP"
            },
            "windows_local": {
                "0": [1, 6],
                "1": [1, 6]
            },
            "facade": [
                {"img_id": "tavern_facade_0", "kind": "wall", "col": 3, "row": 5, "cell": 3, "h": 2.0, "sprite": "sign_beer"},
                {"img_id": "tavern_facade_1", "kind": "wall", "col": 5, "row": 5, "cell": 5, "h": 2.0, "tile": ["kenshi", 1, 3, 32, 32]}
            ]
        },
        {
            "building_id": "blacksmith",
            "label": "東北鐵匠鋪",
            "style": "stone",
            "footprint": {
                "origin": cell(21, 10),
                "cols": 8,
                "rows": 6
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            # 南牆 (local row = 5)，沿 x 佔 2 格 (local col = 4, 5)
            "doors_local": [
                cell(4, 5),
                cell(5, 5)
            ],
            "door_height_units": 2.0,
            # R31 / R46: 2 格寬室內石梯通向屋頂 DECK，室內 ≥ 6×4
            "stair": {
                "width": 2,
                "flight_local": [
                    {"col": 2, "row": 3, "step_offset": 1},
                    {"col": 3, "row": 3, "step_offset": 1},
                    {"col": 2, "row": 2, "step_offset": 2},
                    {"col": 3, "row": 2, "step_offset": 2}
                ],
                "void_cells_local": [
                    cell(2, 2),
                    cell(3, 2),
                    cell(2, 3),
                    cell(3, 3)
                ],
                "opening_local_on_upper_floor": [
                    cell(2, 2),
                    cell(3, 2),
                    cell(2, 3),
                    cell(3, 3)
                ]
            },
            # R31: 可站 DECK 屋頂
            "roof": {
                "walkable": True,
                "elevation": 3,
                "kind": "DECK"
            },
            "windows_local": {
                "0": [1, 6]
            },
            "facade": [
                {"img_id": "blacksmith_facade_0", "kind": "wall", "col": 2, "row": 5, "cell": 2, "h": 0.5, "sprite": "sign_hammer"},
                {"img_id": "blacksmith_facade_1", "kind": "roof", "col": 7, "row": 0, "cell": cell(7, 0), "h": 0.0, "tile": ["kenshi", 2, 3, 32, 32]}
            ]
        },
        {
            "building_id": "general_store",
            "label": "西北雜貨鋪",
            "style": "adobe",
            "footprint": {
                "origin": cell(10, 10),
                "cols": 6,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            # 南牆 (local row = 4)，沿 x 佔 2 格 (local col = 2, 3)
            "doors_local": [
                cell(2, 4),
                cell(3, 4)
            ],
            "door_height_units": 2.0,
            "stair": None,
            "roof": {
                "walkable": False,
                "elevation": 3,
                "kind": "ROOF_CAP"
            },
            "windows_local": {
                "0": [5]
            },
            "facade": [
                {"img_id": "general_store_facade_0", "kind": "wall", "col": 0, "row": 4, "cell": 0, "h": 0.5, "sprite": "sign_potion"},
                {"img_id": "general_store_facade_1", "kind": "wall", "col": 1, "row": 4, "cell": 1, "h": 2.1, "tile": ["kenshi", 0, 3, 32, 32]},
                {"img_id": "general_store_facade_2", "kind": "wall", "col": 2, "row": 4, "cell": 2, "h": 2.1, "tile": ["kenshi", 0, 3, 32, 32]},
                {"img_id": "general_store_facade_3", "kind": "wall", "col": 3, "row": 4, "cell": 3, "h": 2.1, "tile": ["kenshi", 0, 3, 32, 32]},
                {"img_id": "general_store_facade_4", "kind": "wall", "col": 4, "row": 4, "cell": 4, "h": 2.1, "tile": ["kenshi", 0, 3, 32, 32]}
            ]
        },
        {
            "building_id": "farm_shed",
            "label": "東南田舍與農具倉",
            "style": "timber",
            "footprint": {
                "origin": cell(22, 24),
                "cols": 6,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            # 南牆 (local row = 4)，沿 x 佔 2 格 (local col = 2, 3)
            "doors_local": [
                cell(2, 4),
                cell(3, 4)
            ],
            "door_height_units": 2.0,
            "stair": None,
            "roof": {
                "walkable": False,
                "elevation": 3,
                "kind": "ROOF_CAP"
            },
            "windows_local": {
                "0": [1, 4]
            },
            "facade": []
        }
    ]

    # --------------------------------------------------------
    # R34 / Round 12 強制斷言防火牆：
    # 1. facade 僅限牆面懸掛物 (招牌、燈籠、煙囪、遮陽篷、窗台)，嚴禁放置地面道具 (sack, barrel, crate 等)
    # 2. 門面元件必須整張落在牆帶內：h + bbox高 / 23.0 <= 牆高
    # --------------------------------------------------------
    FORBIDDEN_FACADE_SPRITES = {"sack", "sacks", "barrel", "crate", "box", "jar", "anvil", "woodpile"}
    KNOWN_SPRITE_HEIGHTS = {
        "sign_beer": 46,
        "sign_hammer": 46,
        "sign_potion": 46,
        "lantern": 32,
        "chimney": 32,
        "awning": 32
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    props_json_path = os.path.abspath(os.path.join(script_dir, "..", "reports", "keluo_props_sprites.json"))
    props_png_path = os.path.abspath(os.path.join(script_dir, "..", "reports", "keluo_kenshi_props.png"))
    tileset_png_path = os.path.abspath(os.path.join(script_dir, "..", "reports", "keluo_kenshi_tileset.png"))

    props_coords_spec = {}
    if os.path.exists(props_json_path):
        try:
            with open(props_json_path, "r", encoding="utf-8") as f_pj:
                props_coords_spec = json.load(f_pj)
        except Exception:
            pass

    props_img = None
    if os.path.exists(props_png_path):
        try:
            props_img = Image.open(props_png_path).convert("RGBA")
        except Exception:
            props_img = None

    tileset_img = None
    if os.path.exists(tileset_png_path):
        try:
            tileset_img = Image.open(tileset_png_path).convert("RGBA")
        except Exception:
            tileset_img = None

    def get_facade_bbox_height(f_item):
        """依據素材實際透明邊進行 bbox 裁切後量測真實高度"""
        sp = f_item.get("sprite", "")
        img = None
        if "tile" in f_item:
            tile_def = f_item["tile"]
            if tileset_img:
                col, row = tile_def[1], tile_def[2]
                w = tile_def[3] if len(tile_def) >= 4 else 32
                h = tile_def[4] if len(tile_def) >= 5 else 32
                img = tileset_img.crop((col * 32, row * 48, col * 32 + w, row * 48 + h))
            else:
                if len(tile_def) >= 5:
                    return tile_def[4]
                elif len(tile_def) == 4:
                    return tile_def[3]
                return 32
        elif sp in props_coords_spec and props_img:
            x, y, w, h = props_coords_spec[sp]
            img = props_img.crop((x, y, x + w, y + h))

        if img is not None:
            bbox = img.getbbox()
            if bbox:
                return bbox[3] - bbox[1]
            return img.height

        if sp in KNOWN_SPRITE_HEIGHTS:
            return KNOWN_SPRITE_HEIGHTS[sp]
        elif sp in props_coords_spec:
            return props_coords_spec[sp][3]
        return 32

    for b in buildings:
        b_id = b["building_id"]
        wall_height = float(b.get("height_units", b.get("floors", 1) * b.get("units_per_floor", 3.0)))
        units_per_floor = float(b.get("units_per_floor", 3.0))
        door_height = float(b.get("door_height_units", 2.0))
        wall_row = b["footprint"]["rows"] - 1

        doors_set = {(dc, dr) for dc, dr in b.get("doors_local", [])}
        windows_local = b.get("windows_local", {})

        for idx, f_item in enumerate(b.get("facade", [])):
            if "img_id" not in f_item:
                f_item["img_id"] = f"{b_id}_facade_{idx}"

            sp = f_item.get("sprite", "")
            assert sp not in FORBIDDEN_FACADE_SPRITES, (
                f"斷言失敗！建築 '{b_id}' facade 包含地面道具 '{sp}'！"
                f"依據規範，facade 只放掛在牆上的東西，地面道具必須放在 props。"
            )

            # 計算元件高度 (px)：以 bbox 裁掉透明邊後的真實高度量測
            sprite_h = get_facade_bbox_height(f_item)

            fh = float(f_item.get("h", 0.0))
            f_top = fh + (sprite_h / 23.0)
            assert f_top <= wall_height + 1e-4, (
                f"斷言失敗！建築 '{b_id}' facade 元件 '{f_item.get('img_id')}' (bbox 高 {sprite_h}px) "
                f"超出牆高！h ({fh}) + 高/23 ({sprite_h / 23.0:.3f}) = {f_top:.3f} > 牆高 {wall_height}！"
            )

            # --------------------------------------------------------
            # R34 補 強制斷言防火牆：門面元件不得跟窗、門重疊
            # facade 佔的格與高度範圍（h ~ h+高/23）不得與 windows_local／doors_local 對應的牆格與樓層重疊
            # --------------------------------------------------------
            fc = f_item.get("col", f_item.get("cell"))
            fr = f_item.get("row", wall_row)

            # 1. 大門重疊檢查：若在門格，高度範圍 [fh, f_top] 不得與大門高度 [0.0, door_height] 重疊
            if (fc, fr) in doors_set:
                overlap_door = max(fh, 0.0) < min(f_top, door_height) - 1e-4
                assert not overlap_door, (
                    f"斷言失敗！建築 '{b_id}' facade 元件 '{f_item.get('img_id')}' (col={fc}, row={fr}) "
                    f"高度範圍 [{fh:.2f}, {f_top:.2f}] 與大門高度 [0.0, {door_height:.2f}] 重疊！"
                )

            # 2. 窗戶重疊檢查：不得與 windows_local 對應的牆格與樓層重疊
            if fr == wall_row:
                for fl_str, win_cols in windows_local.items():
                    fl_idx = int(fl_str)
                    fl_bottom = fl_idx * units_per_floor
                    fl_top = (fl_idx + 1) * units_per_floor
                    if fc in win_cols:
                        overlap_win = max(fh, fl_bottom) < min(f_top, fl_top) - 1e-4
                        assert not overlap_win, (
                            f"斷言失敗！建築 '{b_id}' facade 元件 '{f_item.get('img_id')}' (col={fc}, row={fr}) "
                            f"高度範圍 [{fh:.2f}, {f_top:.2f}] 與 {fl_idx} 樓窗戶格 (col={fc}, 樓層高度 [{fl_bottom:.2f}, {fl_top:.2f}]) 重疊！"
                        )

    # --------------------------------------------------------
    # R46 強制斷言防火牆：stair 存在 ⇒ 室內空間 ≥ 6×4
    # --------------------------------------------------------
    for b in buildings:
        b_id = b["building_id"]
        if b.get("stair") is not None:
            w = b["footprint"]["cols"]
            h = b["footprint"]["rows"]
            t = b.get("wall_ring_thickness", 1)
            indoor_w = w - 2 * t
            indoor_h = h - 2 * t
            assert indoor_w >= 6 and indoor_h >= 4, (
                f"斷言失敗！建築 '{b_id}' 含有樓梯，但室內尺寸 {indoor_w}×{indoor_h} 小於 6×4！"
                f"依據 R46，有樓梯的建築腳印至少需 8×6。"
            )

    # --------------------------------------------------------
    # 強制斷言防火牆：每棟建築腳印格高程必須嚴格等於 base_elevation
    # --------------------------------------------------------
    for b in buildings:
        b_id = b["building_id"]
        base_elev = b["base_elevation"]
        c0, r0 = b["footprint"]["origin"]
        w = b["footprint"]["cols"]
        h = b["footprint"]["rows"]
        for r in range(r0, r0 + h):
            for c in range(c0, c0 + w):
                actual_elev = elevation_rows[r][c]
                assert actual_elev == base_elev, (
                    f"斷言失敗！建築 '{b_id}' 腳印格 (col={c}, row={r}) 高程為 {actual_elev}，"
                    f"不等於預期 base_elevation={base_elev}！座標可能顛倒或腳印範圍有誤。"
                )

    # 建築各類空間集合提取 (內部以 (col, row) tuple 為鍵)
    all_footprint_cells = set()
    all_wall_ring_cells = set()
    all_door_cells = set()
    all_solid_wall_cells = set()
    all_interior_cells = set()

    building_door_portals = set()  # 保存門與相鄰通行格的配對 ((col, row), (ncol, nrow))

    for b in buildings:
        c0, r0 = b["footprint"]["origin"]
        w = b["footprint"]["cols"]
        h = b["footprint"]["rows"]

        b_doors = set()
        for dc, dr in b["doors_local"]:
            door_world = (c0 + dc, r0 + dr)
            b_doors.add(door_world)
            all_door_cells.add(door_world)

        b_footprint = set()
        b_wall_ring = set()
        for r in range(r0, r0 + h):
            for c in range(c0, c0 + w):
                cell_pt = (c, r)
                b_footprint.add(cell_pt)
                all_footprint_cells.add(cell_pt)
                if r == r0 or r == r0 + h - 1 or c == c0 or c == c0 + w - 1:
                    b_wall_ring.add(cell_pt)
                    all_wall_ring_cells.add(cell_pt)
                    if cell_pt not in b_doors:
                        all_solid_wall_cells.add(cell_pt)
                else:
                    all_interior_cells.add(cell_pt)

        # 建立該建築門向內與向外的通行 portal
        for dc, dr in b_doors:
            for nc, nr in [(dc, dr - 1), (dc, dr + 1), (dc - 1, dr), (dc + 1, dr)]:
                if (nc, nr) not in (b_wall_ring - b_doors):
                    building_door_portals.add(((dc, dr), (nc, nr)))
                    building_door_portals.add(((nc, nr), (dc, dr)))

    # 7. 東南梯級農田格 (field_cells): Rows 23..38, Cols 22..38
    # 扣除農舍腳印、幹道、水面格、泥灘與支渠
    field_cells = []
    field_cells_set = set()
    for r in range(23, 39):
        for c in range(22, 39):
            cell_pt = (c, r)
            if (cell_pt not in road_cells_set and
                cell_pt not in all_footprint_cells and
                cell_pt not in water_cells_set and
                cell_pt not in mudflat_cells_set and
                cell_pt not in ditch_cells_set):
                field_cells.append(cell(c, r))
                field_cells_set.add(cell_pt)

    # 8. 計算 surfaces (同高度 4-連通之非建築格集合；R42: 必須覆蓋所有非建築格，含水面、泥灘與支渠)
    # 規則：Round 10 定稿——水格 surface elevation ＝ 最高河床 + 1（通常 0）。
    # R44 補：泥灘格已改為 H0，與一般 H0 地面一同納入地面 surface。
    cell_wb_level = {}
    for wb in water_bodies:
        lvl = wb["level"]
        for pt in wb["cells"]:
            cell_wb_level[(pt[0], pt[1])] = lvl

    is_surface_cell = set()
    for r in range(40):
        for c in range(40):
            cell_pt = (c, r)
            if cell_pt not in all_footprint_cells:
                is_surface_cell.add(cell_pt)

    visited_surface = set()
    surfaces = []
    surface_idx = 1

    for r in range(40):
        for c in range(40):
            start_cell = (c, r)
            if start_cell in is_surface_cell and start_cell not in visited_surface:
                is_water = start_cell in water_cells_set
                if is_water:
                    elev = cell_wb_level[start_cell]
                    kind = "WATER"
                else:
                    elev = elevation_rows[r][c]
                    if elev == 0:
                        kind = "GROUND"
                    elif elev > 0:
                        kind = "PLATEAU"
                    else:
                        kind = "PIT"

                cluster = []
                queue = deque([start_cell])
                visited_surface.add(start_cell)

                while queue:
                    curr_c, curr_r = queue.popleft()
                    cluster.append(cell(curr_c, curr_r))

                    for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nc, nr = curr_c + dc, curr_r + dr
                        ncell = (nc, nr)
                        if 0 <= nc < 40 and 0 <= nr < 40:
                            if ncell in is_surface_cell and ncell not in visited_surface:
                                ncell_is_water = ncell in water_cells_set
                                if ncell_is_water == is_water:
                                    ncell_elev = cell_wb_level[ncell] if ncell_is_water else elevation_rows[nr][nc]
                                    if ncell_elev == elev:
                                        visited_surface.add(ncell)
                                        queue.append(ncell)

                surfaces.append({
                    "surface_id": f"S{surface_idx:02d}",
                    "elevation": elev,
                    "kind": kind,
                    "cells": cluster
                })
                surface_idx += 1

    # --------------------------------------------------------
    # R42 強制斷言防火牆：surface 必須且僅能覆蓋每一個非建築格
    # --------------------------------------------------------
    all_surface_cells = [tuple(pt) for s in surfaces for pt in s["cells"]]
    all_surface_set = set(all_surface_cells)
    expected_non_building_count = 40 * 40 - len(all_footprint_cells)

    assert len(all_surface_cells) == len(all_surface_set), (
        f"斷言失敗！surfaces 存在重複格點！總計 {len(all_surface_cells)} 格，去重後 {len(all_surface_set)} 格。"
    )
    assert all_surface_set == is_surface_cell, (
        f"斷言失敗！surfaces 未能完全覆蓋非建築格！"
        f"缺失格數：{len(is_surface_cell - all_surface_set)}，多餘格數：{len(all_surface_set - is_surface_cell)}。"
    )
    assert len(all_surface_set) == expected_non_building_count, (
        f"斷言失敗！surfaces 總格數 {len(all_surface_set)} 不等於非建築格數 {expected_non_building_count}！"
    )

    # 9. 指定斷崖 (authored_cliffs): 本圖無高差 1 之指定斷崖，清空為空陣列
    authored_cliffs = []
    authored_cliffs_set = set()

    # 地形格定義 (非水且非建築，供邊界坡度分類)
    is_terrain = set(pt for pt in is_surface_cell if pt not in water_cells_set)

    # 10. 計算 edges (每對 4-鄰格只出一條，from 取較西或較北那格)
    edges = []
    for r in range(40):
        for c in range(40):
            cell_from = (c, r)
            h_from = elevation_rows[r][c]

            neighbors = []
            if c + 1 < 40:
                neighbors.append((c + 1, r))  # 東向 (較西 -> 較東)
            if r + 1 < 40:
                neighbors.append((c, r + 1))  # 南向 (較北 -> 較南)

            for cell_to in neighbors:
                nc, nr = cell_to
                h_to = elevation_rows[nr][nc]
                edge_fwd = (cell_from, cell_to)
                edge_rev = (cell_to, cell_from)

                # 規則 1: 門格通道 (DOOR)
                if edge_fwd in building_door_portals or edge_rev in building_door_portals:
                    edge_type = "DOOR"
                # 任一方是建築實體牆環格 (WALL)
                elif cell_from in all_solid_wall_cells or cell_to in all_solid_wall_cells:
                    edge_type = "WALL"
                elif (cell_from in all_door_cells and cell_to in all_wall_ring_cells) or \
                     (cell_to in all_door_cells and cell_from in all_wall_ring_cells):
                    edge_type = "WALL"
                # 規則 2: 任一方是水面格 (WATER)
                elif cell_from in water_cells_set or cell_to in water_cells_set:
                    edge_type = "WATER"
                # 規則 2.5: R45 任一方是支渠格且非水面格 (DITCH)
                elif cell_from in ditch_cells_set or cell_to in ditch_cells_set:
                    edge_type = "DITCH"
                # 規則 3: authored_cliffs 內列的邊標 CLIFF_AUTHORED
                elif edge_fwd in authored_cliffs_set or edge_rev in authored_cliffs_set:
                    edge_type = "CLIFF_AUTHORED"
                else:
                    diff = abs(h_from - h_to)
                    # 規則 4: 高差 >= 2 級 → CLIFF
                    if diff >= 2:
                        edge_type = "CLIFF"
                    # 規則 5: 高差 1 級且雙方都是地形（非水、非建築腳印）→ WALK_SLOPE
                    elif diff == 1:
                        if cell_from in is_terrain and cell_to in is_terrain:
                            edge_type = "WALK_SLOPE"
                        else:
                            edge_type = "PIT_RIM"
                    # 規則 6: 兩格高度相等 → WALK
                    else:
                        edge_type = "WALK"

                edges.append({
                    "from": cell(cell_from[0], cell_from[1]),
                    "to": cell(cell_to[0], cell_to[1]),
                    "type": edge_type
                })

    # 11. 裝飾道具清單 (props): R38 改回手繪 3/4 視角 sprite，拿掉 sprite_box
    # Round 12 修訂：田舍 sack 從 facade 移至 props (shed_sack_2 放置於西側角牆前 cell(22, 29))
    raw_props = [
        # 北方岩台哨塔 (H3)
        {
            "id": "watchtower",
            "cell": cell(25, 4),
            "footprint": [4, 2],
            "elevation": 3,
            "sprite": "watchtower"
        },
        # 中央廣場設施
        {
            "id": "well",
            "cell": cell(17, 17),
            "footprint": [2, 2],
            "elevation": 0,
            "sprite": "well"
        },
        {
            "id": "market_stall_fruit",
            "cell": cell(21, 17),
            "footprint": [2, 1],
            "elevation": 0,
            "sprite": "stall"
        },
        {
            "id": "market_stall_fish",
            "cell": cell(17, 21),
            "footprint": [2, 1],
            "elevation": 0,
            "sprite": "stall"
        },

        # R47: 酒館門口道具群 (門在 cols 11..12, row 29；門前 row 30 cols 11..12 不壓)
        # 兩個桶＋一個罐
        {
            "id": "tavern_barrel_1",
            "cell": cell(9, 30),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "barrel"
        },
        {
            "id": "tavern_barrel_2",
            "cell": cell(10, 30),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "barrel"
        },
        {
            "id": "tavern_jar_1",
            "cell": cell(13, 30),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "jar"
        },

        # R47: 鐵匠鋪門口道具群 (門在 cols 25..26, row 15；門前 row 16 cols 25..26 不壓)
        # anvil＋一堆 rock (煤)＋露天爐 forge
        {
            "id": "blacksmith_anvil",
            "cell": cell(24, 16),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "anvil"
        },
        {
            "id": "blacksmith_coal_1",
            "cell": cell(23, 16),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "rock_1"
        },
        {
            "id": "blacksmith_coal_2",
            "cell": cell(22, 16),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "rock_2"
        },
        {
            "id": "forge",
            "cell": cell(27, 16),
            "footprint": [2, 2],
            "elevation": 0,
            "sprite": "furnace"
        },

        # R47: 雜貨鋪門口道具群 (門在 cols 12..13, row 14；門前 row 15 cols 12..13 不壓)
        # crate×2＋sack
        {
            "id": "store_crate_1",
            "cell": cell(10, 15),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "crate"
        },
        {
            "id": "store_crate_2",
            "cell": cell(11, 15),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "crate"
        },
        {
            "id": "store_sack_1",
            "cell": cell(14, 15),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "sack"
        },

        # R47 / Round 12: 田舍門口道具群 (門在 cols 24..25, row 28；門前 row 29 cols 24..25 不壓)
        # woodpile＋sack群 (shed_sack_2 接收原田舍 facade 之 sack，放置於西側角牆前 cell(22, 29))
        {
            "id": "shed_woodpile",
            "cell": cell(23, 29),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "woodpile"
        },
        {
            "id": "shed_sack_1",
            "cell": cell(26, 29),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "sack"
        },
        {
            "id": "shed_sack_2",
            "cell": cell(22, 29),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "sack"
        }
    ]

    props = []
    for item in raw_props:
        sprite_name = item.get("sprite", item["id"])
        fp = item.get("footprint", [1, 1])
        prop_entry = {
            "id": item["id"],
            "cell": item["cell"],
            "footprint": fp,
            "elevation": item["elevation"],
            "sprite": sprite_name
        }
        props.append(prop_entry)

    # --------------------------------------------------------
    # R46 / R47 強制斷言防火牆：任何道具腳印不得與建築大門「門前一格」重疊
    # --------------------------------------------------------
    door_front_cells = set()
    for b in buildings:
        c0, r0 = b["footprint"]["origin"]
        for dc, dr in b["doors_local"]:
            door_front_cells.add((c0 + dc, r0 + dr + 1))

    for p in props:
        p_id = p["id"]
        pc, pr = p["cell"]
        pw, ph = p["footprint"]
        prop_footprint = {(pc + dx, pr + dy) for dy in range(ph) for dx in range(pw)}
        overlap = prop_footprint & door_front_cells
        assert not overlap, (
            f"斷言失敗！道具 '{p_id}' 腳印格 {overlap} 與建築門前一格重疊！"
            f"道具不得堵門、不得壓門前通行通道。"
        )

    # 12. 演員站位固定裝置 (actors_fixture): 至少四筆（主角、衛兵、漁夫、鐵匠鋪屋頂弓手）
    # R44 補：泥灘格改為 H0，漁夫站位調整至 H0
    actors_fixture = [
        {
            "id": "arya",
            "label": "主",
            "color": [56, 189, 248],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(18, 20, 0)]
        },
        {
            "id": "guard",
            "label": "衛",
            "color": [234, 179, 8],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(24, 5, 3)]
        },
        {
            "id": "fisherman",
            "label": "漁",
            "color": [34, 197, 94],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(30, 16, 0)]
        },
        {
            "id": "archer",
            "label": "弓",
            "color": [249, 115, 22],
            "indoor": None,
            "on_building": "blacksmith",
            # 鐵匠鋪屋頂可站 DECK (world col 25, row 13, elevation 3，位於 blacksmith origin (21, 10))
            "cells": [cell_3d(25, 13, 3)]
        }
    ]

    # 組裝完整 Chunk Spec 字典
    spec = {
        "chunk_id": "chunk_0_0_border_village_v2",
        "grid": {
            "cols": 40,
            "rows": 40,
            "cell_px": 32,
            "world_origin": [0, 0]
        },
        "projection_presentation_only": {
            "rise_ratio": 0.72,
            "side_shift_ratio": 0.12,
            "side_spread_cells": 6
        },
        "bridge_cells": bridge_cells,
        "authored_cliffs": authored_cliffs,
        "elevation_rows": elevation_rows,
        "road_cells": road_cells,
        "plaza_cells": plaza_cells,
        "field_cells": field_cells,
        "ditch_cells": ditch_cells,
        "mud_cells": mud_cells,
        "water_cells": water_cells,
        "water_bodies": water_bodies,
        "surfaces": surfaces,
        "edges": edges,
        "buildings": buildings,
        "props": props,
        "actors_fixture": actors_fixture
    }

    # 輸出到 reports/chunk_0_0_spec_v2.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(os.path.join(script_dir, "..", "reports"))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "chunk_0_0_spec_v2.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)

    print(f"✅ 成功生成 chunk_0_0_spec_v2.json 於：{output_path}")

if __name__ == "__main__":
    build_chunk_spec()
