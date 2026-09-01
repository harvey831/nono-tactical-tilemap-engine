"""
test_spatial_projection.py
==========================
TDD: 驗證 2D 斜俯視共投影數學、高程位移 (ΔY)、鏡頭動態側向錯位 (ΔX) 與逆投影轉換
"""

import unittest
from pathlib import Path
import sys

# 加入 src 路徑
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from spatial.projection import (
    Point, Rect, ProjectionConfig,
    compute_screen_side, project_rect, project_cell_rect, project_point, unproject_point
)

class TestSpatialProjection(unittest.TestCase):
    def setUp(self):
        self.config = ProjectionConfig(
            cell_size=32,
            rise_ratio=0.72,
            side_shift_ratio=0.12,
            grid_width=40,
            grid_height=40
        )

    def test_01_constants_and_rise_values(self):
        """TDD 1: 驗證每級高程垂直與側向位移基準量"""
        self.assertEqual(self.config.cell_size, 32)
        self.assertAlmostEqual(self.config.rise, 23.04, places=2)
        self.assertAlmostEqual(self.config.side_shift, 3.84, places=2)
        self.assertEqual(self.config.world_width, 1280)
        self.assertEqual(self.config.world_height, 1280)

    def test_02_screen_side_bounds_and_clamping(self):
        """TDD 2: 驗證 screen_side 動態計算在各視口位置的平滑性與邊界收斂 [-1.0, 1.0]"""
        # 1. 固定模式
        self.assertEqual(compute_screen_side(640, mode="fixed"), 1.0)

        # 2. 鏡頭中心正中時 (delta = 0)，side 應為 0
        side_center = compute_screen_side(world_center_x=400, pan_x=0, viewport_width=800, mode="camera")
        self.assertAlmostEqual(side_center, 0.0, places=3)

        # 3. 鏡頭偏左與偏右邊界
        side_left = compute_screen_side(world_center_x=0, pan_x=0, viewport_width=800, mode="camera")
        self.assertEqual(side_left, -1.0) # clamped to -1.0

        side_right = compute_screen_side(world_center_x=1200, pan_x=0, viewport_width=800, mode="camera")
        self.assertEqual(side_right, 1.0) # clamped to 1.0

    def test_03_project_rect_and_elevations(self):
        """TDD 3: 驗證矩形投影隨高程升高向上偏移且寬高不變"""
        base_rect = Rect(x=100.0, y=200.0, w=64.0, h=64.0)

        # 高程 0：零偏移
        p0 = project_rect(base_rect, height=0, side=0.5, config=self.config)
        self.assertEqual(p0.x, 100.0)
        self.assertEqual(p0.y, 200.0)
        self.assertEqual(p0.w, 64.0)
        self.assertEqual(p0.h, 64.0)

        # 高程 3 (2F 樓面)：ΔY = -3 * 23.04 = -69.12px, ΔX = 0.5 * 3 * 3.84 = 5.76px
        p3 = project_rect(base_rect, height=3, side=0.5, config=self.config)
        self.assertAlmostEqual(p3.x, 105.76, places=2)
        self.assertAlmostEqual(p3.y, 130.88, places=2)
        self.assertEqual(p3.w, 64.0)
        self.assertEqual(p3.h, 64.0)

    def test_04_point_projection_and_unprojection(self):
        """TDD 4: 驗證 2D 螢幕點逆投影回網格座標的精確還原性"""
        col, row, height, side = 15, 20, 2, 0.3
        pt = project_point(col, row, height, side, self.config)

        # 逆投影
        recovered_col, recovered_row = unproject_point(pt.x, pt.y, height, side, self.config)
        self.assertEqual(recovered_col, col)
        self.assertEqual(recovered_row, row)

if __name__ == "__main__":
    unittest.main()
