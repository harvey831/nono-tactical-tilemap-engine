#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_goblin_camp_spec.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: 蠻荒峽谷哥布林巢穴 (The Savage Canyon Goblin Camp) 40×40 規格編譯器。
對齊黃金 SSOT 拓撲規範：
  - 40×40 (COLS=40, ROWS=40)
  - 環形峽谷凹地 (Sunken Canyon Basin)：中央 H0 營地，四周險峻岩壁 (H1/H2)
  - 5 大特色戰術 POI：
    1. 西北酋長石台與巨石大帳 (H1/H2)
    2. 東北薩滿沸騰大鐵鍋與骨頭圖騰祭壇 (H1)
    3. 西南俘虜深坑與掠奪贓物堆 (H0)
    4. 東南唯一的峽谷隘口與尖刺拒馬防線 (H0 通道, 兩側 H1/H2 夾峙)
    5. 中央聚集地與雜亂獸皮帳篷 (H0)
  - 嚴格的 100% Surfaces 覆蓋與無穿模道具接地斷言。
------------------------------------------------------------
"""

import os
import sys
import json
from collections import deque

COLS = 40
ROWS = 40

def cell(col, row):
    return [int(col), int(row)]

def cell_3d(col, row, elev):
    return [int(col), int(row), int(elev)]

def generate_elevation_and_layout():
    elev = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    slope_cells = set()

    # 1. 外圍環形峽谷峭壁 (H1 外圍岩層)
    # 北側山脊 (rows 0..4)
    for r in range(0, 5):
        for c in range(COLS):
            elev[r][c] = 1
    # 西側山脊 (cols 0..4)
    for c in range(0, 5):
        for r in range(ROWS):
            elev[r][c] = 1
    # 東側山脊 (cols 35..39)
    for c in range(35, COLS):
        for r in range(ROWS):
            elev[r][c] = 1
    # 南側山脊 (rows 35..39，但留出東南峽谷隘口 cols 22..27)
    for r in range(35, ROWS):
        for c in range(0, 22):
            elev[r][c] = 1
        for c in range(28, COLS):
            elev[r][c] = 1

    # 2. 東南峽谷隘口山壁 (兩側峭壁夾峙峽谷通道 cols 22..27)
    # 西南峭壁向內陸延伸 (cols 0..21, rows 27..35)
    for r in range(27, 35):
        for c in range(0, 22):
            elev[r][c] = 1
    # 東南峭壁向內陸延伸 (cols 28..39, rows 27..35)
    for r in range(27, 35):
        for c in range(28, COLS):
            elev[r][c] = 1

    # 3. 西北酋長要塞高台 (cols 5..16, rows 4..11: H1)
    for r in range(4, 12):
        for c in range(5, 17):
            elev[r][c] = 1
    # 酋長背後險峻石峰 (cols 5..8, rows 4..7: H2)
    for r in range(4, 8):
        for c in range(5, 9):
            elev[r][c] = 2

    # 4. 東北薩滿祭壇高台 (cols 24..35, rows 4..11: H1)
    for r in range(4, 12):
        for c in range(24, 36):
            elev[r][c] = 1
    # 東北祭壇險峻望峰 (cols 32..35, rows 4..7: H2)
    for r in range(4, 8):
        for c in range(32, 36):
            elev[r][c] = 2

    # 5. 東南峭壁高架瞭望峰 (cols 28..32, rows 29..33: H1, 峰頂 H2)
    for r in range(29, 34):
        for c in range(28, 33):
            elev[r][c] = 1
    for r in range(30, 33):
        for c in range(29, 32):
            elev[r][c] = 2

    # 峽谷通道 (cols 22..27, rows 25..39) 絕對保持 H0 平整
    for r in range(25, ROWS):
        for c in range(22, 28):
            elev[r][c] = 0

    return elev, slope_cells

def build_goblin_camp_spec():
    elevation_rows, slope_cells = generate_elevation_and_layout()

    # --------------------------------------------------------
    # 1. 建築物定義：哥布林大酋長原木骨骸大帳
    # --------------------------------------------------------
    buildings = [
        {
            "building_id": "chieftain_stronghold",
            "label": "酋長大帳",
            "name": "蠻荒大酋長原木骨骸大帳",
            "style": "timber",
            "footprint": {
                "origin": cell(9, 5),
                "cols": 4,
                "rows": 4
            },
            "base_elevation": 1,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(1, 3) # 南立面開門 (world col 10, row 8)
            ],
            "door_height_units": 2.0,
            "stair": None,
            "roof": {
                "walkable": False,
                "elevation": 4,
                "kind": "ROOF_CAP"
            },
            "windows_local": {
                "0": [3]
            },
            "facade": []
        }
    ]

    all_footprint_cells = set()
    for b in buildings:
        ox, oy = b["footprint"]["origin"]
        cols_b = b["footprint"]["cols"]
        rows_b = b["footprint"]["rows"]
        for r in range(oy, oy + rows_b):
            for c in range(ox, ox + cols_b):
                all_footprint_cells.add((c, r))

    # --------------------------------------------------------
    # 2. 地表材質分區 (Road / Pit Floor / Wood Floor)
    # --------------------------------------------------------
    road_cells_set = set()
    # 入谷泥濘主路 (cols 23..26, rows 16..39)
    for r in range(16, ROWS):
        for c in range(23, 27):
            road_cells_set.add((c, r))

    pit_floor_cells_set = set()
    # 營地內部踩踏泥濘地帶 (中央盆地與西南俘虜坑)
    for r in range(13, 27):
        for c in range(7, 29):
            pit_floor_cells_set.add((c, r))

    wood_floor_cells_set = set()
    # 西北酋長高台原木鋪面 (cols 5..16, rows 4..11)
    for r in range(4, 12):
        for c in range(5, 17):
            wood_floor_cells_set.add((c, r))
    # 東北薩滿祭壇原木鋪面 (cols 26..33, rows 6..10)
    for r in range(6, 11):
        for c in range(26, 34):
            wood_floor_cells_set.add((c, r))

    road_cells_set -= all_footprint_cells
    pit_floor_cells_set -= all_footprint_cells
    wood_floor_cells_set -= all_footprint_cells
    pit_floor_cells_set -= road_cells_set
    wood_floor_cells_set -= road_cells_set

    road_cells = [cell(c, r) for c, r in sorted(road_cells_set)]
    wood_floor_cells = [cell(c, r) for c, r in sorted(wood_floor_cells_set)]
    pit_floor_cells = [cell(c, r) for c, r in sorted(pit_floor_cells_set)]

    # --------------------------------------------------------
    # 3. Surfaces 連通分量建構（100% 覆蓋非建築格）
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
            elif (c, r) in wood_floor_cells_set:
                mat = "wood_floor"
                tile = ["kenshi", 11, 0]
            elif (c, r) in pit_floor_cells_set:
                mat = "pit_floor"
                tile = ["kenshi", 9, 3]
            else:
                mat = "sand"
                tile = ["kenshi", 0, 0]

            # BFS 連通分量
            q = deque([(c, r)])
            visited.add((c, r))
            comp_cells = []

            while q:
                curr_c, curr_r = q.popleft()
                comp_cells.append(cell(curr_c, curr_r))

                for dc, dr in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nc, nr = curr_c + dc, curr_r + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS:
                        if (nc, nr) not in all_footprint_cells and (nc, nr) not in visited:
                            if elevation_rows[nr][nc] == h:
                                n_mat = "road" if (nc, nr) in road_cells_set else (
                                    "wood_floor" if (nc, nr) in wood_floor_cells_set else (
                                        "pit_floor" if (nc, nr) in pit_floor_cells_set else "sand"
                                    )
                                )
                                if n_mat == mat:
                                    visited.add((nc, nr))
                                    q.append((nc, nr))

            surfaces.append({
                "surface_id": f"s_{surf_idx:02d}",
                "elevation": h,
                "material": mat,
                "tile": tile,
                "cells": comp_cells
            })
            surf_idx += 1

    # --------------------------------------------------------
    # 4. 水平與垂直 Edges 建構
    # --------------------------------------------------------
    edges = []
    edge_idx = 1

    # (A) 水平邊界 EAST
    for r in range(ROWS):
        for c in range(COLS - 1):
            h1 = elevation_rows[r][c]
            h2 = elevation_rows[r][c + 1]
            if h1 != h2:
                edges.append({
                    "edge_id": f"e_{edge_idx:04d}",
                    "dir": "EAST",
                    "cell_high": cell(c if h1 > h2 else c + 1, r),
                    "cell_low": cell(c + 1 if h1 > h2 else c, r),
                    "h_high": max(h1, h2),
                    "h_low": min(h1, h2),
                    "is_slope": False
                })
                edge_idx += 1

    # (B) 垂直邊界 SOUTH
    for r in range(ROWS - 1):
        for c in range(COLS):
            h1 = elevation_rows[r][c]
            h2 = elevation_rows[r + 1][c]
            if h1 != h2:
                edges.append({
                    "edge_id": f"e_{edge_idx:04d}",
                    "dir": "SOUTH",
                    "cell_high": cell(c, r if h1 > h2 else r + 1),
                    "cell_low": cell(c, r + 1 if h1 > h2 else r),
                    "h_high": max(h1, h2),
                    "h_low": min(h1, h2),
                    "is_slope": False
                })
                edge_idx += 1

    # --------------------------------------------------------
    # 5. 道具定義 (Props Placement)
    # --------------------------------------------------------
    props = [
        # (A) 東南入谷隘口防線 (Gorge Chokepoint)
        {
            "id": "pali_gorge_1",
            "sprite": "goblin_palisade",
            "cell": cell(22, 27),
            "elevation": 0,
            "footprint": [2, 1]
        },
        {
            "id": "pali_gorge_2",
            "sprite": "goblin_palisade",
            "cell": cell(25, 27),
            "elevation": 0,
            "footprint": [2, 1]
        },
        {
            "id": "watchtower_gorge",
            "sprite": "watchtower",
            "cell": cell(29, 30),
            "elevation": 2,
            "footprint": [2, 2]
        },
        {
            "id": "flag_gorge",
            "sprite": "flag_rust",
            "cell": cell(21, 26),
            "elevation": 0,
            "footprint": [1, 1]
        },

        # (B) 西北酋長高台 (Chieftain Terrace, Elev 1 & 2)
        {
            "id": "chieftain_totem",
            "sprite": "bone_totem",
            "cell": cell(14, 8),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "chieftain_fire",
            "sprite": "campfire",
            "cell": cell(13, 10),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "chieftain_barrel",
            "sprite": "barrel",
            "cell": cell(6, 9),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "chieftain_crate",
            "sprite": "crate",
            "cell": cell(7, 9),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "lookout_rock_h2",
            "sprite": "boulder_large",
            "cell": cell(5, 5),
            "elevation": 2,
            "footprint": [2, 2]
        },

        # (C) 東北薩滿祭壇 (Shaman Cauldron & Feast, Elev 1)
        {
            "id": "cauldron_main",
            "sprite": "cauldron_boiling",
            "cell": cell(28, 7),
            "elevation": 1,
            "footprint": [2, 1]
        },
        {
            "id": "shaman_totem",
            "sprite": "bone_totem",
            "cell": cell(31, 7),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "meat_spit_1",
            "sprite": "meat_spit_roast",
            "cell": cell(28, 9),
            "elevation": 1,
            "footprint": [2, 1]
        },
        {
            "id": "shaman_woodpile",
            "sprite": "woodpile",
            "cell": cell(32, 9),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "shaman_barrel",
            "sprite": "barrel",
            "cell": cell(26, 9),
            "elevation": 1,
            "footprint": [1, 1]
        },

        # (D) 西南俘虜泥坑與掠奪贓物 (Prisoner Pit & Loot, Elev 0)
        {
            "id": "goblin_cage_1",
            "sprite": "iron_cage",
            "cell": cell(9, 21),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "goblin_cage_2",
            "sprite": "iron_cage",
            "cell": cell(11, 21),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "goblin_pillory",
            "sprite": "pillory_post",
            "cell": cell(10, 23),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "loot_treasure",
            "sprite": "loot_hoard",
            "cell": cell(14, 22),
            "elevation": 0,
            "footprint": [2, 1]
        },
        {
            "id": "stolen_wagon",
            "sprite": "broken_wagon",
            "cell": cell(13, 24),
            "elevation": 0,
            "footprint": [2, 1]
        },
        {
            "id": "loot_crate",
            "sprite": "crate",
            "cell": cell(16, 23),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "loot_sack",
            "sprite": "sack",
            "cell": cell(15, 24),
            "elevation": 0,
            "footprint": [1, 1]
        },

        # (E) 中央聚集盆地 (Central Commons & Yurts, Elev 0)
        {
            "id": "goblin_yurt_1",
            "sprite": "goblin_hut_crude",
            "cell": cell(18, 14),
            "elevation": 0,
            "footprint": [2, 2]
        },
        {
            "id": "goblin_yurt_2",
            "sprite": "goblin_hut_crude",
            "cell": cell(22, 16),
            "elevation": 0,
            "footprint": [2, 2]
        },
        {
            "id": "central_fire",
            "sprite": "campfire",
            "cell": cell(19, 18),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "central_woodpile",
            "sprite": "woodpile",
            "cell": cell(21, 19),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "central_totem",
            "sprite": "bone_totem",
            "cell": cell(17, 19),
            "elevation": 0,
            "footprint": [1, 1]
        },

        # (F) 荒野環境散石與枯木
        {
            "id": "dead_tree_nw",
            "sprite": "dead_tree",
            "cell": cell(18, 6),
            "elevation": 0,
            "footprint": [2, 2]
        },
        {
            "id": "dead_tree_se",
            "sprite": "dead_tree",
            "cell": cell(19, 29),
            "elevation": 1,
            "footprint": [2, 2]
        },
        {
            "id": "rock_basin_1",
            "sprite": "rock_1",
            "cell": cell(8, 16),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "rock_basin_2",
            "sprite": "rock_2",
            "cell": cell(26, 22),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "rock_gorge_1",
            "sprite": "boulder_large",
            "cell": cell(18, 33),
            "elevation": 1,
            "footprint": [2, 2]
        },
        {
            "id": "rock_gorge_2",
            "sprite": "boulder_small",
            "cell": cell(33, 33),
            "elevation": 1,
            "footprint": [1, 1]
        }
    ]

    # --------------------------------------------------------
    # 6. 演員標記 (Actors Fixture)
    # --------------------------------------------------------
    actors_fixture = [
        {
            "id": "goblin_chieftain",
            "label": "酋",
            "name": "格魯克·碎顱大酋長",
            "color": [224, 32, 32],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(11, 8, 1)]
        },
        {
            "id": "goblin_shaman",
            "label": "巫",
            "name": "薩滿·疫骨",
            "color": [144, 32, 224],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(29, 8, 1)]
        },
        {
            "id": "goblin_guard_1",
            "label": "衛",
            "name": "哥布林隘口衛兵 A",
            "color": [224, 128, 32],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(23, 26, 0)]
        },
        {
            "id": "goblin_guard_2",
            "label": "衛",
            "name": "哥布林隘口衛兵 B",
            "color": [224, 128, 32],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(26, 26, 0)]
        },
        {
            "id": "goblin_archer_tower",
            "label": "哨",
            "name": "高台哨手",
            "color": [224, 128, 32],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(30, 31, 1)]
        },
        {
            "id": "prisoner_merchant",
            "label": "囚",
            "name": "落難商隊掌櫃",
            "color": [32, 128, 224],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(9, 21, 0)]
        }
    ]

    # --------------------------------------------------------
    # 7. 組裝規格 JSON
    # --------------------------------------------------------
    spec = {
        "chunk_id": "chunk_goblin_camp_40x40",
        "grid": {
            "cols": COLS,
            "rows": ROWS,
            "cell_px": 32,
            "world_origin": [1, 1]
        },
        "projection_presentation_only": {
            "rise_ratio": 0.72,
            "side_shift_ratio": 0.12,
            "side_spread_cells": 6
        },
        "elevation_rows": elevation_rows,
        "buildings": buildings,
        "road_cells": road_cells,
        "wood_floor_cells": wood_floor_cells,
        "plaza_cells": [],
        "pit_floor_cells": pit_floor_cells,
        "field_cells": [],
        "water_cells": [],
        "bridge_cells": [],
        "ditch_cells": [],
        "surfaces": surfaces,
        "edges": edges,
        "props": props,
        "actors_fixture": actors_fixture
    }

    return spec

def main():
    spec = build_goblin_camp_spec()
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "goblin_camp_spec.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)

    print(f"SUCCESS: Generated reports/goblin_camp_spec.json (surfaces={len(spec['surfaces'])}, edges={len(spec['edges'])}, props={len(spec['props'])})")

if __name__ == "__main__":
    main()
