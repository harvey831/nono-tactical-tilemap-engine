"""
test_layered_village_architecture.py
====================================
TDD 驗證套件：驗證 (0, 0) 邊境村落新分層空間拓撲架構、實體階梯、32px 網格與切面規範
"""

import unittest
import json
from pathlib import Path
from PIL import Image

class TestLayeredVillageArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.assets_dir = cls.repo_root / "assets"
        cls.reports_dir = cls.repo_root / "reports"
        cls.chunk_dir = cls.assets_dir / "chunk_0_0_border_village"
        cls.slices_dir = cls.chunk_dir / "slices"
        cls.buildings_dir = cls.chunk_dir / "buildings"

    def test_01_slices_and_buildings_exist_and_dimensions(self):
        """TDD 1: 驗證分層切片與建築切片均存在且尺寸符合 32px 倍數"""
        ground_path = self.slices_dir / "H0_ground_surface.png"
        props_path = self.slices_dir / "H0_props_y_sort.png"
        self.assertTrue(ground_path.exists(), "H0_ground_surface.png 必須存在")
        self.assertTrue(props_path.exists(), "H0_props_y_sort.png 必須存在")

        with Image.open(ground_path) as img:
            self.assertEqual(img.size, (1280, 1280), "地表底圖必須為 1280x1280 (40x40 @ 32px)")
        with Image.open(props_path) as img:
            self.assertEqual(img.size, (1280, 1280), "Props 切片必須為 1280x1280")

        # 驗證酒館切片 (256x192 = 8x6 格 @ 32px)
        tav_parts = [
            "tavern_floor_1f.png",
            "tavern_stairs_h1_h2.png",
            "tavern_floor_2f.png",
            "tavern_exterior_roof.png",
            "tavern_roof_cut_cap.png"
        ]
        for part in tav_parts:
            p = self.buildings_dir / part
            self.assertTrue(p.exists(), f"酒館切片 {part} 必須存在")
            with Image.open(p) as img:
                self.assertEqual(img.size, (256, 192), f"{part} 尺寸必須為 256x192 (8x6 @ 32px)")

    def test_02_spatial_spec_schema_and_elevation_continuity(self):
        """TDD 2: 驗證 chunk_0_0_surface_spec.json 空間規格與高程連續性"""
        spec_path = self.chunk_dir / "chunk_0_0_surface_spec.json"
        self.assertTrue(spec_path.exists(), "chunk_0_0_surface_spec.json 必須存在")

        with open(spec_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["grid_size"], [40, 40], "網格必須為 40x40")
        self.assertEqual(data["cell_size_px"], 32, "單元格尺寸必須為 32px")
        self.assertEqual(data["projection"]["delta_y_per_elevation"], 23.04, "ΔY 投影必須為 23.04px")

        # 驗證高程階梯包含 H0, H1, H2, H3
        elevations = {s["elevation"] for s in data["surfaces"]}
        self.assertTrue({0, 1, 2, 3}.issubset(elevations), "必須涵蓋 H0, H1, H2, H3 四級高程")

    def test_03_tavern_physical_stairs_and_stair_void_projection(self):
        """TDD 3: 驗證酒館實體階梯與 2F 梯洞過度延伸防切頭幾何"""
        def_path = self.buildings_dir / "tavern_definition.json"
        self.assertTrue(def_path.exists(), "tavern_definition.json 必須存在")

        with open(def_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["building_id"], "bldg_tavern_00")
        self.assertEqual(data["footprint"]["width"], 8)
        self.assertEqual(data["footprint"]["height"], 6)

        # 尋找 2F 與梯洞
        f2 = next((s for s in data["storeys"] if s.get("floor_index") == 2), None)
        self.assertIsNotNone(f2, "酒館必須有 2F 樓層定義")
        self.assertIn("stair_void_rect", f2, "2F 必須定義梯洞開口")

        # 驗證梯洞過度延伸量 >= 3 * 23.04 = 69.12px
        self.assertGreaterEqual(f2["stair_void_rect"]["over_extension_px"], 69.0, "梯洞過度延伸量必須補償 3 級高程投影差")

    def test_04_html_layered_report_validity(self):
        """TDD 4: 驗證 HTML 多層切面報告完整性、Base64 內嵌與圖層切換控制"""
        report_path = self.reports_dir / "map_delivery_report_0_0_layered.html"
        self.assertTrue(report_path.exists(), "map_delivery_report_0_0_layered.html 必須存在")
        
        # 報告內嵌 Base64 圖片，大小應 > 500KB
        self.assertGreater(report_path.stat().st_size, 500000, "報告必須完整內嵌高解析度 Base64 貼圖")

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("data:image/png;base64,", content, "必須使用 Base64 內嵌貼圖")
        self.assertIn("switchSemView", content, "必須包含語意圖層切換控制邏輯")
        self.assertIn("openLightboxImage", content, "必須包含 800% Lightbox 放大功能")
        self.assertIn("ADR-0072", content, "必須註記 ADR-0072 合規")

    def test_05_authoring_overlay_and_preview_integrity(self):
        """TDD 5: 驗證 32 格網 Overlay 標註圖與全景預覽圖正常生成"""
        overlay_path = self.chunk_dir / "chunk_0_0_authoring_overlay.png"
        preview_path = self.chunk_dir / "chunk_0_0_preview.png"
        self.assertTrue(overlay_path.exists(), "chunk_0_0_authoring_overlay.png 必須存在")
        self.assertTrue(preview_path.exists(), "chunk_0_0_preview.png 必須存在")

        with Image.open(overlay_path) as img:
            self.assertEqual(img.size, (1280, 1280))
        with Image.open(preview_path) as img:
            self.assertEqual(img.size, (1280, 1280))


if __name__ == "__main__":
    unittest.main()
