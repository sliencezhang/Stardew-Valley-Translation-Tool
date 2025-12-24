# ui/custom_message_box.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PySide6.QtCore import Qt

from core.config import config
from ui.styles import get_dialog_style
from ui.widgets import BackgroundWidget, load_background_image


class CustomMessageBox(QDialog):
    """自定义消息框 - 带自定义标题栏"""
    
    # 返回值常量
    Yes = 1
    No = 0
    Ok = 1
    Cancel = 0
    
    def __init__(self, parent=None, title="提示", message="", icon="ℹ️", buttons=("确定",)):
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # 设置无边框窗口和透明背景以实现圆角
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(get_dialog_style(config.theme))
        
        # 加载背景图片
        self.background_pixmap = load_background_image(config.theme)
        
        self.result_value = 0
        self.init_ui(title, message, icon, buttons)
    
    def init_ui(self, title, message, icon, buttons):
        """初始化UI"""
        # 创建主布局（透明）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建带背景图片的容器
        self.container_widget = BackgroundWidget(self.background_pixmap, config.theme)
        self.container_widget.setObjectName("dialogContainer")
        container_layout = QVBoxLayout(self.container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        main_layout.addWidget(self.container_widget)
        
        # 添加自定义标题栏
        from ui.custom_title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(self)
        container_layout.addWidget(self.title_bar)
        
        # 内容区域
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        container_layout.addWidget(content_widget)
        
        # 消息内容
        message_layout = QHBoxLayout()
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px;")
        message_layout.addWidget(icon_label)
        
        # 消息文本
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 13px;")
        message_layout.addWidget(message_label, 1)
        
        layout.addLayout(message_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        for i, btn_text in enumerate(buttons):
            btn = QPushButton(btn_text)
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda checked, idx=i: self.button_clicked(idx))
            button_layout.addWidget(btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def button_clicked(self, index):
        """按钮点击"""
        self.result_value = index
        
        # 获取内容按钮（排除标题栏按钮）
        all_buttons = self.findChildren(QPushButton)
        content_buttons = [btn for btn in all_buttons if btn.parent() == self.container_widget]
        
        # 对于"是/否"对话框，第一个按钮（是）返回accept，第二个按钮（否）返回reject
        if len(content_buttons) == 2:
            if index == 0:  # "是"按钮
                self.accept()
            else:  # "否"按钮
                self.reject()
        else:
            # 其他情况，默认都accept
            self.accept()
    
    @staticmethod
    def information(parent, title, message):
        """信息提示"""
        dialog = CustomMessageBox(parent, title, message, "ℹ️", ("确定",))
        dialog.exec()
        return CustomMessageBox.Ok
    
    @staticmethod
    def warning(parent, title, message):
        """警告提示"""
        dialog = CustomMessageBox(parent, title, message, "⚠️", ("确定",))
        dialog.exec()
        return CustomMessageBox.Ok
    
    @staticmethod
    def critical(parent, title, message):
        """错误提示"""
        dialog = CustomMessageBox(parent, title, message, "❌", ("确定",))
        dialog.exec()
        return CustomMessageBox.Ok
    
    @staticmethod
    def question(parent, title, message, buttons=None):
        """询问对话框"""
        if buttons is None:
            buttons = ("是", "否")
        dialog = CustomMessageBox(parent, title, message, "❓", buttons)
        result = dialog.exec()
        # 返回正确的Yes/No值：点击"是"（索引0）返回Yes(1)，点击"否"（索引1）返回No(0)
        return CustomMessageBox.Yes if dialog.result_value == 0 else CustomMessageBox.No
