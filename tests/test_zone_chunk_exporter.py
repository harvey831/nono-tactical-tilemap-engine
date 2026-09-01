"""
test_zone_chunk_exporter.py
===========================
TDD: 驗證 ZoneChunkDataset ADR-0072 空間拓撲 Schema 驗證與 JSON 序列化
"""

import unittest
from pathlib import Path
import sys

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from exporters.zone_chunk_exporter import (
    validate_zone_chunk_dataset, export_zone_chunk_dataset, ValidationError
)

class TestZoneChunkExporter(unittest.TestCase):
    def test_01_valid_dataset_passes(self):
        """TDD 1: 驗證標準合規的 ZoneChunkDataset 通過驗證"""
        valid_data = {
            "chunk_id": "chunk_0_0_border_village",
            "grid_size": [40, 40],
            "cell_size_px": 32,
            "projection": {
                "delta_y_per_elevation": 23.04,
                "delta_x_per_elevation": 3.84
            },
            "surfaces": [
                {"surface_id": "surf_ground", "elevation": 0},
                {"surface_id": "surf_tavern_2f", "elevation": 3}
            ],
            "buildings": [
                {
                    "building_id": "bldg_tavern",
                    "storeys": [
                        {"floor_index": 1, "elevation": 0},
                        {"floor_index": "stairs", "elevation_range": [1, 2]},
                        {"floor_index": 2, "elevation": 3}
                    ]
                }
            ]
        }
        errors = validate_zone_chunk_dataset(valid_data)
        self.assertEqual(len(errors), 0, f"合規資料不應有錯誤: {errors}")

    def test_02_invalid_dataset_detected(self):
        """TDD 2: 驗證缺失欄位或超出高程範圍之無效資料被正確攔截"""
        invalid_data = {
            "chunk_id": "chunk_bad",
            "cell_size_px": 16, # 錯誤：應為 32
            "surfaces": [
                {"surface_id": "surf_invalid", "elevation": 99} # 錯誤：超出合法高程 [-2, 9]
            ],
            "buildings": [
                {
                    "building_id": "bldg_multi_no_stairs",
                    "storeys": [{"floor_index": 1}, {"floor_index": 2}] # 錯誤：多樓層未定義 stairs
                }
            ]
        }
        errors = validate_zone_chunk_dataset(invalid_data)
        self.assertGreaterEqual(len(errors), 3)

        out_path = Path(__file__).resolve().parent.parent / "reports" / "should_not_exist.json"
        with self.assertRaises(ValidationError):
            export_zone_chunk_dataset(invalid_data, out_path, strict_validation=True)

if __name__ == "__main__":
    unittest.main()
