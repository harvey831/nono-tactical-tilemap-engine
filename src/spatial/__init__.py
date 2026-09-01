"""
src/spatial/__init__.py
======================
諾諾 (Nono) 空間拓撲與 2D 共投影模組導出包
"""

from .projection import (
    Point, Rect, ProjectionConfig,
    compute_screen_side, project_rect, project_cell_rect, project_point, unproject_point
)
from .geometry import (
    Polygon, generate_raised_faces, generate_raised_faces_with_door, generate_pit_aperture_mask
)
from .building import (
    BuildingDef, StairDef, DoorDef, CellCoord
)
from .footprint import (
    FootprintCell, resolve_base_tile_rotation_and_count,
    compute_actor_stance, generate_height_connection_polygons
)

__all__ = [
    "Point", "Rect", "ProjectionConfig",
    "compute_screen_side", "project_rect", "project_cell_rect", "project_point", "unproject_point",
    "Polygon", "generate_raised_faces", "generate_raised_faces_with_door", "generate_pit_aperture_mask",
    "BuildingDef", "StairDef", "DoorDef", "CellCoord",
    "FootprintCell", "resolve_base_tile_rotation_and_count",
    "compute_actor_stance", "generate_height_connection_polygons"
]
