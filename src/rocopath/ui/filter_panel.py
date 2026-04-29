"""
筛选面板组件

封装快捷筛选和刷新规则筛选的UI构建与事件处理逻辑。
保持主窗口代码简洁，职责分离。
"""

from dataclasses import dataclass
from collections.abc import Callable
from PySide6.QtWidgets import QVBoxLayout, QCheckBox, QScrollArea, QWidget, QTabWidget
from rocopath.models import NpcRefreshRule


@dataclass
class QuickFilter:
    """快捷筛选定义 - 支持多个关键词和多个规则ID"""

    display_name: str
    keywords: list[str]
    rule_ids: list[int]


# 预定义的常用快捷筛选
DEFAULT_QUICK_FILTERS: list[QuickFilter] = [
    QuickFilter("常见采集物", [""], [46, 8]),
    QuickFilter("四种矿物", ["黄石榴石", "黑晶琉璃", "紫莲刚玉", "蓝晶碧玺"], [46, 8]),
    QuickFilter("美妙球", ["天使草", "短木莲", "雪菇", "荧光蓝"], [46, 8]),
    QuickFilter("光合球", ["喵喵草", "象牙花", "凤眼莲"], [46, 8]),
    QuickFilter("好战球", ["睡铃", "海珊瑚", "大嘴花", "藻羽花"], [46, 8]),
    QuickFilter("淘沙球", ["幽幽鬼火", "石耳", "蜜黄菌", "彩玉花"], [46, 8]),
    QuickFilter("暗星球", ["幽幽草", "恶魔雪茄", "骨片"], [46, 8]),
    QuickFilter("网兜球", ["海神花", "蓝掌", "喷气菇", "风卷草"], [46, 8]),
    QuickFilter("网兜球，无风卷草", ["海神花", "蓝掌", "喷气菇"], [46, 8]),
    QuickFilter("调温球", ["向阳花", "星霜花", "伞伞菌", "火焰花"], [46, 8]),
    QuickFilter("变幻球", ["紫雀花", "紫晶菇", "流星兰"], [46, 8]),
    QuickFilter("绝缘球", ["洋红珊瑚", "杏黄贝", "海桑花", "花星角"], [46, 8]),
    QuickFilter("蓝掌", ["蓝掌"], [46, 8]),
    QuickFilter("睡铃", ["睡铃"], [46, 8]),
    QuickFilter("石耳", ["石耳"], [46, 8]),
    QuickFilter("雪菇", ["雪菇"], [46, 8]),
    QuickFilter("骨片", ["骨片"], [46, 8]),
    QuickFilter("向阳花", ["向阳花"], [46, 8]),
    QuickFilter("喵喵草", ["喵喵草"], [46, 8]),
    QuickFilter("天使草", ["天使草"], [46, 8]),
    QuickFilter("伞伞菌", ["伞伞菌"], [46, 8]),
    QuickFilter("蜜黄菌", ["蜜黄菌"], [46, 8]),
    QuickFilter("喷气菇", ["喷气菇"], [46, 8]),
    QuickFilter("凤眼莲", ["凤眼莲"], [46, 8]),
    QuickFilter("幽幽草", ["幽幽草"], [46, 8]),
    QuickFilter("星霜花", ["星霜花"], [46, 8]),
    QuickFilter("花星角", ["花星角"], [46, 8]),
    QuickFilter("荧光兰", ["荧光兰"], [46, 8]),
    QuickFilter("大嘴花", ["大嘴花"], [46, 8]),
    QuickFilter("流星兰", ["流星兰"], [46, 8]),
    QuickFilter("紫晶菇", ["紫晶菇"], [46, 8]),
    QuickFilter("海桑花", ["海桑花"], [46, 8]),
    QuickFilter("火焰花", ["火焰花"], [46, 8]),
    QuickFilter("海珊瑚", ["海珊瑚"], [46, 8]),
    QuickFilter("短木莲", ["短木莲"], [46, 8]),
    QuickFilter("杏黄贝", ["杏黄贝"], [46, 8]),
    QuickFilter("象牙花", ["象牙花"], [46, 8]),
    QuickFilter("藻羽花", ["藻羽花"], [46, 8]),
    QuickFilter("彩玉花", ["彩玉花"], [46, 8]),
    QuickFilter("海神花", ["海神花"], [46, 8]),
    QuickFilter("风卷草", ["风卷草"], [46, 8]),
    QuickFilter("紫雀花", ["紫雀花"], [46, 8]),
    QuickFilter("恶魔雪茄", ["恶魔雪茄"], [46, 8]),
    QuickFilter("幽幽鬼火", ["幽幽鬼火"], [163]),
    QuickFilter("洋红珊瑚", ["洋红珊瑚"], [46, 8]),
    QuickFilter("黄石榴石", ["黄石榴石"], [46, 8]),
    QuickFilter("黑晶琉璃", ["黑晶琉璃"], [46, 8]),
    QuickFilter("紫莲刚玉", ["紫莲刚玉"], [46, 8]),
    QuickFilter("蓝晶碧玺", ["蓝晶碧玺"], [46, 8]),
    QuickFilter(
        "眠枭之星（光点+放置+石像）", ["眠枭之星", " 眠枭石像 - 终点 - 大型"], [2, 5]
    ),
    QuickFilter("魔力之源", ["NPC预设露营点/枯枝"], [5, 7]),
    QuickFilter("眠枭庇护所（大+小）", ["型庇护所"], [2, 5]),
    QuickFilter("大型庇护所", ["大型庇护所"], [2, 5]),
    QuickFilter("小型庇护所", ["小型庇护所"], [2, 5]),
    QuickFilter("智慧树苗", ["智慧树苗"], [2]),
    QuickFilter("背景音乐", ["音乐光点"], [2, 5]),
    QuickFilter("雪山火盆（有多余点位）", ["普通火盆"], [2, 5]),
    QuickFilter("噩梦祭坛(有多余点位)", ["噩梦祭坛"], [2, 5]),
    QuickFilter(
        "传送门入口（守护地等）",
        ["-入口", "-隐藏入口", "精灵王的馈赠前置巨大矿石"],
        [2],
    ),
    QuickFilter("扭蛋机", ["扭蛋机"], [2, 5]),
]


