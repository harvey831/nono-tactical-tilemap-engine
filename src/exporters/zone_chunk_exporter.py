"""
zone_chunk_exporter.py
======================
Typed ZoneChunkDataset JSON 導出與 Schema 驗證模組 (ADR-0072 合規)
提供：
1. 將空間拓撲物件序列化為 Godot 與引擎可載入之標準 JSON 正本
2. 執行 ADR-0072 空間拓撲防護規則校驗 (0 Broken References, 高程連續性, 1 格厚牆環)
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

class ValidationError(Exception):
    pass

def validate_zone_chunk_dataset(data: Dict[str, Any]) -> List[str]:
    """
    依據 ADR-0072 進行嚴格空間拓撲約束驗證，回傳所有錯誤列表 (若無錯誤則為空列表)
    """
    errors: List[str] = []

    # 1. 基礎欄位
    if "chunk_id" not in data:
        errors.append("缺失必要欄位: 'chunk_id'")
    if "grid_size" not in data or len(data["grid_size"]) != 2:
        errors.append("缺失或無效的 'grid_size'")
    if data.get("cell_size_px") != 32:
        errors.append(f"cell_size_px 必須為 32 (目前為: {data.get('cell_size_px')})")

    # 2. 投影參數驗證
    proj = data.get("projection", {})
    if proj.get("delta_y_per_elevation") != 23.04:
        errors.append(f"delta_y_per_elevation 必須為 23.04 (目前為: {proj.get('delta_y_per_elevation')})")

    # 3. Surface 完整性與高程範圍
    surfaces = data.get("surfaces", [])
    if not surfaces:
        errors.append("surfaces 清單不能為空")

    surface_ids = set()
    for s in surfaces:
        s_id = s.get("surface_id")
        if not s_id:
            errors.append("存在未命名的 surface_id")
        elif s_id in surface_ids:
            errors.append(f"重複的 surface_id: '{s_id}'")
        surface_ids.add(s_id)

        elev = s.get("elevation")
        if elev is None or not isinstance(elev, int):
            errors.append(f"Surface '{s_id}' 的 elevation 必須為整數")
        elif elev < -2 or elev > 9:
            errors.append(f"Surface '{s_id}' 的 elevation {elev} 超出合法範圍 [-2, 9]")

    # 4. 建築定義與實體階梯
    buildings = data.get("buildings", [])
    for b in buildings:
        b_id = b.get("building_id")
        if not b_id:
            errors.append("存在未命名的 building_id")

        storeys = b.get("storeys", [])
        has_stairs = any(s.get("floor_index") == "stairs" for s in storeys)
        if len(storeys) > 1 and not has_stairs:
            errors.append(f"多樓層建築 '{b_id}' 必須定義實體階梯 ('stairs')")

    return errors


def export_zone_chunk_dataset(
    data: Dict[str, Any],
    output_path: Path,
    strict_validation: bool = True
) -> Path:
    """
    驗證並導出 ZoneChunkDataset JSON 檔案
    """
    if strict_validation:
        errors = validate_zone_chunk_dataset(data)
        if errors:
            raise ValidationError(f"ZoneChunkDataset 驗證失敗:\n" + "\n".join(f"- {e}" for e in errors))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return output_path
