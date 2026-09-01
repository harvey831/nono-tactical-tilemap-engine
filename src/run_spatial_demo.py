"""
run_spatial_demo.py
===================
執行空間共投影引擎演示，生成 demo_spatial_projection_engine.html
"""

import sys
from pathlib import Path

# 加入當前路徑
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from generators.svg_interactive_generator import generate_interactive_svg_html

def run():
    reports_dir = src_dir.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    spec = {
        "grid_width": 40,
        "grid_height": 40,
        "cell_size": 32,
        "plateaus": [
            {"col": 4, "row": 4, "cols": 12, "rows": 8, "height": 2, "label": "北方採石高台 (H2)"},
            {"col": 24, "row": 6, "cols": 10, "rows": 6, "height": 1, "label": "東側梯田 (H1)"}
        ],
        "buildings": [
            {
                "col": 4, "row": 25, "cols": 8, "rows": 6, "height": 3, "floors": 2,
                "label": "邊境大酒館 (H0-H3)",
                "stairs": [
                    {"col": 10, "row": 29, "height": 1},
                    {"col": 10, "row": 28, "height": 2}
                ]
            },
            {
                "col": 26, "row": 24, "cols": 6, "rows": 5, "height": 2, "floors": 1,
                "label": "鐵匠工坊 (H0-H2)",
                "stairs": []
            }
        ],
        "actors": [
            {"col": 10, "row": 29, "height": 1, "label": "Arya (階梯 H1)", "color": "#38bdf8"},
            {"col": 8, "row": 7, "height": 2, "label": "守衛 (高台 H2)", "color": "#eab308"},
            {"col": 18, "row": 20, "height": 0, "label": "平民 (主街 H0)", "color": "#22c55e"}
        ]
    }

    out_path = reports_dir / "demo_spatial_projection_engine.html"
    generate_interactive_svg_html(
        spec,
        out_path,
        title="荒原 2D 斜俯視多高程分層空間引擎 — 即時互動演示",
        subtitle="ADR-0072 空間拓撲與 pan-layered-map-prototype.html 同構空間流水線"
    )
    print("✅ 成功生成空間引擎動態互動演示報告:", out_path)

if __name__ == "__main__":
    run()
