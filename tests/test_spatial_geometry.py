"""
test_spatial_geometry.py
========================
TDD: 驗證懸崖立面、負高程洞口 Mask、1 格厚外牆環、實體階梯與多格演員底盤連接
"""

import unittest
from pathlib import Path
import sys

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from spatial.projection import Rect, Point, ProjectionConfig
from spatial.geometry import generate_raised_faces, generate_raised_faces_with_door, generate_pit_aperture_mask
from spatial.building import BuildingDef, StairDef, DoorDef
from spatial.footprint import (
    FootprintCell, resolve_base_tile_rotation_and_count,
    compute_actor_stance, generate_height_connection_polygons
)

class TestSpatialGeometry(unittest.TestCase):
    def setUp(self):
        self.config = ProjectionConfig(cell_size=32)

    def test_01_raised_faces_generation(self):
        """TDD 1: 驗證懸崖正面崖壁與側向斜壁面片正確生成"""
        top_rect = Rect(100, 100, 64, 64)
        lower_rect = Rect(100, 123.04, 64, 64)

        # 1. 側向係數為正時產生左側壁
        faces_left = generate_raised_faces(top_rect, lower_rect, side=0.5)
        self.assertEqual(len(faces_left), 2)
        self.assertEqual(faces_left[0].data_attrs["type"], "cliff_front")
        self.assertEqual(faces_left[1].data_attrs["type"], "cliff_side_left")

        # 2. 側向係數為負時產生右側壁
        faces_right = generate_raised_faces(top_rect, lower_rect, side=-0.5)
        self.assertEqual(len(faces_right), 2)
        self.assertEqual(faces_right[1].data_attrs["type"], "cliff_side_right")

    def test_02_building_outer_wall_ring_computation(self):
        """TDD 2: 驗證 1 格厚實心外牆環識別與室內格子完全分離"""
        # 建立一個 4x4 格的長方形建築 (共 16 格)
        cells = [{"col": x, "row": y} for y in range(4) for x in range(4)]
        bldg = BuildingDef(
            building_id="bldg_test",
            label="Test House",
            origin=(10, 10),
            size=(4, 4),
            cells=cells,
            height=3,
            floors=2
        )

        # 4x4 矩形的最外圈應有 12 格，內部有 4 格 (2x2)
        self.assertEqual(len(bldg.wall_cells), 12)
        self.assertEqual(len(bldg.interior_cells), 4)

    def test_03_building_cutaway_and_stair_void(self):
        """TDD 3: 驗證在 cut_height=1 裁切時，2F 樓板正確切除並露出實體階梯"""
        cells = [{"col": x, "row": y} for y in range(4) for x in range(4)]
        stair = StairDef(
            flight_cells=[{"col": 3, "row": 2, "step_offset": 1}, {"col": 3, "row": 1, "step_offset": 2}],
            opening_cells=[{"col": 3, "row": 1}, {"col": 3, "row": 2}],
            width=1
        )
        bldg = BuildingDef(
            building_id="bldg_tavern",
            label="Tavern",
            origin=(4, 25),
            size=(4, 4),
            cells=cells,
            height=3,
            floors=2,
            stair=stair
        )

        cut_struct = bldg.generate_cutaway_structure(cut_height=1, side=0.2, config=self.config)
        self.assertTrue(cut_struct["is_cut"])
        self.assertEqual(len(cut_struct["visible_stairs"]), 1) # 只有 step_offset <= 1 的第 1 階可見
        self.assertEqual(cut_struct["visible_floor_height"], 0.0) # 1 樓地面

    def test_04_footprint_stance_and_height_connection(self):
        """TDD 4: 驗證跨高低差多格演員底盤 Stance 錨定與相鄰高差連接面片"""
        # 建立跨越 H1 與 H2 的 2 格演員
        cells = [
            FootprintCell(col=10, row=10, height=1),
            FootprintCell(col=10, row=11, height=2)
        ]
        stance, core_h = compute_actor_stance(cells, self.config, side=0.1)
        self.assertEqual(core_h, 1) # 核心錨定在第 1 格高度

        # 生成高差連接面片
        conn_polys = generate_height_connection_polygons(cells, self.config, side=0.1)
        self.assertEqual(len(conn_polys), 1)
        self.assertEqual(conn_polys[0].data_attrs["height_connection"], "1-2")

if __name__ == "__main__":
    unittest.main()
