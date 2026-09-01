"""
building.py
===========
建築空間拓撲與動態切面模型 (ADR-0072 & pan-layered-map-prototype.html 同構)
提供：
1. 1 格厚實心外牆環自動計算 (1-Tile Wall Ring)
2. 實體階梯級數 (Physical Stairs Flights) 與 2F 梯洞開口 (Stair Void)
3. 動態切面剖面 (Building Cutaway) 與實心黑邊 Cap
"""

from typing import List, Dict, Set, Tuple, Optional, Any
from .projection import Rect, Point, ProjectionConfig, project_rect, project_cell_rect
from .geometry import Polygon, generate_raised_faces_with_door

class CellCoord:
    def __init__(self, col: int, row: int):
        self.col = col
        self.row = row

    def key(self) -> str:
        return f"{self.col},{self.row}"

class StairDef:
    def __init__(
        self,
        flight_cells: List[Dict[str, Any]], # [{"col": x, "row": y, "step_offset": h}, ...]
        opening_cells: List[Dict[str, int]], # [{"col": x, "row": y}, ...]
        width: int = 2
    ):
        self.flight_cells = flight_cells
        self.opening_cells = opening_cells
        self.width = width

class DoorDef:
    def __init__(self, col: int, row: int, height: float = 1.65):
        self.col = col
        self.row = row
        self.height = height

class BuildingDef:
    def __init__(
        self,
        building_id: str,
        label: str,
        origin: Tuple[int, int],
        size: Tuple[int, int],
        cells: List[Dict[str, int]],
        height: int,
        floors: int = 2,
        doors: Optional[List[DoorDef]] = None,
        stair: Optional[StairDef] = None
    ):
        self.building_id = building_id
        self.label = label
        self.origin = origin
        self.size = size
        self.cells = cells
        self.height = height
        self.floors = floors
        self.doors = doors or []
        self.stair = stair

        # 自動計算 1 格厚外牆環與室內格子
        self.wall_cells, self.interior_cells = self._compute_wall_and_interior()

    def _compute_wall_and_interior(self) -> Tuple[List[Dict[str, int]], List[Dict[str, int]]]:
        cell_keys: Set[str] = {f"{c['col']},{c['row']}" for c in self.cells}
        walls: List[Dict[str, int]] = []
        interiors: List[Dict[str, int]] = []

        for cell in self.cells:
            col, row = cell["col"], cell["row"]
            # 檢查 4-鄰域正交格，若有任一相鄰格不在建築內，則屬於 1 格厚外牆環
            is_wall = False
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                if f"{col + dx},{row + dy}" not in cell_keys:
                    is_wall = True
                    break
            if is_wall:
                walls.append(cell)
            else:
                interiors.append(cell)

        return walls, interiors

    def get_floor_height(self) -> float:
        return self.height / self.floors

    def get_visible_floor_height(self, cut_height: Optional[float]) -> float:
        """計算在當前 cut_height 裁切下應該顯示的樓面高程"""
        floor_h = self.get_floor_height()
        if cut_height is None:
            return float(self.height)
        return min(float(self.height), int(max(0.0, cut_height) // floor_h) * floor_h)

    def generate_cutaway_structure(
        self,
        cut_height: Optional[float],
        side: float,
        config: ProjectionConfig
    ) -> Dict[str, Any]:
        """
        生成指定 cut_height 下的建築視覺切面結構：
        - 樓面頂面
        - 實體階梯
        - 梯洞開口
        - 被切斷之牆體實心 Cap (Cut Cap)
        - 門洞與門楣
        """
        is_cut = cut_height is not None and cut_height >= 0 and cut_height < self.height
        display_height = cut_height if is_cut else float(self.height)
        visible_floor_h = self.get_visible_floor_height(cut_height)

        # 樓面基底
        base_rect = Rect(
            x=self.origin[0] * config.cell_size,
            y=self.origin[1] * config.cell_size,
            w=self.size[0] * config.cell_size,
            h=self.size[1] * config.cell_size
        )
        floor_top_rect = project_rect(base_rect, visible_floor_h, side, config)

        # 實體階梯計算
        visible_stairs = []
        if self.stair and display_height > 0:
            stair_floor_idx = min(self.floors - 1, int(display_height // self.get_floor_height()))
            stair_base_h = stair_floor_idx * self.get_floor_height()
            for flight in self.stair.flight_cells:
                step_h = stair_base_h + flight["step_offset"]
                if step_h <= display_height:
                    step_rect = project_cell_rect(flight["col"], flight["row"], step_h, side, config)
                    visible_stairs.append({"col": flight["col"], "row": flight["row"], "height": step_h, "rect": step_rect})

        # 梯洞開口計算
        opening_rects = []
        if self.stair and visible_floor_h > 0:
            for op in self.stair.opening_cells:
                op_rect = project_cell_rect(op["col"], op["row"], visible_floor_h, side, config)
                opening_rects.append(op_rect)

        # 牆體 Cap (被切斷牆頂面的實心黑色/深色 Cap)
        wall_caps = []
        if is_cut and display_height > visible_floor_h:
            for w in self.wall_cells:
                cap_rect = project_cell_rect(w["col"], w["row"], display_height, side, config)
                wall_caps.append(cap_rect)

        return {
            "building_id": self.building_id,
            "display_height": display_height,
            "visible_floor_height": visible_floor_h,
            "floor_top_rect": floor_top_rect,
            "visible_stairs": visible_stairs,
            "opening_rects": opening_rects,
            "wall_caps": wall_caps,
            "is_cut": is_cut
        }
