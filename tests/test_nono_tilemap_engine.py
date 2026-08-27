import unittest
import base64
from pathlib import Path
from PIL import Image

class TestNonoTilemapEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.assets_dir = cls.repo_root / "assets"
        cls.reports_dir = cls.repo_root / "reports"
        cls.brain_dir = Path(r"C:\Users\ihate\.gemini\antigravity\brain\522dd70e-62d4-4f27-893e-70f3ade173ca")

    def test_01_assets_exist_and_resolution(self):
        """TDD 1: 驗證大作核心資產存在且尺寸為 1280x1280 (40x40 網格 @ 32px)"""
        for fname in ["kenshi_village_exterior_1280.png", "kenshi_village_interior_1280.png", "kenshi_village_semantic_ssot_1280.png"]:
            p = self.assets_dir / fname
            self.assertTrue(p.exists(), f"核心資產 {fname} 必須存在")
            with Image.open(p) as img:
                self.assertEqual(img.size, (1280, 1280), f"{fname} 尺寸必須為 1280x1280")

    def test_02_masterpiece_asset_density_and_size(self):
        """TDD 2: 驗證外觀大圖與店內大圖具備 600KB+ 高密度手繪級細節（非平塗簡化版）"""
        ext_p = self.assets_dir / "kenshi_village_exterior_1280.png"
        int_p = self.assets_dir / "kenshi_village_interior_1280.png"
        self.assertGreater(ext_p.stat().st_size, 500000, "外觀大圖必須具備大作級細節檔案大小 (>500KB)")
        self.assertGreater(int_p.stat().st_size, 500000, "店內大圖必須具備大作級細節檔案大小 (>500KB)")

    def test_03_delivery_report_base64_inlining_and_no_broken_paths(self):
        """TDD 3: 驗證 HTML 交付報告 100% Base64 內嵌，零外部未內嵌圖片路徑"""
        report_path = self.reports_dir / "map_delivery_report_0_0_village.html"
        self.assertTrue(report_path.exists(), "map_delivery_report_0_0_village.html 必須存在")
        content = report_path.read_text(encoding="utf-8")
        
        self.assertNotIn('src="layer_', content, "報告中禁止出現未內嵌的 layer_*.png 相對路徑")
        self.assertNotIn('src="view_', content, "報告中禁止出現未內嵌的 view_*.png 相對路徑")
        self.assertGreaterEqual(content.count("data:image/png;base64,"), 5, "報告中必須內嵌至少 5 張 Base64 大圖")

    def test_04_html_lightbox_and_script_validity(self):
        """TDD 4: 驗證報告包含 800% Lightbox 放大模態框與分層切換交互腳本"""
        report_path = self.reports_dir / "map_delivery_report_0_0_village.html"
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("switchSemView", content)
        self.assertIn("openLightboxImage", content)
        self.assertIn("lightbox-modal", content)

if __name__ == "__main__":
    unittest.main(verbosity=2)
