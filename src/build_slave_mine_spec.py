#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_slave_mine_spec.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: 極致美學 AI 軟體架構師
Target: 將 48×48「真·奴隸礦坑」(The Grand Slavers' Quarry) 編譯為完全符合幾何規範與空間邏輯的機器可讀 spec。
Rules Alignment:
  - 空間主題：奴隸露天巨坑採石＋殘酷暴力看管設施＋全套工業運輸鐵軌閉環
  - 尺寸：48×48 (1536×1536 px，寬闊飽滿，杜絕擠壓，機能率 > 75%)
  - 核心修復：
      1. 哨塔高腳 100% 踩在 H3 平整實地上，四周留有 1~4 格平坦台地，0 懸空踩崖！
      2. 狙擊守衛演員精確站立於哨塔中央頂層甲板，0 浮空！
      3. 鍛造坊面寬擴大至 9 格，鐵鎚招牌移至 col 8 空白實牆區，100% 杜絕遮擋門窗！
      4. 實裝露天鐵籠群、雙刑柱行刑台、採礦鐵軌網絡與翻斗礦車（空車+滿載赤鐵車）！
------------------------------------------------------------
"""

import os
import sys
import json
from collections import deque
from PIL import Image

def cell(col, row):
    """spec 座標標準格式：[col, row] = [x, y]"""
    return [int(col), int(row)]

def cell_3d(col, row, elev):
    """3D 座標標準格式：[col, row, elevation]"""
    return [int(col), int(row), int(elev)]

COLS = 48
ROWS = 48

def generate_elevation_and_layout():
    """
    建構 48×48 奴隸礦坑高程矩陣與地表屬性
    高程分佈：
      - 北部大台地 (H2)：Rows 2..12, Cols 4..27
      - 西北最高點哨塔基地 (H3)：Rows 2..8, Cols 4..13
      - 巡邏斜坡 (WALK_SLOPE, H2 -> H1 -> H0)：Rows 11..12, Cols 25..27
      - 階梯開採深坑 (H-1)：Rows 18..38, Cols 20..44
      - 赤鐵深層採掘面 (H-2)：Rows 22..34, Cols 25..40
      - 幽暗核心礦脈深井 (H-3)：Rows 26..30, Cols 29..36
      - 採礦運輸斜坡 1 (WALK_SLOPE, H0 -> H-1)：Rows 20..22, Cols 18..19
      - 採礦運輸斜坡 2 (WALK_SLOPE, H-1 -> H-2)：Rows 26..28, Cols 23..24
      - 其他地面 (H0)：基準平地
    """
    elev = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    slope_cells = set()

    # 1. 北部大台地 H2
    for r in range(2, 13):
        for c in range(4, 28):
            elev[r][c] = 2

    # 2. 西北角拔高 H3 (哨塔專屬座基，給予足夠周邊平坦實地)
    for r in range(2, 9):
        for c in range(4, 14):
            elev[r][c] = 3

    # 3. 北部台地巡邏坡道 (H2 -> H1 -> H0)
    elev[11][26] = 1
    elev[11][27] = 1
    elev[12][26] = 1
    elev[12][27] = 1
    slope_cells.add((26, 11))
    slope_cells.add((27, 11))
    slope_cells.add((26, 12))
    slope_cells.add((27, 12))

    # 4. 中央露天採石坑 (H-1)
    for r in range(18, 39):
        for c in range(20, 45):
            elev[r][c] = -1

    # 5. 赤鐵深層採掘面 (H-2)
    for r in range(22, 35):
        for c in range(25, 41):
            elev[r][c] = -2

    # 6. 幽暗核心礦脈深井 (H-3)
    for r in range(26, 31):
        for c in range(29, 37):
            elev[r][c] = -3

    # 7. 採礦運輸斜坡道 1 (H0 -> H-1)
    for r in range(20, 23):
        elev[r][18] = 0
        elev[r][19] = -1
        slope_cells.add((18, r))
        slope_cells.add((19, r))

    # 8. 採礦運輸斜坡道 2 (H-1 -> H-2)
    for r in range(26, 29):
        elev[r][23] = -1
        elev[r][24] = -2
        slope_cells.add((23, r))
        slope_cells.add((24, r))

    return elev, slope_cells

def build_slave_mine_spec():
    elevation_rows, slope_cells = generate_elevation_and_layout()

    # --------------------------------------------------------
    # 1. 建築物定義（4 棟功能各異、空間錯落的實體建築）
    # --------------------------------------------------------
    buildings = [
        # (1) 奴隸牢房 (Stone Barracks) - 厚石封閉牢獄
        {
            "building_id": "slave_barracks",
            "label": "奴隸囚牢",
            "name": "奴隸石造囚牢",
            "style": "stone",
            "footprint": {
                "origin": cell(4, 28),
                "cols": 7,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(3, 4) # world (7, 32), 南向大門開向露天刑場
            ],
            "door_height_units": 2.0,
            "stair": None,
            "roof": {
                "walkable": False,
                "elevation": 3,
                "kind": "ROOF_CAP"
            },
            "windows_local": {
                "0": [1, 5]
            },
            "facade": []
        },
        # (2) 警衛守備哨 (Guard Station) - 土磚卡哨
        {
            "building_id": "guard_station",
            "label": "守衛哨",
            "name": "營區守備哨",
            "style": "adobe",
            "footprint": {
                "origin": cell(4, 15),
                "cols": 5,
                "rows": 4
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(2, 3) # world (6, 18), 南門朝向營區大道
            ],
            "door_height_units": 2.0,
            "stair": None,
            "roof": {
                "walkable": False,
                "elevation": 3,
                "kind": "ROOF_CAP"
            },
            "windows_local": {
                "0": [0, 4]
            },
            "facade": []
        },
        # (3) 黑鐵鍛造坊 (Blacksmith Forge) - 面寬擴大至 9 格，徹底解放門窗與招牌空間！
        {
            "building_id": "blacksmith_forge",
            "label": "黑鐵鍛造坊",
            "name": "黑鐵鍛造坊",
            "style": "stone",
            "footprint": {
                "origin": cell(28, 4),
                "cols": 9,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 4.0,
            "height_units": 4.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(4, 4) # world (32, 8), 南門朝向露天熔爐坪
            ],
            "door_height_units": 2.0,
            "stair": None,
            "roof": {
                "walkable": False,
                "elevation": 4,
                "kind": "ROOF_CAP"
            },
            "windows_local": {
                "0": [1, 7] # 窗開在 col 1 與 col 7
            },
            "facade": [
                # 鐵鎚招牌：掛在南牆 col 8 (world 36, 8)。左側是 col 7 的窗，門在 col 4，招牌向右有足夠空白實牆，100% 0 遮擋門窗！
                {
                    "img_id": "forge_hammer_sign",
                    "kind": "wall",
                    "col": 8,
                    "row": 4,
                    "cell": 8,
                    "h": 0.5,
                    "sprite": "sign_hammer",
                    "sprite_px": [72, 70]
                }
            ]
        },
        # (4) 礦石裝卸貨棧 (Ore Storehouse) - 原木粗構倉庫
        {
            "building_id": "ore_storehouse",
            "label": "礦石貨棧",
            "name": "精選礦石貨棧",
            "style": "timber",
            "footprint": {
                "origin": cell(30, 40),
                "cols": 8,
                "rows": 5
            },
            "base_elevation": 0,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(3, 4) # world (33, 44)
            ],
            "door_height_units": 2.0,
            "stair": None,
            "roof": {
                "walkable": False,
                "elevation": 3,
                "kind": "ROOF_CAP"
            },
            "windows_local": {
                "0": [1, 6]
            },
            "facade": []
        }
    ]

    # 動態讀取 keluo_props_sprites.json 接死尺寸
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sprites_json_candidates = [
        os.path.abspath(os.path.join(script_dir, "..", "reports", "keluo_props_sprites.json")),
        os.path.abspath(os.path.join(script_dir, "reports", "keluo_props_sprites.json")),
        "C:/GPTfile/godot/Nono's Little Base/nono_google_cloud/nono-tactical-tilemap-engine/reports/keluo_props_sprites.json"
    ]
    props_sprites_table = {}
    for sp_candidate in sprites_json_candidates:
        if os.path.exists(sp_candidate):
            try:
                with open(sp_candidate, "r", encoding="utf-8") as f_sp:
                    props_sprites_table = json.load(f_sp)
                break
            except Exception:
                pass

    if props_sprites_table:
        for b in buildings:
            for f in b.get("facade", []):
                sp_name = f.get("sprite")
                if sp_name in props_sprites_table:
                    sp_box = props_sprites_table[sp_name]
                    if len(sp_box) >= 4:
                        f["sprite_px"] = [sp_box[2], sp_box[3]]

    # 計算所有建築腳印格點
    all_footprint_cells = set()
    door_front_cells = set()
    for b in buildings:
        ox, oy = b["footprint"]["origin"]
        w = b["footprint"]["cols"]
        h = b["footprint"]["rows"]
        for r in range(h):
            for c in range(w):
                all_footprint_cells.add((ox + c, oy + r))
        for dc, dr in b["doors_local"]:
            door_world = (ox + dc, oy + dr)
            door_front_cells.add((door_world[0], door_world[1] + 1))

    # --------------------------------------------------------
    # 2. 道路 (Road) 與 廣場 (Plaza) 拓撲
    # --------------------------------------------------------
    road_cells_set = set()
    # 主幹道 (Rows 18..44, Cols 13..16)
    for r in range(18, 45):
        for c in range(13, 17):
            road_cells_set.add((c, r))
    # 守備哨前橫道 (Rows 18..20, Cols 8..14)
    for r in range(18, 21):
        for c in range(8, 15):
            road_cells_set.add((c, r))
    # 通往鍛造坊斜坡大道 (Rows 12..18, Cols 24..28)
    for r in range(12, 19):
        for c in range(24, 29):
            road_cells_set.add((c, r))
    # 採礦運礦斜坡道 1 (Rows 20..22, Cols 17..20)
    for r in range(20, 23):
        for c in range(17, 21):
            road_cells_set.add((c, r))
    # 採礦運礦斜坡道 2 (Rows 26..28, Cols 22..25)
    for r in range(26, 29):
        for c in range(22, 26):
            road_cells_set.add((c, r))

    # 廣場 (Plaza)：鍛造作業坪、貨棧裝卸棧坪、中央刑場點名坪
    plaza_cells_set = set()
    # 鍛造作業坪 (Rows 9..14, Cols 26..38)
    for r in range(9, 15):
        for c in range(26, 39):
            plaza_cells_set.add((c, r))
    # 貨棧裝卸棧坪 (Rows 39..46, Cols 28..32)
    for r in range(39, 47):
        for c in range(28, 33):
            plaza_cells_set.add((c, r))
    # 奴隸集結刑場點名坪 (Rows 28..36, Cols 11..16)
    for r in range(28, 37):
        for c in range(11, 17):
            plaza_cells_set.add((c, r))

    # 露天採石坑底 (Pit Floor)：所有高程 < 0 的格點
    pit_floor_cells_set = set()
    for r in range(ROWS):
        for c in range(COLS):
            if elevation_rows[r][c] < 0:
                pit_floor_cells_set.add((c, r))

    # 排除建築腳印
    road_cells_set -= all_footprint_cells
    plaza_cells_set -= all_footprint_cells
    pit_floor_cells_set -= all_footprint_cells

    # 優先級消歧：pit_floor > road > plaza
    road_cells_set -= pit_floor_cells_set
    plaza_cells_set -= pit_floor_cells_set
    plaza_cells_set -= road_cells_set

    road_cells = [cell(c, r) for c, r in sorted(road_cells_set)]
    plaza_cells = [cell(c, r) for c, r in sorted(plaza_cells_set)]

    # --------------------------------------------------------
    # 3. Surfaces 連通分量建構（嚴格保證 100% 覆蓋非建築格）
    # --------------------------------------------------------
    surfaces = []
    surf_idx = 1
    visited = set()

    for r in range(ROWS):
        for c in range(COLS):
            if (c, r) in all_footprint_cells:
                continue
            if (c, r) in visited:
                continue

            h = elevation_rows[r][c]
            if (c, r) in road_cells_set:
                mat = "road"
                tile = ["kenshi", 0, 1]
            elif (c, r) in plaza_cells_set:
                mat = "plaza"
                tile = ["kenshi", 4, 0]
            elif (c, r) in pit_floor_cells_set:
                mat = "pit_floor"
                tile = ["kenshi", 9, 3]
            else:
                mat = "sand"
                if h == 3:
                    tile = ["kenshi", 2, 0]
                elif h in (1, 2):
                    tile = ["kenshi", 1, 0]
                else:
                    tile = ["kenshi", 0, 0]

            comp_cells = []
            queue = deque([(c, r)])
            visited.add((c, r))

            while queue:
                qc, qr = queue.popleft()
                comp_cells.append(cell(qc, qr))

                for dc, dr in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nc, nr = qc + dc, qr + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS:
                        if (nc, nr) not in visited and (nc, nr) not in all_footprint_cells:
                            nh = elevation_rows[nr][nc]
                            if (nc, nr) in road_cells_set:
                                nmat = "road"
                            elif (nc, nr) in plaza_cells_set:
                                nmat = "plaza"
                            elif (nc, nr) in pit_floor_cells_set:
                                nmat = "pit_floor"
                            else:
                                nmat = "sand"

                            if nh == h and nmat == mat:
                                visited.add((nc, nr))
                                queue.append((nc, nr))

            surfaces.append({
                "surface_id": f"s_{surf_idx:03d}_{mat}_h{h}",
                "elevation": h,
                "material": mat,
                "tile": tile,
                "cells": comp_cells
            })
            surf_idx += 1

    # --------------------------------------------------------
    # 4. 拓撲邊緣 Edges (Cliff & Slope)
    # --------------------------------------------------------
    edges = []
    edge_idx = 1

    # 水平邊 (EAST)
    for r in range(ROWS):
        for c in range(COLS - 1):
            h1 = elevation_rows[r][c]
            h2 = elevation_rows[r][c + 1]
            if h1 != h2:
                is_slope = (c, r) in slope_cells and (c + 1, r) in slope_cells
                edges.append({
                    "edge_id": f"edge_h_{edge_idx}",
                    "cell_a": cell(c, r),
                    "cell_b": cell(c + 1, r),
                    "direction": "EAST",
                    "elev_a": h1,
                    "elev_b": h2,
                    "diff": h1 - h2,
                    "kind": "WALK_SLOPE" if is_slope else "CLIFF"
                })
                edge_idx += 1

    # 垂直邊 (SOUTH)
    for r in range(ROWS - 1):
        for c in range(COLS):
            h1 = elevation_rows[r][c]
            h2 = elevation_rows[r + 1][c]
            if h1 != h2:
                is_slope = (c, r) in slope_cells and (c, r + 1) in slope_cells
                edges.append({
                    "edge_id": f"edge_v_{edge_idx}",
                    "cell_a": cell(c, r),
                    "cell_b": cell(c, r + 1),
                    "direction": "SOUTH",
                    "elev_a": h1,
                    "elev_b": h2,
                    "diff": h1 - h2,
                    "kind": "WALK_SLOPE" if is_slope else "CLIFF"
                })
                edge_idx += 1

    # --------------------------------------------------------
    # 5. 道具定義 (Props) - 充滿奴隸礦坑細節、鐵籠、刑柱、礦車、鐵軌
    # --------------------------------------------------------
    props = [
        # (1) 西北 H3 拔高台地巨型看守哨塔 (四腳四周留足 2~4 格平整石地，0 懸空踩崖！)
        {
            "id": "watchtower_nw",
            "sprite": "watchtower",
            "cell": cell(6, 3),
            "footprint": [3, 3],
            "elevation": 3
        },
        # (2) 北部 H2 高台奴隸主游牧大帳
        {
            "id": "overseer_tent",
            "sprite": "tent",
            "cell": cell(16, 4),
            "footprint": [3, 2],
            "elevation": 2
        },
        # (3) 高台大帳前營火與戰旗
        {
            "id": "camp_fire",
            "sprite": "campfire",
            "cell": cell(20, 5),
            "footprint": [1, 1],
            "elevation": 2
        },
        {
            "id": "flag_overseer",
            "sprite": "flag_rust",
            "cell": cell(14, 4),
            "footprint": [1, 1],
            "elevation": 2
        },
        {
            "id": "wine_barrel_camp",
            "sprite": "barrel",
            "cell": cell(15, 6),
            "footprint": [1, 1],
            "elevation": 2
        },

        # (4) 露天鐵籠排 (關押帶刺奴隸，在牢房前方與點名坪旁)
        {
            "id": "iron_cage_1",
            "sprite": "iron_cage",
            "cell": cell(12, 29),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "iron_cage_2",
            "sprite": "iron_cage",
            "cell": cell(12, 32),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "iron_cage_3",
            "sprite": "iron_cage",
            "cell": cell(12, 35),
            "footprint": [1, 1],
            "elevation": 0
        },

        # (5) 點名刑場中央雙刑柱 (行刑鞭笞柱)
        {
            "id": "pillory_post_1",
            "sprite": "pillory_post",
            "cell": cell(15, 30),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "pillory_post_2",
            "sprite": "pillory_post",
            "cell": cell(15, 33),
            "footprint": [1, 1],
            "elevation": 0
        },

        # (6) 採礦鐵軌路線 (Mine Rails)
        # 地面軌道連接至貨棧
        {
            "id": "rail_ground_1",
            "sprite": "mine_rail_v",
            "cell": cell(18, 23),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "rail_ground_2",
            "sprite": "mine_rail_v",
            "cell": cell(18, 24),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "rail_ground_3",
            "sprite": "mine_rail_v",
            "cell": cell(18, 25),
            "footprint": [1, 1],
            "elevation": 0
        },
        # 斜坡軌道進入 H-1
        {
            "id": "rail_slope_1",
            "sprite": "mine_rail_h",
            "cell": cell(19, 21),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "rail_slope_2",
            "sprite": "mine_rail_h",
            "cell": cell(20, 21),
            "footprint": [1, 1],
            "elevation": -1
        },
        {
            "id": "rail_slope_3",
            "sprite": "mine_rail_h",
            "cell": cell(21, 21),
            "footprint": [1, 1],
            "elevation": -1
        },
        # 坑底軌道進入 H-2
        {
            "id": "rail_pit_1",
            "sprite": "mine_rail_h",
            "cell": cell(22, 27),
            "footprint": [1, 1],
            "elevation": -1
        },
        {
            "id": "rail_pit_2",
            "sprite": "mine_rail_h",
            "cell": cell(23, 27),
            "footprint": [1, 1],
            "elevation": -1
        },
        {
            "id": "rail_pit_3",
            "sprite": "mine_rail_h",
            "cell": cell(24, 27),
            "footprint": [1, 1],
            "elevation": -2
        },

        # (7) 翻斗礦車 (Minecarts)
        {
            "id": "minecart_ore_ground",
            "sprite": "minecart_ore",
            "cell": cell(18, 20),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "minecart_ore_slope",
            "sprite": "minecart_ore",
            "cell": cell(21, 20),
            "footprint": [1, 1],
            "elevation": -1
        },
        {
            "id": "minecart_empty_pit",
            "sprite": "minecart_empty",
            "cell": cell(25, 27),
            "footprint": [1, 1],
            "elevation": -2
        },
        {
            "id": "minecart_empty_depot",
            "sprite": "minecart_empty",
            "cell": cell(29, 42),
            "footprint": [1, 1],
            "elevation": 0
        },

        # (8) 露天冶煉雙熔爐與黑鐵鍛造坊作業區 (H0)
        {
            "id": "smelting_furnace_1",
            "sprite": "furnace",
            "cell": cell(30, 11),
            "footprint": [2, 2],
            "elevation": 0
        },
        {
            "id": "smelting_furnace_2",
            "sprite": "furnace",
            "cell": cell(34, 11),
            "footprint": [2, 2],
            "elevation": 0
        },
        {
            "id": "cooling_well",
            "sprite": "well",
            "cell": cell(27, 11),
            "footprint": [2, 2],
            "elevation": 0
        },
        {
            "id": "anvil_forge",
            "sprite": "anvil",
            "cell": cell(32, 13),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "charcoal_woodpile_1",
            "sprite": "woodpile",
            "cell": cell(38, 10),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "charcoal_woodpile_2",
            "sprite": "woodpile",
            "cell": cell(38, 11),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "water_barrel_forge",
            "sprite": "barrel",
            "cell": cell(28, 13),
            "footprint": [1, 1],
            "elevation": 0
        },

        # (9) 礦石裝卸貨棧儲存箱與麻袋
        {
            "id": "ore_crate_depot_1",
            "sprite": "crate",
            "cell": cell(28, 39),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "ore_crate_depot_2",
            "sprite": "crate",
            "cell": cell(29, 39),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "ore_sack_depot_1",
            "sprite": "sack",
            "cell": cell(30, 38),
            "footprint": [1, 1],
            "elevation": 0
        },
        {
            "id": "ore_sack_depot_2",
            "sprite": "sack",
            "cell": cell(31, 38),
            "footprint": [1, 1],
            "elevation": 0
        },

        # (10) 坑底採石面散佈原石巨塊與作業工具
        {
            "id": "quarry_rock_1",
            "sprite": "rock_1",
            "cell": cell(24, 23),
            "footprint": [1, 1],
            "elevation": -2
        },
        {
            "id": "quarry_rock_2",
            "sprite": "rock_2",
            "cell": cell(27, 24),
            "footprint": [1, 1],
            "elevation": -2
        },
        {
            "id": "quarry_rock_3",
            "sprite": "rock_3",
            "cell": cell(30, 25),
            "footprint": [1, 1],
            "elevation": -2
        },
        {
            "id": "quarry_rock_4",
            "sprite": "rock_1",
            "cell": cell(32, 28),
            "footprint": [1, 1],
            "elevation": -3
        },
        {
            "id": "quarry_rock_5",
            "sprite": "rock_2",
            "cell": cell(34, 29),
            "footprint": [1, 1],
            "elevation": -3
        },
        {
            "id": "anvil_pit_worker",
            "sprite": "anvil",
            "cell": cell(26, 25),
            "footprint": [1, 1],
            "elevation": -2
        },
        {
            "id": "jar_pit_water",
            "sprite": "jar",
            "cell": cell(25, 25),
            "footprint": [1, 1],
            "elevation": -2
        },

        # (11) 荒漠枯樹
        {
            "id": "dead_tree_nw",
            "sprite": "dead_tree",
            "cell": cell(10, 2),
            "footprint": [2, 2],
            "elevation": 3
        },
        {
            "id": "dead_tree_west",
            "sprite": "dead_tree",
            "cell": cell(1, 20),
            "footprint": [2, 2],
            "elevation": 0
        },
        {
            "id": "dead_tree_east",
            "sprite": "dead_tree",
            "cell": cell(44, 15),
            "footprint": [2, 2],
            "elevation": 0
        }
    ]

    # --------------------------------------------------------
    # 6. 演員配置 (Actors) - 修正狙擊手座標，杜絕懸空
    # --------------------------------------------------------
    actors_fixture = [
        {
            "id": "arya",
            "label": "主",
            "color": [56, 189, 248],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(14, 38, 0)] # 抵達南側主幹道
        },
        {
            "id": "overseer",
            "label": "監",
            "color": [234, 179, 8],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(17, 7, 2)] # 北部高台巡視
        },
        {
            "id": "sniper_guard",
            "label": "哨",
            "color": [239, 68, 68],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(7, 4, 3)] # 哨塔頂層中央！100% 踩實！
        },
        {
            "id": "pit_slave_1",
            "label": "奴",
            "color": [156, 163, 175],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(31, 28, -3)] # 核心礦脈深掘奴隸
        },
        {
            "id": "pit_slave_2",
            "label": "運",
            "color": [148, 163, 184],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(21, 21, -1)] # 斜坡推車奴隸
        },
        {
            "id": "blacksmith",
            "label": "匠",
            "color": [245, 158, 11],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(32, 12, 0)] # 鍛造鐵砧前打鐵匠
        },
        {
            "id": "patrol_guard",
            "label": "衛",
            "color": [220, 38, 38],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(13, 31, 0)] # 刑場看守巡邏衛兵
        }
    ]

    # --------------------------------------------------------
    # 7. 組裝全規格 dictionary
    # --------------------------------------------------------
    spec = {
        "chunk_id": "chunk_0_1_grand_slavers_quarry",
        "grid": {
            "cols": COLS,
            "rows": ROWS,
            "cell_px": 32,
            "world_origin": [0, 1]
        },
        "projection_presentation_only": {
            "rise_ratio": 0.72,
            "side_shift_ratio": 0.12,
            "side_spread_cells": 6
        },
        "bridge_cells": [],
        "authored_cliffs": [],
        "elevation_rows": elevation_rows,
        "road_cells": road_cells,
        "plaza_cells": plaza_cells,
        "field_cells": [],
        "ditch_cells": [],
        "mud_cells": [],
        "water_cells": [],
        "water_bodies": [],
        "surfaces": surfaces,
        "edges": edges,
        "buildings": buildings,
        "props": props,
        "actors_fixture": actors_fixture,
        "tiles": {
            "sand": [
                ["kenshi", 0, 0],
                ["kenshi", 1, 0],
                ["kenshi", 2, 0],
                ["kenshi", 3, 0]
            ],
            "plaza": ["kenshi", 4, 0],
            "field": ["kenshi", 5, 0],
            "cliff_face": ["kenshi", 6, 0],
            "cliff_face_base": ["kenshi", 7, 0],
            "cliff_side": ["kenshi", 6, 0],
            "pit_floor": ["kenshi", 9, 3],
            "pit_wall": ["kenshi", 10, 3],
            "pit_wall_side": ["kenshi", 10, 3],
            "face_stone": ["kenshi", 1, 2],
            "face_water": ["kenshi", 8, 3],
            "water": ["kenshi", 7, 3],
            "water_deep": ["kenshi", 8, 3],
            "bridge_top": ["kenshi", 11, 3],
            "ditch": ["kenshi", 12, 3],
            "bridge_face": ["kenshi", 0, 2],
            "cut_plane": ["kenshi", 10, 0],
            "wood_floor": ["kenshi", 11, 0],
            "wall_cap": ["kenshi", 12, 0],
            "step": ["kenshi", 13, 0],
            "roof_deck": ["kenshi", 14, 0],
            "door_2u": ["kenshi", 15, 0, 32, 46]
        },
        "styles": {
            "timber": {
                "wall": ["kenshi", 0, 2],
                "base": False,
                "door": ["kenshi", 15, 0, 32, 46],
                "window": ["kenshi", 13, 2, 32, 24],
                "roof": {"all": ["kenshi", 3, 2]},
                "cap": ["kenshi", 6, 2],
                "floor": ["kenshi", 11, 0],
                "step": ["kenshi", 13, 0],
                "deck": ["kenshi", 14, 0],
                "eave": [60, 30, 20]
            },
            "stone": {
                "wall": ["kenshi", 1, 2],
                "base": False,
                "door": ["kenshi", 11, 2, 32, 46],
                "window": ["kenshi", 14, 2, 32, 24],
                "roof": {"all": ["kenshi", 4, 2]},
                "cap": ["kenshi", 7, 2],
                "floor": ["kenshi", 9, 2],
                "step": ["kenshi", 3, 3],
                "deck": ["kenshi", 4, 3],
                "eave": [60, 56, 46]
            },
            "adobe": {
                "wall": ["kenshi", 2, 2],
                "base": False,
                "door": ["kenshi", 12, 2, 32, 46],
                "window": ["kenshi", 15, 2, 32, 24],
                "roof": {"all": ["kenshi", 5, 2]},
                "cap": ["kenshi", 8, 2],
                "floor": ["kenshi", 10, 2],
                "step": ["kenshi", 13, 0],
                "deck": ["kenshi", 5, 3],
                "eave": [120, 92, 44]
            }
        },
        "road_autotile": {str(i): [i, 1] for i in range(16)},
        "ditch_autotile": {str(i): [i, 4] for i in range(16)},
        "atlas_row_h": {
            "kenshi": 48
        },
        "face_crop_y0": {
            "nono,1,4": 0,
            "keluo,12,0": 0,
            "foozle,25,7": 0,
            "kenshi,6,0": 0,
            "kenshi,7,0": 9,
            "kenshi,9,0": 0,
            "kenshi,0,2": 0,
            "kenshi,1,2": 0,
            "kenshi,2,2": 0
        },
        "plateau_tint": {
            "color": [118, 92, 52],
            "alpha": {
                "1": 0.14,
                "2": 0.26,
                "3": 0.38
            }
        }
    }

    # --------------------------------------------------------
    # 8. 驗證幾何斷言 (Strict Assertions)
    # --------------------------------------------------------
    # B 建築腳印高程一致
    for b in buildings:
        bid = b["building_id"]
        ox, oy = b["footprint"]["origin"]
        w, h = b["footprint"]["cols"], b["footprint"]["rows"]
        hs = {elevation_rows[oy + r][ox + c] for r in range(h) for c in range(w)}
        assert hs == {b["base_elevation"]}, f"建築 {bid} 腳印高程不符：{hs} != {b['base_elevation']}"

    # S1 surfaces 覆蓋所有非建築格
    bset = set(all_footprint_cells)
    cell_surf = {}
    for s in surfaces:
        for c in s["cells"]:
            cell_surf[tuple(c)] = s
    missing = [(c, r) for r in range(ROWS) for c in range(COLS) if (c, r) not in bset and (c, r) not in cell_surf]
    assert not missing, f"Surfaces 未覆蓋非建築格：{missing[:5]}"

    # P1 道具不堵門
    prop_overlaps_door = []
    for p in props:
        pc, pr = p["cell"]; pw, ph = p.get("footprint", [1, 1])
        for dy in range(ph):
            for dx in range(pw):
                if (pc + dx, pr + dy) in door_front_cells:
                    prop_overlaps_door.append((p["id"], (pc + dx, pr + dy)))
    assert not prop_overlaps_door, f"道具堵門：{prop_overlaps_door}"

    # P2 道具不壓建築
    prop_overlaps_bld = []
    for p in props:
        pc, pr = p["cell"]; pw, ph = p.get("footprint", [1, 1])
        for dy in range(ph):
            for dx in range(pw):
                if (pc + dx, pr + dy) in bset:
                    prop_overlaps_bld.append((p["id"], (pc + dx, pr + dy)))
    assert not prop_overlaps_bld, f"道具壓建築：{prop_overlaps_bld}"

    # F 門面掛牆物斷言
    for b in buildings:
        H = b["height_units"]
        for f in b.get("facade", []):
            if f.get("kind") == "wall":
                px_h = f.get("sprite_px", [0, 0])[1]
                assert f.get("h", 0) + px_h / 23.04 <= H + 1e-6, f"門面物件超出牆頂：{f}"
                if str(f.get("sprite", "")).startswith("sign"):
                    assert f.get("kind") == "wall", "招牌 kind 必須為 wall"

    # 輸出 spec json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.abspath(os.path.join(script_dir, "..", "reports"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "slave_mine_spec.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)

    print("SUCCESS: Slave mine spec generated successfully.")
    print(f"Dimensions: {COLS}x{ROWS}")
    print(f"Buildings: {len(buildings)}")
    print(f"Surfaces: {len(surfaces)} (100% covered)")
    print(f"Props: {len(props)}")
    print(f"Actors: {len(actors_fixture)}")

if __name__ == "__main__":
    build_slave_mine_spec()
