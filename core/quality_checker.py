# core/quality_checker.py
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from core.signal_bus import signal_bus
from core.file_tool import file_tool
from core.variable_protector import VariableProtector


class QualityChecker:
    """质量检查器"""

    def __init__(self):
        self.enable_variable_check = True
        self.enable_untranslated_check = True
        self.enable_english_check = True

        # 英文检测排除词
        self.excluded_words = {'joja', 'true', 'false', 'null', 'stardew', 'valley', 'id'}
        self._excluded_pattern = '|'.join(re.escape(word) for word in self.excluded_words)
        
        # 初始化变量保护器
        self.variable_protector = VariableProtector()
    
    def check_files(self, en_file: str, zh_file: str, mod_mapping: Dict = None) -> Dict[str, any]:
        """检查单个文件对的质量"""
        try:
            if not os.path.exists(en_file) or not os.path.exists(zh_file):
                return {'成功': False, '消息': '文件不存在'}
            
            # 读取文件
            en_file_data = file_tool.read_json_file(en_file)
            zh_file_data = file_tool.read_json_file(zh_file)
            
            # 提取实际数据和mod_mapping
            if isinstance(en_file_data, dict) and 'data' in en_file_data:
                en_data = en_file_data['data']
                # 如果文件中有mod_mapping，使用它
                if 'mod_mapping' in en_file_data:
                    mod_mapping = en_file_data['mod_mapping']
            else:
                en_data = en_file_data
                
            if isinstance(zh_file_data, dict) and 'data' in zh_file_data:
                zh_data = zh_file_data['data']
            else:
                zh_data = zh_file_data
            
            # 检查质量
            issues = self._check_file(en_data, zh_data, os.path.basename(en_file), mod_mapping)
            
            return {
                '成功': True,
                '问题': issues,
                '消息': f'检查完成，发现 {len(issues)} 个问题'
            }
        except Exception as e:
            return {'成功': False, '消息': f'检查失败: {str(e)}'}

    def run_quality_check(self, en_folder: str, zh_folder: str, max_files: int = 20) -> Dict[str, any]:
        """运行质量检查"""
        try:
            # 获取JSON文件
            en_files = file_tool.get_all_json_files(en_folder)

            all_issues, checked_files, skipped_files = [], 0, 0

            # 检查文件（限制数量）
            for i, en_file in enumerate(en_files[:max_files]):
                en_path, zh_path = Path(en_file), self._find_zh_file(en_file, en_folder, zh_folder)

                if not zh_path or not zh_path.exists():
                    error_msg = "未找到对应的中文文件" if not zh_path else f"中文文件不存在: {zh_path.name}"
                    signal_bus.log_message.emit("ERROR", error_msg, {})
                    skipped_files += 1
                    continue

                # 检查文件内容
                try:
                    en_data = file_tool.read_json_file(en_file)
                    zh_data = file_tool.read_json_file(zh_path)

                    signal_bus.log_message.emit("INFO",
                                           f"[{i + 1}/{min(max_files, len(en_files))}] 处理: {en_path.name} "
                                           f"对应: {zh_path.name} 英文键: {len(en_data)}, 中文键: {len(zh_data)}", {})

                    # 使用相对路径作为文件名，这样应用修复时能找到对应的输出文件
                    relative_path = str(en_path.relative_to(en_folder))
                    file_issues = self._check_file(en_data, zh_data, relative_path)

                    if file_issues:
                        all_issues.extend(file_issues)

                    checked_files += 1

                except Exception:
                    import traceback
                    traceback.print_exc()

            # 统计和保存结果
            stats = self._calculate_stats(all_issues)

            return {
                '成功': True,
                '问题列表': all_issues,
                '统计': stats,
                '已检查文件数': checked_files,
                '跳过文件数件数': skipped_files,
                '总文件数': len(en_files)
            }

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"质量检查失败: {e}", {})
            import traceback
            traceback.print_exc()
            return {'成功': False, '错误': str(e)}

    def _check_file(self, en_data: Dict, zh_data: Dict, filename: str, mod_mapping: Dict = None) -> List[Dict]:
        """检查单个文件"""
        issues = []

        for key, en_value in en_data.items():
            if not isinstance(en_value, str) or not en_value.strip():
                continue

            zh_value = zh_data.get(key, "").strip()
            if not zh_value:
                continue

            # 获取mod信息
            mod_name = ''
            mod_filename = ''
            if mod_mapping and key in mod_mapping:
                mod_name = mod_mapping[key].get('mod_name', '')
                mod_filename = mod_mapping[key].get('filename', '')
            
            # 按优先级检查问题
            if self.enable_variable_check and (var_issue := self._check_variables(en_value, zh_value)):
                issues.append(self._build_issue(key, en_value, zh_value, filename, '变量不匹配', var_issue, mod_name, mod_filename))
            elif self.enable_untranslated_check and self._is_untranslated(en_value, zh_value):
                issues.append(self._build_issue(key, en_value, zh_value, filename, '未翻译',{'新翻译': ""}, mod_name, mod_filename))
            elif self.enable_english_check and (eng_issue := self._check_english_content(zh_value)):
                issues.append(self._build_issue(key, en_value, zh_value, filename, '中英文夹杂', eng_issue, mod_name, mod_filename))

        return issues

    def analyze_quality_results(self, quality_results: Dict) -> Dict[str, any]:
        """分析质量检查结果"""
        try:
            signal_bus.log_message.emit("INFO", "开始分析质量结果", {})

            # 加载问题数据
            issues_list = quality_results.get('问题列表', [])

            # 分析和提取需要修复的问题
            stats = self._calculate_stats(issues_list)
            issues_to_fix = self._extract_fixable_issues(issues_list)

            signal_bus.log_message.emit("INFO",f"分析完成: 总问题数={stats['总问题数']}, 准备修复={len(issues_to_fix)}", {})

            return {
                '成功': True,
                '统计': stats,
                '待修复问题': issues_to_fix
            }

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"分析质量结果失败: {e}", {})
            import traceback
            traceback.print_exc()
            return {'成功': False, '消息': str(e)}

    def _extract_fixable_issues(self, issues: List[Dict]) -> List[Dict]:
        """提取需要修复的问题 - 确保格式正确"""
        fixable_issues = []

        for issue in issues:
            if not isinstance(issue, dict):
                continue

            # 确定问题类型
            issue_type = issue.get('问题类型', '')
            if not issue_type:
                continue

            # 构建标准格式的问题项
            fixable_issue = {
                '键': issue.get('键', ''),
                '英文': issue.get('英文', ''),
                '中文': issue.get('中文', ''),
                '新翻译': issue.get('新翻译', ''),
                '问题类型': issue_type,
                '原始文件': issue.get('原始文件', ''),
                '详细信息': issue.get('详细信息', '')
            }

            # 确保关键字段存在
            if not fixable_issue['键']:
                # 如果没有键，创建一个
                english_hash = hash(fixable_issue['英文'])
                fixable_issue['键'] = f"issue_{abs(english_hash) % 10000}"

            fixable_issues.append(fixable_issue)
        return fixable_issues
    # ==================== 辅助方法 ====================

    def _check_variables(self, original: str, translated: str) -> Dict:
        """检查变量不匹配"""
        # 创建独立的变量保护器实例，避免影响全局状态
        from core.variable_protector import VariableProtector
        local_protector = VariableProtector()
        
        # 提取变量
        protected_orig, orig_vars = local_protector.protect_variables(original)
        protected_trans, trans_vars = local_protector.protect_variables(translated)

        # 使用变量保护器准确计算变量数量
        orig_var_count = local_protector.count_variables_in_text(original)
        trans_var_count = local_protector.count_variables_in_text(translated)

        # 检查变量数量是否不同
        if orig_var_count != trans_var_count:
            from core.signal_bus import signal_bus
            original_short = original[:50] + "..." if len(original) > 50 else original
            signal_bus.log_message.emit("WARNING", "变量数量不匹配!", {"original": original_short})
            return {'新翻译': translated}

        # 检查变量内容是否完全匹配（按顺序）
        orig_vars_list = list(orig_vars.values())
        trans_vars_list = list(trans_vars.values())
        
        if orig_vars_list != trans_vars_list:
            from core.signal_bus import signal_bus
            original_short = original[:50] + "..." if len(original) > 50 else original
            signal_bus.log_message.emit("WARNING", "变量内容不匹配!", {"original": original_short})
            return {'新翻译': translated}

        return {}

    def _check_english_content(self, text: str) -> Dict:
        """检查中英文夹杂"""
        if not text or not text.strip():
            return {}

        # 使用 VariableProtector 的变量模式移除变量，避免检测变量中的英文
        temp_text = text
        for pattern in self.variable_protector.variable_patterns:
            temp_text = re.sub(pattern, '', temp_text)
        
        # 移除排除词
        temp_text = re.sub(self._excluded_pattern, '', temp_text, flags=re.IGNORECASE)

        # 查找英文内容
        issues = set(re.findall(r'[a-zA-Z]{3,}', temp_text))

        if not issues:
            return {}

        # 标记原文
        for word in sorted(issues, key=len, reverse=True):
            text = text.replace(word, f"【{word}】")

        return {
            '新翻译': text
        }

    @staticmethod
    def _is_untranslated(original: str, translated: str) -> bool:
        """检查是否未翻译"""
        return not translated or not translated.strip() or original.strip().lower() == translated.strip().lower()

    @staticmethod
    def _find_zh_file(en_file: str | Path, en_folder: str | Path, zh_folder: str | Path) -> Optional[Path]:
        """找到对应的中文文件"""
        try:
            rel_path = Path(en_file).relative_to(en_folder)

            if rel_path.name.lower() == 'default.json':
                rel_path = rel_path.with_name('zh.json')

            return Path(zh_folder) / rel_path
        except ValueError:
            return None

    @staticmethod
    def _calculate_stats(issues: List[Dict]) -> Dict[str, int]:
        """计算统计信息"""
        if not issues:
            return {'总问题数': 0, '中英文夹杂数': 0, '未翻译数': 0, '变量不匹配数': 0}

        type_counter = Counter(issue.get('问题类型') for issue in issues if isinstance(issue, dict))

        return {
            '总问题数': len([i for i in issues if isinstance(i, dict)]),
            '中英文夹杂数': type_counter.get('中英文夹杂', 0),
            '未翻译数': type_counter.get('未翻译', 0),
            '变量不匹配数': type_counter.get('变量不匹配', 0)
        }

    @staticmethod
    def _build_issue(key: str, en_text: str, zh_text: str, filename: str,
                     issue_type: str, details: Dict, mod_name: str = '', mod_filename: str = '') -> Dict:
        """构建问题字典"""
        return {
            '键': key,
            '英文': en_text,
            '中文': zh_text,
            '问题类型': issue_type,
            '新翻译': details.get('新翻译', ''),
            '详细信息': details.get('详细信息', ''),
            '原始文件': filename,
            '状态': '等待翻译',
            'mod_name': mod_name,
            'filename': mod_filename
        }
