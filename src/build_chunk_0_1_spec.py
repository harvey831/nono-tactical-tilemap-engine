#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_chunk_0_1_spec.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: 將 50×50 高程格網與山谷礦坑聚落配置生成為符合珂洛規範的機器可讀 chunk spec (Chunk 0,1)。
Core Features & Principles:
  1. 50×50 尺寸推導與配置：
     - 檢視器一屏 38 格，50 格寬度約 1.31 屏，高度 2.53 屏，具備真正深入礦谷的空間縱深。
     - 建築 7 棟（含 3 棟 8×6 且具備室內樓梯，其中 2 棟上平頂 DECK 屋頂）。
  2. 雙水體（R44 水面高度新規）：
     - 水體 1（主河道）：延續 (0,0) 東側河道，四周岸為 H0，水面 level = 0，河床 bed = -1 (深處 -2)。
     - 水體 2（山上蓄水池）：挖在 H2 台地上，四周岸皆為 H2，水面 level = 2，池底河床 bed = 1。
     - 強制斷言：水面＝四周岸格最低高度；水格 surface elevation ＝ 體內水面 level。
  3. 落差地形與通行動線：
     - H0 谷地 → H2 台地 → H4 礦坑山壁，具備 H1 及 H3 之可通行坡道 (WALK_SLOPE)，其餘為斷崖 (CLIFF)。
  4. 一格寬水渠 (ditch)：自蓄水池引水下山，平鋪於地面 (H2/H1/H0)，不做高差。
  5. 泥灘 (mudflat)：鋪於河岸 H0，頂面貼 pit_floor，不沉格。
  6. 門面 (facade) 與道具 (props) 嚴格防火牆：
     - facade 僅限牆面懸掛物 (招牌、煙囪、遮陽篷)，h + bbox/23 <= 牆高，不撞窗不撞門。
     - 地面物一律進 props，不堵門、不壓水、不壓溝。
  7. 演員 fixture：共 7 位演員，包含站在鍛造坊 DECK 屋頂之採礦領班。
------------------------------------------------------------
"""

import os
import sys
import json
import re
from collections import deque
from PIL import Image

def cell(col, row):
    """spec 座標唯一出口：所有輸出的 2D 格點一律為 [col, row] = [x, y]。"""
    return [int(col), int(row)]

def cell_3d(col, row, elev):
    """3D 座標出口：[col, row, elevation]。"""
    return [int(col), int(row), int(elev)]

def find_elevation_md():
    """尋找 nono_chunk_0_1_elevation.md 的路徑"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(script_dir, "..", "..", "..", "nono_chunk_0_1_elevation.md")),
        "C:/GPTfile/godot/Nono's Little Base/nono_chunk_0_1_elevation.md",
        os.path.join(os.getcwd(), "nono_chunk_0_1_elevation.md")
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"無法找到高程格網 Markdown，候選路徑：{candidates}")

