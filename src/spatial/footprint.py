"""
footprint.py
============
多格演員跨高低差底盤與斜向面片連接模組 (ADR-0072 & pan-layered-map-prototype.html 同構)
提供：
1. 多格演員阻尼加權 Stance 站姿中心計算
2. 跨階正交相鄰底盤連接斜面 (Height Connection Polygons)
3. 底盤 4-方向連接次數與旋轉角度計算
"""

from typing import List, Dict, Tuple, Set, Optional, Any
from .projection import Rect, Point, ProjectionConfig, project_rect, project_cell_rect
from .geometry import Polygon

FOOTPRINT_DIRECTIONS = [
    {"x": 0, "y": -1, "rotation": 0},
    {"x": 1, "y": 0, "rotation": 90},
    {"x": 0, "y": 1, "rotation": 180},
    {"x": -1, "y": 0, "rotation": 270}
]

class FootprintCell:
    def __init__(self, col: int, row: int, height: int):
        self.col = col
        self.row = row
        self.height = height

    def key(self) -> str:
        return f"{self.col},{self.row}"


def resolve_base_tile_rotation_and_count(
    cell: FootprintCell,
    all_cells: List[FootprintCell]
) -> Tuple[int, int]:
    """
    計算單格底盤貼圖的相鄰連接數與旋轉角度 (0/90/180/270 度)
    """
    occupied: Set[str] = {c.key() for c in all_cells}
    neighbors = [
        d for d in FOOTPRINT_DIRECTIONS
        if f"{cell.col + d['x']},{cell.row + d['y']}" in occupied
    ]
    count = len(neighbors)
    if count == 0:
        return 0, 0
    if count == 1:
        return neighbors[0]["rotation"], 1
    if count == 2:
        # 對向 (直線) vs 鄰向 (拐角)
        if neighbors[0]["x"] + neighbors[1]["x"] == 0 and neighbors[0]["y"] + neighbors[1]["y"] == 0:
            is_horizontal = any(d["x"] != 0 for d in neighbors)
            return (90 if is_horizontal else 0), 2

        # 拐角旋轉判斷
        has = lambda x, y: any(d["x"] == x and d["y"] == y for d in neighbors)
        if has(0, -1) and has(1, 0): rot = 0
        elif has(1, 0) and has(0, 1): rot = 90
        elif has(0, 1) and has(-1, 0): rot = 180
        else: rot = 270
        return rot, 2
    if count == 3:
        if not any(d["x"] == -1 and d["y"] == 0 for d in neighbors): rot = 0
        elif not any(d["x"] == 0 and d["y"] == -1 for d in neighbors): rot = 90
        elif not any(d["x"] == 1 and d["y"] == 0 for d in neighbors): rot = 180
        else: rot = 270
        return rot, 3

    return 0, 4


def compute_actor_stance(
    cells: List[FootprintCell],
    config: ProjectionConfig,
    side: float
) -> Tuple[Point, int]:
    """
    計算多格演員的錨定核心高程與阻尼加權 Stance 螢幕座標
    """
    if not cells:
        return Point(0, 0), 0

    anchor = cells[0]
    core_height = anchor.height
    n = len(cells)

    offsets_x = [c.col - anchor.col for c in cells]
    offsets_y = [c.row - anchor.row for c in cells]

    avg_x = sum(offsets_x) / n
    avg_y = sum(offsets_y) / n

    min_x, max_x = min(offsets_x), max(offsets_x)
    min_y, max_y = min(offsets_y), max(offsets_y)
    fills_bounding_box = (n == (max_x - min_x + 1) * (max_y - min_y + 1))
    damping = 1.0 if fills_bounding_box else (1.0 - 1.0 / n)

    stance_col = anchor.col + 0.5 + damping * avg_x
    stance_row = anchor.row + 0.5 + damping * avg_y

    root_x = stance_col * config.cell_size + side * core_height * config.side_shift
    root_y = stance_row * config.cell_size - core_height * config.rise

    return Point(x=root_x, y=root_y), core_height


def generate_height_connection_polygons(
    cells: List[FootprintCell],
    config: ProjectionConfig,
    side: float,
    cut_height: Optional[float] = None
) -> List[Polygon]:
    """
    當多格演員跨越不同高度時，在相鄰正交格之間生成斜向連接面片 (Height Connection Polygon)
    """
    visible_cells = [c for c in cells if cut_height is None or c.height <= cut_height]
    visible_keys = {c.key() for c in visible_cells}
    polygons: List[Polygon] = []

    for i, a in enumerate(cells):
        for j in range(i + 1, len(cells)):
            b = cells[j]
            if a.key() not in visible_keys or b.key() not in visible_keys:
                continue
            dx = b.col - a.col
            dy = b.row - a.row
            if abs(dx) + abs(dy) != 1 or a.height == b.height:
                continue

            rect_a = project_cell_rect(a.col, a.row, a.height, side, config)
            rect_b = project_cell_rect(b.col, b.row, b.height, side, config)

            if dx != 0:
                ax = rect_a.x + rect_a.w if dx > 0 else rect_a.x
                bx = rect_b.x if dx > 0 else rect_b.x + rect_b.w
                pts = [
                    Point(ax, rect_a.y),
                    Point(bx, rect_b.y),
                    Point(bx, rect_b.y + rect_b.h),
                    Point(ax, rect_a.y + rect_a.h)
                ]
            else:
                ay = rect_a.y + rect_a.h if dy > 0 else rect_a.y
                by = rect_b.y if dy > 0 else rect_b.y + rect_b.h
                pts = [
                    Point(rect_a.x, ay),
                    Point(rect_a.x + rect_a.w, ay),
                    Point(rect_b.x + rect_b.w, by),
                    Point(rect_b.x, by)
                ]

            polygons.append(Polygon(
                points=pts,
                fill="var(--accent-gold, #f2c94c)",
                stroke_width=1.0,
                data_attrs={"height_connection": f"{min(a.height, b.height)}-{max(a.height, b.height)}"}
            ))

    return polygons
