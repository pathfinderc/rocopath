"""
主窗口

负责UI事件处理，调用 Controller 执行业务逻辑，显示结果。
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QMessageBox, QDialog, QLabel, QPushButton,
)
from PySide6.QtGui import QPixmap
from loguru import logger

from rocopath.ui import Ui_MainWindow
from rocopath.utils import pil_image_to_qimage
from rocopath.ui.map_view import MapView, InteractionMode
from rocopath.ui.map_scene import MapScene, PlannablePoint
from rocopath.ui.npc_point_item import NpcPointItem
from rocopath.ui.path_point_item import PathPointItem
from rocopath.ui.filter_panel import FilterPanel
from rocopath.ui.export_import_panel import ExportImportPanel
from rocopath.ui.route_planning_manager import RoutePlanningManager
from rocopath.core.map_controller import MapController
from rocopath.models import NpcPoint
from rocopath.models.path_point import PathPoint
from rocopath.config import BIGWORLD_MAP_ID


class MainWindow(QMainWindow):
    def __init__(self, map_controller: MapController):
        super().__init__()
        # 依赖注入：控制器由外部创建传入
        self.map_controller = map_controller
        # 加载 UI 设计文件
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # 当前地图ID
        self._current_map_id: str = ""
        # 当前点击选中查看信息的点位
        self._selected_point: PlannablePoint | None = None
        # 基础点位集合 - 只由 checkbox 筛选结果决定，line_search 不修改它
        self._base_points: list[NpcPoint] | None = None
        # 筛选面板（处理快捷筛选和规则筛选）
        self._filter_panel: FilterPanel | None = None
        # 导出导入面板
        self._export_import_panel: ExportImportPanel | None = None
        # 地图场景（管理点位、路径、选择状态）
        self.map_scene: MapScene

        # 更新 UI 元素
        self.update_ui()

    def update_ui(self):
        """初始化所有UI元素"""
        self._init_map_view()
        self._set_search_group()
        self._set_point_filter()
        self._init_export_import_panel()
        self._init_route_planning_manager()
        self._connect_menu_actions()
        self._connect_search()
        self._connect_route_planning()
        self._set_help_text()
        self.load_map(BIGWORLD_MAP_ID)

    def _init_export_import_panel(self):
        """初始化导出导入面板"""
        self._export_import_panel = ExportImportPanel(
            parent=self,
            get_map_scene=lambda: self.map_scene,
            get_map_controller=lambda: self.map_controller,
            get_current_map_id=lambda: self._current_map_id,
            show_status=lambda msg: self.ui.statusbar.showMessage(msg),
        )

    def _init_route_planning_manager(self):
        """初始化路径规划管理器"""
        self._route_planning_manager = RoutePlanningManager(
            get_map_scene=lambda: self.map_scene,
            get_map_controller=lambda: self.map_controller,
            get_current_map_id=lambda: self._current_map_id,
            get_selected_point=lambda: self._selected_point,
            set_selected_point=lambda p: setattr(self, "_selected_point", p),
            show_point_info=lambda text: self.ui.point_info.setText(text),
            show_status=lambda msg: self.ui.statusbar.showMessage(msg),
            set_select_num_text=lambda text: self.ui.select_num.setText(text),
            set_start_status_text=lambda text: self.ui.start_status.setText(text),
            set_clear_select_enabled=lambda enabled: self.ui.clear_select.setEnabled(enabled),
            set_reset_all_enabled=lambda enabled: self.ui.reset_all.setEnabled(enabled),
            set_plan_route_enabled=lambda enabled: self.ui.plan_route.setEnabled(enabled),
        )

    def _set_search_group(self):
        """设置搜索框事件处理"""
        # 回车也触发搜索
        self.ui.line_search.returnPressed.connect(self._do_search)

    def _set_point_filter(self):
        """创建筛选面板并构建UI"""
        # 获取所有刷新规则
        rules = self.map_controller.get_all_refresh_rules()
        # 创建筛选面板并构建
        self._filter_panel = FilterPanel(
            tab_widget=self.ui.tabWidget,
            on_filter_changed=self._on_filter_changed,
            on_keywords_changed=self._on_keywords_changed
        )
        self._filter_panel.build(rules)

    def _on_keywords_changed(self, keywords: str) -> None:
        """关键词变化：更新搜索框文本"""
        self.ui.line_search.setText(keywords)

    def _connect_menu_actions(self):
        """连接菜单栏动作"""
        # 切换地图
        from rocopath.config import MAGIC_ACADEMY_MAP_ID, BIGWORLD_MAP_ID
        self.ui.action_main_map.triggered.connect(lambda: self.load_map(BIGWORLD_MAP_ID))
        self.ui.action_magic_map.triggered.connect(lambda: self.load_map(MAGIC_ACADEMY_MAP_ID))
        # 键位说明
        self.ui.action_key.triggered.connect(self._show_key_bindings)
        # 关于
        self.ui.action_about.triggered.connect(self._show_about)
        # 兼容格式导出
        self.ui.action_compatible_export.triggered.connect(self._on_compatible_export)
        # 新兼容格式导出
        self.ui.action_new_compatible_export.triggered.connect(self._on_new_compatible_export)
        # 导入资源点文件
        self.ui.action_import_points.triggered.connect(self._on_npc_import)
        # 导入兼容格式路径
        self.ui.action_import_old.triggered.connect(self._on_import_old)
        self.ui.action_import_new.triggered.connect(self._on_import_new)
        # action_export / action_export_point / action_export_route / action_export_all_points / action_import_route 暂不连接（预留后续新功能）

    def _connect_search(self):
        """连接搜索按钮"""
        self.ui.search_button.clicked.connect(self._do_search)

    def _connect_route_planning(self):
        """连接路径规划相关UI信号"""
        # 全选/清空按钮
        self.ui.select_all.clicked.connect(self._on_select_all_clicked)
        self.ui.clear_select.clicked.connect(self._on_clear_select_clicked)
        self.ui.reset_all.clicked.connect(self._on_reset_route_selection_clicked)
        # 规划路径按钮（选择起点简化为自动）
        self.ui.plan_route.clicked.connect(self._on_plan_route_clicked)
        # 合并路径和删除选中点
        self.ui.merge_select.clicked.connect(self._on_merge_select_clicked)
        self.ui.remove_select.clicked.connect(self._on_remove_select_clicked)
        # MapView 信号
        self.map_view.box_selection_finished.connect(self._handle_box_selection)
        self.map_view.point_clicked.connect(self._handle_point_click)
        self.map_view.path_point_clicked.connect(self._handle_path_point_click)
        self.map_view.path_point_created.connect(self._handle_path_point_created)
        # add_path checkbox
        self.ui.add_path.toggled.connect(self._on_add_path_toggled)
        # 初始化UI状态
        self._route_planning_manager._update_route_ui_state()

    def load_map(self, map_id: str) -> bool:
        """
        通过控制器加载并显示地图

        Returns:
            加载成功返回 True，失败返回 False
        """
        map_info = self.map_controller.load_map(map_id)
        if map_info is None or map_info.image is None:
            logger.warning("地图加载失败: {}", map_id)
            return False

        self._current_map_id = map_id
        q_image = pil_image_to_qimage(map_info.image)
        # 转 QPixmap（给 QGraphicsView 显示）
        pixmap = QPixmap.fromImage(q_image)

        # 先清点位（从列表移除，避免删除已经被scene.clear删除的对象）
        self._clear_point_items()
        self._clear_point_info()
        # 切换地图清空路径规划选择、路线和路径点
        self._clear_route_selection()
        self._clear_route_selection_and_routes()
        self.map_scene.clear_path_points()

        # 清除旧内容添加新地图
        self.map_scene.add_background_pixmap(pixmap)
        # 将视图中心定位到图片中心
        self.map_view.centerOn(self.map_scene.sceneRect().center())
        # 更新窗口标题
        self.setWindowTitle(f"洛寻 - {map_info.name}")
        return True

    def _init_map_view(self):
        """初始化地图视图"""
        group_box = self.ui.map_group
        layout = QVBoxLayout(group_box)
        self.map_view = MapView()
        layout.addWidget(self.map_view)

        self.map_scene = MapScene()
        self.map_view.setScene(self.map_scene)
        self.map_view.mouse_moved.connect(self.update_status_bar_coordinates)
        # 连接点位选中信号（只需要连接一次）
        self.map_scene.point_selected.connect(self._on_point_selected)

    def update_status_bar_coordinates(self, scene_pos: QPointF):
        """更新状态栏显示当前场景坐标"""
        x = int(scene_pos.x())
        y = int(scene_pos.y())
        self.ui.statusbar.showMessage(f"坐标: ({x}, {y})")

    def _on_filter_changed(self):
        """筛选规则变化（checkbox 变化）：重新计算基础点位，清空搜索框，显示全部"""
        # checkbox 变化，清除所有路径规划选择和绘制
        self._clear_route_selection()
        # 清空搜索框，line_search 不影响基础点位
        self.ui.line_search.clear()
        # 重新计算基础点位
        self._rebuild_base_points()
        # 显示全部基础点位
        self._do_search()

    def _rebuild_base_points(self):
        """根据当前 checkbox 勾选状态重新计算基础点位集合

        QuickFilter 搜索逻辑：每个勾选的 QuickFilter 单独计算结果，最后取并集
        result = (quick_filter_1 result) ∪ (quick_filter_2 result) ∪ ...
        每个 quick_filter result = (rule in rule_ids) AND (name contains any keyword)
        最后如果有额外勾选的 rule_ids（来自 tab_3 手动勾选），再做一次规则筛选
        """
        if not self._current_map_id or not self._filter_panel:
            self._base_points = []
            return

        all_points = self.map_controller.get_all_points(self._current_map_id)
        selected_rule_ids = self._filter_panel.get_selected_rule_ids()
        selected_quick_filters = self._filter_panel.get_all_selected_quick_filters()

        logger.debug("重新计算基础点位: quick_filters={}, rule_ids={}",
                    len(selected_quick_filters), len(selected_rule_ids))

        # 如果没有勾选任何规则，清空
        if not selected_rule_ids:
            self._base_points = []
            self.ui.point_info.setText("请至少勾选一个刷新规则")
            logger.info("基础点位: 没有勾选任何规则 → 清空")
            return

        # 如果没有勾选 QuickFilter，只按 rule_ids 筛选
        if not selected_quick_filters:
            self._base_points = self.map_controller.filter_by_rule_ids(
                all_points, selected_rule_ids
            )
            logger.info("基础点位: 无 QuickFilter，按规则筛选 → {} 个点位", len(self._base_points))
            return

        # 每个勾选的 QuickFilter 单独计算，结果取并集
        result_set: dict[int, NpcPoint] = {}  # 使用 refresh_id 去重

        for qf in selected_quick_filters:
            # QuickFilter: (rule in rule_ids) AND (name contains any keyword)
            qf_result = self.map_controller.filter_by_rule_ids(all_points, qf.rule_ids)
            if qf.keywords and any(k.strip() for k in qf.keywords):
                qf_result = self.map_controller.filter_by_any_keyword(qf_result, qf.keywords)
            # 添加到结果集合（去重）
            for point in qf_result:
                result_set[point.refresh_id] = point

        # 将结果转为列表
        quick_result = list(result_set.values())

        # 最后按 tab_3 当前所有勾选的 rule_ids 再筛选一次
        # 保证 tab_3 手动勾选的规则会包含，取消勾选的会排除
        self._base_points = self.map_controller.filter_by_rule_ids(quick_result, selected_rule_ids)

        logger.info("基础点位: {} QuickFilters → {} 个点位",
                    len(selected_quick_filters), len(self._base_points))

    def _do_search(self):
        """执行搜索：line_search 在基础点位中进一步筛选，不修改 _base_points"""
        if not self._base_points:
            self._clear_point_items()
            if self._base_points is not None:
                self.ui.point_info.setText("未找到匹配点位")
            return

        keyword = self.ui.line_search.text().strip()

        if not keyword:
            # 关键词为空，显示全部基础点位
            points = self._base_points
        else:
            # 在基础点位中筛选
            points = self.map_controller.filter_by_keyword(self._base_points, keyword)

        logger.debug("line_search: keyword='{}' → base={}, result={}",
                    keyword, len(self._base_points), len(points))

        # 打印前5个点的坐标方便调试
        if points:
            sample = [f"({p.map_x:.1f}, {p.map_y:.1f})" for p in points[:5]]
            logger.debug("前5个点位坐标示例: {}", ", ".join(sample))

        self._clear_point_items()
        self._clear_point_info()
        # 搜索刷新点位后清空路径规划选择
        self._clear_route_selection()
        self._show_points(points)

        if not points:
            self.ui.point_info.setText("未找到匹配点位")

    def _clear_point_items(self):
        """清除当前显示的所有点位"""
        self.map_scene.clear_points()
        self._selected_point = None

    def _clear_point_info(self):
        """清除点位信息"""
        self.ui.point_info.clear()

    def _show_points(self, points: list[NpcPoint]):
        """在地图上显示搜索到的点位"""
        logger.debug("_show_points: 开始添加 {} 个点位到场景", len(points))
        self.map_scene.add_points(points)
        logger.debug("_show_points: 添加完成，当前共有 {} 个点位项", self.map_scene.get_selected_count())
        # 在状态栏显示找到的点位数量
        self.ui.statusbar.showMessage(f"共找到 {len(points)} 个点位")

    def _on_point_selected(self, point_id: str):
        """点位被点击：显示详情"""
        self._route_planning_manager.on_point_selected(point_id)

    def _on_select_all_clicked(self) -> None:
        """全选当前显示的所有点位"""
        self._route_planning_manager.on_select_all()

    def _on_clear_select_clicked(self) -> None:
        """清空选中状态，但保留已规划路径"""
        self._route_planning_manager.on_clear_selection()

    def _on_reset_route_selection_clicked(self) -> None:
        """清空所有路径选择和已规划路径"""
        self._route_planning_manager.on_reset_all()

    def _clear_route_selection(self) -> None:
        """清空所有路径选择状态（保留已规划路径）"""
        self._route_planning_manager._clear_route_selection()

    def _clear_route_selection_and_routes(self) -> None:
        """清空所有路径选择和已规划路径"""
        self._route_planning_manager._clear_route_selection_and_routes()

    def _handle_box_selection(self, rect: QRectF, modifiers: Qt.KeyboardModifier) -> None:
        """处理框选完成：添加或移除矩形内的点位"""
        self._route_planning_manager.handle_box_selection(rect, modifiers)

    def _handle_point_click(self, item: NpcPointItem) -> None:
        """处理NpcPoint点选：toggle 选中状态"""
        self._route_planning_manager.handle_point_click(item)

    def _handle_path_point_click(self, item: PathPointItem) -> None:
        """处理PathPoint点选：toggle 选中状态"""
        self._route_planning_manager.handle_point_click(item)

    def _handle_path_point_created(self, scene_pos: QPointF) -> None:
        """add_path 模式下空白处点击创建路径点"""
        self.map_scene.add_path_point(scene_pos.x(), scene_pos.y())

    def _on_add_path_toggled(self, checked: bool) -> None:
        """add_path checkbox 切换"""
        if checked:
            self.map_view.set_interaction_mode(InteractionMode.ADD_PATH)
            self.map_scene.enter_add_path_mode()
        else:
            self.map_view.set_interaction_mode(InteractionMode.NORMAL)
            self.map_scene.leave_add_path_mode()

    def _on_import_old(self) -> None:
        """导入旧版兼容格式"""
        assert self._export_import_panel is not None
        self._export_import_panel.import_compatible_old()

    def _on_import_new(self) -> None:
        """导入新版兼容格式"""
        assert self._export_import_panel is not None
        self._export_import_panel.import_compatible_new()

    def _on_plan_route_clicked(self) -> None:
        """点击规划路径按钮"""
        self._route_planning_manager.on_plan_route()

    def _show_key_bindings(self):
        """显示键位说明对话框"""
        key_info = """左键点选地图标点
