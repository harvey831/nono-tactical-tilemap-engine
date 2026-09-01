"""
projection.py
=============
2D 斜俯視共投影數學模組 (ADR-0072 & pan-layered-map-prototype.html 同構)
提供垂直高程位移 (ΔY)、動態鏡頭側向錯位 (ΔX) 與世界座標/網格座標投影轉換。
"""

import math
from typing import Dict, Tuple, NamedTuple, Optional

class Point(NamedTuple):
    x: float
    y: float

class Rect(NamedTuple):
    x: float
    y: float
    w: float
    h: float

class ProjectionConfig:
    def __init__(
        self,
        cell_size: int = 32,
        rise_ratio: float = 0.72,
        side_shift_ratio: float = 0.12,
        grid_width: int = 40,
        grid_height: int = 40
    ):
        self.cell_size = cell_size
        self.rise_ratio = rise_ratio
        self.side_shift_ratio = side_shift_ratio
        self.grid_width = grid_width
        self.grid_height = grid_height

    @property
    def rise(self) -> float:
        """每級高度垂直向上投影位移 (像素)"""
        return self.cell_size * self.rise_ratio

    @property
    def side_shift(self) -> float:
        """每級高度側向投影位移基準量 (像素)"""
        return self.cell_size * self.side_shift_ratio

    @property
    def world_width(self) -> float:
        return self.grid_width * self.cell_size

    @property
    def world_height(self) -> float:
        return self.grid_height * self.cell_size


def compute_screen_side(
    world_center_x: float,
    pan_x: float = 0.0,
    viewport_width: float = 800.0,
    cell_size: int = 32,
    mode: str = "camera"
) -> float:
    """
    計算鏡頭側向透視係數 side ∈ [-1.0, 1.0]
    - mode="fixed": 固定向右 (1.0)
    - mode="camera": 依據世界物體相對於鏡頭視口中心之距離動態平滑過渡
    """
    if mode == "fixed":
        return 1.0
    delta = pan_x + world_center_x - viewport_width * 0.5
    spread = cell_size * 6.0
    return max(-1.0, min(1.0, delta / spread))


def project_rect(
    rect: Rect,
    height: float,
    side: float,
    config: ProjectionConfig
) -> Rect:
    """
    將平面矩形依照指定高程 height 與側向係數 side 投影到位移後的 2D 矩形
    X' = X + side * height * side_shift
    Y' = Y - height * rise
    """
    return Rect(
        x=rect.x + side * height * config.side_shift,
        y=rect.y - height * config.rise,
        w=rect.w,
        h=rect.h
    )


def project_cell_rect(
    col: int,
    row: int,
    height: float,
    side: float,
    config: ProjectionConfig
) -> Rect:
    """將單個網格 (col, row) 投影為高程為 height 的 2D 矩形"""
    base = Rect(
        x=col * config.cell_size,
        y=row * config.cell_size,
        w=config.cell_size,
        h=config.cell_size
    )
    return project_rect(base, height, side, config)


def project_point(
    col: float,
    row: float,
    height: float,
    side: float,
    config: ProjectionConfig
) -> Point:
    """計算 (col, row) 中心在指定高程的 2D 螢幕錨點座標"""
    root_x = (col + 0.5) * config.cell_size + side * height * config.side_shift
    root_y = (row + 0.5) * config.cell_size - height * config.rise
    return Point(x=root_x, y=root_y)


def unproject_point(
    screen_x: float,
    screen_y: float,
    height: float,
    side: float,
    config: ProjectionConfig
) -> Tuple[int, int]:
    """將 2D 螢幕點逆投影回給定高程 height 下的整數網格座標 (col, row)"""
    world_x = screen_x - side * height * config.side_shift
    world_y = screen_y + height * config.rise
    col = int(math.floor(world_x / config.cell_size))
    row = int(math.floor(world_y / config.cell_size))
    return col, row
