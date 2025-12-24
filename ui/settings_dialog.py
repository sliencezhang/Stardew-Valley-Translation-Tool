# ui/settings_dialog.py
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QDialogButtonBox, QFileDialog,
                               QSpinBox, QGroupBox, QComboBox)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap, QPainter, QBrush, QColor

from core.config import config
from core.file_tool import file_tool
from core.project_manager import ProjectManager
from core.terminology_manager import TerminologyManager
from core.translation_cache import TranslationCache
from core.signal_bus import signal_bus
from ui.styles import (get_dialog_style, get_settings_desc_style, get_red_button_style, get_roll_button_style,
    get_font_red_style, get_scroll_area_style, get_widget_background_style, apply_table_header_style)
from ui.custom_message_box import CustomMessageBox
from ui.widgets import BackgroundWidget, load_background_image


class GlobalSettingsDialog(QDialog):
    """全局设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("全局设置")
        self.setModal(True)
        self.setMinimumSize(850, 650)
        
        # 设置无边框窗口和透明背景以实现圆角
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet(get_dialog_style(config.theme))

        # 工具和组件初始化
        self.project_manager: Optional[ProjectManager] = None
        self.cache: Optional[TranslationCache] = None

        self.temperature_spin = None
        self.batch_size_spin = None
        self.terminology_file = (Path(__file__).parent / "../resources/terminology.json").resolve()
        
        # 背景图片初始化
        self.background_pixmap = None
        self._load_background_image()

        self._init_ui()
        self._load_current_settings()



    def set_project_manager(self, project_manager: ProjectManager):
        """设置 project_manager 并初始化缓存"""
        self.project_manager = project_manager
        if self.project_manager:
            self.cache = TranslationCache(self.project_manager)
            # 延迟加载缓存信息
            QTimer.singleShot(100, self._refresh_cache_info)

    def _init_ui(self):
        """初始化UI"""
        # 创建主布局（透明）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建容器（用于绘制背景）
        self.container_widget = BackgroundWidget(self.background_pixmap, config.theme)
        self.container_widget.setObjectName("dialogContainer")
        container_layout = QVBoxLayout(self.container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        main_layout.addWidget(self.container_widget)
        
        # 添加自定义标题栏（默认不显示主题切换按钮）
        from ui.custom_title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(self)
        container_layout.addWidget(self.title_bar)
        
        # 内容区域
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        container_layout.addWidget(content_widget)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 添加标签页
        tabs = [
            ("🔑 API设置", self._create_api_tab),
            ("📝 翻译设置", self._create_merged_translation_tab),
            ("📚 术语表", self._create_glossary_tab),
            ("🗃️ 缓存管理", self._create_cache_tab),
            ("📖 使用说明", self._create_help_tab)
        ]

        for name, creator in tabs:
            self.tab_widget.addTab(creator(), name)

        layout.addWidget(self.tab_widget)

        # 按钮区域
        button_box = self._create_button_box()
        layout.addWidget(button_box)

        self.setLayout(main_layout)

    def _create_button_box(self):
        """创建按钮区域"""
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )

        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)

        save_btn.setText("保存")
        cancel_btn.setText("取消")
        cancel_btn.setStyleSheet(get_red_button_style(config.theme))

        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)

        return button_box

    def _create_api_tab(self) -> QWidget:
        """创建API设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # API提供商选择
        provider_group = QGroupBox("API提供商")
        provider_layout = QVBoxLayout(provider_group)
        
        provider_select_layout = QHBoxLayout()
        provider_select_layout.addWidget(QLabel("选择提供商:"))
        
        self.api_provider_combo = QComboBox()
        from core.api_client import APIClientFactory
        providers = APIClientFactory.get_providers()
        for provider in providers:
            info = APIClientFactory.get_provider_info(provider)
            self.api_provider_combo.addItem(info["name"], provider)
        
        self.api_provider_combo.currentTextChanged.connect(self._on_api_provider_changed)
        provider_select_layout.addWidget(self.api_provider_combo)
        
        provider_layout.addLayout(provider_select_layout)
        layout.addWidget(provider_group)

        # API密钥设置组
        api_group = QGroupBox("API配置")
        api_layout = QVBoxLayout(api_group)

        # API密钥输入
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API密钥:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("输入API密钥...")
        key_layout.addWidget(self.api_key_edit)

        # 测试连接按钮
        test_btn = QPushButton("🔗 测试连接")
        test_btn.clicked.connect(self._test_api_connection)
        key_layout.addWidget(test_btn)

        api_layout.addLayout(key_layout)

        # API URL输入
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("API地址:"))
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("API地址...")
        url_layout.addWidget(self.api_url_edit)
        api_layout.addLayout(url_layout)

        # 模型输入
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.api_model_edit = QLineEdit()
        self.api_model_edit.setPlaceholderText("模型名称...")
        model_layout.addWidget(self.api_model_edit)
        api_layout.addLayout(model_layout)

        # API状态显示
        self.api_status_label = QLabel("未连接")
        self.api_status_label.setStyleSheet(get_font_red_style(config.theme))
        api_layout.addWidget(self.api_status_label)

        # API使用说明
        api_help_layout = QHBoxLayout()
        
        self.api_help_label = QLabel()
        self.api_help_label.setStyleSheet(get_settings_desc_style(config.theme))
        self.api_help_label.setWordWrap(True)
        api_help_layout.addWidget(self.api_help_label)
        
        # 添加复制网址按钮
        copy_url_btn = QPushButton("🔗 复制网址")
        copy_url_btn.setFixedWidth(100)
        copy_url_btn.clicked.connect(self._copy_api_url)
        api_help_layout.addWidget(copy_url_btn)
        
        api_layout.addLayout(api_help_layout)
        
        # 初始化说明文本
        self._update_api_help_text()

        layout.addWidget(api_group)
        layout.addStretch()

        return widget


    def _create_merged_translation_tab(self) -> QWidget:
        """创建合并的翻译设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 翻译提示词组
        prompt_group = QGroupBox("翻译提示词")
        prompt_layout = QVBoxLayout(prompt_group)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("加载默认提示词...")
        self.prompt_edit.setMinimumHeight(200)
        prompt_layout.addWidget(self.prompt_edit)

        # 提示词操作按钮
        prompt_btn_layout = QHBoxLayout()

        buttons = [
            ("📂 加载默认提示词", self._load_default_prompt),
            ("💾 保存为默认", self._save_default_prompt)
        ]

        for text, slot in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            prompt_btn_layout.addWidget(btn)

        prompt_btn_layout.addStretch()
        prompt_layout.addLayout(prompt_btn_layout)

        layout.addWidget(prompt_group)

        # 批量设置组
        batch_group = QGroupBox("批量翻译设置")
        batch_layout = QVBoxLayout(batch_group)

        # 创建设置项
        settings_items = [
            ("每批翻译数量:", "batch_size_spin", config.default_batch_size,
             "每次发送给API的翻译条目数量", 1, 50, ""),
            ("温度参数:", "temperature_spin", int(config.temperature * 100),
             "控制翻译的创造性，越低越保守", 0, 100, "%")
        ]

        for label_text, attr_name, value, tooltip, min_val, max_val, suffix in settings_items:
            layout_item = QHBoxLayout()
            layout_item.addWidget(QLabel(label_text))

            spinbox = self._create_vertical_spinbox(value, min_val, max_val, suffix)
            spinbox.setToolTip(tooltip)

            setattr(self, attr_name, spinbox)
            layout_item.addWidget(spinbox)
            layout_item.addStretch()
            batch_layout.addLayout(layout_item)

        layout.addWidget(batch_group)

        # 背景图片设置组
        bg_group = QGroupBox("背景图片设置")
        bg_layout = QVBoxLayout(bg_group)

        # 是否使用背景图片
        from PySide6.QtWidgets import QCheckBox
        use_bg_layout = QHBoxLayout()
        self.use_background_checkbox = QCheckBox("使用背景图片")
        self.use_background_checkbox.setChecked(config.use_background)
        self.use_background_checkbox.setToolTip("关闭后将使用纯色背景")
        use_bg_layout.addWidget(self.use_background_checkbox)
        use_bg_layout.addStretch()
        bg_layout.addLayout(use_bg_layout)

        # 浅色模式背景图片
        light_bg_layout = QHBoxLayout()
        light_bg_layout.addWidget(QLabel("浅色背景:"))
        self.custom_bg_light_edit = QLineEdit()
        self.custom_bg_light_edit.setPlaceholderText("留空使用默认背景...")
        self.custom_bg_light_edit.setText(config.custom_background_light)
        self.custom_bg_light_edit.setReadOnly(True)
        light_bg_layout.addWidget(self.custom_bg_light_edit)

        select_light_btn = QPushButton("📁 选择")
        select_light_btn.clicked.connect(lambda: self._select_background_image("light"))
        light_bg_layout.addWidget(select_light_btn)

        clear_light_btn = QPushButton("🗑️")
        clear_light_btn.setStyleSheet(get_red_button_style(config.theme))
        clear_light_btn.clicked.connect(lambda: self.custom_bg_light_edit.clear())
        light_bg_layout.addWidget(clear_light_btn)

        bg_layout.addLayout(light_bg_layout)

        # 深色模式背景图片
        dark_bg_layout = QHBoxLayout()
        dark_bg_layout.addWidget(QLabel("深色背景:"))
        self.custom_bg_dark_edit = QLineEdit()
        self.custom_bg_dark_edit.setPlaceholderText("留空使用默认背景...")
        self.custom_bg_dark_edit.setText(config.custom_background_dark)
        self.custom_bg_dark_edit.setReadOnly(True)
        dark_bg_layout.addWidget(self.custom_bg_dark_edit)

        select_dark_btn = QPushButton("📁 选择")
        select_dark_btn.clicked.connect(lambda: self._select_background_image("dark"))
        dark_bg_layout.addWidget(select_dark_btn)

        clear_dark_btn = QPushButton("🗑️")
        clear_dark_btn.setStyleSheet(get_red_button_style(config.theme))
        clear_dark_btn.clicked.connect(lambda: self.custom_bg_dark_edit.clear())
        dark_bg_layout.addWidget(clear_dark_btn)

        bg_layout.addLayout(dark_bg_layout)

        # 背景图片说明
        bg_help = QLabel(
            "背景图片说明：\n"
            "• 关闭背景图片后将使用纯色背景\n"
            "• 可以分别为浅色和深色模式设置不同的背景图片\n"
            "• 支持 PNG、JPG、JPEG 格式\n"
            "• 留空则使用内置的默认背景图片"
        )
        bg_help.setStyleSheet(get_settings_desc_style(config.theme))
        bg_help.setWordWrap(True)
        bg_layout.addWidget(bg_help)

        layout.addWidget(bg_group)
        layout.addStretch()

        return widget

    def _create_glossary_tab(self) -> QWidget:
        """创建术语表标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 术语表编辑组
        glossary_group = QGroupBox("术语表管理")
        glossary_layout = QVBoxLayout(glossary_group)

        # 术语表表格
        self.glossary_table = QTableWidget()
        self.glossary_table.setColumnCount(2)
        self.glossary_table.setHorizontalHeaderLabels(["英文", "中文"])
        self.glossary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.glossary_table.setMinimumHeight(450)
        apply_table_header_style(self.glossary_table, config.theme)
        glossary_layout.addWidget(self.glossary_table)

        # 术语表使用说明
        help_text = QLabel(
            "术语表说明：\n"
            "• 添加游戏专有名词的翻译对应关系\n"
            "• 翻译时会自动替换术语表中的内容\n"
            "• 支持导入/导出JSON格式\n"
            "• 例如：Abigail -> 阿比盖尔, Pelican Town -> 鹈鹕镇"
        )
        help_text.setStyleSheet(get_settings_desc_style(config.theme))
        help_text.setWordWrap(True)
        glossary_layout.addWidget(help_text)

        layout.addWidget(glossary_group)

        # 术语表操作按钮
        glossary_btn_layout = self._create_glossary_buttons()
        glossary_layout.addLayout(glossary_btn_layout)

        layout.addStretch()

        return widget

    def _create_glossary_buttons(self) -> QHBoxLayout:
        """创建术语表按钮布局"""
        btn_layout = QHBoxLayout()

        buttons = [
            ("➕ 添加术语", self._add_glossary_term, None),
            ("🗑️ 删除选中", lambda: self._remove_selected_table_row(self.glossary_table), get_red_button_style(config.theme)),
            ("📥 导入JSON", self._import_glossary, get_red_button_style(config.theme)),
            ("📤 导出JSON", self._export_glossary, None)
        ]
        for i, (text, slot, style) in enumerate(buttons):
            btn_layout.addStretch() if i == 2 else None

            btn = QPushButton(text)
            btn.clicked.connect(slot)
            if style:
                btn.setStyleSheet(style)
            btn_layout.addWidget(btn)


        return btn_layout



    def _create_cache_tab(self) -> QWidget:
        """创建缓存管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 缓存管理组
        cache_group = QGroupBox("缓存管理")
        cache_layout = QVBoxLayout(cache_group)

        # 搜索和分页
        cache_layout.addLayout(self._create_cache_controls())

        # 缓存表格
        self.cache_table = QTableWidget()
        self.cache_table.setColumnCount(2)
        self.cache_table.setHorizontalHeaderLabels(["哈希值", "翻译结果"])
        self.cache_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        apply_table_header_style(self.cache_table, config.theme)
        cache_layout.addWidget(self.cache_table)

        # 缓存信息显示
        self.cache_info_label = QLabel("正在获取缓存信息...")
        self.cache_info_label.setStyleSheet(get_settings_desc_style(config.theme))
        self.cache_info_label.setWordWrap(True)
        cache_layout.addWidget(self.cache_info_label)

        # 缓存操作按钮
        cache_layout.addLayout(self._create_cache_buttons())

        # 缓存说明
        cache_help_text = QLabel(
            "缓存说明：\n"
            "• 翻译缓存可以加速重复内容的翻译\n"
            "• 每个项目有独立的缓存文件\n"
            "• 删除缓存不会影响已翻译的文件\n"
            "• 删除选中缓存需要保存才会执行"
        )
        cache_help_text.setStyleSheet(get_settings_desc_style(config.theme))
        cache_help_text.setWordWrap(True)
        cache_layout.addWidget(cache_help_text)

        layout.addWidget(cache_group)

        # 延迟加载缓存信息
        QTimer.singleShot(100, self._refresh_cache_info)

        return widget

    def _create_cache_controls(self) -> QHBoxLayout:
        """创建缓存控制布局"""
        controls_layout = QHBoxLayout()

        # 搜索框
        controls_layout.addWidget(QLabel("搜索:"))
        self.cache_search_edit = QLineEdit()
        self.cache_search_edit.setPlaceholderText("输入关键词搜索缓存...")
        self.cache_search_edit.textChanged.connect(self._filter_cache_table)
        controls_layout.addWidget(self.cache_search_edit)

        # 显示数量选择
        controls_layout.addWidget(QLabel("显示数量:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["显示100条", "显示500条", "显示1000条", "显示10000条"])
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        controls_layout.addWidget(self.page_size_combo)

        return controls_layout

    def _create_cache_buttons(self) -> QHBoxLayout:
        """创建缓存按钮布局"""
        btn_layout = QHBoxLayout()

        buttons = [
            ("🔄 刷新缓存信息", self._refresh_cache_info, None),
            ("📂 打开缓存文件", self._open_cache_file, None),
            ("🗑️ 删除选中缓存", lambda: self._remove_selected_table_row(self.cache_table), get_red_button_style(config.theme)),
            ("🗑️ 删除全部缓存", self._clear_translation_cache, get_red_button_style(config.theme))
        ]


        for i, (text, slot, style) in enumerate(buttons):
            btn_layout.addStretch() if i == 2 else None
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            if style:
                btn.setStyleSheet(style)
            setattr(self, text.split()[-1] + "_btn", btn)  # 动态设置属性名
            btn_layout.addWidget(btn)

        return btn_layout

    def _open_cache_file(self):
        """打开缓存文件"""
        if not self.cache:
            CustomMessageBox.warning(self, "警告", "缓存未初始化，请先设置项目管理器")
            return

        try:
            success = file_tool.open_folder(self.cache.get_cache_stats().get('缓存文件'))
            if not success:
                CustomMessageBox.warning(self, "警告", "打开缓存文件夹失败")
        except Exception as e:
            CustomMessageBox.critical(self, "错误", f"打开缓存文件夹失败: {str(e)}")

    def _refresh_cache_info(self):
        """刷新缓存信息"""
        try:
            if not self._is_cache_initialized():
                self._update_cache_status("缓存未初始化，请先设置项目管理器", False)
                return

            # 加载缓存
            self.cache.cache = self.cache.load_cache()
            stats = self.cache.get_cache_stats()

            total_cached = stats.get('缓存条目数', 0)
            cache_file = stats.get('缓存文件', '未知')

            # 加载预览数据到表格
            self._load_cache_preview(total_cached)

            # 更新状态显示
            display_path = f"...{cache_file[-57:]}" if len(cache_file) > 60 else cache_file
            info_text = f"""📊 缓存统计：
            路径: {display_path}
            条目数: {total_cached} 条"""

            self.cache_info_label.setText(info_text.strip())
            self._update_cache_buttons_state(total_cached > 0)

        except Exception as e:
            self._update_cache_status(f"获取缓存信息失败: {str(e)}", False)

    def _is_cache_initialized(self) -> bool:
        """检查缓存是否初始化"""
        return hasattr(self, 'cache') and self.cache is not None

    def _update_cache_status(self, message: str, enabled: bool):
        """更新缓存状态"""
        self.cache_info_label.setText(message)
        if hasattr(self, 'clear_cache_btn'):
            self.clear_cache_btn.setEnabled(enabled)
        if hasattr(self, 'remove_term_btn'):
            self.remove_term_btn.setEnabled(enabled)

    def _load_cache_preview(self, total_cached: int):
        """加载缓存预览数据"""
        if total_cached == 0:
            self.cache_table.setRowCount(0)
            return

        # 根据显示设置加载数据
        page_text = self.page_size_combo.currentText()
        limit = int(page_text.replace("显示", "").replace("条", ""))

        # 只加载限制数量的数据
        preview_items = dict(list(self.cache.cache.items())[:limit])
        self._load_dict_to_table(preview_items, self.cache_table)

    def _update_cache_buttons_state(self, enabled: bool):
        """更新缓存按钮状态"""
        for btn_name in ['clear_cache_btn', 'remove_term_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setEnabled(enabled)

    def _clear_translation_cache(self):
        """清除翻译缓存"""
        if not self.cache:
            CustomMessageBox.warning(self, "警告", "缓存未初始化")
            return

        try:
            stats_before = self.cache.get_cache_stats()
            total_before = stats_before.get('缓存条目数', 0)

            if total_before == 0:
                CustomMessageBox.information(self, "提示", "缓存已为空")
                return

            if not self._confirm_clear_cache(total_before):
                return

            if self._execute_cache_clear():
                self._on_cache_cleared(stats_before)

        except Exception as e:
            self._handle_cache_error(e)

    def _confirm_clear_cache(self, cache_count: int) -> bool:
        """确认清除缓存"""
        return CustomMessageBox.question(
            self,
            "确认删除",
            f"确定要删除所有 {cache_count} 条翻译缓存吗？\n\n"
            "注意：\n"
            "• 这将删除所有缓存的翻译结果\n"
            "• 已翻译的文件不受影响\n"
            "• 删除后重新翻译相同内容会调用API\n"
            "• 此操作不可撤销"
        ) == CustomMessageBox.Yes

    def _execute_cache_clear(self) -> bool:
        """执行缓存清除"""
        self.cache.cache.clear()
        success = self.cache.save_cache()

        if not success:
            CustomMessageBox.critical(self, "删除失败", "删除缓存失败，请检查文件权限")
            return False

        self.cache_table.setRowCount(0)
        return True

    def _on_cache_cleared(self, stats_before: dict):
        """缓存清除后的处理"""
        total_before = stats_before.get('缓存条目数', 0)
        cache_file = stats_before.get('缓存文件', '')

        self._refresh_cache_info()

        CustomMessageBox.information(
            self,
            "删除成功",
            f"已成功删除 {total_before} 条缓存记录\n\n"
            f"缓存文件：{cache_file}"
        )

        # 发射缓存清除信号
        signal_bus.cacheCleared.emit(self.project_manager or total_before)

    def _handle_cache_error(self, error: Exception):
        """处理缓存错误"""
        CustomMessageBox.critical(
            self,
            "删除失败",
            f"删除缓存时发生错误：\n{str(error)}"
        )

    def _filter_cache_table(self, search_text: str):
        """根据搜索文本过滤表格"""
        if not search_text or not self.cache:
            return

        search_text = search_text.lower()
        filtered_data = {
            key: value for key, value in list(self.cache.cache.items())[:1000]
            if search_text in str(key).lower() or search_text in str(value).lower()
        }

        self._load_dict_to_table(filtered_data, self.cache_table)

    def _on_page_size_changed(self, text: str):
        """显示数量改变"""
        limits = {
            "显示100条": 100,
            "显示500条": 500,
            "显示1000条": 1000,
            "显示10000条": 10000
        }

        if limit := limits.get(text):
            self._load_partial_cache(limit)

    def _load_partial_cache(self, limit: int):
        """只加载部分缓存"""
        if not self.cache:
            return

        partial_data = dict(list(self.cache.cache.items())[:limit])
        self._load_dict_to_table(partial_data, self.cache_table)

    def _load_current_settings(self):
        """加载当前设置"""
        # API设置
        provider = config.api_provider
        
        # 设置当前选择的提供商
        for i in range(self.api_provider_combo.count()):
            if self.api_provider_combo.itemData(i) == provider:
                self.api_provider_combo.setCurrentIndex(i)
                break
        
        # 加载该提供商的配置
        self.api_key_edit.setText(config.api_keys.get(provider, ""))
        self.api_url_edit.setText(config.api_urls.get(provider, ""))
        self.api_model_edit.setText(config.api_models.get(provider, ""))

        # 提示词
        self._load_default_prompt(silent=True)

        # 术语表
        self._load_default_terminology()

        # 翻译设置
        self.batch_size_spin.setValue(config.default_batch_size)
        self.temperature_spin.setValue(int(config.temperature * 100))

        # 缓存
        self._load_cache_data()
    
    def _on_api_provider_changed(self, provider_name: str):
        """API提供商变更处理"""
        # 获取提供商代码
        for i in range(self.api_provider_combo.count()):
            if self.api_provider_combo.itemText(i) == provider_name:
                provider_code = self.api_provider_combo.itemData(i)
                break
        else:
            return
        
        # 加载该提供商的配置
        self.api_key_edit.setText(config.api_keys.get(provider_code, ""))
        self.api_url_edit.setText(config.api_urls.get(provider_code, ""))
        self.api_model_edit.setText(config.api_models.get(provider_code, ""))
        
        # 更新帮助文本
        self._update_api_help_text(provider_code)
    
    def _update_api_help_text(self, provider_code: str = None):
        """更新API帮助文本"""
        if provider_code is None:
            provider_code = self.api_provider_combo.currentData()
        
        help_texts = {
            "siliconflow": (
                "获取硅基流动API密钥：\n"
                "1. 访问 https://cloud.siliconflow.cn/i/J1D1FRdM\n"
                "2. 注册账号并登录\n"
                "3. 在账号管理-API秘钥处获取API密钥\n"
                "4. 将密钥粘贴到上方输入框"
            ),
            "deepseek": (
                "获取DeepSeek API密钥：\n"
                "1. 访问 https://platform.deepseek.com\n"
                "2. 注册账号并登录\n"
                "3. 在API密钥页面获取密钥\n"
                "4. 将密钥粘贴到上方输入框"
            ),
            "openai": (
                "获取OpenAI API密钥：\n"
                "1. 访问 https://platform.openai.com\n"
                "2. 注册账号并登录\n"
                "3. 在API Keys页面创建密钥\n"
                "4. 将密钥粘贴到上方输入框"
            ),
            "qwen": (
                "获取通义千问API密钥：\n"
                "1. 访问 https://dashscope.aliyun.com\n"
                "2. 注册阿里云账号并登录\n"
                "3. 在控制台获取API Key\n"
                "4. 将密钥粘贴到上方输入框"
            ),
            "kimi": (
                "获取Kimi API密钥：\n"
                "1. 访问 https://platform.moonshot.cn\n"
                "2. 注册账号并登录\n"
                "3. 在API密钥页面获取密钥\n"
                "4. 将密钥粘贴到上方输入框"
            ),
            "zhipu": (
                "获取智谱AI API密钥：\n"
                "1. 访问 https://open.bigmodel.cn\n"
                "2. 注册账号并登录\n"
                "3. 在控制台获取API Key\n"
                "4. 将密钥粘贴到上方输入框"
            ),
            "doubao": (
                "获取豆包API密钥：\n"
                "1. 访问火山引擎控制台\n"
                "2. 开通豆包大模型服务\n"
                "3. 创建API密钥和接入点\n"
                "4. 将密钥和URL粘贴到上方"
            ),
            "hunyuan": (
                "获取混元API密钥：\n"
                "1. 访问腾讯云控制台\n"
                "2. 开通混元大模型服务\n"
                "3. 获取SecretId和SecretKey\n"
                "4. 将密钥粘贴到上方输入框"
            ),
            "local": (
                "使用本地API (如 LM Studio)：\n"
                "1. 启动本地API服务 (如 LM Studio)\n"
                "2. 确认服务地址 (默认: http://127.0.0.1:1234)\n"
                "3. API密钥可留空\n"
                "4. 模型名称通常为 local-model"
            )
        }
        
        self.api_help_label.setText(help_texts.get(provider_code, ""))

    def _copy_api_url(self):
        """复制API网址到剪贴板"""
        from PySide6.QtWidgets import QApplication
        
        provider_code = self.api_provider_combo.currentData()
        
        # 定义各API提供商的网址
        api_urls = {
            "siliconflow": "https://cloud.siliconflow.cn/i/J1D1FRdM",
            "deepseek": "https://platform.deepseek.com",
            "openai": "https://platform.openai.com",
            "qwen": "https://dashscope.aliyun.com",
            "kimi": "https://platform.moonshot.cn",
            "zhipu": "https://open.bigmodel.cn",
            "doubao": "https://console.volcengine.com",
            "hunyuan": "https://hunyuan.tencent.com",
            "local": "本地API服务"
        }
        
        url = api_urls.get(provider_code, "")
        if url:
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
            CustomMessageBox.information(self, "成功", f"网址已复制到剪贴板: {url}")
        else:
            CustomMessageBox.warning(self, "警告", "没有可复制的网址")

    def _load_default_prompt(self, silent: bool = False):
        """加载默认提示词"""
        try:
            prompt_file = (Path(__file__).parent / "../resources/default_prompts.json").resolve()
            prompt_data = file_tool.read_json_file(str(prompt_file))
            default_prompt = prompt_data.get("translation_prompt", "")
            self.prompt_edit.setPlainText(default_prompt)
            if not silent:
                CustomMessageBox.information(self, "成功", "已加载默认提示词")
        except Exception as e:
            if not silent:
                CustomMessageBox.warning(self, "警告", f"加载提示词失败: {str(e)}")

    def _load_default_terminology(self):
        """加载默认术语表"""
        terminology_data = file_tool.read_json_file(str(self.terminology_file))
        self._load_dict_to_table(terminology_data, self.glossary_table)

    def _load_cache_data(self):
        """加载缓存数据"""
        if self.cache:
            cache_data = self.cache.load_cache()
            self._load_dict_to_table(cache_data, self.cache_table)
    @staticmethod
    def _load_dict_to_table(data_dict: Dict[str, Any], table_widget: QTableWidget):
        """将字典加载到表格中"""
        table_widget.setRowCount(len(data_dict))
        for i, (key, value) in enumerate(data_dict.items()):
            table_widget.setItem(i, 0, QTableWidgetItem(str(key)))
            table_widget.setItem(i, 1, QTableWidgetItem(str(value)))

    @staticmethod
    def _get_dict_from_table(table_widget: QTableWidget, key_column: int = 0, value_column: int = 1) -> Dict[str, str]:
        """从表格获取字典数据"""
        result = {}
        for row in range(table_widget.rowCount()):
            key_item = table_widget.item(row, key_column)
            value_item = table_widget.item(row, value_column)

            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key:  # 键不能为空
                    result[key] = value

        return result

    def _add_glossary_term(self):
        """添加术语表条目"""
        row_count = self.glossary_table.rowCount()
        self.glossary_table.insertRow(row_count)

    def _remove_selected_table_row(self, table_widget: QTableWidget):
        """删除选中的表格条目"""
        current_row = table_widget.currentRow()
        if current_row >= 0:
            table_widget.removeRow(current_row)

    def _import_glossary(self):
        """导入术语表JSON"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入术语表", "", "JSON文件 (*.json);;所有文件 (*)")

        if not file_path:
            return

        try:
            glossary = file_tool.read_json_file(file_path)

            if isinstance(glossary, dict):
                self._load_dict_to_table(glossary, self.glossary_table)
                CustomMessageBox.information(self, "成功", f"已导入 {len(glossary)} 个术语")
            else:
                CustomMessageBox.warning(self, "警告", "术语表文件格式不正确，必须是JSON对象")

        except Exception as e:
            CustomMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def _export_glossary(self):
        """导出术语表JSON"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出术语表", "glossary.json", "JSON文件 (*.json)")

        if not file_path:
            return

        glossary = self._get_dict_from_table(self.glossary_table)
        file_tool.save_json_file(glossary, file_path)
        CustomMessageBox.information(self, "成功", f"已导出 {len(glossary)} 个术语")

    def _save_default_prompt(self):
        """保存为默认提示词"""
        prompt_data = {"translation_prompt": self.prompt_edit.toPlainText().strip()}
        ter = TerminologyManager()
        ter.save_default_prompt(prompt_data)
        CustomMessageBox.information(self, "成功", "已保存为默认提示词")

    def _select_background_image(self, mode="light"):
        """选择自定义背景图片"""
        title = "选择浅色模式背景图片" if mode == "light" else "选择深色模式背景图片"
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            title, 
            "", 
            "图片文件 (*.png *.jpg *.jpeg);;所有文件 (*)"
        )
        
        if file_path:
            if mode == "light":
                self.custom_bg_light_edit.setText(file_path)
            else:
                self.custom_bg_dark_edit.setText(file_path)

    def _test_api_connection(self):
        """测试API连接"""
        provider_code = self.api_provider_combo.currentData()
        api_key = self.api_key_edit.text().strip()
        api_url = self.api_url_edit.text().strip()
        api_model = self.api_model_edit.text().strip()
        
        # 本地API不需要API密钥
        if not api_key and provider_code != "local":
            CustomMessageBox.warning(self, "警告", "请输入API密钥")
            return
        
        if not api_url:
            CustomMessageBox.warning(self, "警告", "请输入API地址")
            return

        try:
            from core.api_client import APIClientFactory
            # 创建临时客户端进行测试
            client = APIClientFactory.create_client(provider_code, api_key, api_url, api_model)
            
            # 发送测试请求
            test_prompt = "请回复：测试成功"
            response = client.call_api(test_prompt)
            
            if "测试成功" in response or "test" in response.lower():
                status = "连接成功"
                style = "color: green; font-weight: bold;"
                message = f"{client.get_name()} API连接测试成功！"
                success = True
            else:
                status = "连接异常"
                style = "color: red; font-weight: bold;"
                message = f"API响应异常: {response[:100]}"
                success = False

        except Exception as e:
            status = "连接失败"
            style = "color: red; font-weight: bold;"
            message = f"API连接失败: {str(e)}"
            success = False

        # 更新UI
        self.api_status_label.setText(status)
        self.api_status_label.setStyleSheet(style)

        # 发送信号
        signal_bus.apiTested.emit(success, message)

        # 显示消息
        if success:
            CustomMessageBox.information(self, "成功", message)
        else:
            CustomMessageBox.critical(self, "错误", message)

    def _save_settings(self):
        """保存设置"""
        # 获取设置数据
        glossary = self._get_dict_from_table(self.glossary_table)

        # 获取API配置
        provider_code = self.api_provider_combo.currentData()
        api_key = self.api_key_edit.text().strip()
        api_url = self.api_url_edit.text().strip()
        api_model = self.api_model_edit.text().strip()

        # 更新API配置
        try:
            config.set_current_api_config(provider_code, api_key, api_url, api_model)
        except Exception as e:
            CustomMessageBox.warning(self, "警告", f"保存API配置失败: {str(e)}")
            return

        # 更新其他配置
        config.default_batch_size = self.batch_size_spin.value()
        config.temperature = self.temperature_spin.value() / 100.0
        config.use_background = self.use_background_checkbox.isChecked()
        config.custom_background_light = self.custom_bg_light_edit.text().strip()
        config.custom_background_dark = self.custom_bg_dark_edit.text().strip()

        # 保存到QSettings
        config.save_to_settings()

        # 保存术语表
        self._save_terminology_file(glossary)

        # 保存缓存
        self._save_cache_data()

        # 发送信号
        settings = {
            'api_provider': provider_code,
            'api_key': api_key,
            'api_url': api_url,
            'api_model': api_model,
            'batch_size': config.default_batch_size,
            'temperature': config.temperature,
            'terminology': glossary
        }

        signal_bus.settingsSaved.emit(settings)
        self.accept()


    def _save_terminology_file(self, glossary: Dict[str, str]):
        """保存术语表到文件"""
        file_tool.save_json_file(glossary, str(self.terminology_file))

    def _save_cache_data(self):
        """保存缓存数据"""
        if not self.cache:
            return
        cache_from_table = self._get_dict_from_table(self.cache_table)
        self.cache.cache = cache_from_table

        if not self.cache.save_cache():
            CustomMessageBox.warning(self, "警告", "缓存保存失败，请检查文件权限")

    @staticmethod
    def _create_vertical_spinbox(value: int = 1, min_val: int = 1, max_val: int = 100,
                                 suffix: str = "", step: int = 1) -> QSpinBox:
        """创建垂直按钮的 SpinBox"""
        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(value)
        spinbox.setSingleStep(step)

        if suffix:
            spinbox.setSuffix(suffix)

        spinbox.setStyleSheet(get_roll_button_style(config.theme))
        return spinbox

    def _create_help_tab(self):
        """创建使用说明标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建滚动区域
        from PySide6.QtWidgets import QScrollArea
        from ui.styles import get_scroll_area_style, get_widget_background_style
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 使用透明背景
        scroll_area.setStyleSheet(get_scroll_area_style(config.theme))
        
        # 内容widget
        content_widget = QWidget()
        # 使用透明背景
        content_widget.setStyleSheet(get_widget_background_style(config.theme))
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("📖 星露谷翻译工具使用说明")
        if config.theme == "dark":
            title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e0e0e0; margin-bottom: 10px;")
        else:
            title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        content_layout.addWidget(title)

        # 1. 快速开始
        quick_start_group = QGroupBox("1. 快速开始 🚀")
        quick_start_layout = QVBoxLayout(quick_start_group)
        
        quick_start_text = QLabel()
        quick_start_text.setTextFormat(Qt.TextFormat.RichText)
        quick_start_text.setText(
            "<b>欢迎使用星露谷翻译工具！</b>这是一个专门为<b>Stardew Valley模组</b>设计的AI翻译工具，目前仅支持<b>英文→中文</b>。<br>"
            "当然也可以通过修改<b>翻译提示词</b>翻译为其他语言，但是不确保质量检查功能有效<br><br>"
            "<b>基本使用流程：</b><br>"
            "1. 创建新项目或打开现有项目<br>"
            "2. 打开全局设置配置API密钥（支持大部分国产AI模型API以及本地API）<br>"
            "3. 将需要翻译的模组文件放入对应拖选框（en/、zh/等）<br>"
            "4. 点击绿色开始翻译按钮开始翻译<br>"
            "5. 使用质量检查功能检查翻译问题项（变量问题，未翻译，中英文夹杂）<br>"
            "6. AI重新翻译或人工编辑后勾选满意的问题项应用修复到Output，打开output文件夹查看翻译结果"
        )
        quick_start_text.setWordWrap(True)
        quick_start_text.setStyleSheet("background-color: transparent;")
        quick_start_layout.addWidget(quick_start_text)
        
        content_layout.addWidget(quick_start_group)
        
        # 2. 功能介绍
        features_group = QGroupBox("2. 功能介绍 ✨")
        features_layout = QVBoxLayout(features_group)
        
        features_text = QLabel()
        features_text.setTextFormat(Qt.TextFormat.RichText)
        features_text.setText(
            "<b>主要功能模块：</b><br><br>"
            "<b>🔄 一键更新：</b><br>"
            "• 自动完成所有步骤<br>"
            "• 包括i18n文件翻译，manifest文件翻译，content文件翻译，Portraits文件夹复制（自己替换的肖像图不用手动复制了），config文件复制<br>"
            "• 需先拖动下载的mod文件夹到步骤1，游戏中已有的mod文件夹到步骤2<br>"
            "• 会先进行人名地名检查，不需要的话点击跳过选项<br>"
            "• 会将完整mod文件夹输出到output，只需将游戏mod目录内对应文件夹内容删除，将output/mod文件夹的内容复制过去就完成更新<br><br>"
            "<b>🚀 智能翻译：</b><br>"
            "• 支持<b>增量翻译</b>，若添加对应的中文 json 会自动回填已翻译中文（default和zh是对应关系，不用修改）<br>"
            "• AI翻译自动保存<b>缓存</b>，随时可退出翻译，再次翻译时极速加载缓存<br>"
            "• 智能识别和保护<b>变量</b>，减少误翻<br>"
            "• 构筑提示词会智能识别该批量内容中的<b>术语</b>（术语表中的），有效保证人名地名一致性<br>"
            "• 仅向AI发送键值对中的<b>值</b>，有效减少 token 消耗<br><br>"
            "<b>🔍 质量检查：</b><br>"
            "• 检查<b>中英混杂</b>、<b>未翻译内容</b>、<b>变量一致性</b><br>"
            "• 支持批量AI修复问题（不使用缓存）和人工编辑<br>"
            "• 应用修复Output后会自动将新翻译内容保存到缓存中<br><br>"
            "<b>🖋️ 人工翻译：</b><br>"
            "• 提供人工翻译界面，<b>变量实时高亮显示</b>，数量统计<br>"
            "• output 中若有同名文件（default和zh是对应关系），会自动显示现有翻译<br>"
            "• 支持<b>分页浏览</b>、<b>搜索</b>和<b>编辑</b><br><br>"
            "<b>📋 Manifest翻译：</b><br>"
            "• 专门处理模组的 <b>manifest.json</b> 文件<br>"
            "• 支持增量翻译，用于 mod 更新时恢复此文件原有翻译<br>"
            "• 翻译其中的 <b>name</b> 和 <b>description</b><br><br>"
            "<b>⚙️ 配置菜单翻译：</b><br>"
            "• 翻译模组的配置菜单 <b>content.json</b> 内容<br>"
            "• 若 content.json 中没有 <b>ConfigSchema</b> 将无法构建翻译内容<br>"
            "• 输出文件在 <b>output/mod文件名_zh.json</b>，手动将内容添加到 output/zh.json 中<br>"
            "• 翻译内容不保证有效，因为有的 mod 作者未按规范制作配置菜单<br>"
            "• 添加时注意<b>英文逗号</b>问题，补充或删除，<b>不要添加花括号</b>，若有重复键记得去重<br><br>"
            "<b>🏷️ 人名地名检测：</b><br>"
            "• 快速提取 i18n 中的中英文对应<b>术语</b><br>"
            "• 用于补充术语表，提高人名地名翻译<b>一致性</b>"
        )
        features_text.setWordWrap(True)
        features_text.setStyleSheet("background-color: transparent;")
        features_layout.addWidget(features_text)
        
        content_layout.addWidget(features_group)

        # 3. 常见问题
        faq_group = QGroupBox("3. 常见问题 ❓")
        faq_layout = QVBoxLayout(faq_group)

        faq_text = QLabel()
        faq_text.setTextFormat(Qt.TextFormat.RichText)
        faq_text.setText(
            "<b>Q: 点击翻译按钮没有响应怎么办？</b><br>"
            "<b>A:</b> 请检查<b>API密钥</b>是否正确配置，<b>网络连接</b>是否正常。<b>本地API不用输入秘钥</b>。<br><br>"
            "<b>Q: 如何备份翻译进度？</b><br>"
            "<b>A:</b> 整个<b>项目文件夹</b>就是备份，建议定期复制备份。<br><br>"
            "<b>Q: 支持哪些翻译API？</b><br>"
            "<b>A:</b> 目前支持 <b>chatgpt</b>，大部分<b>国内AI模型API</b>，<b>本地API</b>（推荐 qwen3-30b-a3b-instruct-2507 Q4量化，32Gb运存体感不错）<br><br>"
            "<b>Q: 翻译速度很慢怎么办？</b><br>"
            "<b>A:</b> 可以在设置中调整<b>批次大小</b>，启用<b>缓存机制</b>。<br><br>"
            "<b>Q: 如何提高翻译质量？</b><br>"
            "<b>A:</b> 使用<b>术语表</b>功能，添加专业术语；翻译完成后运行<b>质量检查</b>，或在<b>人工翻译</b>中手动校对重要内容。"
        )
        faq_text.setWordWrap(True)
        faq_text.setStyleSheet("background-color: transparent;")
        faq_layout.addWidget(faq_text)

        content_layout.addWidget(faq_group)
        
        # 4. 项目管理
        project_group = QGroupBox("4. 项目管理 📁")
        project_layout = QVBoxLayout(project_group)
        
        project_text = QLabel()
        project_text.setTextFormat(Qt.TextFormat.RichText)
        project_text.setText(
            "<b>项目结构说明：</b><br><br>"
            "<b>项目文件夹结构：</b><br>"
            "├── <b>en/</b>          # 英文原文文件<br>"
            "├── <b>zh/</b>          # 中文参考文件<br>"
            "├── <b>output/</b>      # 翻译输出文件<br>"
            "├── <b>manifest/</b>    # manifest翻译输出文件<br>"
            "├── <b>cache/</b>       # 翻译缓存<br>"
            "└── <b>project_config.json</b>  # 项目配置文件<br><br>"
            "<b>支持的文件格式：</b><br>"
            "• 支持<b>.json文件</b>中的注释结构和特殊格式，保存翻译时也会保留注释<br>"
            "• 存在重复键，将更新没有被注释的那条，若两条都没有被注释，会产生问题，需手动打开文件修改<br>"
            "• 多行文本会修改为单行，换行符会自动替换为\\n<br><br>"
            "<b>注意事项：</b><br>"
            "• <b>default.json</b>会自动映射为<b>zh.json</b><br>"
            "• 建议大型 mod 单独使用一个项目文件夹，专门创建一个项目用于 manifest 文件的翻译或恢复"
        )
        project_text.setWordWrap(True)
        project_text.setStyleSheet("background-color: transparent;")
        project_layout.addWidget(project_text)
        
        content_layout.addWidget(project_group)
        
        # 5. 翻译功能详解
        translation_group = QGroupBox("5. 翻译功能详解 🌐")
        translation_layout = QVBoxLayout(translation_group)
        
        translation_text = QLabel()
        translation_text.setTextFormat(Qt.TextFormat.RichText)
        translation_text.setText(
            "<b>变量保护机制：</b><br>"
            "程序会自动识别并保护以下类型的变量：<br>"
            "• <b>[...] ${...} 和 {{...}}</b> 格式的变量<br>"
            "• <b>%item...%%</b> 格式的物品变量<br>"
            "• <b>%fork、%noturn</b> 等特殊标记<br>"
            "• <b>$q...# 和 $r...#</b> 格式的对话变量<br>"
            "• 其他游戏特定的变量格式<br><br>"
            "<b>增量翻译：</b><br>"
            "• 自动检测<b>已翻译的内容</b><br>"
            "• 只翻译<b>新增或修改的内容</b><br>"
            "• 保持原有翻译的<b>格式和注释</b><br><br>"
            "<b>缓存机制：</b><br>"
            "• <b>自动缓存已翻译</b>内容的原英文值<br>"
            "• 相同英文内容直接使用<b>缓存</b><br>"
            "• 可在<b>全局设置</b>中清理缓存<br><br>"
            "<b>翻译顺序机制：</b><br>"
            "• 智能翻译：增量翻译→缓存翻译→AI翻译<br>"
            "• 质量检查：仅使用AI翻译，人工编辑保存后会将结果保存到缓存<br>"
            "• Manifest翻译：增量翻译与AI翻译互斥，当name和description仅有一个是中文时，即使拖放中文mod，也不会翻译未翻译的那条<br>"
            "• 配置菜单翻译：缓存翻译→AI翻译"
        )
        translation_text.setWordWrap(True)
        translation_text.setStyleSheet("background-color: transparent;")
        translation_layout.addWidget(translation_text)
        
        content_layout.addWidget(translation_group)
        
        # 6. 质量检查
        quality_group = QGroupBox("6. 质量检查 🔍")
        quality_layout = QVBoxLayout(quality_group)

        quality_text = QLabel()
        quality_text.setTextFormat(Qt.TextFormat.RichText)
        quality_text.setText(
            "<b>质量检查功能：</b><br><br>"
            "<b>检查项目：</b><br>"
            "• <b>中英混杂</b>：检查翻译中是否包含英文<br>"
            "• <b>未翻译</b>：检查是否有未翻译的英文<br>"
            "• <b>变量问题</b>：检查变量数量与内容是否与英文一致<br><br>"
            "<b>使用方法：</b><br>"
            "1. 点击<b>开始质量检查</b><br>"
            "2. 查看<b>检查结果</b><br>"
            "3. 可以<b>批量AI修复</b>或<b>手动编辑</b><br><br>"
            "<b>建议：</b><br>"
            "• 翻译完成后务必进行<b>质量检查</b><br>"
            "• 重点关注<b>未翻译</b>和<b>中英夹杂</b>问题<br>"
            "• 使用<b>AI重新翻译</b>功能，再<b>手动编辑</b>提高效率"
        )
        quality_text.setWordWrap(True)
        quality_text.setStyleSheet("background-color: transparent;")
        quality_layout.addWidget(quality_text)

        content_layout.addWidget(quality_group)

        # 7. 人名地名检测
        location_name_group = QGroupBox("7. 人名地名检测 🏷️")
        location_name_layout = QVBoxLayout(location_name_group)

        location_name_text = QLabel()
        location_name_text.setTextFormat(Qt.TextFormat.RichText)
        location_name_text.setText(
            "<b>人名地名检测功能：</b><br><br>"
            "目前仅能检测<b>中英文人名地名</b><br>"
            "因作为一个小工具使用，所以并没有依赖成熟的人名检测包<br>"
            "依靠简单算法提取<b>术语</b>，需要<b>人工筛选</b><br><br>"
            "<b>使用方法：</b><br>"
            "1. 将解压后的 mod 文件夹拖入步骤1，需要有 <b>i18n</b> 中的 <b>default</b> 和 <b>zh</b> 文件<br>"
            "2. 点击<b>开始检测人名地名</b>，稍等片刻，点击<b>查看结果</b><br>"
            "3. 在新打开的窗口进行<b>人工筛选</b>，需要的勾选中复选框，点击<b>移动到已确认</b><br>"
            "4. 筛选完毕后，点击下方<b>已确认追加到术语表</b>按钮，添加术语<br><br>"
            "<b>注意：</b><br>"
            "• 此功能仅做<b>补充使用</b>，精确术语还是需要查看 mod 官方 wiki 查看官方翻译<br>"
            "• 误添加术语可在<b>全局设置-术语表</b>处修改删除<br>"
            "• 为提高效率可<b>导出术语表 Json</b>，在编辑器中修改完毕后再<b>导入 Json</b>"
        )
        location_name_text.setWordWrap(True)
        location_name_text.setStyleSheet("background-color: transparent;")
        location_name_layout.addWidget(location_name_text)

        content_layout.addWidget(location_name_group)

        project_info_group = QGroupBox("8. 项目信息与支持 📚")
        project_info_layout = QVBoxLayout(project_info_group)

        project_info_text = QLabel()
        project_info_text.setTextFormat(Qt.TextFormat.RichText)
        project_info_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        project_info_text.setOpenExternalLinks(True)
        project_info_text.setText(
            "项目开源地址与联系方式：<br><br>"
            "<b>GitHub 开源仓库：</b><br>"
            "<a href='https://github.com/sliencezhang/Stardew-Valley-Translation-Tool' style='color: #0078d4; text-decoration: none;'>"
            "https://github.com/sliencezhang/Stardew-Valley-Translation-Tool</a><br><br>"
            "<b>B站教程地址：</b><br>"
            "<a href='https://www.bilibili.com/video/BV15NqbBAEQN/' style='color: #0078d4; text-decoration: none;'>"
            "https://www.bilibili.com/video/BV15NqbBAEQN/</a><br><br>"
            "<b>硅基流动注册邀请：</b><br>"
            "<a href='https://cloud.siliconflow.cn/i/J1D1FRdM' style='color: #0078d4; text-decoration: none;'>"
            "https://cloud.siliconflow.cn/i/J1D1FRdM</a><br>"
            "<b>注册送2000W token，足够翻译使用，若可以还请通过我的链接注册支持我哦！</b><br><br>"
            "<b>说明：</b><br>"
            "• 本项目采用原生 PySide6 构建GUI，前期调教 DeepSeek3.2 生成，后期通过 iFlow Cli 的 GLM-4.6 优化与美化<br>"
            "• 不可避免的💩山代码，还请见谅<br>"
            "• 本项目完全<b>开源免费</b>，欢迎在 GitHub 上提交 Issue 或 Pull Request<br>"
            "• 如有使用问题或建议，可在 GitHub Issues 或 B站 使用教程视频评论区反馈<br>"
            "• 欢迎 Star 项目支持开发，也欢迎参与翻译或代码贡献<br><br>"
            "<b>致谢：</b><br>"
            "感谢 DeepSeek3.2，iFlow Cli 与 GLM-4.6。<br>"
            "特别感谢星露谷物语模组作者对游戏生态的支持！"
        )
        project_info_text.setWordWrap(True)
        project_info_text.setStyleSheet("background-color: transparent;")
        project_info_layout.addWidget(project_info_text)

        content_layout.addWidget(project_info_group)

        # 添加弹性空间
        content_layout.addStretch()
        
        # 设置滚动区域
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return widget

    def _load_background_image(self):
        """加载背景图片"""
        self.background_pixmap = load_background_image(config.theme)





if __name__ == "__main__":

    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = GlobalSettingsDialog()
    dialog.show()
    sys.exit(app.exec())