class FilterPanel:
    """
    筛选面板

    管理两个标签页：
    1. 常用快捷筛选 - 预定义的快速选择项
    2. 刷新规则筛选 - 全选 + 所有规则复选框
    """

    def __init__(
        self,
        tab_widget: QTabWidget,
        on_filter_changed: Callable[[], None],
        on_keywords_changed: Callable[[str], None],
        default_quick_filters: list[QuickFilter] = DEFAULT_QUICK_FILTERS,
    ):
        """
        初始化筛选面板

        Args:
            tab_widget: 包含三个标签页的 QTabWidget
                tab 0: 常用快捷筛选 (tab_1)
                tab 2: 高级刷新规则筛选 (tab_3)
            on_filter_changed: 筛选变化回调函数（触发搜索）
            on_keywords_changed: 关键词变化回调函数（更新搜索框文本）
            default_quick_filters: 预定义快捷筛选列表
        """
        self._tab_widget = tab_widget
        self._default_quick_filters = default_quick_filters
        self._on_filter_changed_callback = on_filter_changed
        self._on_keywords_changed_callback = on_keywords_changed

        # UI 元素引用
        self._rule_checkboxes: dict[int, QCheckBox] = {}
        self._quick_filters: list[tuple[QCheckBox, QuickFilter]] = []
        self._select_all_checkbox: QCheckBox | None = None

        self._built = False

    def build(self, all_rules: list[NpcRefreshRule]) -> None:
        """构建所有UI元素"""
        self._build_quick_filter_tab()
        self._build_rule_filter_tab(all_rules)
        self._connect_signals()
        self._built = True

    def _build_quick_filter_tab(self) -> None:
        """构建快捷筛选标签页（第一个标签）"""
        tab = self._tab_widget.widget(0)
        assert tab is not None, "Tab widget 0 should exist in the UI file"
        layout = tab.layout()
        if layout is None:
            layout = QVBoxLayout(tab)

        # 创建滚动区域容纳所有快捷筛选
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # 创建预定义快捷筛选复选框
        for quick_filter in self._default_quick_filters:
            checkbox = QCheckBox(quick_filter.display_name)
            checkbox.setChecked(False)
            scroll_layout.addWidget(checkbox)
            self._quick_filters.append((checkbox, quick_filter))

        scroll_layout.addStretch()

    def _build_rule_filter_tab(self, all_rules: list[NpcRefreshRule]) -> None:
        """构建刷新规则筛选标签页（第三个标签）"""
        tab = self._tab_widget.widget(2)
        assert tab is not None, "Tab widget 2 should exist in the UI file"
        layout = tab.layout()
        if layout is None:
            layout = QVBoxLayout(tab)

        # 创建滚动区域容纳所有复选框
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # 添加全选复选框（放在最前面）
        self._select_all_checkbox = QCheckBox("全选")
        self._select_all_checkbox.setChecked(False)
        scroll_layout.addWidget(self._select_all_checkbox)

        # 创建所有规则复选框
        for rule in all_rules:
            checkbox = QCheckBox(f"{rule.id}: {rule.description}")
            checkbox.setChecked(False)
            scroll_layout.addWidget(checkbox)
            self._rule_checkboxes[rule.id] = checkbox

        scroll_layout.addStretch()

    def _connect_signals(self) -> None:
        """连接信号"""
        # 全选复选框
        if self._select_all_checkbox:
            self._select_all_checkbox.stateChanged.connect(self._on_select_all_changed)

        # 规则复选框
        for checkbox in self._rule_checkboxes.values():
            checkbox.stateChanged.connect(self._trigger_filter_changed)

        # 快捷筛选复选框
        for checkbox, _ in self._quick_filters:
            checkbox.stateChanged.connect(self._on_quick_filter_changed)

    def _on_select_all_changed(self, state: int) -> None:
        """全选复选框状态变化"""
        is_checked = state == 2  # 2 = Qt.Checked
        # 阻塞所有复选框的信号，避免每个都触发搜索
        for checkbox in self._rule_checkboxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(is_checked)
            checkbox.blockSignals(False)
        # 全选完成后只触发一次搜索
        self._trigger_filter_changed()

    def _trigger_filter_changed(self) -> None:
        """筛选规则变化，通知外部"""
        self._on_filter_changed_callback()

    def _on_filter_changed(self) -> None:
        """筛选规则变化，通知外部（兼容旧代码，实际不应该被调用）"""
        self._trigger_filter_changed()

    def _on_quick_filter_changed(self) -> None:
        """快捷筛选变化，合并条件后通知外部"""
        # 更新规则复选框勾选状态（同步 tab_1 勾选到 tab_3）
        self._update_rule_checkboxes()
        self._update_select_all_state()
        self._trigger_filter_changed()

    def _update_rule_checkboxes(self) -> None:
        """根据快捷筛选选中状态更新规则复选框"""
        all_rule_ids: set[int] = set()
        for checkbox, quick_filter in self._quick_filters:
            if checkbox.isChecked():
                all_rule_ids.update(quick_filter.rule_ids)

        # 更新勾选状态，阻塞信号避免多次触发搜索
        for rule_id, checkbox in self._rule_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(rule_id in all_rule_ids)
            checkbox.blockSignals(False)

    def _update_select_all_state(self) -> None:
        """更新全选复选框状态"""
        if self._select_all_checkbox:
            all_selected = all(cb.isChecked() for cb in self._rule_checkboxes.values())
            self._select_all_checkbox.blockSignals(True)
            self._select_all_checkbox.setChecked(all_selected)
            self._select_all_checkbox.blockSignals(False)

    def get_selected_rule_ids(self) -> list[int]:
        """获取当前勾选的刷新规则ID"""
        return [
            rule_id
            for rule_id, checkbox in self._rule_checkboxes.items()
            if checkbox.isChecked()
        ]

    def get_all_selected_quick_filters(self) -> list[QuickFilter]:
        """获取所有当前勾选的快捷筛选项"""
        return [
            quick_filter
            for checkbox, quick_filter in self._quick_filters
            if checkbox.isChecked()
        ]

    def get_combined_keywords(self) -> str:
        """获取所有选中快捷筛选组合后的关键词（保留兼容）"""
        all_keywords: list[str] = []
        for checkbox, quick_filter in self._quick_filters:
            if checkbox.isChecked():
                all_keywords.extend(quick_filter.keywords)
        return " ".join(all_keywords)

    @property
    def select_all_checkbox(self) -> QCheckBox | None:
        """获取全选复选框"""
        return self._select_all_checkbox

    @property
    def quick_filters(self) -> list[tuple[QCheckBox, QuickFilter]]:
        """获取所有快捷筛选项"""
        return self._quick_filters

    @property
    def rule_checkboxes(self) -> dict[int, QCheckBox]:
        """获取所有规则复选框"""
        return self._rule_checkboxes

    @property
    def is_built(self) -> bool:
        """是否已经构建完成"""
        return self._built