按住左键拖动地图
右键框选点位
Ctrl+右键取消框选点位
点击框选点位中的一个则自动设置为起点
设置起点后可以点击规划路径算出路径"""
        QMessageBox.information(
            self,
            "键位说明",
            key_info,
            QMessageBox.StandardButton.Ok
        )

    def _show_about(self):
        """显示关于对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("关于")
        dialog.setFixedSize(350, 180)

        layout = QVBoxLayout(dialog)

        label = QLabel("""<h3>洛寻 (rocopath)</h3>
<p>《洛克王国：世界》采集路径规划工具</p>
<p>项目地址：<br>
<a href="https://github.com/pathfinderc/rocopath">https://github.com/pathfinderc/rocopath</a></p>""")
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)

        layout.addWidget(label)
        layout.addWidget(ok_button)

        dialog.exec()

    def _on_new_compatible_export(self):
        """导出新版兼容格式路径"""
        assert self._export_import_panel is not None
        self._export_import_panel.export_new_compatible()

    def _on_compatible_export(self):
        """导出旧版兼容格式路径"""
        assert self._export_import_panel is not None
        self._export_import_panel.export_compatible()

    def _on_npc_export(self):
        """导出全部NPC点位"""
        assert self._export_import_panel is not None
        self._export_import_panel.export_npc_points()

    def _on_npc_import(self):
        """导入NPC点位"""
        assert self._export_import_panel is not None
        self._export_import_panel.import_npc_points(
            rebuild_callback=lambda: (self._rebuild_base_points(), self._do_search())
        )

    def _on_export_current_points(self):
        """导出当前显示的点位"""
        assert self._export_import_panel is not None
        self._export_import_panel.export_current_points()

    def _on_export_routes(self):
        """导出所有规划路径"""
        assert self._export_import_panel is not None
        self._export_import_panel.export_routes()

    def _set_help_text(self):
        """设置使用帮助文本"""
        help_text = """<h3>操作说明</h3>
<b>=== 基本操作 ===</b><br>
• 左键拖动 → 平移地图<br>
• 右键拖动 → 框选点位（可多次框选）<br>
• Ctrl + 右键拖动 → 框选取消点位<br>
<br>
<b>=== 路径规划 ===</b><br>
• 框选多个点位后，点击其中一个点位自动设为起点<br>
• 点击「规划路径」→ 生成路径，自动清空选中，可继续规划下一条<br>
• 每条路径起点显示序号，序号与导出文件名对应<br>
• 点击「清空」→ 清空所有选择和所有已规划路径<br>
<br>
<b>=== 移除选中点 ===</b><br>
• 框选路径上要删除的点<br>
• 点击「移除选中」→ 删除选中点，自动将路径分割为多条<br>
• 分割后长度不足 2 个点的路径自动删除<br>
<br>
<b>=== 合并路径 ===</b><br>
• 必须框选：<i>所有需要合并路径</i> 的 <i>所有连接端点</i><br>
• 举例：合并 <code>a-c-d</code> 和 <code>d-f-e</code>，起点选 a → 至少需要框选 a（起点）和 d（连接点）<br>
• 通常情况下，直接框选要合并的路径的所有点即可，有多余点和其他不相连路径的点也没关系，不受影响 <br>
• 左键点击你想作为 <b>合并起点</b> 的端点（必须是路径端点）<br>
• 点击「合并路径」→ 从起点开始，自动合并所有相连路径<br>
• 合并规则：从起点出发，如果下一连接处端点已框选，则继续合并，遇到端点未框选时停止
"""
        self.ui.help_text.setHtml(help_text)

    def _on_merge_select_clicked(self):
        """从起点合并相连路径"""
        self._route_planning_manager.on_merge_selected()

    def _on_remove_select_clicked(self):
        """删除选中点，断开路径为多条"""
        self._route_planning_manager.on_remove_selected()
