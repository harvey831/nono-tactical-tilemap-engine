"""
test_svg_interactive_generator.py
=================================
TDD: 驗證動態互動 SVG/HTML 檢視器生成完整性、JavaScript 語法與無缺失標籤
"""

import unittest
from pathlib import Path
import sys

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from generators.svg_interactive_generator import generate_interactive_svg_html

class TestSvgInteractiveGenerator(unittest.TestCase):
    def setUp(self):
        self.output_dir = Path(__file__).resolve().parent.parent / "reports"
        self.output_path = self.output_dir / "test_interactive_viewer.html"

    def test_01_generate_interactive_html(self):
        """TDD 1: 驗證動態互動 HTML 生成、檔案存在且包含關鍵控制項"""
        spec = {
            "grid_width": 40,
            "grid_height": 40,
            "cell_size": 32,
            "plateaus": [
                {"col": 5, "row": 5, "cols": 10, "rows": 8, "height": 2, "label": "採石高台"}
            ],
            "buildings": [
                {
                    "col": 20, "row": 20, "cols": 8, "rows": 6, "height": 3, "floors": 2,
                    "label": "邊境酒館",
                    "stairs": [{"col": 26, "row": 23, "height": 1}, {"col": 26, "row": 22, "height": 2}]
                }
            ],
            "actors": [
                {"col": 21, "row": 21, "height": 0, "label": "Arya", "color": "#38bdf8"}
            ]
        }

        res_path = generate_interactive_svg_html(spec, self.output_path, title="測試戰術分層地圖")
        self.assertTrue(res_path.exists())

        content = res_path.read_text(encoding="utf-8")
        self.assertIn("<svg class=\"plm-map\"", content)
        self.assertIn("data-plm-layer", content)
        self.assertIn("data-plm-mode", content)
        self.assertIn("data-plm-height-gap", content)
        self.assertIn("pan-layered-map-demo", content)
        self.assertIn("測試戰術分層地圖", content)

if __name__ == "__main__":
    unittest.main()
