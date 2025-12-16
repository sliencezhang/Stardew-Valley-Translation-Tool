# ui/tabs/tab_smart_translation.py
from pathlib import Path
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QGroupBox)

from core.config import config
from core.signal_bus import signal_bus
from core.file_tool import file_tool
from ui.styles import get_start_button_style
from ui.widgets import DragDropWidget


class TabSmartTranslation(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = None
        self.init_ui()

    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager
        if project_manager and project_manager.current_project:
            self.refresh_project_files()

    def refresh_project_files(self):
        """刷新项目文件显示"""
        self.refresh_en_files()
        self.refresh_zh_files()

    def init_ui(self):

        layout = QVBoxLayout()

        # 步骤1: 拖放英文文件
        step1_group = QGroupBox("步骤1: 导入英文JSON文件")
        step1_layout = QVBoxLayout(step1_group)
        self.en_files_widget = DragDropWidget(
            "拖放多个JSON文件到这里",
            accept_folders=False,
            accept_files=True,
            multi_select=True
        )
        # 设置标识
        self.en_files_widget.sender_id = 'en'
        signal_bus.filesDropped.connect(self.on_files_dropped)
        signal_bus.foldersDropped.connect(self.on_files_dropped)
        step1_layout.addWidget(self.en_files_widget)
        layout.addWidget(step1_group)

        # 步骤2: 拖放中文文件 (增量翻译)
        step2_group = QGroupBox("步骤2: 导入中文JSON文件 (增量翻译)")
        step2_layout = QVBoxLayout(step2_group)
        self.zh_files_widget = DragDropWidget(
            "拖放多个JSON文件到这里",
            accept_folders=False,
            accept_files=True,
            multi_select=True
        )
        # 设置标识
        self.zh_files_widget.sender_id = 'zh'
        signal_bus.filesDropped.connect(self.on_files_dropped)
        signal_bus.foldersDropped.connect(self.on_files_dropped)
        step2_layout.addWidget(self.zh_files_widget)
        layout.addWidget(step2_group)

        # 文件显示区域（去掉外层GroupBox，直接显示两个文件列表）
        files_display_layout = QHBoxLayout()
        # EN文件列表
        files_display_layout.addWidget(self._create_file_list("EN文件夹 (英文)", "en",
                                                self.refresh_en_files, self.open_en_folder))
        # ZH文件列表
        files_display_layout.addWidget(self._create_file_list("ZH文件夹 (中文)", "zh",
                                                self.refresh_zh_files, self.open_zh_folder))
        layout.addLayout(files_display_layout)

        # 步骤3: AI自动翻译
        layout.addWidget(self._create_translation_group())

        self.setLayout(layout)

    

    def _create_file_list(self, title: str, folder_type: str,
                          refresh_callback, open_callback):
        """创建文件列表组件"""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)

        # 列表控件
        list_widget = QListWidget()
        setattr(self, f"{folder_type}_list", list_widget)
        layout.addWidget(list_widget)

        # 按钮
        # layout.addStretch()
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(refresh_callback)
        open_btn = QPushButton("打开文件夹")
        # open_btn.setStyleSheet(get_blue_button_style())
        open_btn.clicked.connect(open_callback)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(open_btn)
        # btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_file_list(self, title: str, folder_type: str,
                          refresh_callback, open_callback):
        """创建文件列表组件"""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)

        # 列表控件
        list_widget = QListWidget()
        setattr(self, f"{folder_type}_list", list_widget)
        layout.addWidget(list_widget)

        # 按钮
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(refresh_callback)
        open_btn = QPushButton("打开文件夹")
        # open_btn.setStyleSheet(get_blue_button_style())
        open_btn.clicked.connect(open_callback)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(open_btn)
        # btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_translation_group(self):
        """创建翻译按钮区域"""
        group = QGroupBox("步骤3: AI智能翻译")
        layout = QVBoxLayout(group)

        self.auto_translate_btn = QPushButton("🤖 开始AI智能翻译")
        self.auto_translate_btn.clicked.connect(self.start_smart_translation)
        self.auto_translate_btn.setStyleSheet(get_start_button_style(config.theme))
        # 按钮始终启用
        layout.addWidget(self.auto_translate_btn)

        return group

    def on_files_dropped(self, paths, sender_id):
        """处理文件拖放，根据来源标识决定处理方式"""
        if sender_id == 'en':
            self._import_files(paths, 'en', "英文")
        elif sender_id == 'zh':
            self._import_files(paths, 'zh', "中文")

    def _import_files(self, paths, folder_type: str, display_name: str):
        """通用文件导入方法"""
        if not (self.project_manager and self.project_manager.current_project):
            signal_bus.log_message.emit("ERROR", "请先创建或打开项目", {})
            return

        target_dir = Path(self.project_manager.get_folder_path(folder_type))
        target_dir.mkdir(parents=True, exist_ok=True)

        copied_count = 0
        for source in paths:
            try:
                source_path = Path(source)
                if source_path.is_file():
                    shutil.copy2(source_path, target_dir / source_path.name)
                    copied_count += 1
            except Exception as e:
                signal_bus.log_message.emit("ERROR", f"导入文件失败: {str(e)}", {})

        if copied_count:
            signal_bus.log_message.emit("SUCCESS",
                                        f"成功导入 {copied_count} 个{display_name}文件", {})
            getattr(self, f"refresh_{folder_type}_files")()
        else:
            signal_bus.log_message.emit("ERROR", f"{display_name}文件导入失败", {})
    
    

    def refresh_en_files(self):
        """刷新en文件列表"""
        self._refresh_file_list('en', "EN文件夹 (英文)")

    def refresh_zh_files(self):
        """刷新zh文件列表"""
        self._refresh_file_list('zh', "ZH文件夹 (中文)")

    def _refresh_file_list(self, folder_type: str, title: str):
        """刷新文件列表"""
        if not self.project_manager or not self.project_manager.current_project:
            return

        list_widget = getattr(self, f"{folder_type}_list")
        list_widget.clear()

        # 直接构建路径，避免调用 get_folder_path（会发送日志）
        project_path = self.project_manager.current_project.path
        folder_path = Path(project_path) / folder_type

        if folder_path.exists():
            for json_file in folder_path.iterdir():
                if json_file.is_file() and json_file.suffix == '.json':
                    rel_path = json_file.relative_to(folder_path)
                    list_widget.addItem(str(rel_path))

    def open_en_folder(self):
        """打开en文件夹"""
        self._open_folder('en')

    def open_zh_folder(self):
        """打开zh文件夹"""
        self._open_folder('zh')

    def _open_folder(self, folder_type: str):
        """打开文件夹"""
        if self.project_manager and self.project_manager.current_project:
            folder_path = self.project_manager.get_folder_path(folder_type)
            file_tool.open_folder(folder_path)

    def start_smart_translation(self):
        """开始智能翻译"""
        from ui.custom_message_box import CustomMessageBox
        
        # 检查1: 是否配置了API密钥（本地API除外）
        if config.api_provider != "local" and not config.api_key:
            reply = CustomMessageBox.question(
                self,
                "需要配置API密钥",
                "检测到未配置API密钥，无法进行AI翻译。\n\n是否前往全局设置配置API密钥？"
            )
            if reply == CustomMessageBox.Yes:
                # 打开全局设置
                from ui.main_window import GlobalSettingsDialog
                dialog = GlobalSettingsDialog(self)
                dialog.set_project_manager(self.project_manager)
                dialog.exec()
            return
        
        # 检查2: 是否有项目
        if not self.project_manager or not self.project_manager.current_project:
            CustomMessageBox.warning(
                self,
                "需要项目",
                "请先创建或打开一个项目才能进行翻译。"
            )
            return

        en_folder = self.project_manager.get_folder_path('en')
        output_folder = self.project_manager.get_folder_path('output')

        params = {
            '原始文件夹': en_folder,
            '输出文件夹': output_folder,
            '项目路径': self.project_manager.current_project.path
        }

        signal_bus.startSmartTranslation.emit(params)

    