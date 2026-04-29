# 直接导入编译好的 UI 代码（标准包导入，适配 src 结构）
from PySide6.QtCore import Signal, QPointF, QRectF, Qt
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QPainter, QWheelEvent, QMouseEvent, QPen, QBrush, QColor
from rocopath.ui.npc_point_item import NpcPointItem


# 自定义可缩放/拖拽的视图
class MapView(QGraphicsView):
    """支持滚轮缩放（以鼠标为中心）和左键拖拽的地图视图
    额外支持：框选模式下右键框选点位用于路径规划。
    """

    mouse_moved = Signal(QPointF)
    box_selection_finished = Signal(QRectF, Qt.KeyboardModifier)
    point_clicked = Signal(NpcPointItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 启用抗锯齿与平滑缩放
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        # 禁用滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 设置默认光标为箭头
        self.setCursor(Qt.CursorShape.ArrowCursor)
        # 禁用内置拖拽模式，我们自己处理来控制光标
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        # 允许鼠标追踪，无需按下按键也能触发 moveEvent
        self.setMouseTracking(True)
        # 拖拽状态
        self._panning = False
        self._last_pan_pos = QPointF()
        # 缩放范围限制
        self._zoom_factor = 1.15
        self._min_scale = 0.2
        self._max_scale = 1.5
        # 框选状态
        self._is_box_dragging = False
        self._box_start_scene = QPointF()
        self._box_current_scene = QPointF()

    def wheelEvent(self, event: QWheelEvent):
        """滚轮事件：以鼠标位置为中心进行缩放"""
        # 获取鼠标在视图坐标系中的位置
        view_pos = event.position()
        # 转换为场景坐标（缩放前的场景坐标）
        scene_pos = self.mapToScene(view_pos.toPoint())

        # 计算缩放比例
        delta = event.angleDelta().y()
        if delta > 0:
            factor = self._zoom_factor
        else:
            factor = 1 / self._zoom_factor

        # 应用缩放
        current_scale = self.transform().m11()
        new_scale = current_scale * factor
        if self._min_scale <= new_scale <= self._max_scale:
            self.scale(factor, factor)

        # 将之前鼠标下的场景点重新定位到鼠标位置，实现以鼠标为中心的缩放效果
        new_view_pos = self.mapFromScene(scene_pos)
        delta_pos = view_pos - new_view_pos
        self.translate(delta_pos.x(), delta_pos.y())

        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下：
        - 左键：正常拖拽 / 点选点位（任何模式都需要，编辑模式也需要点击点位）
        - 右键：框选模式下开始框选
        """
        # 右键开始框选（始终启用）
        if event.button() == Qt.MouseButton.RightButton:
            # 右键开始框选
            self._is_box_dragging = True
            self._box_start_scene = self.mapToScene(event.position().toPoint())
            self._box_current_scene = self._box_start_scene
            event.accept()
            return

        # 左键点击：任何模式下都需要检测是否点击了点位（框选模式和编辑模式都需要）
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            items = self.scene().items(scene_pos)
            for item in items:
                if isinstance(item, NpcPointItem):
                    self.point_clicked.emit(item)
                    break
            # 开始拖拽
            if not self._is_box_dragging:
                self._panning = True
                self._last_pan_pos = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动：拖拽时平移地图 / 框选时更新矩形"""
        if self._is_box_dragging:
            # 更新框选矩形
            self._box_current_scene = self.mapToScene(event.position().toPoint())
            self.viewport().update()
            event.accept()

        if self._panning:
            current_pos = event.position()
            delta = current_pos - self._last_pan_pos
            self._last_pan_pos = current_pos
            # 平移视图
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()

        # 将视图坐标转换为场景坐标并发射信号
        scene_pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(scene_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放：结束拖拽 / 结束框选"""
        if self._is_box_dragging:
            if event.button() == Qt.MouseButton.RightButton:
                # 框选完成，发出信号
                rect = self._get_selection_rect()
                modifiers = event.modifiers()
                self.box_selection_finished.emit(rect, modifiers)
                self._is_box_dragging = False
                self.viewport().update()
                event.accept()
                return

        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()

        super().mouseReleaseEvent(event)

    def _get_selection_rect(self) -> QRectF:
        """获取当前框选矩形（场景坐标）"""
        x1, y1 = self._box_start_scene.x(), self._box_start_scene.y()
        x2, y2 = self._box_current_scene.x(), self._box_current_scene.y()
        return QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    def paintEvent(self, event):
        """绘制：如果正在框选，绘制半透明矩形框"""
        super().paintEvent(event)

        if self._is_box_dragging:
            # 在视口上绘制框选矩形
            painter = QPainter(self.viewport())
            rect = self._get_selection_rect()
            # 转换为视口坐标
            top_left = self.mapFromScene(rect.topLeft())
            bottom_right = self.mapFromScene(rect.bottomRight())
            painter_rect = QRectF(top_left, bottom_right).normalized()

            # 半透明浅蓝色填充 + 蓝色边框
            painter.setPen(QPen(QColor(100, 149, 237, 255), 2))
            painter.setBrush(QBrush(QColor(100, 149, 237, 50)))
            painter.drawRect(painter_rect)
            painter.end()

    