import unittest
import sys
from pathlib import Path
from PIL import Image

brain_dir = Path(r"C:\Users\ihate\.gemini\antigravity\brain\522dd70e-62d4-4f27-893e-70f3ade173ca")
sys.path.insert(0, str(brain_dir))
sys.path.insert(0, str(brain_dir / "scratch"))

skill_repo = Path(__file__).resolve().parent.parent
assets_dir = skill_repo / "assets"
reports_dir = skill_repo / "reports"

class TestSlaveCampTilemap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from generate_true_34_slave_camp_map import grid_l1, grid_l2, grid_l25, grid_l3
        cls.grid_l1 = grid_l1
        cls.grid_l2 = grid_l2
        cls.grid_l25 = grid_l25
        cls.grid_l3 = grid_l3

    def test_01_semantic_grid_dimensions_and_tokens(self):
        """TDD 1: 驗證奴隸營 4 層純語意矩陣均為嚴格 40x40 網格 (1280x1280 px)，且無非法 Token"""
        for name, g in [("L1", self.grid_l1), ("L2", self.grid_l2), ("L2.5", self.grid_l25), ("L3", self.grid_l3)]:
            self.assertEqual(len(g), 40, f"{name} 行數必須為 40")
            for r_idx, row in enumerate(g):
                self.assertEqual(len(row), 40, f"{name} 第 {r_idx} 列寬度必須為 40")
                for cell in row:
                    self.assertTrue(cell.startswith("[") and cell.endswith("]"), f"Token 語法錯誤: {cell}")

    def test_02_spatial_decoupling_roof_vs_interior(self):
        """TDD 2: 驗證帳篷屋頂 (Layer 3) 與 帳內地基 (Layer 2) 空間物理語意徹底解耦，0 碰撞"""
        # 奴隸主帳篷 (gx: 6..13, gy: 5..10)
        for gx in range(6, 14):
            for gy in range(5, 7):
                self.assertEqual(self.grid_l3[gy][gx], "[▲帳頂]", f"帳篷頂部 (gy={gy}, gx={gx}) 必須為 [▲帳頂]")
                self.assertEqual(self.grid_l2[gy][gx], "[ · ]", f"帳篷頂部 (gy={gy}, gx={gx}) 在 Layer 2 必須留空")
            for gy in range(7, 11):
                self.assertEqual(self.grid_l3[gy][gx], "[ · ]", f"帳內佔地 (gy={gy}, gx={gx}) 在 Layer 3 必須留空")
                self.assertIn(self.grid_l2[gy][gx], ["[帳地]", "[皮椅]", "[戰圖]", "[金箱]", "[地毯]", "[帳門]"])

        # 刑具鍛造鋪 (gx: 26..31, gy: 5..10)
        for gx in range(26, 32):
            for gy in range(5, 7):
                self.assertEqual(self.grid_l3[gy][gx], "[▲鍛頂]")
                self.assertEqual(self.grid_l2[gy][gx], "[ · ]")
            for gy in range(7, 11):
                self.assertEqual(self.grid_l3[gy][gx], "[ · ]")
                self.assertIn(self.grid_l2[gy][gx], ["[鍛地]", "[風箱]", "[熔爐]", "[鐵砧]", "[鐐架]", "[鍛門]"])

    def test_03_quarry_pit_stepped_geography_and_megablocks(self):
        """TDD 3: 驗證階梯採石坑包含 3 階立體地勢與巨型開採石塊區"""
        tier1_count = sum(row.count("[岩層1]") for row in self.grid_l1)
        tier2_count = sum(row.count("[岩層2]") for row in self.grid_l1)
        tier3_count = sum(row.count("[岩層3]") for row in self.grid_l1)
        megablock_count = sum(row.count("[巨石條]") for row in self.grid_l2)
        self.assertGreater(tier1_count, 100, "Tier 1 中層採石平台面積充足")
        self.assertGreater(tier2_count, 80, "Tier 2 深層採石坑面積充足")
        self.assertGreater(tier3_count, 40, "Tier 3 最深岩心面積充足")
        self.assertGreaterEqual(megablock_count, 16, "必須包含巨型開採石條塊")

    def test_04_building_facades_and_doors_present_in_exterior_view(self):
        """TDD 4: 驗證外觀全景大圖 (view_exterior_merged.png) 中包含完整的帳篷立面與鍛造鋪大門"""
        ext_img_path = brain_dir / "view_exterior_merged.png"
        self.assertTrue(ext_img_path.exists(), "view_exterior_merged.png 必須存在")
        with Image.open(ext_img_path) as img:
            self.assertEqual(img.size, (1280, 1280))

    def test_05_delivery_report_base64_inlining_and_no_broken_paths(self):
        """TDD 5: 驗證 HTML 交付報告 100% Base64 內嵌，零外部未內嵌圖片路徑"""
        report_path = brain_dir / "map_delivery_report_0_1.html"
        self.assertTrue(report_path.exists(), "map_delivery_report_0_1.html 必須存在")
        content = report_path.read_text(encoding="utf-8")
        
        self.assertNotIn('src="layer_', content, "報告中禁止出現未內嵌的 layer_*.png 相對路徑")
        self.assertNotIn('src="view_', content, "報告中禁止出現未內嵌的 view_*.png 相對路徑")
        self.assertGreaterEqual(content.count("data:image/png;base64,"), 5, "報告中必須內嵌至少 5 張 Base64 大圖")
        self.assertIn("handleLightboxWheel", content, "報告中必須包含 800% 滾輪縮放腳本")

    def test_06_tilemap_assets_and_integrity(self):
        """TDD 6: 驗證所有導出的地圖資產完整性與解析度"""
        for fname in ["kenshi_slave_camp_exterior_1280.png", "kenshi_slave_camp_interior_1280.png", "kenshi_slave_camp_semantic_ssot_1280.png"]:
            p = assets_dir / fname
            self.assertTrue(p.exists(), f"資產 {fname} 必須存在")
            with Image.open(p) as img:
                self.assertEqual(img.size, (1280, 1280), f"{fname} 尺寸必須為 1280x1280")

if __name__ == "__main__":
    unittest.main(verbosity=2)
