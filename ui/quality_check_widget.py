import os
from typing import List, Dict

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QGroupBox,
                               QHeaderView, QDialog, QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from core.config import config
from core.signal_bus import signal_bus
from ui.custom_message_box import CustomMessageBox
from ui.styles import (get_start_button_style, get_background_blue_style, get_new_translation_bg_color, 
                       get_table_edit_button_style, get_edited_translation_bg_color, apply_table_header_style)


class QualityCheckWidget(QWidget):
    """独立的质量检查组件 - 完全复制质量检查标签页的布局和功能"""
    check_completed = Signal(dict)  # 质量检查完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = None
        self.quality_fixes = {}
        self.en_file = None
        self.zh_file = None
        self.init_ui()
    
    def apply_theme(self):
        """应用主题"""
        # 更新按钮样式
        if hasattr(self, 'run_quality_check_btn'):
            self.run_quality_check_btn.setStyleSheet(get_start_button_style(config.theme))
        if hasattr(self, 'retranslate_issues_btn'):
            self.retranslate_issues_btn.setStyleSheet(get_start_button_style(config.theme))
        if hasattr(self, 'apply_fixes_btn'):
            self.apply_fixes_btn.setStyleSheet(get_start_button_style(config.theme))
        if hasattr(self, 'select_all_btn'):
            self.select_all_btn.setStyleSheet(get_start_button_style(config.theme))
        if hasattr(self, 'deselect_all_btn'):
            self.deselect_all_btn.setStyleSheet(get_start_button_style(config.theme))
        
        # 更新标签样式
        if hasattr(self, 'quality_stats_label'):
            self.quality_stats_label.setStyleSheet(get_background_blue_style(config.theme))
        
        # 更新表格主题
        if hasattr(self, 'quality_issues_table'):
            self.update_table_theme()

    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager

    def set_files_for_check(self, en_file, zh_file):
        """设置要检查的文件"""
        # 保存文件路径
        self.en_file = en_file
        self.zh_file = zh_file
        # 直接运行质量检查
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.run_quality_check)

    def init_ui(self):
        layout = QVBoxLayout()

        # 质量检查按钮
        quality_check_group = QGroupBox("步骤1: 质量检查")
        quality_check_layout = QVBoxLayout(quality_check_group)

        self.run_quality_check_btn = QPushButton("🔍 运行质量检查")
        self.run_quality_check_btn.clicked.connect(self.run_quality_check)
        self.run_quality_check_btn.setStyleSheet(get_start_button_style(config.theme))
        quality_check_layout.addWidget(self.run_quality_check_btn)

        layout.addWidget(quality_check_group)

        # 质量检查结果处理
        quality_result_group = QGroupBox("步骤2: 质量检查结果处理")
        quality_result_layout = QVBoxLayout(quality_result_group)

        # 处理按钮
        process_btn_layout = QHBoxLayout()
        self.retranslate_issues_btn = QPushButton("🤖 AI重新翻译问题项")
        self.retranslate_issues_btn.clicked.connect(self.retranslate_quality_issues)
        self.retranslate_issues_btn.setStyleSheet(get_start_button_style(config.theme))
        
        self.apply_fixes_btn = QPushButton("💾 应用修复到Output")
        self.apply_fixes_btn.clicked.connect(self.apply_quality_fixes)
        self.apply_fixes_btn.setStyleSheet(get_start_button_style(config.theme))
        
        self.select_all_btn = QPushButton("✅ 全选")
        self.select_all_btn.clicked.connect(self.select_all_items)
        self.deselect_all_btn = QPushButton("⬜ 反选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_items)

        process_btn_layout.addWidget(self.retranslate_issues_btn)
        process_btn_layout.addWidget(self.select_all_btn)
        process_btn_layout.addWidget(self.deselect_all_btn)
        process_btn_layout.addWidget(self.apply_fixes_btn)

        quality_result_layout.addLayout(process_btn_layout)

        # 问题统计显示
        self.quality_stats_label = QLabel("")
        self.quality_stats_label.setStyleSheet(get_background_blue_style(config.theme))
        self.quality_stats_label.setWordWrap(True)
        self.quality_stats_label.setMinimumHeight(40)
        quality_result_layout.addWidget(self.quality_stats_label)

        # 问题项表格
        table_label = QLabel("问题项详情 (勾选需要应用的项，点击编辑按钮进行修改)")
        quality_result_layout.addWidget(table_label)

        self.quality_issues_table = QTableWidget()
        self.quality_issues_table.setColumnCount(6)  # 增加多选框列
        self.quality_issues_table.setHorizontalHeaderLabels(["选择", "键", "英文原文", "原中文", "新翻译", "操作"])
        self.quality_issues_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.quality_issues_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.quality_issues_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.quality_issues_table.horizontalHeader().resizeSection(0, 40)  # 设置选择列宽度为50像素
        self.quality_issues_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        # self.quality_issues_table.horizontalHeader().resizeSection(1, 80)  # 设置键列宽度为80像素
        self.quality_issues_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.quality_issues_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.quality_issues_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.quality_issues_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.quality_issues_table.setMinimumHeight(300)
        
        # 应用表头样式
        apply_table_header_style(self.quality_issues_table, config.theme)

        quality_result_layout.addWidget(self.quality_issues_table)

        layout.addWidget(quality_result_group)

        self.setLayout(layout)

    def run_quality_check(self):
        """运行质量检查"""
        # 检查控件是否还存在
        if not hasattr(self, 'quality_stats_label') or self.quality_stats_label is None:
            return
            
        # 使用保存的文件路径
        if not self.en_file or not self.zh_file:
            if hasattr(self, 'quality_stats_label') and self.quality_stats_label:
                CustomMessageBox.warning(self, "提示", "没有设置要检查的文件")
            return

        # 先显示加载状态
        if hasattr(self, 'quality_stats_label') and self.quality_stats_label:
            try:
                self.quality_stats_label.setText("正在运行质量检查...")
            except RuntimeError:
                # 控件已被删除，直接返回
                return
                
        if hasattr(self, 'quality_issues_table') and self.quality_issues_table:
            try:
                self.quality_issues_table.setRowCount(0)
            except RuntimeError:
                # 控件已被删除，直接返回
                return

        # 直接使用文件路径运行质量检查
        try:
            from core.quality_checker import QualityChecker
            checker = QualityChecker()
            
            # 获取mod_mapping（如果有的话）
            mod_mapping = getattr(self, 'mod_mapping', None)
            
            # 检查单个文件对
            result = checker.check_files(self.en_file, self.zh_file, mod_mapping)
            
            if result.get('成功', False):
                issues = result.get('问题', [])
        
                
                # 转换问题格式
                issues_data = []
                for issue in issues:
                    issues_data.append({
                        '键': issue.get('键', ''),
                        '英文': issue.get('英文', ''),
                        '中文': issue.get('中文', ''),
                        '新翻译': issue.get('新翻译', ''),
                        '问题类型': issue.get('问题类型', ''),
                        '原始文件': issue.get('原始文件', ''),
                        'mod_name': issue.get('mod_name', ''),  # 添加mod名称
                        'filename': issue.get('filename', '')   # 添加文件名
                    })
                
                # 更新表格
                self.update_quality_issues_table(issues_data)
                
                # 更新统计
                stats = self._calculate_stats_from_issues(issues)
                self.update_quality_stats(stats)
                
                if hasattr(self, 'quality_stats_label') and self.quality_stats_label:
                    try:
                        self.quality_stats_label.setText(f"质量检查完成，发现 {len(issues)} 个问题")
                    except RuntimeError:
                        pass
            else:
                if hasattr(self, 'quality_stats_label') and self.quality_stats_label:
                    try:
                        self.quality_stats_label.setText(f"质量检查失败: {result.get('消息', '未知错误')}")
                    except RuntimeError:
                        pass
                signal_bus.log_message.emit("ERROR", f"质量检查失败: {result.get('消息', '未知错误')}", {})
                
        except Exception as e:
            if hasattr(self, 'quality_stats_label') and self.quality_stats_label:
                try:
                    self.quality_stats_label.setText(f"质量检查出错: {str(e)}")
                except RuntimeError:
                    pass
            signal_bus.log_message.emit("ERROR", f"质量检查出错: {str(e)}", {})
    
    def _calculate_stats_from_issues(self, issues):
        """从问题列表计算统计信息"""
        stats = {
            '总问题数': len(issues),
            '中英文夹杂数': 0,
            '未翻译数': 0,
            '变量不匹配数': 0
        }
        
        for issue in issues:
            issue_type = issue.get('问题类型', '')
            if '中英文夹杂' in issue_type:
                stats['中英文夹杂数'] += 1
            elif '未翻译' in issue_type:
                stats['未翻译数'] += 1
            elif '变量不匹配' in issue_type:
                stats['变量不匹配数'] += 1
        
        return stats

    def analyze_quality_results(self):
        """分析质量检查结果"""
        # 这里应该从项目管理器获取已经检查到的问题
        if not self.project_manager or not self.project_manager.current_project:
            signal_bus.log_message.emit("WARNING", "没有活动项目", {})
            return

        # 从项目管理器获取质量检查结果
        quality_results = getattr(self.project_manager, 'quality_results', None)

        if not quality_results:
            signal_bus.log_message.emit("WARNING", "没有可用的质量检查结果", {})
            return

        # 确保我们获取的是字典格式
        if isinstance(quality_results, dict):
            issues_list = quality_results.get('问题列表', [])
            signal_bus.log_message.emit("INFO", f"📊 从质量检查结果获取到 {len(issues_list)} 个问题", {})

            # 直接调用质量检查器分析
            from core.quality_checker import QualityChecker
            checker = QualityChecker()
            result = checker.analyze_quality_results(quality_results)  # 传入完整字典

            if result['成功']:
                # 更新UI
                self.update_quality_issues_table(result['待修复问题'])
                self.update_quality_stats(result['状态'])
                signal_bus.log_message.emit("INFO", f"分析成功，更新了 {len(result['待修复问题'])} 个问题项", {})
            else:
                signal_bus.log_message.emit("ERROR", f"分析失败: {result.get('消息', '未知错误')}", {})
        else:
            signal_bus.log_message.emit("ERROR", f"不支持的质量结果格式: {type(quality_results)}", {})

    def retranslate_quality_issues(self):
        """重新翻译质量问题"""
        if not self.quality_fixes:
            CustomMessageBox.warning(self, "提示", "请先运行质量检查")
            return

        # 禁用按钮，防止重复点击
        self.retranslate_issues_btn.setEnabled(False)
        self.retranslate_issues_btn.setText("🔄 翻译中...")

        # 提取需要翻译的问题
        issues_to_translate = []
        for key, issue in self.quality_fixes.items():
            english = issue.get('英文', '')
            if english and english.strip():
                issues_to_translate.append({
                    '键': key,
                    '英文': english,
                    '中文': issue.get('中文', ''),
                    '问题类型': issue.get('问题类型', ''),
                    '原始文件': issue.get('原始文件', '')
                })

        if not issues_to_translate:
            CustomMessageBox.warning(self, "提示", "没有找到需要重新翻译的问题")
            # 重新启用按钮
            self.retranslate_issues_btn.setEnabled(True)
            self.retranslate_issues_btn.setText("🤖 AI重新翻译问题项")
            return

        if not issues_to_translate:
            # 显示详细原因
            error_msg = "没有找到需要重新翻译的问题。可能原因：\n"
            error_msg += "1. 问题项的英文原文为空\n"
            error_msg += "2. 请先运行质量检查获取问题项\n"
            error_msg += "3. 检查表格中是否有英文原文内容"
            CustomMessageBox.warning(self, "提示", error_msg)
            # 重新启用按钮
            self.retranslate_issues_btn.setEnabled(True)
            self.retranslate_issues_btn.setText("🤖 AI重新翻译问题项")
            return

        params = {'问题列表': issues_to_translate}
        signal_bus.log_message.emit("INFO", f"🤖 开始重新翻译 {len(issues_to_translate)} 个问题", {})
        signal_bus.retranslateQualityIssues.emit(params)

    def select_all_items(self):
        """全选所有项"""
        for row in range(self.quality_issues_table.rowCount()):
            checkbox = self.quality_issues_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(True)

    def deselect_all_items(self):
        """反选所有项"""
        for row in range(self.quality_issues_table.rowCount()):
            checkbox = self.quality_issues_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(not checkbox.isChecked())

    def apply_quality_fixes(self):
        """应用质量修复 - 只应用选中的项"""
        if not self.quality_fixes:
            CustomMessageBox.warning(self, "提示", "没有可应用的修复")
            return

        

        # 收集选中且有new_translation的修复
        fixes_to_apply = {}
        for row in range(self.quality_issues_table.rowCount()):
            checkbox = self.quality_issues_table.cellWidget(row, 0)
            if checkbox and hasattr(checkbox, 'isChecked') and checkbox.isChecked():
                key_item = self.quality_issues_table.item(row, 1)
                if key_item:
                    key = key_item.text()
                    if key in self.quality_fixes:
                        fix_data = self.quality_fixes[key]
                        new_translation = fix_data.get('新翻译', '')
                        if new_translation and new_translation.strip():
                            fixes_to_apply[key] = {
                                '键': key,
                                '新翻译': new_translation,
                                '原始文件': fix_data.get('原始文件', ''),
                                '英文': fix_data.get('英文', ''),
                                '中文': fix_data.get('中文', ''),
                                'mod_name': fix_data.get('mod_name', ''),  # 添加mod名称
                                'filename': fix_data.get('filename', '')  # 添加文件名
                            }

        if not fixes_to_apply:
            CustomMessageBox.warning(self, "提示", "没有选中任何有新翻译的项")
            return

        # 获取output文件夹路径
        if hasattr(self, 'output_folder') and self.output_folder:
            # 使用保存的output文件夹路径
            output_folder = self.output_folder
            self.mod_mapping = getattr(self, 'mod_mapping', None)  # 也保存到实例变量
        elif self.project_manager:
            output_folder = self.project_manager.get_folder_path('output')
        else:
            # 如果都没有，尝试从文件路径推导
            # 使用zh_file的父目录作为output文件夹
            if self.zh_file:
                output_folder = os.path.dirname(self.zh_file)
            else:
                CustomMessageBox.warning(self, "提示", "无法确定输出文件夹路径")
                return

        params = {
            '问题列表': list(self.quality_fixes.values()),
            'fixes': fixes_to_apply,
            '输出文件夹': output_folder
        }

        signal_bus.log_message.emit("SUCCESS", f"应用 {len(fixes_to_apply)} 个选中的修复到: {output_folder}",{})
        signal_bus.applyQualityFixes.emit(params)

    def edit_translation(self, row):
        """编辑翻译 - 通过编辑按钮触发"""
        try:
            key_item = self.quality_issues_table.item(row, 1)
            english_item = self.quality_issues_table.item(row, 2)
            original_zh_item = self.quality_issues_table.item(row, 3)
            new_translation_item = self.quality_issues_table.item(row, 4)

            if not all([key_item, english_item, original_zh_item, new_translation_item]):
                signal_bus.log_message.emit("ERROR", f"编辑失败: 第{row}行数据不完整", {})
                return

            key = key_item.text()
            english_text = english_item.text()
            original_chinese = original_zh_item.text()
            current_translation = new_translation_item.text()

            # 获取问题类型
            issue_type = ""
            if key in self.quality_fixes:
                issue_type = self.quality_fixes[key].get('问题类型', '')

            from ui.edit_translation_dialog import EditTranslationDialog
            dialog = EditTranslationDialog(self)
            dialog.set_data(english_text, original_chinese, current_translation, issue_type)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_text = dialog.get_new_translation()
                if new_text and new_text != current_translation:
                    # 更新表格
                    new_translation_item.setText(new_text)

                    # 更新数据存储
                    for fix_key, fix_data in self.quality_fixes.items():
                        if fix_data.get('键') == key:
                            self.quality_fixes[fix_key]['新翻译'] = new_text
                            
                            break

                    # 高亮显示已编辑
                    new_translation_item.setBackground(get_edited_translation_bg_color(config.theme))

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"编辑翻译失败: {e}", {})
            import traceback
            traceback.print_exc()

    def update_quality_issues_table(self, issues_data):
        """更新质量问题表格"""
        # 检查表格是否存在
        if not hasattr(self, 'quality_issues_table') or self.quality_issues_table is None:
            return
            
        try:
            # 清空表格和存储
            self.quality_issues_table.setRowCount(0)
        except RuntimeError:
            # 表格已被删除
            return
            
        self.quality_fixes = {}

        if not issues_data:
            signal_bus.log_message.emit("WARNING", "没有收到问题数据", {})
            return

        for i, issue in enumerate(issues_data):

            self.quality_issues_table.insertRow(i)

            # 多选框 - 使用QCheckBox控件
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.quality_issues_table.setCellWidget(i, 0, checkbox)

            # 键 - 确保正确获取
            display_key = issue.get('键', '')

            key_item = QTableWidgetItem(str(display_key))
            key_item.setToolTip(str(display_key))
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.quality_issues_table.setItem(i, 1, key_item)

            # 英文原文 - 确保正确获取
            english_text = issue.get('英文', '')

            english_item = QTableWidgetItem(str(english_text))
            english_item.setToolTip(str(english_text))
            english_item.setFlags(english_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.quality_issues_table.setItem(i, 2, english_item)

            # 原中文
            original_chinese = issue.get('中文', '')

            original_zh_item = QTableWidgetItem(str(original_chinese))
            original_zh_item.setToolTip(str(original_chinese))
            original_zh_item.setFlags(original_zh_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.quality_issues_table.setItem(i, 3, original_zh_item)

            # 新翻译
            new_translation = issue.get('新翻译', '')

            new_translation_item = QTableWidgetItem(str(new_translation))
            new_translation_item.setToolTip(str(new_translation))
            new_translation_item.setFlags(new_translation_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # 如果有新翻译，根据主题设置背景色
            if new_translation:
                new_translation_item.setBackground(get_new_translation_bg_color(config.theme))

            self.quality_issues_table.setItem(i, 4, new_translation_item)

            # 编辑按钮
            edit_btn = QPushButton("编辑")
            edit_btn.setMinimumWidth(45)
            edit_btn.setMaximumHeight(28)
            edit_btn.setStyleSheet(get_table_edit_button_style(config.theme))
            edit_btn.clicked.connect(lambda checked, row=i: self.edit_translation(row))
            self.quality_issues_table.setCellWidget(i, 5, edit_btn)

            # 处理问题类型
            issue_type = issue.get('问题类型', '')

            # 存储修复数据
            fix_key = str(display_key)
            self.quality_fixes[fix_key] = {
                '键': fix_key,
                '英文': str(english_text),
                '中文': str(original_chinese),
                '新翻译': str(new_translation),
                '原始文件': str(issue.get('原始文件', '')),
                '问题类型': issue_type,
                'mod_name': str(issue.get('mod_name', '')),  # 添加mod名称
                'filename': str(issue.get('filename', ''))   # 添加文件名
            }

    def update_quality_stats(self, stats):
        """更新质量统计"""
        if stats and hasattr(self, 'quality_stats_label') and self.quality_stats_label:
            try:
                stats_text = (
                    f"总问题数: {stats.get('总问题数', stats.get('总问题数', 0))} | "
                    f"中英混杂: {stats.get('中英文夹杂数', stats.get('mixed_language_issues', 0))} | "
                    f"未翻译: {stats.get('未翻译数', stats.get('untranslated_issues', 0))} | "
                    f"变量问题: {stats.get('变量不匹配数', stats.get('variable_issues', 0))}"
                )
                self.quality_stats_label.setText(stats_text)
            except RuntimeError:
                # 标签已被删除
                pass
    
    def update_table_theme(self):
        """更新表格主题 - 在主题切换时调用"""
        # 更新所有新翻译单元格的背景色
        for row in range(self.quality_issues_table.rowCount()):
            new_translation_item = self.quality_issues_table.item(row, 4)
            if new_translation_item and new_translation_item.text():
                # 检查是否是编辑后的橙色背景(需要检查两种主题的橙色)
                current_bg = new_translation_item.background().color()
                light_edited = QColor(255, 228, 196)  # 浅橙色
                dark_edited = QColor(191, 87, 0)  # 深橙色
                
                if current_bg == light_edited or current_bg == dark_edited:
                    # 是编辑后的,更新为当前主题的编辑色
                    new_translation_item.setBackground(get_edited_translation_bg_color(config.theme))
                else:
                    # 不是编辑后的,更新为当前主题的新翻译背景色
                    new_translation_item.setBackground(get_new_translation_bg_color(config.theme))
            
            # 更新编辑按钮样式
            edit_btn = self.quality_issues_table.cellWidget(row, 5)
            if edit_btn:
                edit_btn.setStyleSheet(get_table_edit_button_style(config.theme))
        
        # 更新表头样式
        apply_table_header_style(self.quality_issues_table, config.theme)
    
    def update_translations_from_result(self, translation_result):
        """从翻译结果更新新翻译列"""
        try:
            if not hasattr(self, 'quality_issues_table') or not self.quality_issues_table:
                return
                
            # translation_result 应该是一个字典，键是原始键，值是新的翻译
            if not isinstance(translation_result, dict):
                signal_bus.log_message.emit("WARNING", "翻译结果格式错误", {})
                return
            
            signal_bus.log_message.emit("DEBUG", f"收到翻译结果，包含 {len(translation_result)} 项", {})
            
            # 显示前几个键用于调试
            count = 0
            for key in translation_result.keys():
                if count < 5:
                    signal_bus.log_message.emit("DEBUG", f"翻译结果键: {key}", {})
                    count += 1
            
            updated_count = 0
            # 遍历表格，更新新翻译列
            for row in range(self.quality_issues_table.rowCount()):
                key_item = self.quality_issues_table.item(row, 1)
                if not key_item:
                    continue
                    
                key = key_item.text()
                # 调试：显示表格中的前几个键
                if row < 5:
                    signal_bus.log_message.emit("DEBUG", f"表格中的键: {key}", {})
                
                if key in translation_result:
                    new_translation = translation_result[key]
                    new_translation_item = self.quality_issues_table.item(row, 4)
                    if new_translation_item:
                        new_translation_item.setText(new_translation)
                        # 设置新翻译背景色
                        new_translation_item.setBackground(get_new_translation_bg_color(config.theme))
                        
                        # 更新存储的数据
                        if key in self.quality_fixes:
                            self.quality_fixes[key]['新翻译'] = new_translation
                        
                        updated_count += 1

                            
            
            
            
            # 恢复AI重新翻译按钮状态
            if hasattr(self, 'retranslate_issues_btn') and self.retranslate_issues_btn:
                try:
                    self.retranslate_issues_btn.setEnabled(True)
                    self.retranslate_issues_btn.setText("🤖 AI重新翻译问题项")
                    
                except RuntimeError:
                    pass
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"更新翻译失败: {str(e)}", {})