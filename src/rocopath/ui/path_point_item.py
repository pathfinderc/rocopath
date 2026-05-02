"""
路径点图形项

在 QGraphicsScene 中显示用户自定义路径点标记。
与 NpcPointItem 的区别：
- 菱形外观（蓝色系），区别于 NPC 圆点
- 支持拖拽移动（add_path 模式下）
- point_id 为 str 类型
"""

from PySide6.QtCore import Signal, QObject, QPointF
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsPathItem
from PySide6.QtGui import QBrush, QColor, QPen, QPainterPath
from rocopath.models.path_point import PathPoint


DIAMOND_SIZE = 5
NORMAL_COLOR = QColor(30, 144, 255, 255)  # 蓝色
SELECTED_COLOR = QColor(40, 200, 40, 255)  # 绿色
HOVER_COLOR = QColor(255, 140, 0, 255)     # 橙色


class PathPointItem(QObject, QGraphicsItemGroup):
    """路径点图形项

    菱形标记，蓝色，可拖拽移动，参与路径规划。
    """

    point_selected = Signal(str)  # 发出选中的 point_id

    def __init__(self, path_point: PathPoint):
        QObject.__init__(self)
        QGraphicsItemGroup.__init__(self)
        self.path_point = path_point
        self._is_selected = False
        self._in_box_selection = False
        self._is_route_start = False

        # 菱形：正方形旋转 45 度
        half = DIAMOND_SIZE
        diamond = QPainterPath()
        diamond.moveTo(0, -half)
        diamond.lineTo(half, 0)
        diamond.lineTo(0, half)
        diamond.lineTo(-half, 0)
        diamond.closeSubpath()

        self._shape_item = QGraphicsPathItem(diamond, self)
        self._normal_brush = QBrush(NORMAL_COLOR)
        self._update_visual_style()

        self.setPos(path_point.map_x, path_point.map_y)

        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemIsFocusable, True)
        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

        # 可拖拽（在 add_path 模式下由外部控制行为）
        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemIsMovable, False)

    def set_movable(self, movable: bool) -> None:
        """设置是否可拖拽移动（仅在 add_path 模式下启用）"""
        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    @property
    def point_id(self) -> str:
        return self.path_point.point_id

    @property
    def refresh_id(self) -> str:
        """兼容旧代码使用 refresh_id 的地方，实际返回 point_id"""
        return self.path_point.point_id

    def mousePressEvent(self, event):
        self.point_selected.emit(self.point_id)
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        self._shape_item.setBrush(QBrush(HOVER_COLOR))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if self._is_selected:
            self._shape_item.setBrush(QBrush(SELECTED_COLOR))
        else:
            self._shape_item.setBrush(self._normal_brush)
        super().hoverLeaveEvent(event)

    def set_selected(self, is_selected: bool) -> None:
        self._is_selected = is_selected
        self.setSelected(is_selected)
        if is_selected:
            self._shape_item.setBrush(QBrush(SELECTED_COLOR))
        else:
            self._shape_item.setBrush(self._normal_brush)

    def itemChange(self, change, value):
        if change == QGraphicsItemGroup.GraphicsItemChange.ItemPositionHasChanged:
            # 拖拽后同步更新 model 坐标
            self.path_point.map_x = self.pos().x()
            self.path_point.map_y = self.pos().y()
        return super().itemChange(change, value)

    def set_in_box_selection(self, in_selection: bool) -> None:
        self._in_box_selection = in_selection
        self._update_visual_style()

    def set_route_start(self, is_start: bool) -> None:
        self._is_route_start = is_start
        self._update_visual_style()

    def reset_route_selection(self) -> None:
        self._in_box_selection = False
        self._is_route_start = False
        self._update_visual_style()

    @property
    def is_in_box_selection(self) -> bool:
        return self._in_box_selection

    def _update_visual_style(self) -> None:
        if self._is_route_start:
            fill_color = QColor(128, 0, 128, 255)  # 紫色
        elif self._is_selected:
            fill_color = SELECTED_COLOR
        else:
            fill_color = NORMAL_COLOR

        self._shape_item.setBrush(QBrush(fill_color))

        if self._in_box_selection:
            pen = QPen(QColor(255, 255, 255, 255), 2.5)
        else:
            pen = QPen(QColor(0, 0, 0, 255), 1.5)

        self._shape_item.setPen(pen)
