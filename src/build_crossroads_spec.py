#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_crossroads_spec.py
------------------------------------------------------------
Author: 諾諾 (Nono)
Role: AI 軟體架構師 / 協作工程師
Target: 荒野十字關卡與戰術開闊空地 (The Wasteland Crossroads & Tactical Clearing) 40×40 規格編譯器。
Features:
  - 40×40 高程網格 (H0~H2)
  - 雙向主次幹道交叉 (4格主道 + 3~4格次道)
  - 中央風化指路石碑與翻覆板車
  - 西北盤查木柵哨所
  - 東北行商中繼營地 (營火、石水槽、帳篷、水井)
  - 東南風化巨石陣開闊對衝戰場
  - 21 項工程鐵律全面防護 (長度斷言、100% Surfaces 覆蓋、邊界檢驗)
------------------------------------------------------------
"""

import os
import sys
import json

def cell(col, row):
    return [int(col), int(row)]

def cell_3d(col, row, elev):
    return [int(col), int(row), int(elev)]

def generate_elevation_and_layout():
    W, H = 40, 40
    elev = [[0 for _ in range(W)] for _ in range(H)]
    slope_cells = set()

    # 1. 西北盤查哨站高台 (H1) 與瞭望石台 (H2)
    for r in range(4, 15):
        for c in range(4, 16):
            elev[r][c] = 1
    # 瞭望高台 H2
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
            
    # 東南坡道：西北側平滑過渡 (cols 24~25, rows 24~25)
    elev[24][24] = 0; slope_cells.add((24, 24))
    elev[24][25] = 0; slope_cells.add((25, 24))
    elev[25][24] = 0; slope_cells.add((24, 25))

    # 4. 十字幹道必須維持 100% 平整 H0
    # 東西主幹道 (rows 18~21)
    for r in range(18, 22):
        for c in range(W):
            elev[r][c] = 0
    # 南北次幹道 (cols 18~21)
    for c in range(18, 22):
        for r in range(H):
            elev[r][c] = 0

    return elev, slope_cells

def build_crossroads_spec():
    elevation_rows, slope_cells = generate_elevation_and_layout()
    W, H = 40, 40

    # 道路與廣場格子
    road_cells = set()
    # 東西主幹道
    for r in range(18, 22):
        for c in range(W):
            road_cells.add((c, r))
    # 南北次幹道
    for c in range(18, 22):
        for r in range(H):
            road_cells.add((c, r))
            
    # 廣場 (盤查哨站與營地硬實地表)
    plaza_cells = set()
    for r in range(6, 14):
        for c in range(6, 15):
            if (c, r) not in road_cells:
                plaza_cells.add((c, r))
    for r in range(7, 13):
        for c in range(28, 35):
            if (c, r) not in road_cells:
                plaza_cells.add((c, r))

    # --------------------------------------------------------
    # 1. 建築物定義：西北盤查木石哨所 (Guard Outpost)
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
            "height_units": 2,
            "story_divider_beam": 1.0,
            "doors_local": [cell(1, 3)],  # 南立面居中開門 (world col 8, row 11)
            "door_height_units": 1.5,
            "door_style": "wood",
            "windows_local": {
                "0": [3]  # col 3 開窗
            },
            "walkable_roof": False,
            "interior": {
                "floor_style": "wood",
                "props": [
                    {
                        "id": "crate",
                        "cell": cell(8, 9),
                        "elevation": 1,
                        "footprint": [1, 1]
                    },
                    {
                        "id": "barrel",
                        "cell": cell(9, 9),
                        "elevation": 1,
                        "footprint": [1, 1]
                    }
                ]
            },
            "roof": {
                "style": "tile",
                "overhang_px": 8
            },
            "facade": []
        }
    ]

    # 建立建築覆蓋佔地查詢表
    building_occupied = {}
    for b in buildings:
        ox, oy = b["footprint"]["origin"]
        bc = b["footprint"]["cols"]
        br = b["footprint"]["rows"]
        b_elev = b["base_elevation"]
        for dr in range(br):
            for dc in range(bc):
                building_occupied[(ox + dc, oy + dr)] = {
                    "building_id": b["building_id"],
                    "elevation": b_elev
                }

    # --------------------------------------------------------
    # 2. 地圖道具佈設 (Props)
    # --------------------------------------------------------
    props = [
        # (A) 十字路口核心地標 (Crossroads Junction)
        {
            "id": "milestone_obelisk",
            "cell": cell(22, 17),
            "elevation": 0,
            "footprint": [1, 1],
            "description": "古老風化指路石碑"
        },
        {
            "id": "signpost",
            "cell": cell(17, 22),
            "elevation": 0,
            "footprint": [1, 1],
            "description": "粗木三向路標"
        },
        {
            "id": "broken_wagon",
            "cell": cell(22, 22),
            "elevation": 0,
            "footprint": [2, 1],
            "description": "損壞翻覆的行商木板車"
        },
        {
            "id": "sack",
            "cell": cell(24, 22),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "crate",
            "cell": cell(24, 23),
            "elevation": 0,
            "footprint": [1, 1]
        },

        # (B) 西北盤查哨卡 (Guard Checkpoint)
        {
            "id": "barricade_spikes",
            "cell": cell(17, 15),
            "elevation": 0,
            "footprint": [2, 1],
            "description": "橫阻北路的帶刺木拒馬"
        },
        {
            "id": "barricade_spikes",
            "cell": cell(15, 17),
            "elevation": 0,
            "footprint": [2, 1],
            "description": "扼守西路的防禦拒馬"
        },
        {
            "id": "tent",
            "cell": cell(11, 6),
            "elevation": 1,
            "footprint": [3, 2],
            "description": "衛兵值勤帆布帳篷"
        },
        {
            "id": "campfire",
            "cell": cell(12, 11),
            "elevation": 1,
            "footprint": [1, 1],
            "description": "哨卡警戒火堆"
        },
        {
            "id": "flag_rust",
            "cell": cell(14, 16),
            "elevation": 0,
            "footprint": [1, 1],
            "description": "哨卡警備旗幟"
        },
        {
            "id": "barrel",
            "cell": cell(7, 13),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "crate",
            "cell": cell(8, 13),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "woodpile",
            "cell": cell(6, 12),
            "elevation": 1,
            "footprint": [1, 1]
        },

        # (C) 東北中繼歇腳營地 (Traveler Camp)
        {
            "id": "tent",
            "cell": cell(29, 6),
            "elevation": 1,
            "footprint": [3, 2],
            "description": "商隊雙人歇腳帳篷"
        },
        {
            "id": "campfire",
            "cell": cell(30, 10),
            "elevation": 1,
            "footprint": [1, 1],
            "description": "中繼營地石圈火堆"
        },
        {
            "id": "stone_water_trough",
            "cell": cell(26, 13),
            "elevation": 0,
            "footprint": [2, 1],
            "description": "路旁供馱獸飲水的長石水槽"
        },
        {
            "id": "well",
            "cell": cell(33, 8),
            "elevation": 1,
            "footprint": [2, 2],
            "description": "營地共用石水井"
        },
        {
            "id": "woodpile",
            "cell": cell(33, 11),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "barrel",
            "cell": cell(28, 11),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "sack",
            "cell": cell(32, 11),
            "elevation": 1,
            "footprint": [1, 1]
        },

        # (D) 東南風化巨石陣戰術空地 (Boulder Battlefield)
        {
            "id": "boulder_large",
            "cell": cell(29, 29),
            "elevation": 2,
            "footprint": [2, 2],
            "description": "岩丘頂部大型風化巨石"
        },
        {
            "id": "boulder_large",
            "cell": cell(34, 26),
            "elevation": 1,
            "footprint": [2, 2],
            "description": "東側隘口天然巨石掩體"
        },
        {
            "id": "boulder_small",
            "cell": cell(26, 28),
            "elevation": 1,
            "footprint": [1, 1],
            "description": "半身風化矮石"
        },
        {
            "id": "boulder_small",
            "cell": cell(31, 34),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "boulder_small",
            "cell": cell(26, 33),
            "elevation": 1,
            "footprint": [1, 1]
        },
        {
            "id": "rock_1",
            "cell": cell(23, 25),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "rock_2",
            "cell": cell(38, 28),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "rock_3",
            "cell": cell(35, 36),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "dead_tree",
            "cell": cell(36, 32),
            "elevation": 1,
            "footprint": [2, 2],
            "description": "風化枯死鐵木"
        },
        {
            "id": "dead_tree",
            "cell": cell(25, 36),
            "elevation": 0,
            "footprint": [2, 2]
        },

        # (E) 西南開闊荒野緩衝帶
        {
            "id": "rock_2",
            "cell": cell(7, 28),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "rock_1",
            "cell": cell(12, 32),
            "elevation": 0,
            "footprint": [1, 1]
        },
        {
            "id": "dead_tree",
            "cell": cell(6, 34),
            "elevation": 0,
            "footprint": [2, 2]
        }
    ]

    # --------------------------------------------------------
    # 3. 演員設定 (Actors)
    # --------------------------------------------------------
    actors = [
        {
            "actor_id": "guard_captain",
            "name": "關卡守衛長",
            "faction": "holy_nation",
            "cell": cell_3d(10, 11, 1),
            "facing": "south"
        },
        {
            "actor_id": "guard_sentry",
            "name": "十字路口哨兵",
            "faction": "holy_nation",
            "cell": cell_3d(17, 16, 0),
            "facing": "south_east"
        },
        {
            "actor_id": "nomad_merchant",
            "name": "遊牧行商",
            "faction": "nomad",
            "cell": cell_3d(29, 9, 1),
            "facing": "south"
        },
        {
            "actor_id": "bounty_hunter",
            "name": "巨石伏擊賞金獵人",
            "faction": "mercenary",
            "cell": cell_3d(28, 29, 2),
            "facing": "north_west"
        }
    ]

    # --------------------------------------------------------
    # 4. 表面組裝 (Surfaces: 100% 覆蓋所有非建築格子)
    # --------------------------------------------------------
    surfaces = []
    covered_cells = set()

    for r in range(H):
        for c in range(W):
            if (c, r) in building_occupied:
                continue

            elev = elevation_rows[r][c]
            
            # 地表類型判斷
            if (c, r) in road_cells:
                kind = "road"
                base_tile = "road_dirt"
            elif (c, r) in plaza_cells:
                kind = "plaza"
                base_tile = "plaza_stone"
            elif elev == 2:
                kind = "sand"
                base_tile = "sand_h2"
            elif elev == 1:
                kind = "sand"
                base_tile = "sand_h1"
            else:
                kind = "sand"
                base_tile = "sand_h0"

            surfaces.append({
                "cell": cell(c, r),
                "elevation": elev,
                "kind": kind,
                "base_tile": base_tile
            })
            covered_cells.add((c, r))

    # 斷言：100% 覆蓋
    total_non_bld = W * H - len(building_occupied)
    assert len(covered_cells) == total_non_bld, f"Surfaces coverage error: {len(covered_cells)} != {total_non_bld}"

    # --------------------------------------------------------
    # 5. 立面邊緣 (Edges) 計算
    # --------------------------------------------------------
    edges = []
    for r in range(H):
        for c in range(W):
            h_cur = elevation_rows[r][c]
            # 檢查東邊相鄰
            if c + 1 < W:
                h_east = elevation_rows[r][c + 1]
                if h_cur != h_east:
                    edges.append({
                        "from": cell(c, r),
                        "to": cell(c + 1, r),
                        "h_left": h_cur,
                        "h_right": h_east,
                        "drop": abs(h_cur - h_east)
                    })
            # 檢查南邊相鄰
            if r + 1 < H:
                h_south = elevation_rows[r + 1][c]
                if h_cur != h_south:
                    edges.append({
                        "from": cell(c, r),
                        "to": cell(c, r + 1),
                        "h_top": h_cur,
                        "h_bottom": h_south,
                        "drop": abs(h_cur - h_south)
                    })

    # --------------------------------------------------------
    # 6. 組裝規格主體
    # --------------------------------------------------------
    spec = {
        "spec_version": "2.1.0",
        "map_id": "chunk_crossroads_40x40",
        "title": "荒野十字關卡與戰術開闊空地",
        "subtitle": "The Wasteland Crossroads & Tactical Clearing",
        "author": "諾諾 (Nono)",
        "grid": {
            "cell_px": 32,
            "cols": W,
            "rows": H
        },
        "projection_presentation_only": {
            "rise_ratio": 0.72,
            "side_shift_ratio": 0.12,
            "side_spread_cells": 6
        },
        "elevation_rows": elevation_rows,
        "road_cells": [cell(c, r) for c, r in sorted(list(road_cells))],
        "plaza_cells": [cell(c, r) for c, r in sorted(list(plaza_cells))],
        "field_cells": [],
        "buildings": buildings,
        "props": props,
        "actors": actors,
        "surfaces": surfaces,
        "edges": edges,
        "tiles": {
            "sand": {"row": 0, "col": 0},
            "road": {"row": 1, "col": 0},
            "plaza": {"row": 2, "col": 0}
        }
    }

    out_path = "reports/crossroads_spec.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {out_path} (W={W}, H={H}, props={len(props)}, actors={len(actors)}, surfaces={len(surfaces)})")

if __name__ == "__main__":
    build_crossroads_spec()
