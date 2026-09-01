"""
geometry.py
===========
空間幾何與面片計算模組 (ADR-0072 & pan-layered-map-prototype.html 同構)
提供：
1. 懸崖正面崖壁 (Cliff Front) 與側面斜壁 (Cliff Side) 面片生成
2. 負高程洞口 Mask (Pit Aperture Mask) 生成
3. 帶門立面 (Front Wall with Door & Lintel) 幾何面片
4. 梯洞 (Stair Void) 與天花板開口幾何
"""

from typing import List, Dict, Tuple, Optional, Any
from .projection import Rect, Point, ProjectionConfig, project_rect

class Polygon:
    def __init__(self, points: List[Point], fill: str, stroke: str = "var(--plm-edge)", stroke_width: float = 1.4, data_attrs: Optional[Dict[str, Any]] = None):
        self.points = points
        self.fill = fill
        self.stroke = stroke
        self.stroke_width = stroke_width
        self.data_attrs = data_attrs or {}

    def to_svg_points(self) -> str:
        return " ".join(f"{round(p.x, 2)},{round(p.y, 2)}" for p in self.points)


def generate_raised_faces(
    top_rect: Rect,
    lower_rect: Rect,
    side: float,
    front_fill: str = "var(--plm-cliff-front)",
    side_fill: str = "var(--plm-cliff-side)"
) -> List[Polygon]:
    """
    生成高低落差立面：包含正面懸崖面片與根據 side 係數決定的側面斜壁面片
    """
    faces: List[Polygon] = []

    # 正面崖壁 (四邊形：頂面底邊 -> 下層底邊)
    front_pts = [
        Point(top_rect.x, top_rect.y + top_rect.h),
        Point(top_rect.x + top_rect.w, top_rect.y + top_rect.h),
        Point(lower_rect.x + lower_rect.w, lower_rect.y + lower_rect.h),
        Point(lower_rect.x, lower_rect.y + lower_rect.h)
    ]
    faces.append(Polygon(points=front_pts, fill=front_fill, data_attrs={"type": "cliff_front"}))

    # 側面斜壁
    if side < -0.03:
        # 右側斜壁 (視角朝右，露出物體右側面)
        side_pts = [
            Point(top_rect.x + top_rect.w, top_rect.y),
            Point(top_rect.x + top_rect.w, top_rect.y + top_rect.h),
            Point(lower_rect.x + lower_rect.w, lower_rect.y + lower_rect.h),
            Point(lower_rect.x + lower_rect.w, lower_rect.y)
        ]
        faces.append(Polygon(points=side_pts, fill=side_fill, data_attrs={"type": "cliff_side_right"}))
    elif side > 0.03:
        # 左側斜壁 (視角朝左，露出物體左側面)
        side_pts = [
            Point(top_rect.x, top_rect.y),
            Point(top_rect.x, top_rect.y + top_rect.h),
            Point(lower_rect.x, lower_rect.y + lower_rect.h),
            Point(lower_rect.x, lower_rect.y)
        ]
        faces.append(Polygon(points=side_pts, fill=side_fill, data_attrs={"type": "cliff_side_left"}))

    return faces


def generate_raised_faces_with_door(
    top_rect: Rect,
    lower_rect: Rect,
    side: float,
    door_start_fraction: float,
    door_end_fraction: float,
    visible_wall_height: float,
    door_height: float = 1.65,
    wall_fill: str = "var(--plm-wall)",
    wall_side_fill: str = "var(--plm-wall-side)",
    interior_fill: str = "var(--plm-interior)"
) -> List[Polygon]:
    """
    生成含大門開口之正面實心牆與門楣 (Lintel)
    """
    polygons: List[Polygon] = []
    top_y = top_rect.y + top_rect.h
    bottom_y = lower_rect.y + lower_rect.h
    wall_height = max(0.001, visible_wall_height)
    visible_door_height = min(door_height, wall_height)
    door_top_t = (wall_height - visible_door_height) / wall_height
    door_top_y = top_y + (bottom_y - top_y) * door_top_t

    top_door_left = top_rect.x + top_rect.w * door_start_fraction
    top_door_right = top_rect.x + top_rect.w * door_end_fraction
    bottom_door_left = lower_rect.x + lower_rect.w * door_start_fraction
    bottom_door_right = lower_rect.x + lower_rect.w * door_end_fraction

    door_top_left = top_door_left + (bottom_door_left - top_door_left) * door_top_t
    door_top_right = top_door_right + (bottom_door_right - top_door_right) * door_top_t

    # 左側實心牆
    left_wall = [
        Point(top_rect.x, top_y),
        Point(top_door_left, top_y),
        Point(bottom_door_left, bottom_y),
        Point(lower_rect.x, bottom_y)
    ]
    polygons.append(Polygon(points=left_wall, fill=wall_fill, data_attrs={"type": "wall_left_of_door"}))

    # 右側實心牆
    right_wall = [
        Point(top_door_right, top_y),
        Point(top_rect.x + top_rect.w, top_y),
        Point(lower_rect.x + lower_rect.w, bottom_y),
        Point(bottom_door_right, bottom_y)
    ]
    polygons.append(Polygon(points=right_wall, fill=wall_fill, data_attrs={"type": "wall_right_of_door"}))

    # 門楣 (Lintel) — 當牆高大於門高時存在
    if wall_height > door_height:
        lintel = [
            Point(top_door_left, top_y),
            Point(top_door_right, top_y),
            Point(door_top_right, door_top_y),
            Point(door_top_left, door_top_y)
        ]
        polygons.append(Polygon(points=lintel, fill=wall_fill, data_attrs={"type": "door_lintel"}))

    # 門洞開口 (Doorway Aperture)
    doorway = [
        Point(door_top_left, door_top_y),
        Point(door_top_right, door_top_y),
        Point(bottom_door_right, bottom_y),
        Point(bottom_door_left, bottom_y)
    ]
    polygons.append(Polygon(points=doorway, fill=interior_fill, data_attrs={"type": "doorway_opening"}))

    # 側面外牆
    if side < -0.03:
        side_wall = [
            Point(top_rect.x + top_rect.w, top_rect.y),
            Point(top_rect.x + top_rect.w, top_y),
            Point(lower_rect.x + lower_rect.w, bottom_y),
            Point(lower_rect.x + lower_rect.w, lower_rect.y)
        ]
        polygons.append(Polygon(points=side_wall, fill=wall_side_fill, data_attrs={"type": "wall_side_right"}))
    elif side > 0.03:
        side_wall = [
            Point(top_rect.x, top_rect.y),
            Point(top_rect.x, top_y),
            Point(lower_rect.x, bottom_y),
            Point(lower_rect.x, lower_rect.y)
        ]
        polygons.append(Polygon(points=side_wall, fill=wall_side_fill, data_attrs={"type": "wall_side_left"}))

    return polygons


def generate_pit_aperture_mask(
    ground_rect: Rect,
    hole_rects: List[Rect],
    mask_id: str
) -> Dict[str, Any]:
    """
    生成負高程洞口 Mask 資料結構：在地表白平面中挖去 hole_rects 黑方塊
    """
    return {
        "mask_id": mask_id,
        "ground_rect": ground_rect,
        "hole_rects": hole_rects
    }
