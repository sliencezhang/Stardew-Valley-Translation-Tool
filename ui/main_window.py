# ui/main_window.py
import os
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QTextEdit, QTabWidget, QFileDialog,
                               QGroupBox, QDialog)
from PySide6.QtCore import Qt, QTimer, Slot, QThread, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor

from core.config import config
from core.file_tool import file_tool
from core.project_manager import ProjectManager
from core.signal_bus import signal_bus
from core.translation_executor import TranslationExecutor

from ui.styles import get_main_window_style, get_step_style, get_background_blue_style, get_log_text_style
from ui.settings_dialog import GlobalSettingsDialog
from ui.progress_dialog import TranslationProgressDialog
from ui.custom_message_box import CustomMessageBox
from ui.tabs.tab_config import TabConfig
from ui.tabs.tab_manifest import TabManifest
from ui.tabs.tab_manual_translation import ManualTranslationTab
from ui.tabs.tab_name_detection import TabNameDetection
from ui.tabs.tab_quality_check import TabQualityCheck
from ui.tabs.tab_smart_translation import TabSmartTranslation
from ui.widgets import ProjectDialog, BackgroundWidget, load_background_image


class TranslationWorker(QThread):
    """翻译工作线程"""
    task_completed = Signal(dict)

    def __init__(self, executor, task_type, params):
        super().__init__()
        self.executor = executor
        self.task_type = task_type
        self.params = params

    def run(self):
        """执行翻译任务"""
        try:
            result = self.executor.execute_task(self.task_type, self.params)
            self.task_completed.emit(result)
        except Exception as e:
            self.task_completed.emit({
                '成功': False,
                '消息': f'任务执行失败: {str(e)}'
            })

class StardewTranslationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # 设置窗口透明以显示圆角
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.project_manager = ProjectManager()
        self.translation_executor = None
        self.worker_thread = None
        # 创建进度对话框
        self.progress_dialog = TranslationProgressDialog(self)
        self.progress_dialog.operationStopped.connect(self.stop_current_operation)

        # 设置窗口图标
        from ui.styles import get_icon
        self.setWindowIcon(get_icon("logo"))
        
        # 加载背景图片
        self.background_pixmap = load_background_image(config.theme)

        # 设置现代UI样式
        self.setup_modern_ui()
        self.init_ui()
        # self.setup_logging()

        # 启动时检查当前项目路径
        QTimer.singleShot(100, self.check_current_project_path)

    def check_current_project_path(self):
        """检查当前项目路径是否存在"""
        if self.project_manager.current_project:
            project_path = self.project_manager.current_project.path
            if not os.path.exists(project_path):
                signal_bus.log_message.emit("WARNING", f"当前项目路径不存在: {project_path}", {})
                reply = CustomMessageBox.question(
                    self,
                    "项目路径问题",
                    f"当前项目路径不存在:\n{project_path}\n\n是否重新选择项目文件夹？"
                )
                if reply == CustomMessageBox.Yes:
                    self.open_project()

    def setup_modern_ui(self):
        """设置现代化UI样式"""
        self.setStyleSheet(get_main_window_style(config.theme))


    @Slot(str, str, dict)
    def on_log_message(self, level: str, message: str, detail: dict = None):
        """接收并显示日志"""
        # 为没有图标的类型返回空字符串
        icon_map = {"INFO": "🔵", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍", "NONE": ""}
        icon = icon_map.get(level, "📝")
        
        detail_text = f" ({', '.join(f'{k}={v}' for k, v in detail.items())})" if detail else ""

        # 如果有图标则添加空格，没有则不加
        if icon:
            self.log_text.append(f"{icon} {message}{detail_text}")
        else:
            self.log_text.append(f"{message}{detail_text}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("星露谷翻译工具")
        self.setGeometry(100, 100, 1200, 800)
        QTimer.singleShot(500, self.check_api_status)

        # 创建带背景图片的中心widget
        central_widget = BackgroundWidget(self.background_pixmap, config.theme)
        self.setCentralWidget(central_widget)

        # 主布局（垂直，包含标题栏和内容）
        main_container_layout = QVBoxLayout(central_widget)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        main_container_layout.setSpacing(0)
        
        # 添加自定义标题栏（主窗口显示主题切换按钮）
        from ui.custom_title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(self, show_theme_toggle=True)
        main_container_layout.addWidget(self.title_bar)
        
        # 内容区域
        content_widget = QWidget()
        main_container_layout.addWidget(content_widget)
        
        main_layout = QHBoxLayout(content_widget)

        # 左侧步骤说明
        left_widget = QWidget()
        left_widget.setMaximumWidth(280)
        left_layout = QVBoxLayout(left_widget)

        # 项目信息区域
        project_group = QGroupBox("项目管理")
        project_layout = QVBoxLayout(project_group)

        self.project_info_label = QLabel("当前项目: 无")
        self.project_info_label.setStyleSheet(get_background_blue_style(config.theme))
        self.project_info_label.setWordWrap(True)
        project_layout.addWidget(self.project_info_label)

        btn_layout = QHBoxLayout()
        self.new_project_btn = QPushButton("新建项目")
        self.new_project_btn.clicked.connect(self.create_new_project)
        self.open_project_btn = QPushButton("打开项目")
        self.open_project_btn.clicked.connect(self.open_project)
        self.settings_btn = QPushButton("全局设置")
        self.settings_btn.clicked.connect(self.open_global_settings)
        
        btn_layout.addWidget(self.new_project_btn)
        btn_layout.addWidget(self.open_project_btn)
        btn_layout.addWidget(self.settings_btn)
        project_layout.addLayout(btn_layout)

        left_layout.addWidget(project_group)

        # 工作流程
        title = QLabel("翻译工作流程")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        steps = [
            (1, "创建/打开项目", "新建或打开现有翻译项目"),
            (2, "全局设置", "配置 API、提示词、术语表与缓存\n已内置默认配置，可自定义导入导出"),
            (3, "导入英文文件", "拖放英文 JSON 文件到步骤 1 区域"),
            (4, "导入中文文件（可选）", "拖放中文 JSON 文件到步骤 2 区域\nzh 对应 default，其他文件需同名"),
            (5, "开始 AI 翻译", "增量翻译 → 缓存匹配 → AI 翻译"),
            (6, "质量检查", "检查翻译质量，支持重译或人工修正"),
            (7, "其他功能", "人工翻译、Manifest 翻译、配置翻译、人名检测")
        ]

        self.step_circles = []
        for step_num, title, desc in steps:
            step_widget, step_circle = self.create_step_widget(step_num, title, desc)
            self.step_circles.append(step_circle)
            left_layout.addWidget(step_widget)

        left_layout.addStretch()
        main_layout.addWidget(left_widget)

        # 右侧操作区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 初始化各个标签页
        self.tab_smart_translation = TabSmartTranslation()
        self.quality_tab = TabQualityCheck()
        self.manifest_tab = TabManifest()
        self.config_tab = TabConfig()
        self.manual_translation_tab = ManualTranslationTab()
        self.name_detection_tab = TabNameDetection()

        # 设置项目管理器
        for tab in [self.tab_smart_translation, self.quality_tab, self.manifest_tab, self.config_tab,
                    self.manual_translation_tab, self.name_detection_tab]:
            tab.set_project_manager(self.project_manager)

        # 初始化翻译执行器
        self.translation_executor = TranslationExecutor(self.project_manager)

        # 连接信号
        signal_bus.startSmartTranslation.connect(self.start_smart_translation)
        signal_bus.runQualityCheck.connect(self.run_quality_check)
        signal_bus.retranslateQualityIssues.connect(self.retranslate_quality_issues)
        signal_bus.applyQualityFixes.connect(self.apply_quality_fixes)
        signal_bus.manifest_translate_request.connect(self.translate_manifests)
        signal_bus.manifest_incremental_request.connect(self.incremental_translate_manifests)
        signal_bus.startConfigTranslation.connect(self.translate_config_menu)

        # 添加标签页
        self.tab_widget.addTab(self.tab_smart_translation, "🚀 智能翻译")
        self.tab_widget.addTab(self.quality_tab, "🔍 质量检查")
        self.tab_widget.addTab(self.manual_translation_tab, "🖋️ 人工翻译")
        self.tab_widget.addTab(self.manifest_tab, "📋 Manifest翻译")
        self.tab_widget.addTab(self.config_tab, "⚙️ 配置菜单翻译")
        self.tab_widget.addTab(self.name_detection_tab, "🏷️ 人名地名检测")

        right_layout.addWidget(self.tab_widget)

        # 日志区域
        log_label = QLabel("操作日志")
        right_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setFixedHeight(150)
        self.log_text.setMaximumHeight(400)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(get_log_text_style(config.theme))
        right_layout.addWidget(self.log_text)

        main_layout.addWidget(right_widget)

        # 创建状态栏
        self.statusBar().showMessage("就绪")

        # 连接翻译信号
        self._connect_translation_signals()
        signal_bus.log_message.connect(self.on_log_message)
        
        # 输出启动信息到日志
        signal_bus.log_message.emit("NONE", "✅ 应用程序启动完成", {})
        signal_bus.log_message.emit("NONE", "🎮 开始使用星露谷翻译工具吧！", {})

    def _connect_translation_signals(self):
        """连接翻译引擎信号"""
        # 连接翻译引擎信号 -> 进度对话框
        signal_bus.translation_started.connect(self.progress_dialog.add_file_progress)
        signal_bus.translation_progress.connect(self.update_translation_progress)
        signal_bus.translation_item_added.connect(self.progress_dialog.add_translation_detail)
        signal_bus.translation_item_updated.connect(self.progress_dialog.update_translation_detail)
        signal_bus.translation_completed.connect(self._on_translation_completed)
        signal_bus.translation_error.connect(self._on_translation_error)
        signal_bus.batch_translated.connect(self._on_batch_translated)

    def check_api_status(self):
        """检查API密钥状态"""
        if config.api_key:
            signal_bus.log_message.emit("SUCCESS", "检测到已保存的API密钥，自动翻译功能已启用", {})

    def create_step_widget(self, step_num, title, description):
        """创建步骤组件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        step_circle = QLabel(str(step_num))
        step_circle.setFixedSize(30, 30)
        step_circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_circle.setStyleSheet(get_step_style(config.theme))

        info_layout = QVBoxLayout()
        title_label = QLabel(title)
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)

        info_layout.addWidget(title_label)
        info_layout.addWidget(desc_label)

        layout.addWidget(step_circle)
        layout.addLayout(info_layout)
        layout.addStretch()

        return widget, step_circle

    def open_global_settings(self):
        """打开全局设置对话框"""
        dialog = GlobalSettingsDialog(self)
        dialog.set_project_manager(self.project_manager)
        signal_bus.settingsSaved.connect(self.on_global_settings_saved)
        dialog.exec()

    def on_global_settings_saved(self, settings):
        """全局设置保存回调"""
        signal_bus.log_message.emit("SUCCESS", "全局设置已保存", {})
        # 更新主题和背景图片
        self.apply_theme()

    def apply_theme(self):
        """应用主题到所有组件"""
        from ui.styles import (get_start_button_style, get_save_button_style, 
                                get_background_gray_style, get_settings_desc_style)
        
        # 更新背景图片
        self.background_pixmap = load_background_image(config.theme)
        if hasattr(self, 'centralWidget') and isinstance(self.centralWidget(), BackgroundWidget):
            self.centralWidget().set_background(self.background_pixmap, config.theme)
        
        # 更新自定义标题栏主题
        if hasattr(self, 'title_bar'):
            self.title_bar.update_theme()
        
        self.setStyleSheet(get_main_window_style(config.theme))
        self.project_info_label.setStyleSheet(get_background_blue_style(config.theme))
        
        # 操作日志使用卡片背景色以区分
        if hasattr(self, 'log_text'):
            self.log_text.setStyleSheet(get_log_text_style(config.theme))
        
        # 更新步骤圆圈
        if hasattr(self, 'step_circles'):
            for circle in self.step_circles:
                circle.setStyleSheet(get_step_style(config.theme))
        
        # 智能翻译Tab
        if hasattr(self, 'tab_smart_translation'):
            if hasattr(self.tab_smart_translation, 'auto_translate_btn'):
                self.tab_smart_translation.auto_translate_btn.setStyleSheet(get_start_button_style(config.theme))
            # 更新拖放框
            if hasattr(self.tab_smart_translation, 'en_files_widget'):
                self.tab_smart_translation.en_files_widget._update_style()
            if hasattr(self.tab_smart_translation, 'zh_files_widget'):
                self.tab_smart_translation.zh_files_widget._update_style()
        
        # 质量检查Tab
        if hasattr(self, 'quality_tab'):
            if hasattr(self.quality_tab, 'quality_stats_label'):
                self.quality_tab.quality_stats_label.setStyleSheet(get_background_blue_style(config.theme))
            if hasattr(self.quality_tab, 'run_quality_check_btn'):
                self.quality_tab.run_quality_check_btn.setStyleSheet(get_start_button_style(config.theme))
            if hasattr(self.quality_tab, 'retranslate_issues_btn'):
                self.quality_tab.retranslate_issues_btn.setStyleSheet(get_start_button_style(config.theme))
            if hasattr(self.quality_tab, 'apply_fixes_btn'):
                self.quality_tab.apply_fixes_btn.setStyleSheet(get_start_button_style(config.theme))
            # 更新表格主题
            if hasattr(self.quality_tab, 'update_table_theme'):
                self.quality_tab.update_table_theme()
        
        # 人工翻译Tab
        if hasattr(self, 'manual_translation_tab'):
            if hasattr(self.manual_translation_tab, 'save_btn'):
                self.manual_translation_tab.save_btn.setStyleSheet(get_save_button_style(config.theme))
            if hasattr(self.manual_translation_tab, 'file_info_label'):
                self.manual_translation_tab.file_info_label.setStyleSheet(get_background_gray_style(config.theme))
            # 更新滚动区域和翻译区域背景色
            from PySide6.QtWidgets import QScrollArea
            from ui.styles import get_scroll_area_style, get_widget_background_style
            for scroll in self.manual_translation_tab.findChildren(QScrollArea):
                scroll.setStyleSheet(get_scroll_area_style(config.theme))
            if hasattr(self.manual_translation_tab, 'translation_widget'):
                self.manual_translation_tab.translation_widget.setStyleSheet(get_widget_background_style(config.theme))
            # 重新加载当前页面以更新动态创建的组件样式
            if hasattr(self.manual_translation_tab, 'current_file') and self.manual_translation_tab.current_file:
                self.manual_translation_tab.load_page()
        
        # Manifest翻译Tab
        if hasattr(self, 'manifest_tab'):
            if hasattr(self.manifest_tab, 'manifest_translate_btn'):
                self.manifest_tab.manifest_translate_btn.setStyleSheet(get_start_button_style(config.theme))
            if hasattr(self.manifest_tab, 'selected_en_folders_label'):
                self.manifest_tab.selected_en_folders_label.setStyleSheet(get_background_gray_style(config.theme))
            if hasattr(self.manifest_tab, 'selected_zh_folders_label'):
                self.manifest_tab.selected_zh_folders_label.setStyleSheet(get_background_gray_style(config.theme))
            # 更新拖放框
            if hasattr(self.manifest_tab, 'manifest_widget'):
                self.manifest_tab.manifest_widget._update_style()
            if hasattr(self.manifest_tab, 'manifest_zh_widget'):
                self.manifest_tab.manifest_zh_widget._update_style()
            # 更新help_text
            for child in self.manifest_tab.findChildren(QLabel):
                if child.wordWrap() and "使用说明" in child.text():
                    child.setStyleSheet(get_settings_desc_style(config.theme))
        
        # 配置菜单翻译Tab
        if hasattr(self, 'config_tab'):
            if hasattr(self.config_tab, 'config_translate_btn'):
                self.config_tab.config_translate_btn.setStyleSheet(get_start_button_style(config.theme))
            if hasattr(self.config_tab, 'selected_folders_label'):
                self.config_tab.selected_folders_label.setStyleSheet(get_background_gray_style(config.theme))
            # 更新拖放框
            if hasattr(self.config_tab, 'config_mod_widget'):
                self.config_tab.config_mod_widget._update_style()
            # 更新help_text
            for child in self.config_tab.findChildren(QLabel):
                if child.wordWrap() and "使用说明" in child.text():
                    child.setStyleSheet(get_settings_desc_style(config.theme))
        
        # 人名地名检测Tab
        if hasattr(self, 'name_detection_tab'):
            if hasattr(self.name_detection_tab, 'detect_btn'):
                self.name_detection_tab.detect_btn.setStyleSheet(get_start_button_style(config.theme))
            if hasattr(self.name_detection_tab, 'view_results_btn'):
                self.name_detection_tab.view_results_btn.setStyleSheet(get_start_button_style(config.theme))
            if hasattr(self.name_detection_tab, 'selected_folders_label'):
                self.name_detection_tab.selected_folders_label.setStyleSheet(get_background_gray_style(config.theme))
            if hasattr(self.name_detection_tab, 'results_label'):
                self.name_detection_tab.results_label.setStyleSheet(get_background_gray_style(config.theme))
            # 更新拖放框
            if hasattr(self.name_detection_tab, 'name_mod_widget'):
                self.name_detection_tab.name_mod_widget._update_style()
            # 更新help_text
            for child in self.name_detection_tab.findChildren(QLabel):
                if child.wordWrap() and "使用说明" in child.text():
                    child.setStyleSheet(get_settings_desc_style(config.theme))
        
        # 更新进度对话框主题
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.update_theme()
        
        for i in range(self.findChildren(QWidget).__len__()):
            widget = self.findChildren(QWidget)[i]
            if hasattr(widget, 'apply_theme'):
                widget.apply_theme(config.theme)

    def create_new_project(self):
        """创建新项目"""
        try:
            dialog = ProjectDialog(self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            project_info = dialog.get_project_info()
            name = project_info.get('name', '')
            base_path = project_info.get('path', '')
            
            if not name or not base_path:
                CustomMessageBox.warning(self, "警告", "请输入项目名称和路径")
                return

            signal_bus.log_message.emit("INFO", f"正在创建项目: {name}", {})

            project_path = self.project_manager.create_project(name, base_path)

            if project_path:
                self.update_project_info()
                signal_bus.log_message.emit("SUCCESS", f"项目创建成功: {project_path}", {})
            else:
                signal_bus.log_message.emit("ERROR", "项目创建失败", {})

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"创建项目时发生错误: {str(e)}", {})

    def open_project(self):
        """打开项目"""
        try:
            # 设置默认目录为应用所在目录
            try:
                from core.path_utils import get_application_directory
                default_dir = str(get_application_directory())
            except ImportError:
                import sys
                from pathlib import Path
                if getattr(sys, 'frozen', False):
                    default_dir = str(Path(sys.executable).parent)
                else:
                    default_dir = ""
            
            project_folder = QFileDialog.getExistingDirectory(self, "选择项目文件夹", default_dir)
            if project_folder:
                signal_bus.log_message.emit("INFO", f"正在打开项目: {project_folder}", {})

                success = self.project_manager.open_project(project_folder)
                if success:
                    self.update_project_info()
                    signal_bus.log_message.emit("SUCCESS", "项目打开成功", {})
                else:
                    signal_bus.log_message.emit("ERROR", "项目打开失败", {})

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"打开项目时发生错误: {str(e)}", {})

    def update_project_info(self):
        """更新项目信息显示"""
        try:
            if not self.project_manager.current_project:
                self.project_info_label.setText("当前项目: 无")
                return

            project = self.project_manager.current_project
            project_name = project.name
            project_path = project.path
            
            # 更新翻译执行器的缓存实例
            if self.translation_executor:
                from core.translation_cache import TranslationCache
                self.translation_executor.cache = TranslationCache(self.project_manager)
                signal_bus.log_message.emit("DEBUG", f"更新翻译执行器的缓存实例到项目: {project_path}", {})

            # 验证项目路径是否存在
            if not os.path.exists(project_path):
                CustomMessageBox.warning(self, "项目路径问题",
                                    f"项目路径不存在:\n{project_path}\n\n请重新打开项目。")
                self.project_manager.current_project = None
                self.project_info_label.setText("当前项目: 无 (路径不存在)")
                return

            # 格式化显示路径
            display_path = f"...{project_path[-37:]}" if len(project_path) > 40 else project_path
            self.project_info_label.setText(f"当前项目: {project_name}\n{display_path}")

            # 统计文件数量
            en_folder = self.project_manager.get_folder_path('en')
            zh_folder = self.project_manager.get_folder_path('zh')
            output_folder = self.project_manager.get_folder_path('output')
            manifest_folder = self.project_manager.get_folder_path('manifest')

            # 统计各文件夹的文件数量
            en_files = len(list(Path(en_folder).rglob('*.json'))) if os.path.exists(en_folder) else 0
            zh_files = len(list(Path(zh_folder).rglob('*.json'))) if os.path.exists(zh_folder) else 0
            output_files = len(list(Path(output_folder).rglob('*.json'))) if os.path.exists(output_folder) else 0

            # 统计manifest文件夹中的文件夹数量
            manifest_count = 0
            if os.path.exists(manifest_folder):
                manifest_count = len([d for d in os.listdir(manifest_folder)
                                      if os.path.isdir(os.path.join(manifest_folder, d))])

            # 更新状态栏
            status_msg = f"项目: {project_name} - EN:{en_files} ZH:{zh_files} OUT:{output_files} MANIFEST:{manifest_count}"
            self.statusBar().showMessage(status_msg)

            # 更新文件显示
            self.tab_smart_translation.refresh_project_files()

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"更新项目信息失败: {str(e)}", {})
            self.project_info_label.setText("当前项目: 无")

    def show_progress_dialog(self, operation_name):
        """显示进度对话框"""
        signal_bus.log_message.emit("DEBUG", f"显示进度对话框被调用: {operation_name}", {})
        
        is_task_running = self.worker_thread and self.worker_thread.isRunning()
        
        # 检查进度对话框是否存在或已被关闭
        if not self.progress_dialog:
            # 第一次创建，创建新的进度对话框
            self.progress_dialog = TranslationProgressDialog(self)
            self.progress_dialog.operationStopped.connect(self.stop_current_operation)
            self._connect_translation_signals()
            # 添加标志：任务是否已完成
            self.progress_dialog.task_completed = False
            # 只有在没有任务运行时才调用start_operation
            if not is_task_running:
                self.progress_dialog.start_operation(operation_name)
        elif not self.progress_dialog.isVisible():
            # 窗口已关闭，检查是否有任务正在运行
            if is_task_running:
                # 有任务正在运行，重新显示同一个窗口，不调用start_operation
                signal_bus.log_message.emit("DEBUG", "任务正在运行，重新显示进度窗口（保留数据）", {})
            elif hasattr(self.progress_dialog, 'task_completed') and self.progress_dialog.task_completed:
                # 任务已完成，创建新窗口
                signal_bus.log_message.emit("DEBUG", "任务已完成，创建新的进度窗口", {})
                self.progress_dialog.deleteLater()
                self.progress_dialog = TranslationProgressDialog(self)
                self.progress_dialog.operationStopped.connect(self.stop_current_operation)
                self._connect_translation_signals()
                self.progress_dialog.task_completed = False
                self.progress_dialog.start_operation(operation_name)
            else:
                # 其他情况，重新显示同一个窗口
                signal_bus.log_message.emit("DEBUG", "重新显示进度窗口", {})
                self.progress_dialog.start_operation(operation_name)
        else:
            # 窗口已经可见，不需要做任何操作
            signal_bus.log_message.emit("DEBUG", "进度窗口已经可见", {})
        
        self.progress_dialog.show()

    def update_translation_progress(self, filename, progress, status):
        """更新翻译进度 - 通过 signal_bus 接收"""
        if self.progress_dialog:
            # 先更新文件进度
            self.progress_dialog.update_file_progress(filename, status, progress)

            # 如果提供了数值进度，也更新总体进度
            if isinstance(progress, (int, float)):
                self.progress_dialog.update_overall_progress(int(progress))

    def run_worker_in_thread(self, task_type, params, operation_name):
        """在工作线程中运行翻译任务"""
        signal_bus.log_message.emit("DEBUG", f"当前工作线程: {self.worker_thread}", {})
        
        # 检查是否有线程正在运行
        if self.worker_thread:
            if self.worker_thread.isRunning():
                # 有任务正在运行，只显示进度窗口，不创建新任务
                signal_bus.log_message.emit("DEBUG", "任务正在运行，只显示进度窗口", {})
                self.show_progress_dialog(operation_name)
                return
            else:
                self.worker_thread.deleteLater()
                self.worker_thread = None

        # 显示进度对话框
        self.show_progress_dialog(operation_name)

        # 创建工作线程
        self.worker_thread = TranslationWorker(self.translation_executor, task_type, params)
        self.worker_thread.task_completed.connect(lambda result: self.on_task_completed(task_type, result))
        self.worker_thread.start()

    def on_task_completed(self, task_type, result):
        """任务完成回调"""
        success = result.get('成功', False)

        if task_type == "smart_translation":
            self.on_smart_translation_complete(result)
        elif task_type == "quality_review":
            self.on_quality_review_complete(result)
        elif task_type == "config_menu":
            self.on_config_translation_complete(result)
        elif task_type == "manifest":
            self.on_manifest_translation_complete(result)
        elif task_type == "manifest_incremental":
            self.on_manifest_translation_complete(result)

        # 处理进度对话框
        if self.progress_dialog:
            self.progress_dialog.operation_completed(success)
            # 标记任务已完成
            self.progress_dialog.task_completed = True
        
        # 清理工作线程
        if self.worker_thread:
            self.worker_thread.wait()  # 等待线程完全结束
            self.worker_thread.deleteLater()
            self.worker_thread = None
    
    def _cleanup_progress_dialog(self):
        """清理进度对话框（只在真正需要时调用）"""
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
                self.progress_dialog.deleteLater()
            except:
                pass  # 忽略清理时的错误
            finally:
                self.progress_dialog = None
            signal_bus.log_message.emit("DEBUG", "工作线程已清理", {})

    def _on_translation_completed(self, filename, success, message):
        """翻译完成信号处理"""
        signal_bus.log_message.emit("INFO", f"📄 文件 {filename}: {message}", {})
        
        # 更新进度对话框中对应文件的完成状态
        if self.progress_dialog and hasattr(self.progress_dialog, 'file_items'):
            if filename in self.progress_dialog.file_items:
                # 更新文件项的状态
                item = self.progress_dialog.file_items[filename]
                item['状态'] = '完成' if success else '失败'
                item['progress'] = 100 if success else 0
                
                # 更新表格显示
                if item.get('row') is not None:
                    row = item['row']
                    self.progress_dialog.files_table.item(row, 1).setText('完成' if success else '失败')
                    self.progress_dialog.files_table.item(row, 2).setText('100%' if success else '0%')
                    
                    # 设置颜色
                    color = QColor(76, 175, 80) if success else QColor(220, 53, 69)
                    self.progress_dialog.files_table.item(row, 1).setBackground(color)
                    self.progress_dialog.files_table.item(row, 2).setBackground(color)
                
                # 更新统计
                self.progress_dialog._update_statistics()
            else:
                signal_bus.log_message.emit("DEBUG", f"文件 {filename} 不在文件项目中", {})

    def _on_translation_error(self, filename, error_message):
        """翻译错误信号处理"""
        signal_bus.log_message.emit("ERROR", f"文件 {filename} 错误: {error_message}", {})

    def _on_batch_translated(self, success_count, total_count):
        """批次翻译完成信号处理"""
        if total_count > 0:
            success_rate = (success_count / total_count) * 100
            signal_bus.log_message.emit("INFO", f"📦 批次完成: {success_count}/{total_count} ({success_rate:.1f}%)", {})

    def stop_current_operation(self):
        """停止当前操作"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.translation_executor.stop()
            self.worker_thread.quit()
            self.worker_thread.wait(2000)
            signal_bus.log_message.emit("INFO", "正在停止操作...", {})
            
            # 停止后立即清理进度对话框
            if self.progress_dialog:
                self._cleanup_progress_dialog()

    # ==================== 各种操作的槽函数 ====================

    def run_quality_check(self, params):
        """运行质量检查"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                CustomMessageBox.warning(self, "提示", "请先打开项目")
                return

            en_folder = self.project_manager.get_folder_path('en')
            zh_folder = self.project_manager.get_folder_path('output')

            if not os.path.exists(en_folder) or not os.path.exists(zh_folder):
                signal_bus.log_message.emit("ERROR", "EN或Output文件夹不存在", {})
                return

            # 更新UI状态
            self.quality_tab.quality_stats_label.setText("正在运行质量检查...")
            self.quality_tab.quality_issues_table.setRowCount(0)
            QApplication.processEvents()

            signal_bus.log_message.emit("INFO", "开始质量检查...", {})

            # 运行检查
            from core.quality_checker import QualityChecker
            checker = QualityChecker()
            quality_results = checker.run_quality_check(en_folder, zh_folder)

            # 检查是否成功
            if not quality_results.get('成功', False):
                error_msg = quality_results.get('消息', '质量检查失败')
                self.quality_tab.quality_stats_label.setText(f"检查失败: {error_msg}")
                signal_bus.log_message.emit("ERROR", f"质量检查失败：{error_msg}", {})
                return

            # 分析结果
            analyzed_result = checker.analyze_quality_results(quality_results)

            # 显示结果
            stats = analyzed_result.get('统计', {})
            issues_to_fix = analyzed_result.get('待修复问题', [])

            # 更新统计标签
            stats_text = (
                f"总问题数: {stats.get('总问题数', 0)} | "
                f"中英混杂: {stats.get('中英文夹杂数', 0)} | "
                f"未翻译: {stats.get('未翻译数', 0)} | "
                f"变量问题: {stats.get('变量不匹配数', 0)}"
            )
            self.quality_tab.quality_stats_label.setText(stats_text)

            # 更新问题表格
            if issues_to_fix:
                self.quality_tab.update_quality_issues_table(issues_to_fix)
            else:
                self.quality_tab.quality_issues_table.setRowCount(0)

            signal_bus.log_message.emit("SUCCESS",
                                        f"质量检查完成！发现 {stats.get('总问题数', 0)} 个问题",
                                        {})

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"启动质量检查失败: {str(e)}", {})

    def retranslate_quality_issues(self, params):
        """重新翻译质量问题 - 显示进度对话框"""
        self.run_worker_in_thread("quality_review", params, "质量矫正翻译")

    def apply_quality_fixes(self, params):
        """应用质量修复"""
        try:
            issues = params.get('问题列表', [])
            fixes = params.get('fixes', {})
            output_folder = params.get('输出文件夹', '')

            signal_bus.log_message.emit("DEBUG", f"问题数量: {len(issues)}, 修复数量: {len(fixes)}", {})
            
            if not fixes:
                signal_bus.log_message.emit("WARNING", "没有可应用的修复", {})
                return

            applied_count = 0
            modified_files = set()

            signal_bus.log_message.emit("INFO", f"开始应用 {len(fixes)} 个修复", {})

            # 遍历所有修复，应用到对应的文件
            for key, fix_data in fixes.items():
                new_translation = fix_data.get('新翻译', '')
                source_file = fix_data.get('原始文件', '')  # 使用中文字段名
                
                signal_bus.log_message.emit("INFO", f"处理修复: key={key}, new_translation={new_translation}, source_file={source_file}", {})
                
                if not new_translation or not source_file:
                    signal_bus.log_message.emit("WARNING", f"跳过修复: 缺少新翻译或原始文件", {})
                    continue
                
                # 构建输出文件路径
                if os.path.exists(output_folder):
                    # 建立文件名映射关系
                    filename = os.path.basename(source_file)
                    if filename == 'default.json':
                        output_file = os.path.join(output_folder, 'zh.json')
                    else:
                        output_file = os.path.join(output_folder, filename)
                    
                    signal_bus.log_message.emit("INFO", f"输出文件路径: {output_file}", {})
                    
                    # 读取输出文件
                    if os.path.exists(output_file):
                        signal_bus.log_message.emit("INFO", f"读取文件: {output_file}", {})
                        data = file_tool.read_json_file(output_file)
                        
                        signal_bus.log_message.emit("INFO", f"文件类型: {type(data)}, 是否包含键 '{key}': {key in data if isinstance(data, dict) else 'N/A'}", {})
                        
                        if isinstance(data, dict) and key in data:
                            # 应用修复
                            old_value = data[key]
                            data[key] = new_translation
                            
                            signal_bus.log_message.emit("INFO", f"应用修复: {key}: {old_value} -> {new_translation}", {})
                            
                            # 保存文件
                            # 保存文件，保留注释（使用output文件本身作为original_path）
                            file_tool.save_json_file(data, output_file, original_path=output_file)
                            
                            # 收集需要保存到缓存的翻译对
                            cache_updates = {}
                            if new_translation and old_value != new_translation:
                                # 先尝试用新值更新缓存（可能已有缓存）
                                cache_updates[old_value] = new_translation
                                signal_bus.log_message.emit("DEBUG", f"准备保存到缓存: {old_value[:30]}... -> {new_translation[:30]}...", {})
                                
                                # 获取对应的 fix_data 来获取原文
                                fix_data = fixes.get(key, {})
                                original_value = fix_data.get('中文', '') or fix_data.get('英文', '')
                                if original_value and original_value != old_value:
                                    cache_updates[original_value] = new_translation
                                    signal_bus.log_message.emit("DEBUG", f"准备保存原文到缓存: {original_value[:30]}... -> {new_translation[:30]}...", {})
                            
                            modified_files.add(output_file)
                            applied_count += 1
                            
                            signal_bus.log_message.emit("INFO", 
                                f"修复应用成功: {key} = {new_translation} (文件: {os.path.basename(output_file)})", {})
                        else:
                            signal_bus.log_message.emit("WARNING", f"键 '{key}' 不存在于文件中或文件不是字典格式", {})
                    else:
                        signal_bus.log_message.emit("ERROR", f"输出文件不存在: {output_file}", {})

            # 批量保存缓存更新
            if hasattr(self, 'project_manager') and self.project_manager and hasattr(self.project_manager, 'cache_manager') and self.project_manager.cache_manager:
                # 收集所有缓存更新
                all_cache_updates = {}
                
                # 重新遍历修复以收集缓存更新
                for key, fix_data in fixes.items():
                    new_translation = fix_data.get('新翻译', '')
                    source_file = fix_data.get('原始文件', '')
                    
                    if not new_translation or not source_file:
                        continue
                    
                    # 构建输出文件路径
                    if os.path.exists(output_folder):
                        filename = os.path.basename(source_file)
                        if filename == 'default.json':
                            output_file = os.path.join(output_folder, 'zh.json')
                        else:
                            output_file = os.path.join(output_folder, filename)
                        
                        # 读取输出文件获取原值
                        if os.path.exists(output_file):
                            data = file_tool.read_json_file(output_file)
                            if isinstance(data, dict) and key in data:
                                old_value = data[key]
                                if new_translation and old_value != new_translation:
                                    all_cache_updates[old_value] = new_translation
                                    
                                    # 获取对应的 fix_data 来获取原文
                                    fix_data = fixes.get(key, {})
                                    original_value = fix_data.get('中文', '') or fix_data.get('英文', '')
                                    if original_value and original_value != old_value:
                                        all_cache_updates[original_value] = new_translation
                
                # 批量更新缓存
                if all_cache_updates:
                    original_texts = list(all_cache_updates.keys())
                    translated_texts = list(all_cache_updates.values())
                    self.project_manager.cache_manager.batch_set_cached(original_texts, translated_texts)
                    signal_bus.log_message.emit("INFO", f"💾 批量保存 {len(all_cache_updates)} 个翻译到缓存", {})
            
            signal_bus.log_message.emit("SUCCESS", f"💾 已成功应用 {applied_count} 个修复，修改了 {len(modified_files)} 个文件", {})
            
            # 询问是否打开输出文件夹
            if applied_count > 0 and output_folder and os.path.exists(output_folder):
                self._ask_open_output_folder(output_folder)

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"应用修复失败: {str(e)}", {})
            import traceback
            traceback.print_exc()

    def translate_manifests(self, params):
        """翻译Manifest文件"""
        signal_bus.log_message.emit("DEBUG", f"收到清单翻译请求: {type(params)} = {params}", {})

        # 确保参数是字典格式
        if isinstance(params, dict):
            self.run_worker_in_thread("manifest", params, "Manifest翻译")
        else:
            # 如果参数不是字典，包装成字典
            wrapped_params = {
                '文件夹路径': params if isinstance(params, list) else [],
                '项目路径': self.project_manager.current_project.path if self.project_manager.current_project else ''
            }
            signal_bus.log_message.emit("DEBUG", f"包装后的参数: {wrapped_params}", {})
            self.run_worker_in_thread("manifest", wrapped_params, "Manifest翻译")

    def incremental_translate_manifests(self, params):
        """增量翻译Manifest文件"""
        signal_bus.log_message.emit("DEBUG", f"收到Manifest增量翻译请求: {params}", {})
        self.run_worker_in_thread("manifest_incremental", params, "Manifest增量翻译")
    def translate_config_menu(self, params):
        """翻译配置菜单"""
        self.run_worker_in_thread("config_menu", params, "配置菜单翻译")

    def start_smart_translation(self, params):
        """开始智能翻译"""
        self.run_worker_in_thread("smart_translation", params, "智能翻译")

    # ==================== 任务完成处理函数 ====================

    def _ask_open_output_folder(self, output_folder):
        """询问是否打开输出文件夹"""
        # 强制刷新UI，确保所有状态都已更新
        QApplication.processEvents()

        # 如果进度对话框存在，强制更新它
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.force_refresh()
            QApplication.processEvents()

        reply = CustomMessageBox.question(
            self, "翻译完成",  f"翻译完成！已保存到:\n{output_folder}\n\n是否打开输出文件夹？"
        )

        if reply == CustomMessageBox.Yes:
            file_tool.open_folder(output_folder)

    def on_smart_translation_complete(self, result):
        """智能翻译完成处理"""
        success = result.get('成功', False)

        if success:
            success_files = result.get('成功文件', 0)
            total_files = result.get('总文件数', 0)
            output_folder = result.get('输出文件夹', '')

            signal_bus.log_message.emit("SUCCESS",
                                        f"智能翻译完成！成功 {success_files}/{total_files} 个文件", {})

            if output_folder and os.path.exists(output_folder):
                signal_bus.log_message.emit("INFO", f"📁 输出位置: {output_folder}", {})

                # 延迟询问是否打开输出文件夹，确保所有状态更新完成
                QTimer.singleShot(2000, lambda: self._ask_open_output_folder(output_folder))
        else:
            error_msg = result.get('消息', '未知错误')
            signal_bus.log_message.emit("ERROR", f"智能翻译失败: {error_msg}", {})

    def on_quality_review_complete(self, result):
        """质量矫正翻译完成"""
        success = result.get('成功', False)

        # 重新启用按钮
        if hasattr(self.quality_tab, 'retranslate_issues_btn'):
            self.quality_tab.retranslate_issues_btn.setEnabled(True)
            self.quality_tab.retranslate_issues_btn.setText("🤖 AI重新翻译问题项")

        if success:
            translated_issues = result.get('翻译问题列表', [])
            total_issues = result.get('总问题数', 0)

            # 更新质量检查标签页
            self._update_quality_tab_with_translations(translated_issues)

            signal_bus.log_message.emit("SUCCESS",
                                        f"质量矫正完成！处理了 {len(translated_issues)}/{total_issues} 个问题", {})
        else:
            error_msg = result.get('消息', '未知错误')
            signal_bus.log_message.emit("ERROR", f"质量矫正失败: {error_msg}", {})

    def _update_quality_tab_with_translations(self, translated_issues):
        """用翻译结果更新质量检查标签页"""
        for issue in translated_issues:
            key = issue.get('键', '')
            new_translation = issue.get('新翻译', '')

            if key and new_translation:
                # 更新quality_fixes
                for fix_key, fix_data in self.quality_tab.quality_fixes.items():
                    if fix_data.get('键') == key:
                        fix_data['新翻译'] = new_translation
                        break

        # 刷新表格显示
        issues_list = list(self.quality_tab.quality_fixes.values())
        self.quality_tab.update_quality_issues_table(issues_list)

    def on_config_translation_complete(self, result):
        """配置菜单翻译完成"""
        success = result.get('成功', False)

        if success:
            output_folder = result.get('输出文件夹', '')
            translated_count = result.get('翻译数', 0)

            signal_bus.log_message.emit("SUCCESS",
                                        f"配置菜单翻译完成！处理了 {translated_count} 个配置项", {})

            if output_folder and os.path.exists(output_folder):
                signal_bus.log_message.emit("INFO", f"📁 输出位置: {output_folder}", {})
                
                # 延迟询问是否打开输出文件夹，确保所有状态更新完成
                QTimer.singleShot(2000, lambda: self._ask_open_output_folder(output_folder))
        else:
            error_msg = result.get('消息', '未知错误')
            signal_bus.log_message.emit("ERROR", f"配置菜单翻译失败: {error_msg}", {})

    def on_manifest_translation_complete(self, result):
        """Manifest翻译完成"""
        success = result.get('成功', False)

        if success:
            output_folder = result.get('输出文件夹', '')
            translated_count = result.get('翻译数', 0)

            signal_bus.log_message.emit("SUCCESS",
                                        f"Manifest翻译完成！处理了 {translated_count} 个项目", {})

            if output_folder and os.path.exists(output_folder):
                signal_bus.log_message.emit("INFO", f"📁 输出文件夹: {output_folder}", {})

                # 询问是否打开输出文件夹
                self._ask_open_output_folder(output_folder)
        else:
            error_msg = result.get('消息', '未知错误')
            signal_bus.log_message.emit("ERROR", f"Manifest翻译失败: {error_msg}", {})

        # 关闭进度对话框
        if self.progress_dialog:
            self.progress_dialog.operation_completed(success)


    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止翻译执行器
            if self.translation_executor:
                self.translation_executor.stop()

            # 停止工作线程
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(2000)

            # 程序退出时才真正清理进度对话框
            if self.progress_dialog:
                self._cleanup_progress_dialog()

        except Exception:
            pass

        event.accept()