# ui/edit_translation_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QTextEdit, QDialogButtonBox, QFrame, QWidget)
from PySide6.QtCore import Qt

from core.config import config
from ui.styles import (get_dialog_style, get_background_yellow_style, get_font_gray_style, get_var_error_style,
    get_var_right_style, get_edit_dialog_textedit_style)
from ui.widgets import BackgroundWidget, load_background_image
from core.highlight_util import VariableHighlighter  # 使用高亮器
from core.variable_protector import VariableProtector  # 使用变量保护器

class EditTranslationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑翻译")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        # 设置无边框窗口和透明背景以实现圆角
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        from core.config import config as cfg
        self.setStyleSheet(get_dialog_style(cfg.theme))
        
        # 加载背景图片
        self.background_pixmap = load_background_image(config.theme)

        # 存储高亮器实例
        self.english_highlighter = None
        self.original_highlighter = None
        self.new_highlighter = None

        # 存储变量统计信息
        self.variable_stats = {
            '英文': 0,
            '中文': 0,
            '新翻译': 0
        }

        # 创建变量保护器实例
        self.variable_protector = VariableProtector()

        self.init_ui()

    def init_ui(self):
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
        container_layout.addWidget(content_widget)

        # 问题类型显示
        self.issue_type_label = QLabel("问题类型: -")
        self.issue_type_label.setStyleSheet(get_background_yellow_style(config.theme))
        layout.addWidget(self.issue_type_label)

        # 英文原文区域
        en_group = QFrame()
        en_layout = QVBoxLayout(en_group)

        # 英文原文标题和变量统计
        en_header = QHBoxLayout()
        en_label = QLabel("英文原文:")

        self.english_vars_label = QLabel("变量: 0个")
        self.english_vars_label.setStyleSheet(get_font_gray_style(config.theme))

        en_header.addWidget(en_label)
        en_header.addStretch()
        en_header.addWidget(self.english_vars_label)
        en_layout.addLayout(en_header)

        self.english_edit = QTextEdit()
        self.english_edit.setReadOnly(True)
        self.english_edit.setMaximumHeight(100)
        self.english_edit.setStyleSheet(get_edit_dialog_textedit_style(config.theme))
        self.english_edit.textChanged.connect(lambda: self.update_vars_count('英文'))
        en_layout.addWidget(self.english_edit)

        layout.addWidget(en_group)

        # 原中文区域
        zh_group = QFrame()
        zh_layout = QVBoxLayout(zh_group)

        # 原中文标题和变量统计
        zh_header = QHBoxLayout()
        zh_label = QLabel("原中文:")

        self.original_vars_label = QLabel("变量: 0个")
        self.original_vars_label.setStyleSheet(get_font_gray_style(config.theme))

        zh_header.addWidget(zh_label)
        zh_header.addStretch()
        zh_header.addWidget(self.original_vars_label)
        zh_layout.addLayout(zh_header)

        self.original_zh_edit = QTextEdit()
        self.original_zh_edit.setReadOnly(True)
        self.original_zh_edit.setMaximumHeight(100)
        self.original_zh_edit.setStyleSheet(get_edit_dialog_textedit_style(config.theme))
        self.original_zh_edit.textChanged.connect(lambda: self.update_vars_count('中文'))
        zh_layout.addWidget(self.original_zh_edit)

        layout.addWidget(zh_group)

        # 新翻译区域
        new_group = QFrame()
        new_layout = QVBoxLayout(new_group)

        # 新翻译标题和变量统计
        new_header = QHBoxLayout()
        new_label = QLabel("新翻译:")

        self.new_vars_label = QLabel("变量: 0个")

        new_header.addWidget(new_label)
        new_header.addStretch()
        new_header.addWidget(self.new_vars_label)
        new_layout.addLayout(new_header)

        self.new_translation_edit = QTextEdit()
        self.new_translation_edit.setMinimumHeight(100)
        self.new_translation_edit.setPlaceholderText("请输入新的翻译内容...")
        self.new_translation_edit.setStyleSheet(get_edit_dialog_textedit_style(config.theme))
        self.new_translation_edit.textChanged.connect(lambda: self.update_vars_count('新翻译'))
        new_layout.addWidget(self.new_translation_edit)

        layout.addWidget(new_group)

        # 变量保护提示
        hint_label = QLabel("💡 提示：黄色高亮部分为变量，请确保修改时确保变量与英文原文一致。")
        hint_label.setStyleSheet(get_background_yellow_style(config.theme))
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(main_layout)

    def set_data(self, english_text, original_chinese, new_translation, issue_type=""):
        """设置对话框数据并应用高亮"""
        # 设置问题类型
        self.issue_type_label.setText(f"问题类型: {issue_type}")

        # 设置文本
        self.english_edit.setPlainText(english_text)
        self.original_zh_edit.setPlainText(original_chinese)
        self.new_translation_edit.setPlainText(new_translation)

        # 立即更新变量计数
        self.update_vars_count('英文')
        self.update_vars_count('中文')
        self.update_vars_count('新翻译')

        # 创建高亮器实例,传入当前主题
        self.english_highlighter = VariableHighlighter(self.english_edit.document(), config.theme)
        self.original_highlighter = VariableHighlighter(self.original_zh_edit.document(), config.theme)
        self.new_highlighter = VariableHighlighter(self.new_translation_edit.document(), config.theme)

        # 强制重新高亮
        self.english_highlighter.rehighlight()
        self.original_highlighter.rehighlight()
        self.new_highlighter.rehighlight()

    def update_vars_count(self, var_type):
        """通用变量计数更新方法"""
        type_mapping = {
            '英文': (self.english_edit, self.english_vars_label),
            '中文': (self.original_zh_edit, self.original_vars_label),
            '新翻译': (self.new_translation_edit, self.new_vars_label)
        }

        edit_widget, label_widget = type_mapping[var_type]
        text = edit_widget.toPlainText()
        count = self.variable_protector.count_variables_in_text(text)

        self.variable_stats[var_type] = count
        label_widget.setText(f"变量: {count}个")

        # 新翻译需要与英文原文比较
        if var_type == '新翻译':
            english_count = self.variable_stats.get('英文', 0)
            style_func = get_var_error_style if count != english_count else get_var_right_style
            label_widget.setStyleSheet(style_func(config.theme))

    def get_new_translation(self):
        """获取新翻译内容"""
        return self.new_translation_edit.toPlainText().strip()