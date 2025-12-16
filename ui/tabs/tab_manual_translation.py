# ui/tabs/manual_translation_tab.py
import os
import re

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QGroupBox, QComboBox,
                               QTextEdit, QFrame, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QColor, QTextCharFormat

from core.config import config
from core.variable_protector import VariableProtector
from core.file_tool import file_tool
from core.highlight_util import VariableHighlighter
from core.signal_bus import signal_bus
from ui.custom_message_box import CustomMessageBox
from ui.styles import (get_save_button_style, get_font_gray_style, get_manual_english_style, get_background_gray_style,
    get_manual_basic_style, get_manual_chinese_style, get_manual_new_chinese_style, get_scroll_area_style,
    get_widget_background_style)


class ManualTranslationTab(QWidget):
    """人工翻译Tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = None
        self.current_file = None
        self.current_data = {}  # 当前文件的所有数据
        self.displayed_items = []  # 当前显示的项目
        self.translations = {}  # 用户输入的翻译 {key: translation}
        self.current_page = 0
        self.page_size = 5  # 每页显示5行
        self.variable_protector = VariableProtector()
        
        self.init_ui()
        self.init_highlighter()

    def init_ui(self):
        """初始化UI - 分页导航和操作按钮在同一行"""
        layout = QVBoxLayout()

        # 设置整体边距和间距
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 第一行：文件选择区域
        file_group = QGroupBox("文件选择")
        file_group.setMaximumHeight(100)
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(5)

        # 文件操作按钮 - 紧凑布局（一行）
        file_btn_layout = QHBoxLayout()
        file_btn_layout.setSpacing(5)

        self.refresh_files_btn = QPushButton("🔄 刷新")
        self.refresh_files_btn.clicked.connect(self.refresh_file_list)
        # self.refresh_files_btn.setStyleSheet(get_blue_button_style())
        self.refresh_files_btn.setMaximumWidth(60)

        self.select_file_combo = QComboBox()
        self.select_file_combo.setMinimumWidth(300)
        self.select_file_combo.setMaximumWidth(500)
        self.select_file_combo.currentTextChanged.connect(self.on_file_selected)

        self.load_file_btn = QPushButton("📂 加载")
        self.load_file_btn.clicked.connect(self.load_selected_file)
        # self.load_file_btn.setStyleSheet(get_blue_button_style())
        self.load_file_btn.setMaximumWidth(70)

        self.file_info_label = QLabel("未选择文件")
        self.file_info_label.setStyleSheet(get_background_gray_style(config.theme))
        self.file_info_label.setWordWrap(False)
        self.file_info_label.setMinimumHeight(30)
        self.file_info_label.setMaximumHeight(30)
        self.file_info_label.setMaximumWidth(400)

        file_label = QLabel("文件:")
        file_label.setFixedWidth(40)
        file_btn_layout.addWidget(file_label)
        file_btn_layout.addWidget(self.select_file_combo)
        file_btn_layout.addWidget(self.refresh_files_btn)
        file_btn_layout.addWidget(self.load_file_btn)
        file_btn_layout.addWidget(self.file_info_label, 1)

        file_layout.addLayout(file_btn_layout)

        layout.addWidget(file_group)

        # 第二行：翻译区域
        translation_group = QGroupBox("人工翻译")
        translation_layout = QVBoxLayout(translation_group)
        translation_layout.setSpacing(5)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(500)  # 增大高度
        scroll_area.setStyleSheet(get_scroll_area_style(config.theme))

        self.translation_widget = QWidget()
        self.translation_widget.setStyleSheet(get_widget_background_style(config.theme))
            
        self.translation_layout = QVBoxLayout(self.translation_widget)
        self.translation_layout.setSpacing(15)
        self.translation_layout.setContentsMargins(5, 5, 5, 5)

        scroll_area.setWidget(self.translation_widget)
        translation_layout.addWidget(scroll_area, 1)

        layout.addWidget(translation_group, 1)

        # 第三行：操作区域（包含分页导航和操作按钮）
        action_group = QGroupBox("操作")
        action_group.setMaximumHeight(70)
        action_layout = QHBoxLayout(action_group)
        action_layout.setSpacing(10)

        # 左侧不使用按钮，直接使用搜索框

        # 中间：分页导航（居中）
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.prev_page_btn = QPushButton("◀ 上一页")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.prev_page_btn.setEnabled(False)

        self.page_info_label = QLabel("第 0/0 页")

        # 跳转页输入框
        self.page_spin = QComboBox()
        self.page_spin.setEditable(True)
        self.page_spin.setMaximumWidth(80)
        self.page_spin.currentTextChanged.connect(self.jump_to_page)
        
        # 搜索框
        self.search_input = QTextEdit()
        self.search_input.setMaximumHeight(28)
        self.search_input.setMaximumWidth(200)
        self.search_input.setPlaceholderText("搜索键名或英文原文...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        
        # 添加事件过滤器，支持回车键搜索
        self.search_input.installEventFilter(self)

        self.progress_label = QLabel("进度: 0/0 (0%)")
        self.progress_label.setStyleSheet(get_font_gray_style(config.theme))

        self.next_page_btn = QPushButton("下一页 ▶")
        self.next_page_btn.clicked.connect(self.next_page)
        self.next_page_btn.setEnabled(False)

        nav_layout.addWidget(self.prev_page_btn)
        nav_layout.addWidget(self.page_info_label)
        nav_layout.addWidget(self.page_spin)
        nav_layout.addWidget(QLabel("搜索:"))
        nav_layout.addWidget(self.search_input)
        nav_layout.addWidget(self.progress_label)
        nav_layout.addWidget(self.next_page_btn)

        # 右侧：保存按钮
        self.save_btn = QPushButton("💾 保存翻译")
        self.save_btn.clicked.connect(self.save_translations)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(get_save_button_style(config.theme))
        self.save_btn.setMinimumWidth(120)

        # 将两个部分添加到操作布局
        action_layout.addStretch()  # 左侧弹簧
        action_layout.addLayout(nav_layout)  # 添加导航布局
        action_layout.addStretch()  # 右侧弹簧
        action_layout.addWidget(self.save_btn)

        layout.addWidget(action_group)

        self.setLayout(layout)

    def init_highlighter(self):
        """初始化高亮器格式"""
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor(255, 255, 130))  # 淡黄色
        self.highlight_format.setFontWeight(600)

    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager
        if project_manager and project_manager.current_project:
            self.refresh_file_list()

    def refresh_file_list(self):
        """刷新文件列表"""
        if not self.project_manager or not self.project_manager.current_project:
            CustomMessageBox.warning(self, "提示", "请先打开项目")
            return
        
        en_folder = self.project_manager.get_folder_path('en')
        if not os.path.exists(en_folder):
            CustomMessageBox.warning(self, "提示", "en文件夹不存在")
            return
        
        # 获取所有JSON文件
        files = file_tool.get_all_json_files(en_folder)
        file_names = [os.path.relpath(f, en_folder) for f in files]
        
        # 更新下拉框
        self.select_file_combo.clear()
        if file_names:
            self.select_file_combo.addItems(sorted(file_names))
            self.file_info_label.setText(f"找到 {len(file_names)} 个文件")
        else:
            self.file_info_label.setText("未找到JSON文件")
            
    def on_file_selected(self, file_name):
        """文件选择变化"""
        if file_name:
            self.load_file_btn.setEnabled(True)
        else:
            self.load_file_btn.setEnabled(False)

    def load_selected_file(self):
        """加载选中的文件"""
        file_name = self.select_file_combo.currentText()
        if not file_name:
            CustomMessageBox.warning(self, "提示", "请选择文件")
            return

        en_folder = self.project_manager.get_folder_path('en')
        zh_folder = self.project_manager.get_folder_path('output')

        en_file_path = os.path.join(en_folder, file_name)

        # 检查文件是否存在
        if not os.path.exists(en_file_path):
            CustomMessageBox.critical(self, "错误", f"文件不存在: {en_file_path}")
            return

        try:
            # 读取英文文件
            self.current_data = file_tool.read_json_file(en_file_path)
            if not isinstance(self.current_data, dict):
                CustomMessageBox.critical(self, "错误", f"文件格式错误：不是有效的JSON对象")
                return

            # 检查中文文件是否存在
            # 处理 default.json -> zh.json 的映射
            if file_name.lower() == 'default.json':
                zh_file_path = os.path.join(zh_folder, 'zh.json')
            else:
                zh_file_path = os.path.join(zh_folder, file_name)
                
            existing_translations = {}
            if os.path.exists(zh_file_path):
                try:
                    existing_data = file_tool.read_json_file(zh_file_path)
                    if isinstance(existing_data, dict):
                        existing_translations = existing_data
                except Exception:
                    pass

            # 重置状态
            self.current_file = file_name
            self.translations = existing_translations.copy()
            self.current_page = 0

            # 准备显示的项目
            self.displayed_items = []
            for key, value in self.current_data.items():
                if isinstance(value, str) and value.strip():
                    self.displayed_items.append({
                        '键': key,
                        '英文': value,
                        '中文': existing_translations.get(key, ''),
                        '新翻译': existing_translations.get(key, '')
                    })

            # 更新文件信息 - 更简洁
            total_items = len(self.displayed_items)
            translated_count = sum(1 for item in self.displayed_items if item['新翻译'])
            self.file_info_label.setText(
                f"{file_name} | 总数: {total_items} | 已翻译: {translated_count} | 未翻译: {total_items - translated_count}"
            )

            # 加载第一页
            QTimer.singleShot(100, self.load_page)  # 延迟加载，避免界面卡顿

            # 更新按钮状态
            self.save_btn.setEnabled(True)
            
            # 清空搜索框
            self.search_input.clear()
            self.search_input.setEnabled(True)

        except Exception as e:
            error_msg = f"加载文件失败: {str(e)}"
            CustomMessageBox.critical(self, "错误", error_msg)
            
    def save_current_page_translations(self):
        """保存当前页所有翻译输入框的内容"""
        try:
            # 遍历当前页面的所有翻译输入框
            for i in range(self.translation_layout.count()):
                frame = self.translation_layout.itemAt(i).widget()
                if frame:
                    # 查找翻译输入框
                    for text_edit in frame.findChildren(QTextEdit):
                        if text_edit.property("item_key"):
                            key = text_edit.property("item_key")
                            text = text_edit.toPlainText().strip()
                            self.translations[key] = text
                            # 同时更新displayed_items中的新翻译
                            for item in self.displayed_items:
                                if item['键'] == key:
                                    item['新翻译'] = text
                                    break
        except Exception:
            pass
    
    def load_page(self):
        """加载当前页"""
        try:
            if not self.displayed_items:
                self.clear_translation_display()
                return

            # 在清除显示前，先保存当前页的翻译
            self.save_current_page_translations()

            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.displayed_items))
            
            # 清除现有显示
            self.clear_translation_display()
            
            # 添加当前页的条目
            for i in range(start_idx, end_idx):
                item = self.displayed_items[i]
                self.add_translation_item(item, i - start_idx + 1)
            
            # 更新页面信息
            self.update_page_info()
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"加载页面失败: {e}", {})

    def add_translation_item(self, item, item_num):
        """添加一个翻译项目到显示区域"""
        # 创建主框架
        frame = QFrame()
        frame.setStyleSheet(get_manual_basic_style(config.theme))
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setSpacing(8)  # 减小间距

        # 项目标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        title_layout.setContentsMargins(0, 0, 0, 0)

        # 编号
        num_label = QLabel(f"{item_num}.")
        num_label.setStyleSheet(get_font_gray_style(config.theme))

        # 键名
        key_label = QLabel(f"键: {item['键']}")
        key_label.setStyleSheet(get_font_gray_style(config.theme))

        # 变量统计
        vars_count = self.variable_protector.count_variables_in_text(item['英文'])
        vars_label = QLabel(f"变量: {vars_count}个")
        vars_label.setStyleSheet(get_font_gray_style(config.theme))

        # 字数统计（提前创建）
        char_count_label = QLabel("字数: 0")
        char_count_label.setStyleSheet(get_font_gray_style(config.theme))
        char_count_label.setProperty("item_key", item['键'])

        title_layout.addWidget(num_label)
        title_layout.addWidget(key_label, 1)  # 拉伸因子
        title_layout.addWidget(vars_label)
        title_layout.addWidget(char_count_label)

        frame_layout.addLayout(title_layout)

        # 英文原文 - 减小高度
        english_group = QGroupBox("英文原文")
        english_group.setStyleSheet(get_manual_english_style(config.theme))
        english_layout = QVBoxLayout(english_group)

        english_text = QTextEdit()
        english_text.setPlainText(item['英文'])
        english_text.setReadOnly(True)
        english_text.setMaximumHeight(70)  # 减小高度
        english_text.setMinimumHeight(50)  # 设置最小高度
        # 创建高亮器，但不立即调用 rehighlight()
        english_highlighter = VariableHighlighter(english_text.document(), config.theme)
        # 保存引用
        english_text.highlighter = english_highlighter

        # 使用单次定时器延迟高亮
        QTimer.singleShot(100, english_highlighter.rehighlight)

        english_layout.addWidget(english_text)
        frame_layout.addWidget(english_group)

        # 现有翻译（如果有） - 减小高度
        if item['中文']:
            original_group = QGroupBox("现有翻译")
            original_group.setStyleSheet(get_manual_chinese_style(config.theme))
            original_layout = QVBoxLayout(original_group)

            original_text = QTextEdit()
            original_text.setPlainText(item['中文'])
            original_text.setReadOnly(True)
            original_text.setMaximumHeight(60)  # 减小高度
            original_text.setMinimumHeight(40)  # 设置最小高度

            # 创建高亮器，但不立即调用 rehighlight()
            original_highlighter = VariableHighlighter(original_text.document(), config.theme)
            # 保存引用
            original_text.highlighter = original_highlighter

            # 使用单次定时器延迟高亮
            QTimer.singleShot(100, original_highlighter.rehighlight)

            original_layout.addWidget(original_text)
            frame_layout.addWidget(original_group)

        # 翻译输入框 - 增大高度
        input_group = QGroupBox("输入翻译")
        input_group.setStyleSheet(get_manual_new_chinese_style(config.theme))
        input_layout = QVBoxLayout(input_group)

        translation_input = QTextEdit()
        translation_input.setMinimumHeight(60)  # 增大最小高度
        translation_input.setMaximumHeight(120)  # 增大最大高度
        translation_input.setPlaceholderText("请输入翻译内容...")
        translation_input.setProperty("item_key", item['键'])  # 存储键名
        # 设置初始文本
        if item['新翻译']:
            translation_input.setPlainText(item['新翻译'])

        # 创建高亮器实例
        highlighter = VariableHighlighter(translation_input.document(), config.theme)

        # 重要：保存高亮器引用，避免被垃圾回收
        translation_input.highlighter = highlighter

        # 修复：使用lambda正确捕获变量
        def create_text_changed_handler(text_edit, hl, key):
            def handler():
                # 更新翻译
                new_text = text_edit.toPlainText().strip()
                self.translations[key] = new_text

                # 更新字符计数器
                for i in range(self.translation_layout.count()):
                    widget = self.translation_layout.itemAt(i).widget()
                    if widget:
                        # 查找字符计数标签
                        for child in widget.findChildren(QLabel):
                            if child.property("item_key") == key:
                                child.setText(f"字数: {len(new_text)}")
                                break

                # 延迟重新高亮
                hl.delayed_rehighlight() if hasattr(hl, 'delayed_rehighlight') else hl.rehighlight()

            return handler

        # 创建处理函数
        text_changed_handler = create_text_changed_handler(translation_input, highlighter, item['键'])

        # 连接信号
        translation_input.textChanged.connect(text_changed_handler)

        # 应用高亮
        self.highlight_variables(translation_input)

        # 更新字符数（使用标题行的标签）
        char_count_label.setText(f"字数: {len(translation_input.toPlainText())}")

        input_layout.addWidget(translation_input)

        frame_layout.addWidget(input_group, 1)  # 给输入框添加拉伸因子

        # 添加到主布局
        self.translation_layout.addWidget(frame)

    def highlight_variables(self, text_edit):
        """高亮文本中的变量 - 使用VariableProtector的模式"""
        text = text_edit.toPlainText()
        cursor = text_edit.textCursor()

        # 保存原始格式
        cursor.select(cursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())  # 清除格式

        # 使用VariableProtector中的模式
        variable_patterns = self.variable_protector.variable_patterns

        # 应用高亮
        for pattern in variable_patterns:
            for match in re.finditer(pattern, text):
                cursor.setPosition(match.start())
                cursor.setPosition(match.end(), cursor.MoveMode.KeepAnchor)
                cursor.mergeCharFormat(self.highlight_format)

    def clear_translation_display(self):
        """清除翻译显示区域"""
        # 先移除所有widget
        while self.translation_layout.count():
            item = self.translation_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
    
    def update_page_info(self):
        """更新页面信息"""
        if not self.displayed_items:
            self.page_info_label.setText("第 0/0 页")
            self.progress_label.setText("进度: 0/0 (0%)")
            self.prev_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
            self.page_spin.clear()
            return
        
        total_items = len(self.displayed_items)
        total_pages = (total_items - 1) // self.page_size + 1
        
        # 当前页和总页数
        self.page_info_label.setText(f"第 {self.current_page + 1}/{total_pages} 页")
        
        # 更新页码下拉框
        self.page_spin.blockSignals(True)  # 防止触发信号
        self.page_spin.clear()
        for i in range(1, total_pages + 1):
            self.page_spin.addItem(str(i))
        self.page_spin.setCurrentIndex(self.current_page)
        self.page_spin.blockSignals(False)
        
        # 进度
        translated_count = sum(1 for item in self.displayed_items if item['新翻译'])
        progress_percent = (translated_count / total_items * 100) if total_items > 0 else 0
        self.progress_label.setText(f"进度: {translated_count}/{total_items} ({progress_percent:.1f}%)")
        
        # 按钮状态
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < total_pages - 1)
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()
    
    def next_page(self):
        """下一页"""
        total_items = len(self.displayed_items)
        total_pages = (total_items - 1) // self.page_size + 1
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_page()
    
    def jump_to_page(self):
        """跳转到指定页"""
        try:
            page_text = self.page_spin.currentText()
            if not page_text:
                return
                
            page_num = int(page_text) - 1
            total_items = len(self.displayed_items)
            total_pages = (total_items - 1) // self.page_size + 1
            
            if 0 <= page_num < total_pages:
                self.current_page = page_num
                self.load_page()
        except ValueError:
            pass
    
    def on_search_text_changed(self):
        """搜索文本改变时的处理"""
        search_text = self.search_input.toPlainText().strip()
        # 当搜索文本清空时，恢复显示所有项目
        if not search_text and self.current_file:
            # 直接重新加载页面，避免递归
            self.current_page = 0
            self.load_page()
    
    def search_first_match(self):
        """搜索第一个匹配项"""
        search_text = self.search_input.toPlainText().strip()
        if not search_text or not self.displayed_items:
            return
        
        # 从开头开始搜索
        for i, item in enumerate(self.displayed_items):
            # 搜索键和原文
            if search_text.lower() in item['键'].lower() or search_text.lower() in str(item['英文']).lower():
                # 计算该项所在的页
                target_page = i // self.page_size
                if target_page != self.current_page:
                    self.current_page = target_page
                    self.load_page()
                # TODO: 实现高亮显示匹配的行功能
                return
    
    def search_next(self):
        """搜索下一个匹配项"""
        search_text = self.search_input.toPlainText().strip()
        if not search_text or not self.displayed_items:
            return
        
        # 从当前位置的下一项开始搜索
        start_idx = self.current_page * self.page_size + 1
        total_items = len(self.displayed_items)
        
        # 搜索匹配的项
        for i in range(start_idx, total_items):
            item = self.displayed_items[i]
            # 搜索键和原文
            if search_text.lower() in item['键'].lower() or search_text.lower() in str(item['英文']).lower():
                # 计算该项所在的页
                target_page = i // self.page_size
                if target_page != self.current_page:
                    self.current_page = target_page
                    self.load_page()
                # TODO: 实现高亮显示匹配的行功能
                return
        
        # 如果没找到，从开头继续搜索
        for i in range(0, start_idx):
            item = self.displayed_items[i]
            if search_text.lower() in item['键'].lower() or search_text.lower() in str(item['英文']).lower():
                target_page = i // self.page_size
                if target_page != self.current_page:
                    self.current_page = target_page
                    self.load_page()
                # TODO: 实现高亮显示匹配的行功能
                return
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理回车键搜索"""
        if obj == self.search_input and event.type() == QEvent.Type.KeyPress:
            # 类型提示：event是QKeyEvent
            from PySide6.QtGui import QKeyEvent
            if isinstance(event, QKeyEvent):
                key = event.key()
                if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                    self.search_next()
                    return True
        return super().eventFilter(obj, event)
    
    

    def save_translations(self):
        """保存翻译 - 使用 write_json_file 的 preserve_structure 参数保留注释"""
        if not self.current_file or not self.translations:
            CustomMessageBox.warning(self, "提示", "没有可保存的翻译")
            return

        try:
            # 获取输出文件夹路径
            output_folder = self.project_manager.get_folder_path('output')
            
            # 处理 default.json -> zh.json 的映射
            if self.current_file.lower() == 'default.json':
                output_file = os.path.join(output_folder, 'zh.json')
            else:
                output_file = os.path.join(output_folder, self.current_file)

            # 确保文件夹存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 只保存有内容的翻译
            valid_translations = {}
            for key, translation in self.translations.items():
                if translation and translation.strip():
                    valid_translations[key] = translation

            if not valid_translations:
                CustomMessageBox.warning(self, "提示", "没有有效的翻译内容")
                return

            # 获取英文文件路径作为模板
            en_folder = self.project_manager.get_folder_path('en')
            template_file = os.path.join(en_folder, self.current_file)

            # 检查模板文件是否存在
            if not os.path.exists(template_file):
                CustomMessageBox.warning(self, "提示", f"模板文件不存在: {template_file}")
                return

            # 读取现有的中文文件（如果存在）
            existing_data = {}
            if os.path.exists(output_file):
                existing_data = file_tool.read_json_file(output_file)
                if not isinstance(existing_data, dict):
                    existing_data = {}

            # 合并翻译
            for key, translation in valid_translations.items():
                existing_data[key] = translation
                # 同时保存到缓存
                if hasattr(self, 'project_manager') and self.project_manager and hasattr(self.project_manager, 'cache_manager') and self.project_manager.cache_manager:
                    # 从当前数据中获取英文原文
                    original_value = self.current_data.get(key, '')
                    if original_value and original_value != translation:
                        self.project_manager.cache_manager.set_cached_translation(original_value, translation)
                        signal_bus.log_message.emit("DEBUG", f"手动翻译保存到缓存: {original_value[:30]}... -> {translation[:30]}...", {})

            # 使用 file_tool.save_json_file 来保存
            file_tool.save_json_file(existing_data, output_file, template_file)

            # 更新显示项的翻译状态
            for item in self.displayed_items:
                if item['键'] in self.translations:
                    item['新翻译'] = self.translations[item['键']]

            # 重新加载当前页以更新状态
            self.load_page()

            # 更新文件信息
            total_items = len(self.displayed_items)
            translated_count = sum(1 for item in self.displayed_items if item['新翻译'])
            self.file_info_label.setText(
                f"{self.current_file} | 总数: {total_items} | 已翻译: {translated_count} | 未翻译: {total_items - translated_count}"
            )

            CustomMessageBox.information(self, "成功",
                                    f"已保存 {len(valid_translations)} 条翻译\n"
                                    f"文件: {output_file}\n")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            signal_bus.log_message.emit("ERROR", f"保存失败: {error_details}", {})
            CustomMessageBox.critical(self, "错误", f"保存翻译失败: {str(e)}")
