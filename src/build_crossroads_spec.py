#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_crossroads_spec.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: 荒野十字關卡與戰術開闊空地 (The Wasteland Crossroads) 40×40 規格編譯器。
對齊奴隸礦坑與邊境村落黃金標準：
  - 40×40 (COLS=40, ROWS=40)
  - 高程矩陣 (H0, H1, H2)
  - Surfaces 連通分量建構 (100% 覆蓋非建築格，包含 tile 標籤)
  - 嚴格的水平與垂直 Edges (EAST / SOUTH)
  - 完整的建築規格 (包含 style, wall, door, window, roof)
  - 道具 (id, sprite, cell, footprint, elevation)
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

    # 1. 西北盤查哨站高台 (H1) 與瞭望石台 (H2)
    for r in range(4, 15):
        for c in range(4, 16):
            elev[r][c] = 1
    for r in range(5, 9):
        for c in range(5, 9):
            elev[r][c] = 2

    # 西北坡道：南側向 H0 下滑 (rows 13~14, cols 10~13: H0)
    for c in range(10, 14):
        elev[14][c] = 0
        slope_cells.add((c, 14))

    # 2. 東北商隊營地緩丘 (H1)
    for r in range(5, 14):
        for c in range(27, 36):
            elev[r][c] = 1
    # 東北坡道：西側向主幹道下滑 (cols 27, rows 9~12: H0)
    for r in range(9, 13):
        elev[r][27] = 0
        slope_cells.add((27, r))

    # 3. 東南巨石陣風化平頂岩丘 (H1) 與核心石台 (H2)
    for r in range(24, 38):
        for c in range(24, 38):
            elev[r][c] = 1
    # 核心 H2 巨石台
    for r in range(28, 34):
        for c in range(28, 34):
            elev[r][c] = 2
            
    # 東南坡道：西北側平滑過渡
    elev[24][24] = 0; slope_cells.add((24, 24))
    elev[24][25] = 0; slope_cells.add((25, 24))
    elev[25][24] = 0; slope_cells.add((24, 25))

    # 4. 十字幹道必須維持 100% 平整 H0
    # 東西主幹道 (rows 18~21)
    for r in range(18, 22):
        for c in range(COLS):
            elev[r][c] = 0
    # 南北次幹道 (cols 18~21)
    for c in range(18, 22):
        for r in range(ROWS):
            elev[r][c] = 0

    return elev, slope_cells

