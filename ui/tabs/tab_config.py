# ui/tabs/config_tab.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                               QLabel, QGroupBox)

from core.config import config
from core.signal_bus import signal_bus
from ui.styles import get_start_button_style, get_background_gray_style, get_settings_desc_style
from ui.widgets import DragDropWidget


class TabConfig(QWidget):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = None
        self.mod_folders = []  # 存储拖放的mod文件夹路径
        self.init_ui()

    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager

    def init_ui(self):
        layout = QVBoxLayout()

        # 添加使用说明
        help_text = QLabel(
            "使用说明：\n"
            "1. 拖放包含 content.json 的 mod 文件夹（可多选）\n"
            "2. 点击开始翻译配置菜单按钮\n"
            "3. 翻译结果保存路径 output/[mod文件夹名]_zh.json\n"
            "4. 手动将结果中的键值对粘贴到 i18n 中的 zh.json 中，注意补填逗号\n"
            "5. 现今大部分 mod 都已经将 config.xx.name 放到 i18n 中了，粘贴时注意不要重复"
        )
        help_text.setStyleSheet(get_settings_desc_style(config.theme))
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # 步骤1: 拖放mod文件夹
        step1_group = QGroupBox("步骤1: 拖放包含 content.json 的 mod 文件夹")
        step1_layout = QVBoxLayout(step1_group)
        self.config_mod_widget = DragDropWidget(
            "拖放包含 content.json 的 mod 文件夹到这里（可多选）",
            accept_folders=True,
            accept_files=False,
            multi_select=True
        )
        # 设置 sender_id 以区分拖放源
        self.config_mod_widget.sender_id = 'config_mod'
        signal_bus.foldersDropped.connect(self.on_mod_folders_dropped)
        step1_layout.addWidget(self.config_mod_widget)
        
        # 显示已选择的文件夹
        self.selected_folders_label = QLabel("已选择: 0 个mod文件夹")
        self.selected_folders_label.setStyleSheet(get_background_gray_style(config.theme))
        step1_layout.addWidget(self.selected_folders_label)
        
        layout.addWidget(step1_group)

        # 步骤2: 开始翻译
        step2_group = QGroupBox("步骤2: 开始翻译")
        step2_layout = QVBoxLayout(step2_group)

        self.config_translate_btn = QPushButton("🤖 开始翻译配置菜单")
        self.config_translate_btn.clicked.connect(self.start_config_translation)
        self.config_translate_btn.setStyleSheet(get_start_button_style(config.theme))
        step2_layout.addWidget(self.config_translate_btn)

        layout.addWidget(step2_group)

        layout.addStretch()
        self.setLayout(layout)

    def on_mod_folders_dropped(self, paths, sender_id=None):
        """处理mod文件夹拖放"""
        if sender_id != 'config_mod':
            return
            
        if paths:
            self.mod_folders = paths
            self.selected_folders_label.setText(f"已选择: {len(paths)} 个mod文件夹")
            
            # 显示前几个文件夹路径
            preview_text = "已选择的mod文件夹:\n"
            for i, path in enumerate(paths[:3]):  # 显示前3个
                folder_name = os.path.basename(path)
                preview_text += f"  {i + 1}. {folder_name}\n"
            if len(paths) > 3:
                preview_text += f"  ... 还有 {len(paths) - 3} 个文件夹"

            self.selected_folders_label.setToolTip(preview_text)
            signal_bus.log_message.emit("INFO", f"已选择 {len(paths)} 个mod文件夹", {})

    def start_config_translation(self):
        """开始配置菜单翻译"""
        from ui.custom_message_box import CustomMessageBox
        
        # 检查1: 是否有当前项目
        if not self.project_manager or not self.project_manager.current_project:
            CustomMessageBox.warning(self, "提示", "请先打开或创建一个项目")
            return
        
        # 检查2: 是否选择了文件夹
        if not self.mod_folders:
            CustomMessageBox.warning(self, "提示", "请先拖放包含content.json的mod文件夹")
            return
        
        # 检查3: 是否配置了API密钥（本地API除外）
        if config.api_provider != "local" and not config.api_key:
            reply = CustomMessageBox.question(
                self,
                "需要配置API密钥",
                "检测到未配置API密钥，无法进行翻译。\n\n是否前往全局设置配置API密钥？"
            )
            if reply == CustomMessageBox.Yes:
                # 打开全局设置
                from ui.main_window import GlobalSettingsDialog
                dialog = GlobalSettingsDialog(self)
                dialog.set_project_manager(self.project_manager)
                dialog.exec()
            return
        
        # 所有条件满足，开始翻译
        params = {
            'mod文件夹': self.mod_folders,
            '项目路径': self.project_manager.current_project.path
        }
        signal_bus.startConfigTranslation.emit(params)
