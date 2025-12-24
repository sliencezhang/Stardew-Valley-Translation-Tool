# core/file_tool.py
import json
import os
import re
from pathlib import Path
from typing import Dict, List

import hjson
from PySide6.QtCore import QObject

from core.signal_bus import signal_bus


class FileTool(QObject):



    def __init__(self, parent=None):
        super().__init__(parent)

    @staticmethod
    def read_json_file(file_path: str):
        """读取JSON文件，自动处理注释，尾随逗号，BOM格式问题"""
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        try:
            # 首先尝试直接用 hjson 解析
            return hjson.loads(content)
        except Exception as e:
            # 如果解析失败，尝试清理文件内容
            signal_bus.log_message.emit("WARNING", f"hjson 解析失败，尝试清理文件内容: {file_path}", {'错误': str(e)})
            
            # 更彻底的清理内容
            cleaned_content = content
            
            # 替换各种控制字符
            cleaned_content = cleaned_content.replace('\t', '  ')  # 制表符
            cleaned_content = cleaned_content.replace('\r', '')  # 回车符
            cleaned_content = cleaned_content.replace('\f', '')  # 换页符
            cleaned_content = cleaned_content.replace('\v', '')  # 垂直制表符
            
            # 移除字符串值中的控制字符（保留在字符串外的）
            import re
            # 匹配 JSON 字符串值并清理其中的控制字符
            def clean_string_value(match):
                quote = match.group(1)  # 引号类型
                content = match.group(2)  # 字符串内容
                # 清理字符串内容中的控制字符，但保留转义序列
                cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
                return f'{quote}{cleaned}{quote}'
            
            # 不使用正则表达式，直接逐字符清理控制字符
            # 这种方法更安全，不会误匹配
            def clean_text_preserving_structure(text):
                result = []
                in_string = False
                string_quote = None
                i = 0
                
                while i < len(text):
                    char = text[i]
                    
                    # 检查是否进入或退出字符串
                    if not in_string and char in ['"', "'"]:
                        in_string = True
                        string_quote = char
                        result.append(char)
                    elif in_string and char == string_quote:
                        # 检查是否是转义的引号
                        if i > 0 and text[i-1] == '\\':
                            result.append(char)
                        else:
                            in_string = False
                            string_quote = None
                            result.append(char)
                    elif in_string:
                        # 在字符串内，清理控制字符
                        if ord(char) < 32 and char not in ['\n', '\r']:  # 保留换行符，清理其他控制字符
                            # 跳过控制字符
                            pass
                        else:
                            result.append(char)
                    else:
                        # 在字符串外，保持原样
                        result.append(char)
                    
                    i += 1
                
                return ''.join(result)
            
            cleaned_content = clean_text_preserving_structure(cleaned_content)
            
            try:
                # 再次尝试解析
                return hjson.loads(cleaned_content)
            except Exception as e2:
                # 如果还是失败，尝试用标准 json 解析（忽略注释）
                signal_bus.log_message.emit("WARNING", f"清理后仍然解析失败，尝试标准 json 解析: {file_path}", {'错误': str(e2)})
                try:
                    # 移除注释行
                    lines = []
                    for line in cleaned_content.split('\n'):
                        # 移除行内注释
                        if '//' in line:
                            line = line[:line.index('//')]
                        # 跳过空行和纯注释行
                        if line.strip():
                            lines.append(line)
                    
                    cleaned_json = '\n'.join(lines)
                    # 处理尾随逗号
                    cleaned_json = re.sub(r',(\s*[}\]])', r'\1', cleaned_json)
                    
                    return json.loads(cleaned_json)
                except Exception as e3:
                    try:
                        signal_bus.log_message.emit("WARNING", f"尝试手动解析文件: {file_path}", {})
                        # 创建一个更智能的解析器
                        result = {}
                        lines = cleaned_content.split('\n')
                        i = 0
                        while i < len(lines):
                            line = lines[i].strip()
                            
                            # 跳过空行和注释行
                            if not line or line.startswith('//'):
                                i += 1
                                continue
                            
                            # 查找键值对
                            if ':' in line:
                                # 分割键和值
                                parts = line.split(':', 1)
                                key = parts[0].strip().strip('\"\'')
                                value_part = parts[1].strip()
                                
                                if not key:
                                    i += 1
                                    continue
                                
                                # 检查值是否以引号开始
                                if value_part.startswith('"') or value_part.startswith("'"):
                                    quote = value_part[0]
                                    value = value_part[1:]  # 移除开始引号
                                    
                                    # 检查是否在同一行结束（可能后面有逗号或其他字符）
                                    # 使用正则表达式找到结束引号的位置
                                    import re
                                    match = re.search(rf'(?<!\\){quote}', value)
                                    if match:
                                        # 找到未转义的结束引号
                                        end_pos = match.start()
                                        value = value[:end_pos]  # 只保留引号之前的内容
                                    else:
                                        # 多行字符串，继续读取直到找到未转义的结束引号
                                        i += 1
                                        found_end = False
                                        while i < len(lines):
                                            next_line = lines[i]
                                            value += '\n' + next_line
                                            
                                            # 检查这一行是否有未转义的结束引号
                                            pos = 0
                                            while pos < len(next_line):
                                                if next_line[pos] == quote:
                                                    # 检查是否是转义的引号
                                                    if pos == 0 or next_line[pos-1] != '\\':
                                                        # 找到未转义的结束引号
                                                        # 移除这个引号及之后的内容
                                                        value = value[:value.rfind('\n') + 1 + pos]
                                                        found_end = True
                                                        break
                                                pos += 1
                                            
                                            if found_end:
                                                break
                                            i += 1
                                    
                                    result[key] = value
                                else:
                                    # 非字符串值（如数字、布尔值等）
                                    result[key] = value_part
                            
                            i += 1
                        
                        signal_bus.log_message.emit("SUCCESS", f"手动解析成功，提取了 {len(result)} 个键值对: {file_path}", {})
                        return result
                    except Exception as e4:
                        signal_bus.log_message.emit("ERROR", f"手动解析也失败了: {file_path}", {'错误': str(e4)})
                        raise e3

    def save_json_file(self, translation_data: Dict, target_path: str, original_path: str = None) -> bool:
        """
        安全的翻译合并：完全保留original_path文件的结构、注释和格式
        """
        if original_path:
            try:
                # 读取原始文件（保留原始内容）
                with open(original_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()

                # 读取原始文件的JSON数据（用于获取原始值）
                original_data = self.read_json_file(original_path)
                additional_content = {}
                result_content = original_content

                for key, new_value in translation_data.items():
                    if key not in original_data:
                        additional_content.update({key: new_value})
                        continue

                    old_value = original_data[key]

                    # 统一处理方法，同时支持单行和多行
                    result_content = self._regex_replace(result_content, key, old_value, new_value)

                # 写入目标文件
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(result_content)

                # 发射成功日志信号
                signal_bus.log_message.emit(
                    'SUCCESS',
                    '文件保存成功',
                    {'文件路径': target_path, '源文件路径': original_path}
                )

                # 不再保存额外内容文件
                # 如果有额外内容，只记录日志但不保存文件
                if additional_content:
                    signal_bus.log_message.emit(
                        'SUCCESS',
                        f'发现 {len(additional_content)} 个未匹配到的内容，但不保存到单独文件',
                        {'源文件路径': original_path}
                    )

                return True

            except Exception as e:
                error_msg = str(e)
                # 发射错误日志信号
                signal_bus.log_message.emit(
                    'ERROR',
                    '文件保存失败',
                    {'文件路径': target_path, '错误': error_msg}
                )
                return False
        else:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(translation_data, ensure_ascii=False, indent=2))
                return True

    @staticmethod
    def _regex_replace(content: str, key: str, old_value: str, new_value: str) -> str:
        """
        使用正则表达式进行精确或模糊匹配
        优先匹配未注释的键，避免替换被注释掉的键
        """
        escaped_key = re.escape(key)

        # 先查找所有匹配的位置（包括注释和未注释的）
        all_matches = []
        
        # 对于多行值，总是使用DOTALL标志
        flags = re.DOTALL
        
        # 构建匹配键的正则模式，支持多行字符串
        patterns = [
            # 双引号键 + 任意值（支持转义字符和多行）
            f'"{escaped_key}"\\s*:\\s*"(?:[^"\\\\]|\\\\.)*"',
            # 单引号键 + 任意值
            f"'{escaped_key}'\\s*:\\s*'(?:[^'\\\\]|\\\\.)*'",
            # 无引号键 + 任意值
            f'{escaped_key}\\s*:\\s*"(?:[^"\\\\]|\\\\.)*"',
        ]

        # 收集所有匹配项及其位置
        for pattern in patterns:
            for match in re.finditer(pattern, content, flags):
                # 检查这个匹配是否被注释掉了
                start_pos = match.start()
                # 向前查找，看看这一行是否以 // 开头
                line_start = content.rfind('\n', 0, start_pos) + 1
                line_content = content[line_start:start_pos]
                
                # 如果这一行在键之前有 //（忽略空格），则认为是注释掉的
                is_commented = '//' in line_content
                
                all_matches.append({
                    'match': match,
                    'is_commented': is_commented,
                    'pattern': pattern
                })

        # 优先选择未注释的匹配
        for item in all_matches:
            if not item['is_commented']:
                match = item['match']
                # 使用 json.dumps 确保多行字符串正确格式化
                replacement = f'"{key}": {json.dumps(new_value, ensure_ascii=False)}'
                return content[:match.start()] + replacement + content[match.end():]

        # 如果没有未注释的，才使用注释的
        if all_matches:
            match = all_matches[0]['match']
            replacement = f'"{key}": {json.dumps(new_value, ensure_ascii=False)}'
            return content[:match.start()] + replacement + content[match.end():]

        return content

    @staticmethod
    def get_all_json_files(folder: str) -> List[str]:
        """获取文件夹中所有JSON文件路径"""
        folder_path = Path(folder)
        return [str(file_path) for file_path in folder_path.rglob('*.json')]

    @staticmethod
    def open_folder(folder_path: str) -> bool:
        """打开文件夹"""
        try:
            if os.path.exists(folder_path):
                os.startfile(folder_path)
                return True
            return False
        except Exception:
            # 如果os.startfile不可用，尝试其他方法
            try:
                import subprocess
                if os.name == 'nt':  # Windows
                    subprocess.Popen(f'explorer "{folder_path}"')
                elif os.name == 'posix':  # Linux or macOS
                    subprocess.Popen(['xdg-open', folder_path])
                return True
            except Exception:
                return False


file_tool = FileTool()