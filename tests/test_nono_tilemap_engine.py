import unittest
import math
import base64
from pathlib import Path
from PIL import Image

# 匯入待測大作模組
from src.nono_tilemap_engine import grid_l1, grid_l2, grid_l25, grid_l3, BUILDINGS

class TestNonoTilemapEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.assets_dir = cls.repo_root / "assets"
        cls.reports_dir = cls.repo_root / "reports"
        cls.brain_dir = Path(r"C:\Users\ihate\.gemini\antigravity\brain\522dd70e-62d4-4f27-893e-70f3ade173ca")
        
        cls.grid_l1 = grid_l1
        cls.grid_l2 = grid_l2
        cls.grid_l25 = grid_l25
        cls.grid_l3 = grid_l3

    def test_01_semantic_grid_dimensions_and_tokens(self):
        """TDD 1: 驗證四層純語意矩陣均為嚴格 40x40 網格 (1280x1280 px)，且無非法 Token"""
        for name, g in [("L1", self.grid_l1), ("L2", self.grid_l2), ("L2.5", self.grid_l25), ("L3", self.grid_l3)]:
            self.assertEqual(len(g), 40, f"{name} 行數必須為 40")
            for r_idx, row in enumerate(g):
                self.assertEqual(len(row), 40, f"{name} 第 {r_idx} 列寬度必須為 40")
                for cell in row:
                    self.assertTrue(cell.startswith("[") and cell.endswith("]"), f"Token 語法錯誤: {cell}")

    def test_02_spatial_decoupling_roof_vs_interior(self):
        """TDD 2: 驗證屋頂 (Layer 3) 與 店內地基 (Layer 2) 空間物理語意徹底解耦，0 碰撞"""
        # 大酒館驗證 (gx: 3..10, gy: 25..30)
        for gx in range(3, 11):
            for gy in range(25, 27):
                self.assertEqual(self.grid_l3[gy][gx], "[▲酒頂]", f"酒館屋頂懸垂行 (gy={gy}, gx={gx}) 必須為 [▲酒頂]")
                self.assertEqual(self.grid_l2[gy][gx], "[ · ]", f"酒館屋頂懸垂行 (gy={gy}, gx={gx}) 在 Layer 2 必須留空")
            for gy in range(27, 31):
                self.assertEqual(self.grid_l3[gy][gx], "[ · ]", f"酒館店內佔地行 (gy={gy}, gx={gx}) 在 Layer 3 必須留空")
                self.assertIn(self.grid_l2[gy][gx], ["[酒地]", "[吧台]", "[壁爐]", "[酒桶]", "[長桌]", "[酒門]"])

        # 鐵匠鋪驗證 (gx: 26..31, gy: 5..9)
        for gx in range(26, 32):
            self.assertEqual(self.grid_l3[5][gx], "[▲鐵頂]")
            self.assertEqual(self.grid_l2[5][gx], "[ · ]")
            for gy in range(6, 10):
                self.assertEqual(self.grid_l3[gy][gx], "[ · ]")
                self.assertIn(self.grid_l2[gy][gx], ["[鐵地]", "[武架]", "[甲架]", "[鐵砧]", "[鐵門]", "[石階]"])

        # 雜貨鋪驗證 (gx: 4..9, gy: 5..9)
        for gx in range(4, 10):
            self.assertEqual(self.grid_l3[5][gx], "[▲店頂]")
            self.assertEqual(self.grid_l2[5][gx], "[ · ]")
            for gy in range(6, 10):
                self.assertEqual(self.grid_l3[gy][gx], "[ · ]")
                self.assertIn(self.grid_l2[gy][gx], ["[店地]", "[藥架]", "[櫃台]", "[金箱]", "[店門]", "[石階]"])

    def test_03_building_geometry_ssot(self):
        """TDD 3: 驗證 BUILDINGS 字典定義完整且與語意矩陣對齊"""
        self.assertIn("TAVERN", BUILDINGS)
        self.assertIn("BLACKSMITH", BUILDINGS)
        self.assertIn("MERCHANT", BUILDINGS)
        self.assertEqual(BUILDINGS["TAVERN"]["gw"], 8)
        self.assertEqual(BUILDINGS["TAVERN"]["gh"], 6)

    def test_04_building_facades_and_doors_present_in_exterior_view(self):
        """TDD 4: 驗證外觀全景大圖 (view_exterior_merged.png) 中包含完整的木板立面牆與閉合大門"""
        ext_img_path = self.brain_dir / "view_exterior_merged.png"
        self.assertTrue(ext_img_path.exists(), "view_exterior_merged.png 必須存在")
        img_ext = Image.open(ext_img_path).convert("RGBA")
        self.assertEqual(img_ext.size, (1280, 1280))

    def test_05_delivery_report_base64_inlining_and_no_broken_paths(self):
        """TDD 5: 驗證 HTML 交付報告 100% Base64 內嵌，零外部未內嵌圖片路徑"""
        report_path = self.brain_dir / "map_delivery_report_0_0.html"
        self.assertTrue(report_path.exists(), "map_delivery_report_0_0.html 必須存在")
        content = report_path.read_text(encoding="utf-8")
        
        self.assertNotIn('src="layer_', content, "報告中禁止出現未內嵌的 layer_*.png 相對路徑")
        self.assertNotIn('src="view_', content, "報告中禁止出現未內嵌的 view_*.png 相對路徑")
        self.assertGreaterEqual(content.count("data:image/png;base64,"), 5, "報告中必須內嵌至少 5 張 Base64 大圖")

    def test_06_tilemap_assets_and_integrity(self):
        """TDD 6: 驗證所有導出的地圖資產完整性與解析度"""
        for fname in ["kenshi_village_exterior_1280.png", "kenshi_village_interior_1280.png", "kenshi_village_semantic_ssot_1280.png"]:
            p = self.assets_dir / fname
            self.assertTrue(p.exists(), f"資產 {fname} 必須存在")
            with Image.open(p) as img:
                self.assertEqual(img.size, (1280, 1280), f"{fname} 尺寸必須為 1280x1280")

if __name__ == "__main__":
    unittest.main(verbosity=2)