def parse_elevation_grid(md_path):
    """解析 Markdown 內的 50×50 字串矩陣並轉為整數高程矩陣 (rows[y][x])"""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.findall(r"```(?:text)?\r?\n([\s\S]*?)```", content)
    grid_lines = None
    for b in blocks:
        lines = [line.strip() for line in b.splitlines() if line.strip()]
        if len(lines) == 50 and all(len(line) == 50 for line in lines):
            grid_lines = lines
            break

    if not grid_lines:
        raise ValueError("在 Markdown 中未找到符合 50×50 規範的高程代碼塊！")

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

    # 1. 指定泥灘岸格 (mud_cells): 規則 R44 補：岸就是 H0 的地；水體旁不可有低於地面又不是水的格。
    mudflat_cells_coords = []
    for r in range(12, 16):
        for c in range(26, 29):
            mudflat_cells_coords.append((c, r))
    mud_cells = [cell(c, r) for c, r in mudflat_cells_coords]
    mud_cells_set = set(mudflat_cells_coords)
    mudflat_cells_set = mud_cells_set

    # 將泥灘格高程確保為 0
    for mc, mr in mudflat_cells_coords:
        elevation_rows[mr][mc] = 0

    # 2. 水面格 (water_cells): 扣除泥灘格後，包含主河道與山上蓄水池
    # 蓄水池：Cols 11..14, Rows 7..10
    reservoir_coords = set()
    for r in range(7, 11):
        for c in range(11, 15):
            reservoir_coords.add((c, r))

    water_cells = []
    water_cells_set = set()
    for r in range(50):
        for c in range(50):
            pt = (c, r)
            if pt in reservoir_coords:
                water_cells.append(cell(c, r))
                water_cells_set.add(pt)
            elif elevation_rows[r][c] in (-1, -2):
                if pt not in mudflat_cells_set:
                    water_cells.append(cell(c, r))
                    water_cells_set.add(pt)

    # 2.2 R45 一格寬水渠 (ditch_cells): 高程與所在地面齊平，頂面貼 ditch tile，edge 標 DITCH
    # 自蓄水池東南側 (15, 10) 引出，順坡流向生活洗礦區 (18, 14)
    ditch_cells_coords = [
        (15, 10), (16, 10), (16, 11), (16, 12),
        (16, 13), (17, 13), (17, 14), (18, 14)
    ]
    ditch_cells = [cell(c, r) for c, r in ditch_cells_coords]
    ditch_cells_set = set(ditch_cells_coords)

    # 2.5 計算 water_bodies (新 R44：水面＝四周岸格最低高度；水方塊佔 [level-1, level])
    visited_water = set()
    water_bodies = []
    wb_idx = 0
    for r in range(50):
        for c in range(50):
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
                        if 0 <= nc < 50 and 0 <= nr < 50:
                            if ncell in water_cells_set and ncell not in visited_water:
                                visited_water.add(ncell)
                                queue.append(ncell)

                # 計算四周岸格的最低高度 (出界視為 0)
                shore_levels = []
                for pt in body_cells:
                    bc, br = pt[0], pt[1]
                    for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nc, nr = bc + dc, br + dr
                        if (nc, nr) not in water_cells_set:
                            if 0 <= nc < 50 and 0 <= nr < 50:
                                shore_levels.append(elevation_rows[nr][nc])
                            else:
                                shore_levels.append(0)

                min_shore = min(shore_levels) if shore_levels else 0
                max_bed = max(elevation_rows[pt[1]][pt[0]] for pt in body_cells)

                water_bodies.append({
                    "id": f"wb_{wb_idx}",
                    "level": int(min_shore),
                    "bed": int(max_bed),
                    "cells": body_cells
                })
                wb_idx += 1

    # --------------------------------------------------------
    # R44 強制斷言防火牆：雙水體水面高度與連通性檢驗
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
    assert len(water_bodies) == 2, (
        f"斷言失敗！預期應有 2 個水體（主河道與山上蓄水池），實際檢測出 {len(water_bodies)} 個！"
    )

    for wb in water_bodies:
        wb_cells_set = set(tuple(p) for p in wb["cells"])
        is_reservoir = any(p in reservoir_coords for p in wb_cells_set)
        if is_reservoir:
            assert wb["level"] == 2, (
                f"斷言失敗！山上蓄水池水面高度 level={wb['level']}，不符合 R44 規範的四周 H2 岸高 2！"
            )
            assert wb["bed"] == 1, (
                f"斷言失敗！山上蓄水池河床高度 bed={wb['bed']}，預期為 1！"
            )
        else:
            assert wb["level"] == 0, (
                f"斷言失敗！主河道水面高度 level={wb['level']}，不符合 R44 規範的岸高 0！"
            )
            assert wb["bed"] == -1, (
                f"斷言失敗！主河道最高河床高度 bed={wb['bed']}，預期為 -1！"
            )

    # 3. 木橋格 (bridge_cells): 東西向跨河木橋 Cols 29..32, Rows 20..21
    bridge_cells = []
    bridge_cells_set = set()
    for r in range(20, 22):
        for c in range(29, 33):
            bridge_cells.append(cell(c, r))
            bridge_cells_set.add((c, r))

    # 4. 主街與聯絡道 (road_cells):
    # 南北主幹道：Cols 18..20, Rows 0..49
    # 橫向分支路段：Rows 20..21 (通向渡橋 Cols 21..28)、Rows 13..14 (通向台地坡道 Cols 16..17)
    road_cells_set = set()
    for c in (18, 19, 20):
        for r in range(50):
            road_cells_set.add((c, r))
    for r in (20, 21):
        for c in range(21, 29):
            road_cells_set.add((c, r))
    for r in (13, 14):
        for c in range(16, 18):
            road_cells_set.add((c, r))
    road_cells = sorted([cell(c, r) for c, r in road_cells_set])

    # 5. 中央選礦與水井廣場 (plaza_cells): Cols 18..21, Rows 22..25
    plaza_cells = []
    plaza_cells_set = set()
    for r in range(22, 26):
        for c in range(18, 22):
            plaza_cells.append(cell(c, r))
            plaza_cells_set.add((c, r))

    # 6. 建築列表 (buildings): 7 棟建築規劃
    buildings = [
        {
            "building_id": "mine_office",
            "label": "礦場監督公署",
            "style": "stone",
            "footprint": {
                "origin": cell(10, 16),
                "cols": 8,
                "rows": 6
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(3, 5),
                cell(4, 5)
            ],
            "door_height_units": 2.0,
            "stair": {
                "width": 2,
                "flight_local": [
                    {"col": 2, "row": 3, "step_offset": 1},
                    {"col": 3, "row": 3, "step_offset": 1},
                    {"col": 2, "row": 2, "step_offset": 2},
                    {"col": 3, "row": 2, "step_offset": 2}
                ],
                "void_cells_local": [
                    cell(2, 2), cell(3, 2),
                    cell(2, 3), cell(3, 3)
                ],
                "opening_local_on_upper_floor": [
                    cell(2, 2), cell(3, 2),
                    cell(2, 3), cell(3, 3)
                ]
            },
            "roof": {
                "walkable": True,
                "elevation": 3,
                "kind": "DECK"
            },
            "windows_local": {
                "0": [1, 6]
            },
            "facade": [
                {"img_id": "office_facade_0", "kind": "wall", "col": 2, "row": 5, "cell": 2, "h": 0.5, "sprite": "sign_hammer"}
            ]
        },
        {
            "building_id": "miners_tavern",
            "label": "礦工大酒館",
            "style": "timber",
            "footprint": {
                "origin": cell(22, 16),
                "cols": 8,
                "rows": 6
            },
            "base_elevation": 0,
            "floors": 2,
            "units_per_floor": 3.0,
            "height_units": 6.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(3, 5),
                cell(4, 5)
            ],
            "door_height_units": 2.0,
            "stair": {
                "width": 2,
                "flight_local": [
                    {"col": 2, "row": 3, "step_offset": 1},
                    {"col": 3, "row": 3, "step_offset": 1},
                    {"col": 2, "row": 2, "step_offset": 2},
                    {"col": 3, "row": 2, "step_offset": 2}
                ],
                "void_cells_local": [
                    cell(2, 2), cell(3, 2),
                    cell(2, 3), cell(3, 3)
                ],
                "opening_local_on_upper_floor": [
                    cell(2, 2), cell(3, 2),
                    cell(2, 3), cell(3, 3)
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
                {"img_id": "tavern_facade_0", "kind": "wall", "col": 2, "row": 5, "cell": 2, "h": 2.0, "sprite": "sign_beer"}
            ]
        },
        {
            "building_id": "refinery_forge",
            "label": "精煉鍛造坊",
            "style": "stone",
            "footprint": {
                "origin": cell(10, 26),
                "cols": 8,
                "rows": 6
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(3, 5),
                cell(4, 5)
            ],
            "door_height_units": 2.0,
            "stair": {
                "width": 2,
                "flight_local": [
                    {"col": 2, "row": 3, "step_offset": 1},
                    {"col": 3, "row": 3, "step_offset": 1},
                    {"col": 2, "row": 2, "step_offset": 2},
                    {"col": 3, "row": 2, "step_offset": 2}
                ],
                "void_cells_local": [
                    cell(2, 2), cell(3, 2),
                    cell(2, 3), cell(3, 3)
                ],
                "opening_local_on_upper_floor": [
                    cell(2, 2), cell(3, 2),
                    cell(2, 3), cell(3, 3)
                ]
            },
            "roof": {
                "walkable": True,
                "elevation": 3,
                "kind": "DECK"
            },
            "windows_local": {
                "0": [1, 6]
            },
            "facade": [
                {"img_id": "forge_facade_0", "kind": "wall", "col": 2, "row": 5, "cell": 2, "h": 0.5, "sprite": "sign_hammer"},
                {"img_id": "forge_facade_1", "kind": "roof", "col": 7, "row": 0, "cell": cell(7, 0), "h": 0.0, "tile": ["kenshi", 2, 3, 32, 32]}
            ]
        },
        {
            "building_id": "mining_supply",
            "label": "礦山物資雜貨行",
            "style": "adobe",
            "footprint": {
                "origin": cell(22, 26),
                "cols": 6,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
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
                {"img_id": "supply_facade_0", "kind": "wall", "col": 0, "row": 4, "cell": 0, "h": 0.5, "sprite": "sign_potion"},
                {"img_id": "supply_facade_1", "kind": "wall", "col": 1, "row": 4, "cell": 1, "h": 2.1, "tile": ["kenshi", 0, 3, 32, 32]},
                {"img_id": "supply_facade_2", "kind": "wall", "col": 2, "row": 4, "cell": 2, "h": 2.1, "tile": ["kenshi", 0, 3, 32, 32]},
                {"img_id": "supply_facade_3", "kind": "wall", "col": 3, "row": 4, "cell": 3, "h": 2.1, "tile": ["kenshi", 0, 3, 32, 32]},
                {"img_id": "supply_facade_4", "kind": "wall", "col": 4, "row": 4, "cell": 4, "h": 2.1, "tile": ["kenshi", 0, 3, 32, 32]}
            ]
        },
        {
            "building_id": "tool_depot",
            "label": "炸藥與工具庫",
            "style": "adobe",
            "footprint": {
                "origin": cell(22, 36),
                "cols": 6,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
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
            "facade": [
                {"img_id": "depot_facade_0", "kind": "wall", "col": 0, "row": 4, "cell": 0, "h": 0.5, "sprite": "sign_potion"}
            ]
        },
        {
            "building_id": "miners_cabin_1",
            "label": "一號礦工居所",
            "style": "timber",
            "footprint": {
                "origin": cell(22, 6),
                "cols": 6,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
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
            "facade": [
                {"img_id": "cabin1_facade_0", "kind": "wall", "col": 0, "row": 4, "cell": 0, "h": 0.5, "sprite": "sign_beer"},
                {"img_id": "cabin1_facade_1", "kind": "roof", "col": 5, "row": 0, "cell": cell(5, 0), "h": 0.0, "tile": ["kenshi", 2, 3, 32, 32]}
            ]
        },
        {
            "building_id": "miners_cabin_2",
            "label": "二號礦工居所",
            "style": "timber",
            "footprint": {
                "origin": cell(10, 36),
                "cols": 6,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
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
            "facade": [
                {"img_id": "cabin2_facade_0", "kind": "wall", "col": 0, "row": 4, "cell": 0, "h": 0.5, "sprite": "sign_beer"},
                {"img_id": "cabin2_facade_1", "kind": "roof", "col": 5, "row": 0, "cell": cell(5, 0), "h": 0.0, "tile": ["kenshi", 2, 3, 32, 32]}
            ]
        }
    ]

    # --------------------------------------------------------
    # facade 防火牆斷言
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
                return tile_def[4] if len(tile_def) >= 5 else 32
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
            if f_item.get("kind") == "roof":
                continue  # 屋頂元件不檢查牆面高度限制

            sp = f_item.get("sprite", "")
            assert sp not in FORBIDDEN_FACADE_SPRITES, (
                f"斷言失敗！建築 '{b_id}' facade 包含地面道具 '{sp}'！"
            )

            sprite_h = get_facade_bbox_height(f_item)
            fh = float(f_item.get("h", 0.0))
            f_top = fh + (sprite_h / 23.0)
            assert f_top <= wall_height + 1e-4, (
                f"斷言失敗！建築 '{b_id}' facade 元件 '{f_item.get('img_id')}' (bbox 高 {sprite_h}px) "
                f"超出牆高！h ({fh}) + 高/23 ({sprite_h / 23.0:.3f}) = {f_top:.3f} > 牆高 {wall_height}！"
            )

            fc = f_item.get("col", f_item.get("cell"))
            fr = f_item.get("row", wall_row)

            # 大門重疊檢查
            if (fc, fr) in doors_set:
                overlap_door = max(fh, 0.0) < min(f_top, door_height) - 1e-4
                assert not overlap_door, (
                    f"斷言失敗！建築 '{b_id}' facade 元件 '{f_item.get('img_id')}' 與大門高度重疊！"
                )

            # 窗戶重疊檢查
            if fr == wall_row:
                for fl_str, win_cols in windows_local.items():
                    fl_idx = int(fl_str)
                    fl_bottom = fl_idx * units_per_floor
                    fl_top = (fl_idx + 1) * units_per_floor
                    if fc in win_cols:
                        overlap_win = max(fh, fl_bottom) < min(f_top, fl_top) - 1e-4
                        assert not overlap_win, (
                            f"斷言失敗！建築 '{b_id}' facade 元件 '{f_item.get('img_id')}' 與窗戶重疊！"
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
                    f"不等於預期 base_elevation={base_elev}！"
                )

    # 建築空間集合提取
    all_footprint_cells = set()
    all_wall_ring_cells = set()
    all_door_cells = set()
    all_solid_wall_cells = set()
    all_interior_cells = set()
    building_door_portals = set()

    for b in buildings:
        c0, r0 = b["footprint"]["origin"]
        w = b["footprint"]["cols"]
        h = b["footprint"]["rows"]

        b_doors = set()
        for dc, dr in b["doors_local"]:
            door_world = (c0 + dc, r0 + dr)
            b_doors.add(door_world)
            all_door_cells.add(door_world)

        b_wall_ring = set()
        for r in range(r0, r0 + h):
            for c in range(c0, c0 + w):
                cell_pt = (c, r)
                all_footprint_cells.add(cell_pt)
                if r == r0 or r == r0 + h - 1 or c == c0 or c == c0 + w - 1:
                    b_wall_ring.add(cell_pt)
                    all_wall_ring_cells.add(cell_pt)
                    if cell_pt not in b_doors:
                        all_solid_wall_cells.add(cell_pt)
                else:
                    all_interior_cells.add(cell_pt)

        for dc, dr in b_doors:
            for nc, nr in [(dc, dr - 1), (dc, dr + 1), (dc - 1, dr), (dc + 1, dr)]:
                if (nc, nr) not in (b_wall_ring - b_doors):
                    building_door_portals.add(((dc, dr), (nc, nr)))
                    building_door_portals.add(((nc, nr), (dc, dr)))

    # 7. 作業場坪格 (field_cells): 露天選礦作業坪
    # 位於 Cols 18..21, Rows 26..35（扣除道路與建築）
    field_cells = []
    field_cells_set = set()
    for r in range(26, 36):
        for c in range(18, 22):
            cell_pt = (c, r)
            if (cell_pt not in road_cells_set and
                cell_pt not in all_footprint_cells and
                cell_pt not in water_cells_set and
                cell_pt not in mudflat_cells_set and
                cell_pt not in ditch_cells_set):
                field_cells.append(cell(c, r))
                field_cells_set.add(cell_pt)

    # 8. 計算 surfaces (同高度 4-連通之非建築格集合)
    cell_wb_level = {}
    for wb in water_bodies:
        lvl = wb["level"]
        for pt in wb["cells"]:
            cell_wb_level[(pt[0], pt[1])] = lvl

    is_surface_cell = set()
    for r in range(50):
        for c in range(50):
            cell_pt = (c, r)
            if cell_pt not in all_footprint_cells:
                is_surface_cell.add(cell_pt)

    visited_surface = set()
    surfaces = []
    surface_idx = 1

    for r in range(50):
        for c in range(50):
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
                        if 0 <= nc < 50 and 0 <= nr < 50:
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

    # R42 強制斷言防火牆：surface 必須且僅能覆蓋每一個非建築格
    all_surface_cells = [tuple(pt) for s in surfaces for pt in s["cells"]]
    all_surface_set = set(all_surface_cells)
    expected_non_building_count = 50 * 50 - len(all_footprint_cells)

    assert len(all_surface_cells) == len(all_surface_set), (
        f"斷言失敗！surfaces 存在重複格點！"
    )
    assert all_surface_set == is_surface_cell, (
        f"斷言失敗！surfaces 未能完全覆蓋非建築格！"
    )
    assert len(all_surface_set) == expected_non_building_count, (
        f"斷言失敗！surfaces 總格數 {len(all_surface_set)} 不等於非建築格數 {expected_non_building_count}！"
    )

    # 9. 地形邊界計算 (edges)
    authored_cliffs = []
    authored_cliffs_set = set()
    is_terrain = set(pt for pt in is_surface_cell if pt not in water_cells_set)

    edges = []
    for r in range(50):
        for c in range(50):
            cell_from = (c, r)
            h_from = elevation_rows[r][c]

            neighbors = []
            if c + 1 < 50:
                neighbors.append((c + 1, r))  # 東向
            if r + 1 < 50:
                neighbors.append((c, r + 1))  # 南向

            for cell_to in neighbors:
                nc, nr = cell_to
                h_to = elevation_rows[nr][nc]
                edge_fwd = (cell_from, cell_to)
                edge_rev = (cell_to, cell_from)

                if edge_fwd in building_door_portals or edge_rev in building_door_portals:
                    edge_type = "DOOR"
                elif cell_from in all_solid_wall_cells or cell_to in all_solid_wall_cells:
                    edge_type = "WALL"
                elif (cell_from in all_door_cells and cell_to in all_wall_ring_cells) or \
                     (cell_to in all_door_cells and cell_from in all_wall_ring_cells):
                    edge_type = "WALL"
                elif cell_from in water_cells_set or cell_to in water_cells_set:
                    edge_type = "WATER"
                elif cell_from in ditch_cells_set or cell_to in ditch_cells_set:
                    edge_type = "DITCH"
                elif edge_fwd in authored_cliffs_set or edge_rev in authored_cliffs_set:
                    edge_type = "CLIFF_AUTHORED"
                else:
                    diff = abs(h_from - h_to)
                    if diff >= 2:
                        edge_type = "CLIFF"
                    elif diff == 1:
                        if cell_from in is_terrain and cell_to in is_terrain:
                            edge_type = "WALK_SLOPE"
                        else:
                            edge_type = "PIT_RIM"
                    else:
                        edge_type = "WALK"

                edges.append({
                    "from": cell(cell_from[0], cell_from[1]),
                    "to": cell(cell_to[0], cell_to[1]),
                    "type": edge_type
                })

    # 10. 道具清單 (props)
    raw_props = [
        # 礦坑口前與山壁 (H4/H2)
        {
            "id": "mine_watchtower",
            "cell": cell(1, 1),
            "footprint": [4, 2],
            "elevation": 4,
            "sprite": "watchtower"
        },
        {
            "id": "mine_rock_pile_1",
            "cell": cell(5, 2),
            "footprint": [1, 1],
            "elevation": 4,
            "sprite": "rock_1"
        },
        {
            "id": "mine_rock_pile_2",
            "cell": cell(6, 2),
            "footprint": [1, 1],
            "elevation": 4,
            "sprite": "rock_2"
        },
        {
            "id": "mine_ore_box",
            "cell": cell(5, 3),
            "footprint": [1, 1],
            "elevation": 4,
            "sprite": "crate"
        },

        # 中央水井廣場 (H0)
        {
            "id": "central_well",
            "cell": cell(19, 23),
            "footprint": [2, 2],
            "elevation": 0,
            "sprite": "well"
        },

        # 監督公署門口 (門在 cols 13..14, row 21；門前 row 22 cols 13..14 不壓)
        {
            "id": "office_crate",
            "cell": cell(11, 22),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "crate"
        },
        {
            "id": "office_barrel",
            "cell": cell(12, 22),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "barrel"
        },

        # 大酒館門口 (門在 cols 25..26, row 21；門前 row 22 cols 25..26 不壓)
        {
            "id": "tavern_barrel_1",
            "cell": cell(23, 22),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "barrel"
        },
        {
            "id": "tavern_barrel_2",
            "cell": cell(24, 22),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "barrel"
        },
        {
            "id": "tavern_jar",
            "cell": cell(27, 22),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "jar"
        },

        # 精煉鍛造坊門口 (門在 cols 13..14, row 31；門前 row 32 cols 13..14 不壓)
        {
            "id": "forge_anvil",
            "cell": cell(11, 32),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "anvil"
        },
        {
            "id": "forge_coal",
            "cell": cell(12, 32),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "rock_1"
        },
        {
            "id": "forge_furnace",
            "cell": cell(15, 32),
            "footprint": [2, 2],
            "elevation": 0,
            "sprite": "furnace"
        },

        # 物資雜貨行門口 (門在 cols 24..25, row 30；門前 row 31 cols 24..25 不壓)
        {
            "id": "supply_crate_1",
            "cell": cell(22, 31),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "crate"
        },
        {
            "id": "supply_sack_1",
            "cell": cell(23, 31),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "sack"
        },
        {
            "id": "supply_crate_2",
            "cell": cell(26, 31),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "crate"
        },

        # 工具庫門口 (門在 cols 24..25, row 40；門前 row 41 cols 24..25 不壓)
        {
            "id": "depot_crate",
            "cell": cell(23, 41),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "crate"
        },
        {
            "id": "depot_sack",
            "cell": cell(26, 41),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "sack"
        },

        # 礦工居所 1 門口 (門在 cols 24..25, row 10；門前 row 11 cols 24..25 不壓)
        {
            "id": "cabin1_woodpile",
            "cell": cell(23, 11),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "woodpile"
        },
        {
            "id": "cabin1_sack",
            "cell": cell(26, 11),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "sack"
        },

        # 礦工居所 2 門口 (門在 cols 12..13, row 40；門前 row 41 cols 12..13 不壓)
        {
            "id": "cabin2_woodpile",
            "cell": cell(11, 41),
            "footprint": [1, 1],
            "elevation": 0,
            "sprite": "woodpile"
        },
        {
            "id": "cabin2_sack",
            "cell": cell(14, 41),
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
    # props 防火牆斷言：不堵門、不壓水、不壓溝
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

        # 不堵門
        overlap_door = prop_footprint & door_front_cells
        assert not overlap_door, (
            f"斷言失敗！道具 '{p_id}' 腳印格 {overlap_door} 與建築門前一格重疊！"
        )
        # 不壓水
        overlap_water = prop_footprint & water_cells_set
        assert not overlap_water, (
            f"斷言失敗！道具 '{p_id}' 腳印格 {overlap_water} 與水面格重疊！"
        )
        # 不壓溝
        overlap_ditch = prop_footprint & ditch_cells_set
        assert not overlap_ditch, (
            f"斷言失敗！道具 '{p_id}' 腳印格 {overlap_ditch} 與溝渠格重疊！"
        )

    # 11. 演員固定裝置 (actors_fixture): 7 位演員
    actors_fixture = [
        {
            "id": "arya",
            "label": "主",
            "color": [56, 189, 248],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(19, 21, 0)]
        },
        {
            "id": "overseer",
            "label": "監",
            "color": [234, 179, 8],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(15, 22, 0)]
        },
        {
            "id": "foreman",
            "label": "領",
            "color": [249, 115, 22],
            "indoor": None,
            "on_building": "refinery_forge",
            # 精煉鍛造坊平頂 DECK (world col 14, row 29, elevation 3，位於 refinery_forge origin (10, 26))
            "cells": [cell_3d(14, 29, 3)]
        },
        {
            "id": "miner_panner",
            "label": "淘",
            "color": [34, 197, 94],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(27, 13, 0)]
        },
        {
            "id": "hauler",
            "label": "運",
            "color": [168, 85, 247],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(18, 32, 0)]
        },
        {
            "id": "miner_guard",
            "label": "衛",
            "color": [239, 68, 68],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(8, 14, 2)]
        },
        {
            "id": "blacksmith",
            "label": "匠",
            "color": [245, 158, 11],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(16, 33, 0)]
        }
    ]

    # 組裝完整 Chunk Spec 字典
    spec = {
        "chunk_id": "chunk_0_1_valley_mine",
        "grid": {
            "cols": 50,
            "rows": 50,
            "cell_px": 32,
            "world_origin": [0, 1]
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

    # 輸出到 reports/chunk_0_1_spec.json
    output_dir = os.path.abspath(os.path.join(script_dir, "..", "reports"))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "chunk_0_1_spec.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)

    print(f"✅ 成功生成 chunk_0_1_spec.json 於：{output_path}")

if __name__ == "__main__":
    build_chunk_spec()