def build_crossroads_spec():
    elevation_rows, slope_cells = generate_elevation_and_layout()

    # --------------------------------------------------------
    # 1. 建築物定義：西北盤查木石哨所
    # --------------------------------------------------------
    buildings = [
        {
            "building_id": "guard_outpost",
            "label": "盤查哨所",
            "name": "荒野邊防哨所",
            "style": "stone",
            "footprint": {
                "origin": cell(7, 8),
                "cols": 4,
                "rows": 4
            },
            "base_elevation": 1,
            "floors": 1,
            "units_per_floor": 3.0,
            "height_units": 3.0,
            "wall_ring_thickness": 1,
            "doors_local": [
                cell(1, 3) # 南立面開門 (world col 8, row 11)
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
    # 2. 道路與廣場
    # --------------------------------------------------------
    road_cells_set = set()
    for r in range(18, 22):
        for c in range(COLS):
            road_cells_set.add((c, r))
    for c in range(18, 22):
        for r in range(ROWS):
            road_cells_set.add((c, r))

    plaza_cells_set = set()
    for r in range(6, 14):
        for c in range(6, 15):
            plaza_cells_set.add((c, r))
    for r in range(7, 13):
        for c in range(28, 35):
            plaza_cells_set.add((c, r))

    road_cells_set -= all_footprint_cells
    plaza_cells_set -= all_footprint_cells
    plaza_cells_set -= road_cells_set

    road_cells = [cell(c, r) for c, r in sorted(road_cells_set)]
    plaza_cells = [cell(c, r) for c, r in sorted(plaza_cells_set)]

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
            elif (c, r) in plaza_cells_set:
                mat = "plaza"
                tile = ["kenshi", 4, 0]
            else:
                mat = "sand"
                if h == 2:
                    tile = ["kenshi", 1, 0]
                elif h == 1:
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

    # 驗證覆蓋
    total_surf_cells = sum(len(s["cells"]) for s in surfaces)
    assert total_surf_cells == (COLS * ROWS - len(all_footprint_cells)), f"Surfaces 覆蓋錯誤: {total_surf_cells}"

    # --------------------------------------------------------
    # 4. 拓撲邊緣 Edges (EAST & SOUTH)
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
    # 5. 道具定義 (Props)
    # --------------------------------------------------------
    props = [
        # (A) 十字路口核心地標
        {
            "id": "milestone_obelisk",
            "sprite": "milestone_obelisk",
            "cell": cell(22, 17),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "signpost",
            "sprite": "signpost",
            "cell": cell(17, 22),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "broken_wagon",
            "sprite": "broken_wagon",
            "cell": cell(22, 22),
            "elevation": 0,
            "footprint": [2, 1]
        },
        {
            "id": "sack_wagon_1",
            "sprite": "sack",
            "cell": cell(24, 22),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "crate_wagon_1",
            "sprite": "crate",
            "cell": cell(24, 23),
            "elevation": 0,
            "footprint": [1, 1]
        },

        # (B) 西北盤查哨卡
        {
            "id": "barricade_north",
            "sprite": "barricade_spikes",
            "cell": cell(17, 15),
            "elevation": 0,
            "footprint": [2, 1]
        },
        {
            "id": "barricade_west",
            "sprite": "barricade_spikes",
            "cell": cell(15, 17),
            "elevation": 0,
            "footprint": [2, 1]
        },
        {
            "id": "guard_tent",
            "sprite": "tent",
            "cell": cell(11, 6),
            "elevation": 1,
            "footprint": [3, 2]
        },
        {
            "id": "guard_campfire",
            "sprite": "campfire",
            "cell": cell(12, 11),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "flag_guard",
            "sprite": "flag_rust",
            "cell": cell(14, 16),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "barrel_guard_1",
            "sprite": "barrel",
            "cell": cell(7, 13),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "crate_guard_1",
            "sprite": "crate",
            "cell": cell(8, 13),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "woodpile_guard",
            "sprite": "woodpile",
            "cell": cell(6, 12),
            "elevation": 1,
            "footprint": [1, 1]
        },

        # (C) 東北商隊營地
        {
            "id": "nomad_tent",
            "sprite": "tent",
            "cell": cell(29, 6),
            "elevation": 1,
            "footprint": [3, 2]
        },
        {
            "id": "camp_fire_nomad",
            "sprite": "campfire",
            "cell": cell(30, 10),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "water_trough",
            "sprite": "stone_water_trough",
            "cell": cell(26, 13),
            "elevation": 0,
            "footprint": [2, 1]
        },
        {
            "id": "camp_well",
            "sprite": "well",
            "cell": cell(33, 8),
            "elevation": 1,
            "footprint": [2, 2]
        },
        {
            "id": "woodpile_nomad",
            "sprite": "woodpile",
            "cell": cell(33, 11),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "barrel_nomad",
            "sprite": "barrel",
            "cell": cell(28, 11),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "sack_nomad",
            "sprite": "sack",
            "cell": cell(32, 11),
            "elevation": 1,
            "footprint": [1, 1]
        },

        # (D) 東南風化巨石陣
        {
            "id": "boulder_top_1",
            "sprite": "boulder_large",
            "cell": cell(29, 29),
            "elevation": 2,
            "footprint": [2, 2]
        },
        {
            "id": "boulder_east_1",
            "sprite": "boulder_large",
            "cell": cell(34, 26),
            "elevation": 1,
            "footprint": [2, 2]
        },
        {
            "id": "boulder_small_1",
            "sprite": "boulder_small",
            "cell": cell(26, 28),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "boulder_small_2",
            "sprite": "boulder_small",
            "cell": cell(31, 34),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "boulder_small_3",
            "sprite": "boulder_small",
            "cell": cell(26, 33),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "rock_se_1",
            "sprite": "rock_1",
            "cell": cell(23, 25),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "rock_se_2",
            "sprite": "rock_2",
            "cell": cell(38, 28),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "rock_se_3",
            "sprite": "rock_3",
            "cell": cell(35, 36),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "tree_boulder_1",
            "sprite": "dead_tree",
            "cell": cell(36, 32),
            "elevation": 1,
            "footprint": [2, 2]
        },
        {
            "id": "tree_boulder_2",
            "sprite": "dead_tree",
            "cell": cell(25, 36),
            "elevation": 0,
            "footprint": [2, 2]
        },

        # (E) 西南荒野
        {
            "id": "rock_sw_1",
            "sprite": "rock_2",
            "cell": cell(7, 28),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "rock_sw_2",
            "sprite": "rock_1",
            "cell": cell(12, 32),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "tree_sw",
            "sprite": "dead_tree",
            "cell": cell(6, 34),
            "elevation": 0,
            "footprint": [2, 2]
        }
    ]

    # --------------------------------------------------------
    # 6. 演員設定 (Actors)
    # --------------------------------------------------------
    actors_fixture = [
        {
            "id": "guard_captain",
            "label": "守",
            "color": [239, 68, 68],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(10, 11, 1)]
        },
        {
            "id": "guard_sentry",
            "label": "哨",
            "color": [220, 38, 38],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(17, 16, 0)]
        },
        {
            "id": "nomad_merchant",
            "label": "商",
            "color": [234, 179, 8],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(29, 9, 1)]
        },
        {
            "id": "bounty_hunter",
            "label": "獵",
            "color": [56, 189, 248],
            "indoor": None,
            "on_building": None,
            "cells": [cell_3d(28, 29, 2)]
        }
    ]

    # --------------------------------------------------------
    # 7. 組裝 Dictionary
    # --------------------------------------------------------
    spec = {
        "chunk_id": "chunk_crossroads_40x40",
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
        "road_cells": road_cells,
        "plaza_cells": plaza_cells,
        "field_cells": [],
        "bridge_cells": [],
        "authored_cliffs": [],
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
            "face_stone": ["kenshi", 1, 2],
            "wood_floor": ["kenshi", 11, 0],
            "wall_cap": ["kenshi", 12, 0],
            "step": ["kenshi", 13, 0],
            "roof_deck": ["kenshi", 14, 0],
            "door_2u": ["kenshi", 15, 0, 32, 46]
        },
        "styles": {
            "stone": {
                "wall": ["kenshi", 1, 2],
                "door": ["kenshi", 11, 2, 32, 46],
                "window": ["kenshi", 14, 2, 32, 24],
                "roof": {
                    "all": ["kenshi", 4, 2]
                },
                "floor": ["kenshi", 11, 0],
                "cap": ["kenshi", 12, 0]
            }
        }
    }

    out_path = "reports/crossroads_spec.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    print(f"SUCCESS: Generated {out_path} (surfaces={len(surfaces)}, edges={len(edges)}, props={len(props)})")

if __name__ == "__main__":
    build_crossroads_spec()
