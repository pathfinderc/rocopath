"""
地图场景
继承 QGraphicsScene，封装点位管理、路径绘制和选择操作。

遵循 Qt Graphics View 框架设计：
- Scene 管数据和图元管理
- View 管显示和用户交互
"""

from dataclasses import dataclass
from math import sqrt
from typing import Union
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPathItem, QGraphicsLineItem
from PySide6.QtGui import QPixmap, QPainterPath, QPen, QColor, QBrush
from rocopath.ui.npc_point_item import NpcPointItem
from rocopath.ui.path_point_item import PathPointItem
from rocopath.core.route_planner import NearestNeighborPlanner, BaseRoutePlanner
from rocopath.models import NpcPoint, WorldMapInfo
from rocopath.models.path_point import PathPoint

PlannablePoint = Union[NpcPoint, PathPoint]


@dataclass
class PlannedRoute:
    """已规划的路径"""

    points: list[PlannablePoint]  # 路径点位列表
    total_distance: float  # 总距离
    color: tuple[int, int, int, int]  # 路径颜色 (RGBA)
    path_item: QGraphicsPathItem | None = None  # 绘制的路径线
    text_item: QGraphicsPathItem | None = None  # 起点序号文字标识（带轮廓）


class MapScene(QGraphicsScene):
    """地图场景，管理点位、路径和选择状态"""

    # 点位被点击选中（显示信息）时发出信号，参数是 point_id
    point_selected = Signal(str)

    # 预定义路径颜色，循环使用（RGBA，alpha=200 半透明）
    _ROUTE_COLORS: list[tuple[int, int, int, int]] = [
        (255, 0, 0, 200),  # 红
        (0, 150, 255, 200),  # 蓝
        (0, 200, 0, 200),  # 绿
        (255, 140, 0, 200),  # 橙
        (148, 0, 211, 200),  # 紫
        (255, 0, 255, 200),  # 粉
        (0, 200, 200, 200),  # 青
    ]

    def __init__(self, route_planner: BaseRoutePlanner | None = None):
        super().__init__()
        # 当前显示的NPC点位项
        self._point_items: list[NpcPointItem] = []
        # 路径点（用户自定义点）
        self._path_point_items: list[PathPointItem] = []
        # 路径规划相关状态（统一使用 point_id: str）
        self._route_selected_ids: set[str] = set()
        self._route_start_point: PlannablePoint | None = None
        # 已规划的路径列表（支持多条路径）
        self._planned_routes: list[PlannedRoute] = []
        # 路径规划算法
        self._route_planner: BaseRoutePlanner = (
            route_planner or NearestNeighborPlanner()
        )
        # add_path 模式
        self._is_add_path_mode: bool = False
        self._in_progress_path: list[PathPoint] = []
        self._in_progress_lines: list[QGraphicsLineItem] = []

    def add_background_pixmap(self, pixmap: QPixmap) -> None:
        """添加背景地图图片"""
        self.clear()
        self._point_items.clear()
        self.clear_route_selection_and_routes()
        self.addPixmap(pixmap)
        self.setSceneRect(pixmap.rect())

    def add_points(self, points: list[NpcPoint]) -> None:
        """添加多个点位到场景"""
        for point in points:
            item = NpcPointItem(point)
            self.addItem(item)
            self._point_items.append(item)
            # 转发点位点击信号
            item.point_selected.connect(self.point_selected.emit)

    def clear_points(self) -> None:
        """清除所有点位（含路径点）和路线"""
        for item in self._point_items:
            self.removeItem(item)
        self._point_items.clear()
        self.clear_route_selection_and_routes()
        self.clear_path_points()

    def select_all(self) -> None:
        """全选所有当前点位（含路径点）"""
        for item in self._point_items:
            if item.point_id not in self._route_selected_ids:
                self._route_selected_ids.add(item.point_id)
                item.set_in_box_selection(True)
        for item in self._path_point_items:
            if item.point_id not in self._route_selected_ids:
                self._route_selected_ids.add(item.point_id)
                item.set_in_box_selection(True)

        self._route_start_point = None

    def clear_route_selection(self) -> None:
        """清空所有路径选择状态（保留已规划路径）"""
        for item in self._point_items:
            item.reset_route_selection()
        for item in self._path_point_items:
            item.reset_route_selection()
        self._route_selected_ids.clear()
        self._route_start_point = None

    def clear_route_selection_and_routes(self) -> None:
        """清空所有路径选择状态和已规划路径"""
        self.clear_route_selection()
        self.clear_all_routes()

    def handle_box_selection(
        self, rect: QRectF, modifiers: Qt.KeyboardModifier
    ) -> None:
        """处理框选完成，更新选中状态（含路径点）"""
        remove_mode = modifiers & Qt.KeyboardModifier.ControlModifier

        def _process_item(item):
            nonlocal remove_mode
            pos = item.scenePos()
            if rect.contains(pos):
                if remove_mode:
                    if item.point_id in self._route_selected_ids:
                        self._route_selected_ids.discard(item.point_id)
                        item.set_in_box_selection(False)
                        item.set_route_start(False)
                        if (
                            self._route_start_point
                            and self._route_start_point.point_id == item.point_id
                        ):
                            self._route_start_point = None
                else:
                    if item.point_id not in self._route_selected_ids:
                        self._route_selected_ids.add(item.point_id)
                        item.set_in_box_selection(True)

        for item in self._point_items:
            _process_item(item)
        for item in self._path_point_items:
            _process_item(item)

    def handle_point_click(self, item: NpcPointItem | PathPointItem) -> None:
        """处理点选，切换选中状态"""
        if item.point_id in self._route_selected_ids:
            self._route_selected_ids.discard(item.point_id)
            item.set_in_box_selection(False)
            if (
                self._route_start_point
                and self._route_start_point.point_id == item.point_id
            ):
                self._route_start_point = None
                item.set_route_start(False)
        else:
            self._route_selected_ids.add(item.point_id)
            item.set_in_box_selection(True)

    def set_route_start(self, point: PlannablePoint) -> None:
        """设置路径起点"""
        # 先清除之前起点状态
        if self._route_start_point:
            old_id = self._route_start_point.point_id
            for item in self._point_items:
                if item.point_id == old_id:
                    item.set_route_start(False)
                    break
            for item in self._path_point_items:
                if item.point_id == old_id:
                    item.set_route_start(False)
                    break

        # 设置新起点
        self._route_start_point = point
        for item in self._point_items:
            if item.point_id == point.point_id:
                item.set_route_start(True)
                return
        for item in self._path_point_items:
            if item.point_id == point.point_id:
                item.set_route_start(True)
                return

    def add_route_path(self, points: list[PlannablePoint], total_distance: float) -> None:
        """添加并绘制一条新路径折线（保留已有路径）"""
        if len(points) < 2:
            return

        # 选择颜色：按顺序循环使用颜色列表
        color_index = len(self._planned_routes) % len(self._ROUTE_COLORS)
        color = self._ROUTE_COLORS[color_index]

        # 创建路径
        path = QPainterPath()
        first = points[0]
        path.moveTo(first.map_x, first.map_y)
        for point in points[1:]:
            path.lineTo(point.map_x, point.map_y)

        # 创建图形项
        path_item = QGraphicsPathItem(path)
        # 使用对应颜色粗线条，半透明
        pen = QPen(QColor(*color), 3)
        pen.setCosmetic(True)  # 缩放时保持线宽不变
        path_item.setPen(pen)
        path_item.setZValue(5)  # 在地图之上，点位之下
        self.addItem(path_item)

        # 添加起点序号文字标识（带黑色轮廓，固定大小忽略缩放）
        route_number = len(self._planned_routes) + 1
        text = str(route_number)

        # 使用 QPainterPath 创建带轮廓的文字
        font = self.font()
        font.setPointSize(14)
        font.setBold(True)
        text_path = QPainterPath()
        text_path.addText(0, 0, font, text)

        # 文字使用路径颜色填充，黑色轮廓
        brush = QBrush(QColor(*color))
        text_pen = QPen(QColor(0, 0, 0), 2)

        text_item = QGraphicsPathItem(text_path)
        text_item.setBrush(brush)
        text_item.setPen(text_pen)
        # 忽略变换，保持固定大小，不受地图缩放影响
        text_item.setFlag(
            QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations, True
        )
        # 在起点向右上方偏移
        text_item.setPos(first.map_x + 6, first.map_y - 16)
        text_item.setZValue(6)  # 在路径之上，点位之下
        self.addItem(text_item)

        # 添加到路径列表
        route = PlannedRoute(
            points=points,
            total_distance=total_distance,
            color=color,
            path_item=path_item,
            text_item=text_item,
        )
        self._planned_routes.append(route)

    def clear_all_routes(self) -> None:
        """清除所有已规划路径"""
        for route in self._planned_routes:
            if route.path_item and route.path_item.scene() == self:
                self.removeItem(route.path_item)
            if route.text_item and route.text_item.scene() == self:
                self.removeItem(route.text_item)
        self._planned_routes.clear()

    def clear_route_path(self) -> None:
        """清除路径（保留兼容调用，实际清除所有路径）"""
        self.clear_all_routes()

    # === Getter 方法供 MainWindow 获取状态更新 UI ===

    def get_selected_count(self) -> int:
        """获取选中点位数量"""
        return len(self._route_selected_ids)

    def get_route_start(self) -> PlannablePoint | None:
        """获取当前路径起点"""
        return self._route_start_point

    def get_selected_points(self) -> list[PlannablePoint]:
        """获取所有选中的点位"""
        selected: list[PlannablePoint] = []
        for item in self._point_items:
            if item.point_id in self._route_selected_ids:
                selected.append(item.npc_point)
        for item in self._path_point_items:
            if item.point_id in self._route_selected_ids:
                selected.append(item.path_point)
        return selected

    def get_all_current_points(self) -> list[PlannablePoint]:
        """获取所有当前显示的点位（含路径点）"""
        all_points: list[PlannablePoint] = []
        for item in self._point_items:
            all_points.append(item.npc_point)
        for item in self._path_point_items:
            all_points.append(item.path_point)
        return all_points

    def has_point_items(self) -> bool:
        """是否有任何点位"""
        return len(self._point_items) > 0 or len(self._path_point_items) > 0

    def is_selected(self, point_id: str) -> bool:
        """检查该点位是否已被选中"""
        return point_id in self._route_selected_ids

    def set_selected(self, point_id: str) -> None:
        """设置信息选中状态，更新所有点位视觉样式"""
        for item in self._point_items:
            item.set_selected(item.point_id == point_id)
        for item in self._path_point_items:
            item.set_selected(item.point_id == point_id)

    def get_planned_routes(self) -> list[PlannedRoute]:
        """获取所有已规划的路径"""
        return self._planned_routes

    def has_planned_routes(self) -> bool:
        """是否有已规划的路径"""
        return len(self._planned_routes) > 0

    def remove_route(self, route: PlannedRoute) -> None:
        """删除单条已规划路径"""
        if route.path_item and route.path_item.scene() == self:
            self.removeItem(route.path_item)
        if route.text_item and route.text_item.scene() == self:
            self.removeItem(route.text_item)
        if route in self._planned_routes:
            self._planned_routes.remove(route)

    def add_planned_route(
        self,
        points: list[PlannablePoint],
        total_distance: float,
        color: tuple[int, int, int, int] | None = None,
    ) -> None:
        """添加一条已规划路径，自动绘制
        如果指定 color 则使用该颜色，否则自动分配下一个颜色
        """
        if color is not None:
            # 使用指定颜色
            route = PlannedRoute(
                points=points,
                total_distance=total_distance,
                color=color,
                path_item=None,
                text_item=None,
            )
            self._planned_routes.append(route)
            # 创建并添加图形项
            if len(points) < 2:
                return

            path = QPainterPath()
            first = points[0]
            path.moveTo(first.map_x, first.map_y)
            for point in points[1:]:
                path.lineTo(point.map_x, point.map_y)

            path_item = QGraphicsPathItem(path)
            pen = QPen(QColor(*color), 3)
            pen.setCosmetic(True)
            path_item.setPen(pen)
            path_item.setZValue(5)
            self.addItem(path_item)
            route.path_item = path_item

            # 添加起点序号文字标识（带黑色轮廓，固定大小忽略缩放），序号就是当前列表中的位置
            route_number = len(self._planned_routes)
            text = str(route_number)

            font = self.font()
            font.setPointSize(14)
            font.setBold(True)
            text_path = QPainterPath()
            text_path.addText(0, 0, font, text)

            brush = QBrush(QColor(*color))
            text_pen = QPen(QColor(0, 0, 0), 1)

            text_item = QGraphicsPathItem(text_path)
            text_item.setBrush(brush)
            text_item.setPen(text_pen)
            text_item.setFlag(
                QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations, True
            )
            text_item.setPos(first.map_x + 6, first.map_y - 16)
            text_item.setZValue(6)
            self.addItem(text_item)
            route.text_item = text_item
        else:
            # 自动分配颜色
            self.add_route_path(points, total_distance)

    def plan_route(self, world_map: WorldMapInfo) -> tuple[list[PlannablePoint], float]:
        """规划路径，返回规划好的点位列表和总距离

        Args:
            world_map: 世界地图信息，用于计算距离

        Returns:
            (planned_points, total_distance)
        """
        start_point = self.get_route_start()
        selected_points = self.get_selected_points()
        if not start_point or len(selected_points) < 2:
            return [], 0.0

        # 执行规划
        planned_path = self._route_planner.plan(selected_points, start_point, world_map)

        # 计算总距离
        total_distance = 0.0
        for i in range(len(planned_path) - 1):
            total_distance += self._route_planner.distance(
                planned_path[i], planned_path[i + 1], world_map
            )

        # 添加并绘制路径（保留已有路径）
        self.add_route_path(planned_path, total_distance)

        return planned_path, total_distance

    def set_route_planner(self, planner: BaseRoutePlanner) -> None:
        """切换路径规划算法"""
        self._route_planner = planner

    # ===== add_path 模式 =====

    def enter_add_path_mode(self) -> None:
        """进入路径点创建模式"""
        self._is_add_path_mode = True
        for item in self._path_point_items:
            item.set_movable(True)

    def leave_add_path_mode(self) -> None:
        """退出路径点创建模式，完成当前路径"""
        for item in self._path_point_items:
            item.set_movable(False)
        if len(self._in_progress_path) >= 2:
            self._finalize_in_progress_path()
        self._clear_temp_lines()
        self._in_progress_path.clear()
        self._is_add_path_mode = False

    def add_path_point(self, scene_x: float, scene_y: float) -> None:
        """在 add_path 模式下添加路径点"""
        point = PathPoint(map_x=scene_x, map_y=scene_y)
        item = PathPointItem(point)
        self.addItem(item)
        self._path_point_items.append(item)
        item.point_selected.connect(self.point_selected.emit)
        item.point_moved.connect(self._on_path_point_moved)

        self._in_progress_path.append(point)

        # 绘制临时连线
        self._rebuild_temp_lines()

    def add_imported_route(
        self, path_points: list[PathPoint], total_distance: float, name: str = ""
    ) -> None:
        """导入兼容格式路径：创建路径点并绘制路线"""
        for pp in path_points:
            item = PathPointItem(pp)
            self.addItem(item)
            self._path_point_items.append(item)
            item.point_selected.connect(self.point_selected.emit)
            item.point_moved.connect(self._on_path_point_moved)

        if len(path_points) >= 2:
            self.add_route_path(path_points, total_distance)

    def clear_path_points(self) -> None:
        """清除所有路径点（reset_all 调用）"""
        for item in self._path_point_items:
            self.removeItem(item)
        self._path_point_items.clear()
        self._in_progress_path.clear()
        self._clear_temp_lines()

    # ===== 内部方法 =====

    def _on_path_point_moved(self, point_id: str) -> None:
        """路径点被拖动后更新所有关联的边"""
        self._rebuild_temp_lines()
        self._redraw_routes_for_point(point_id)

    def _rebuild_temp_lines(self) -> None:
        """重建当前构建中路径的临时连线"""
        self._clear_temp_lines()
        if len(self._in_progress_path) >= 2:
            for i in range(len(self._in_progress_path) - 1):
                a = self._in_progress_path[i]
                b = self._in_progress_path[i + 1]
                line = QGraphicsLineItem(a.map_x, a.map_y, b.map_x, b.map_y)
                line.setPen(QPen(QColor(255, 80, 40, 220), 2.5, Qt.PenStyle.SolidLine))
                line.setZValue(4)
                self.addItem(line)
                self._in_progress_lines.append(line)

    def _redraw_routes_for_point(self, point_id: str) -> None:
        """重新绘制包含指定路径点的所有已规划路径"""
        for route in self._planned_routes:
            has_point = any(
                hasattr(p, 'point_id') and p.point_id == point_id
                for p in route.points
            )
            if not has_point:
                continue
            # 移除旧边
            if route.path_item and route.path_item.scene() == self:
                self.removeItem(route.path_item)
                route.path_item = None

            # 重绘路径
            points = route.points
            if len(points) < 2:
                continue
            path = QPainterPath()
            path.moveTo(points[0].map_x, points[0].map_y)
            for p in points[1:]:
                path.lineTo(p.map_x, p.map_y)
            path_item = QGraphicsPathItem(path)
            pen = QPen(QColor(*route.color), 3)
            pen.setCosmetic(True)
            path_item.setPen(pen)
            path_item.setZValue(5)
            self.addItem(path_item)
            route.path_item = path_item

    def _finalize_in_progress_path(self) -> None:
        """将当前构建中的路径转换为正式路径"""
        points = list(self._in_progress_path)
        total_distance = sum(
            sqrt((a.map_x - b.map_x) ** 2 + (a.map_y - b.map_y) ** 2)
            for a, b in zip(points, points[1:])
        )
        self._clear_temp_lines()
        self.add_route_path(points, total_distance)

    def _clear_temp_lines(self) -> None:
        for line in self._in_progress_lines:
            if line.scene() == self:
                self.removeItem(line)
        self._in_progress_lines.clear()
