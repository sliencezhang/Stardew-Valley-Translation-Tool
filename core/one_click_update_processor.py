import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

from PySide6.QtCore import Qt
from core.config import config
from core.signal_bus import signal_bus
from core.file_tool import file_tool
from core.translation_executor import TranslationExecutor


class OneClickUpdateProcessor:
    """一键更新处理器 - 纯粘合剂，只负责调用其他模块的功能"""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.translation_executor = TranslationExecutor(project_manager)
        self._is_running = True
        self._user_processed = None
        self._should_continue = True
        
    def stop(self):
        """停止处理"""
        self._is_running = False
        self.translation_executor.stop()
    
    def process(self, params: Dict) -> Dict[str, Any]:
        """执行一键更新"""
        try:
            en_mod_paths = params.get('英文mod路径', [])
            zh_mod_paths = params.get('中文mod路径', [])
            skip_name_detection = params.get('跳过人名检测', False)
            
            # 首先检查是否有当前打开的项目
            if not self.project_manager or not self.project_manager.current_project:
                return {'成功': False, '消息': '请先打开项目'}
            
            # 检查路径是否存在
            for path in en_mod_paths:
                if not os.path.exists(path):
                    return {'成功': False, '消息': f'英文mod路径不存在: {path}'}
            
            for path in zh_mod_paths:
                if not os.path.exists(path):
                    return {'成功': False, '消息': f'中文mod路径不存在: {path}'}
            
            # 多文件夹模式检查
            is_multi_folder = len(en_mod_paths) > 1 or len(zh_mod_paths) > 1
            if is_multi_folder:
                signal_bus.log_message.emit("INFO", "检测到多文件夹模式，将进行文件夹名称匹配", {})
                if not self._validate_folder_names(en_mod_paths, zh_mod_paths):
                    return {'成功': False, '消息': '多文件夹模式下，英文和中文mod文件夹名称必须对应匹配'}
            
            # 使用project_manager获取输出文件夹路径
            output_folder = self.project_manager.get_folder_path('output')
            signal_bus.log_message.emit("INFO", f"输出文件夹路径: {output_folder}", {})
            
            # 步骤1: 人名地名检测（如果未跳过）
            if not skip_name_detection:
                detection_result = self._perform_name_detection(en_mod_paths, zh_mod_paths)
                if not detection_result['成功']:
                    return detection_result
                
                # 发送检测完成信号
                signal_bus.nameDetectionCompleted.emit(detection_result)
                
                # 等待用户处理完成
                import threading
                import time
                
                # 创建事件来等待用户处理完成
                self._user_processed = threading.Event()
                self._should_continue = True
                
                # 暂停执行，等待用户处理
                signal_bus.log_message.emit("INFO", "等待用户处理人名地名检测结果...", {})
                
                # 等待最多5分钟
                if not self._user_processed.wait(timeout=300):
                    signal_bus.log_message.emit("WARNING", "等待超时，继续执行翻译", {})
                
                # 检查是否应该继续
                if not self._should_continue:
                    return {'成功': False, '消息': '用户取消了操作'}
            
            # 步骤2-6: 执行翻译和处理
            return self._perform_translation_and_processing(en_mod_paths, zh_mod_paths, output_folder, is_multi_folder)
            
        except Exception as e:
            error_msg = f"一键更新失败: {str(e)}"
            signal_bus.log_message.emit("ERROR", error_msg, {})
            return {'成功': False, '消息': error_msg}
    
    def _perform_name_detection(self, en_paths: List[str], zh_paths: List[str]) -> Dict[str, Any]:
        """执行人名地名检测 - 调用人名地名检测标签页的逻辑"""
        try:
            signal_bus.log_message.emit("INFO", "开始人名地名检测步骤...", {})
            
            # 直接使用SmartNameExtractor的逻辑，与标签页完全相同
            from ui.tabs.tab_name_detection import SmartNameExtractor
            
            extractor = SmartNameExtractor()
            all_pairs = []
            
            # 处理每一对英文和中文mod文件夹
            total_pairs = min(len(en_paths), len(zh_paths))
            
            for i in range(total_pairs):
                en_mod_folder = en_paths[i]
                zh_mod_folder = zh_paths[i]
                
                # 查找英文mod的i18n文件夹
                en_i18n_folder = os.path.join(en_mod_folder, 'i18n')
                if not os.path.exists(en_i18n_folder):
                    continue
                
                # 查找中文mod的i18n文件夹
                zh_i18n_folder = os.path.join(zh_mod_folder, 'i18n')
                if not os.path.exists(zh_i18n_folder):
                    continue
                
                # 处理第一种情况：直接有default.json和zh.json
                default_file = os.path.join(en_i18n_folder, 'default.json')
                zh_file = os.path.join(zh_i18n_folder, 'zh.json')
                
                if os.path.exists(default_file) and os.path.exists(zh_file):
                    pairs = extractor.load_and_match_files(default_file, zh_file, en_mod_folder)
                    all_pairs.extend(pairs)
                
                # 处理第二种情况：有Default和Zh文件夹
                default_folder = os.path.join(en_i18n_folder, 'Default')
                zh_folder = os.path.join(zh_i18n_folder, 'Zh')
                
                if os.path.exists(default_folder) and os.path.exists(zh_folder):
                    # 获取两个文件夹中的所有json文件
                    default_files = [f for f in os.listdir(default_folder) if f.endswith('.json')]
                    zh_files = [f for f in os.listdir(zh_folder) if f.endswith('.json')]
                    
                    # 匹配相同文件名的文件
                    for filename in default_files:
                        if filename in zh_files:
                            default_path = os.path.join(default_folder, filename)
                            zh_path = os.path.join(zh_folder, filename)
                            pairs = extractor.load_and_match_files(default_path, zh_path, en_mod_folder)
                            all_pairs.extend(pairs)
            
            # 过滤和去重
            if all_pairs:
                filtered_pairs = extractor.smart_filter_names(all_pairs, min_confidence=0.6)
                # 去重
                seen_pairs = set()
                unique_pairs = []
                for pair in filtered_pairs:
                    key = (pair['en'], pair['zh'])
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        unique_pairs.append(pair)
                
                signal_bus.log_message.emit("SUCCESS", f"人名地名检测完成，检测到 {len(unique_pairs)} 个术语", {})
                return {
                    '成功': True,
                    '检测结果': unique_pairs,
                    '消息': f'检测到 {len(unique_pairs)} 个人名地名'
                }
            else:
                signal_bus.log_message.emit("INFO", "未检测到需要处理的人名地名", {})
                return {
                    '成功': True,
                    '检测结果': [],
                    '消息': '未检测到人名地名'
                }
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"人名地名检测失败: {str(e)}", {})
            return {'成功': False, '消息': f'人名地名检测失败: {str(e)}'}
    
    def _perform_translation_and_processing(self, en_paths: List[str], zh_paths: List[str], output_folder: str, is_multi_folder: bool) -> Dict[str, Any]:
        """执行翻译和处理"""
        try:
            # 先清理项目的en、zh和output文件夹
            signal_bus.log_message.emit("INFO", "清理项目文件夹...", {})
            
            en_folder = self.project_manager.get_folder_path('en')
            zh_folder = self.project_manager.get_folder_path('zh')
            output_folder = self.project_manager.get_folder_path('output')
            
            # 清空en文件夹
            if os.path.exists(en_folder):
                shutil.rmtree(en_folder)
                signal_bus.log_message.emit("INFO", "已清理en文件夹", {})
            
            # 清空zh文件夹
            if os.path.exists(zh_folder):
                shutil.rmtree(zh_folder)
                signal_bus.log_message.emit("INFO", "已清理zh文件夹", {})
            
            # 清空output文件夹
            if os.path.exists(output_folder):
                import subprocess
                
                # 直接使用Windows命令删除文件夹
                try:
                    # 使用rd命令删除文件夹，确保路径格式正确
                    # 将正斜杠转换为反斜杠，Windows命令更喜欢反斜杠
                    windows_path = output_folder.replace('/', '\\')
                    result = subprocess.run(['cmd', '/c', 'rd', '/s', '/q', windows_path], 
                                           capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        signal_bus.log_message.emit("INFO", "已清理output文件夹", {})
                    else:
                        signal_bus.log_message.emit("ERROR", f"删除output文件夹失败: {result.stderr}", {})
                        raise PermissionError(f"无法删除output文件夹")
                except Exception as e:
                    signal_bus.log_message.emit("ERROR", f"删除output文件夹失败: {str(e)}", {})
                    raise
            
            # 收集所有要翻译的文件到项目文件夹
            signal_bus.log_message.emit("INFO", "收集所有mod文件夹中的翻译文件...", {})
            
            # 按顺序收集每个mod文件夹的文件
            for i, (en_path, zh_path) in enumerate(zip(en_paths, zh_paths)):
                mod_name = Path(en_path).name
                signal_bus.log_message.emit("INFO", f"收集mod {i+1}/{len(en_paths)}: {mod_name} 的翻译文件", {})
                signal_bus.log_message.emit("DEBUG", f"mod_name实际值: '{mod_name}'", {})
                
                # 收集英文文件
                self._collect_translation_files(
                    os.path.join(en_path, 'i18n'),
                    en_folder,
                    mod_name
                )
                
                # 收集中文文件
                if os.path.exists(os.path.join(zh_path, 'i18n')):
                    self._collect_chinese_files(
                        os.path.join(zh_path, 'i18n'),
                        zh_folder,
                        mod_name
                    )
            
            # 先收集所有需要翻译的内容
            all_translation_data = {}
            manifest_data = {}
            config_data = {}
            
            # 处理每个mod文件夹，收集翻译内容
            for i, (en_path, zh_path) in enumerate(zip(en_paths, zh_paths)):
                if not self._is_running:
                    break
                    
                mod_name = Path(en_path).name
                signal_bus.log_message.emit("INFO", f"收集mod {i+1}/{len(en_paths)}: {mod_name} 的翻译内容", {})
                signal_bus.log_message.emit("DEBUG", f"en_path: {en_path}", {})
                signal_bus.log_message.emit("DEBUG", f"zh_path: {zh_path}", {})
                
                # 1. 收集i18n文件（已在前面完成）
                
                # 2. 收集manifest文件
                en_manifest = os.path.join(en_path, 'manifest.json')
                zh_manifest = os.path.join(zh_path, 'manifest.json')
                
                if os.path.exists(en_manifest):
                    manifest_content = self._extract_manifest_fields(en_manifest)
                    if manifest_content:
                        # 保存到en文件夹，键名添加前缀
                        en_content_with_prefix = {}
                        for key, value in manifest_content.items():
                            en_content_with_prefix[f"{mod_name}_{key}"] = value
                        
                        en_file = os.path.join(en_folder, f"{mod_name}_manifest.json")
                        file_tool.save_json_file(en_content_with_prefix, en_file)
                        
                        # 如果有中文版本，也保存到zh文件夹
                        if os.path.exists(zh_manifest):
                            zh_manifest_data = file_tool.read_json_file(zh_manifest)
                            zh_content = {}
                            for key in manifest_content.keys():
                                if key in zh_manifest_data and zh_manifest_data[key]:
                                    zh_content[f"{mod_name}_{key}"] = zh_manifest_data[key]
                            
                            if zh_content:
                                zh_file = os.path.join(zh_folder, f"{mod_name}_manifest.json")
                                file_tool.save_json_file(zh_content, zh_file)
                                signal_bus.log_message.emit("INFO", f"保存中文manifest文件: {zh_file}，包含 {len(zh_content)} 项", {})
                        
                        # 添加到翻译数据
                        for key, value in manifest_content.items():
                            # 使用与翻译引擎输出一致的键名格式
                            unique_key = f"{mod_name}_{key}"
                            all_translation_data[unique_key] = value
                            manifest_data[unique_key] = {
                                'mod_name': mod_name,
                                'key': key,  # 保存原始键名
                                'en_path': en_manifest,
                                'zh_path': zh_manifest if os.path.exists(zh_manifest) else None
                            }
                
                # 3. 收集content文件（与单多文件夹无关，只看i18n结构）
                en_content = os.path.join(en_path, 'content.json')
                signal_bus.log_message.emit("DEBUG", f"检查content.json: {en_content}", {})
                if os.path.exists(en_content):
                    signal_bus.log_message.emit("DEBUG", f"找到content.json文件，开始提取字段", {})
                    config_content = self._extract_config_fields(file_tool.read_json_file(en_content))
                    signal_bus.log_message.emit("DEBUG", f"提取到 {len(config_content)} 个配置字段", {})
                    if config_content:
                        # 保存到en文件夹，键名添加前缀
                        en_content_with_prefix = {}
                        for key, value in config_content.items():
                            en_content_with_prefix[f"{mod_name}_{key}"] = value
                        
                        en_file = os.path.join(en_folder, f"{mod_name}_content.json")
                        file_tool.save_json_file(en_content_with_prefix, en_file)
                        
                        # 添加到翻译数据
                        for key, value in config_content.items():
                            # 使用与翻译引擎输出一致的键名格式
                            unique_key = f"{mod_name}_{key}"
                            all_translation_data[unique_key] = value
                            config_data[unique_key] = {
                                'mod_name': mod_name,
                                'key': key,  # 保存原始键名
                                'en_path': en_content
                            }
            
            # 执行一次统一的翻译
            if all_translation_data:
                signal_bus.log_message.emit("INFO", "开始统一翻译所有内容...", {})
                
                # 保存到临时文件
                temp_file = os.path.join(self.project_manager.get_folder_path('output'), 'temp_translation.json')
                file_tool.save_json_file(all_translation_data, temp_file)
                
                # 准备翻译参数
                params = {
                    '原始文件夹': en_folder,
                    '输出文件夹': self.project_manager.get_folder_path('output'),
                    '项目路径': self.project_manager.current_project.path
                }
                
                # 如果zh文件夹有文件，添加为中文文件夹
                if os.path.exists(zh_folder):
                    zh_files = [f for f in os.listdir(zh_folder) if f.endswith('.json')]
                    signal_bus.log_message.emit("INFO", f"zh文件夹中有 {len(zh_files)} 个文件: {zh_files}", {})
                    if zh_files:
                        params['中文文件夹'] = zh_folder
                
                # 执行智能翻译
                result = self.translation_executor._execute_smart_translation(params)
                
                if result.get('成功'):
                    # 收集翻译结果
                    translated_data = {}
                    output_folder_path = self.project_manager.get_folder_path('output')
                    
                    # 读取所有翻译结果文件
                    for filename in os.listdir(output_folder_path):
                        if filename.endswith('.json') and filename != 'temp_translation.json':
                            file_path = os.path.join(output_folder_path, filename)
                            file_data = file_tool.read_json_file(file_path)
                            translated_data.update(file_data)
                            signal_bus.log_message.emit("INFO", f"读取翻译文件 {filename}，包含 {len(file_data)} 项", {})
                    
                    signal_bus.log_message.emit("INFO", f"总共收集到 {len(translated_data)} 项翻译结果", {})
                    
                    
                    # 处理每个mod文件夹的输出
                    for i, (en_path, zh_path) in enumerate(zip(en_paths, zh_paths)):
                        if not self._is_running:
                            break
                            
                        mod_name = Path(en_path).name
                        signal_bus.log_message.emit("INFO", f"处理mod {i+1}/{len(en_paths)}: {mod_name} 的输出", {})
                        
                        # 创建该mod在项目output文件夹中的目录
                        mod_output_dir = os.path.join(output_folder_path, mod_name)
                        os.makedirs(mod_output_dir, exist_ok=True)
                        
                        # 复制整个英文mod文件夹到输出目录
                        signal_bus.log_message.emit("INFO", f"复制英文mod文件夹到输出目录...", {})
                        if os.path.exists(mod_output_dir):
                            shutil.rmtree(mod_output_dir)
                        shutil.copytree(en_path, mod_output_dir)
                        
                        # 处理i18n翻译（从output文件夹中读取已翻译的文件）
                        mod_i18n_dir = os.path.join(mod_output_dir, 'i18n')
                        os.makedirs(mod_i18n_dir, exist_ok=True)
                        
                        # 复制翻译好的i18n文件
                        for filename in os.listdir(output_folder_path):
                            if filename.startswith(mod_name) and filename.endswith('.json'):
                                src_file = os.path.join(output_folder_path, filename)
                                dst_file = os.path.join(mod_i18n_dir, filename)
                                shutil.copy2(src_file, dst_file)
                        
                        # 重命名翻译结果文件，移除mod名称前缀
                        en_i18n_folder = os.path.join(en_path, 'i18n')
                        self._rename_translated_files(mod_i18n_dir, mod_name, en_i18n_folder)
                        
                        # 删除不需要的content.json文件
                        content_file = os.path.join(mod_i18n_dir, 'content.json')
                        if os.path.exists(content_file):
                            os.remove(content_file)
                        
                        # 回填manifest翻译
                        self._backfill_manifest_translation(manifest_data, translated_data, mod_name, mod_output_dir)
                        
                        # 回填config翻译
                        self._backfill_config_translation(config_data, translated_data, mod_name, mod_output_dir)
                        
                        # 复制其他文件
                        self._copy_other_files(en_path, zh_path, mod_output_dir)
                    
                    # 步骤6: 质量检查将在翻译进度窗口关闭后通过信号触发
                    
                    # 清理临时文件（保留质量检查文件）
                    self._cleanup_temp_files(output_folder_path)
                    
                    # 不清理output文件夹，因为质量检查文件可能还在其中
                    signal_bus.log_message.emit("DEBUG", "跳过清理output文件夹，保留质量检查文件", {})
                else:
                    signal_bus.log_message.emit("ERROR", f"统一翻译失败: {result.get('消息', '未知错误')}", {})
            
            return {
                '成功': True,
                '消息': f'一键更新完成，共处理 {len(en_paths)} 个mod',
                '输出目录': output_folder
            }
            
        except Exception as e:
            error_msg = f"翻译处理失败: {str(e)}"
            signal_bus.log_message.emit("ERROR", error_msg, {})
            return {'成功': False, '消息': error_msg}
    
    def _collect_translation_files(self, source_i18n: str, dest_en_folder: str, mod_name: str):
        """收集要翻译的文件（default.json或Default文件夹中的文件）到项目en文件夹"""
        if not os.path.exists(source_i18n):
            return
        
        os.makedirs(dest_en_folder, exist_ok=True)
        
        # 检查i18n文件夹的结构
        has_subdirs = False
        default_folder = None
        
        for item in os.listdir(source_i18n):
            item_path = os.path.join(source_i18n, item)
            if os.path.isdir(item_path):
                has_subdirs = True
                # 查找default文件夹（忽略大小写）
                if item.lower() == 'default':
                    default_folder = item_path
        
        if has_subdirs and default_folder:
            # 有子文件夹的情况：复制Default文件夹中的所有JSON文件
            for root, dirs, files in os.walk(default_folder):
                for file in files:
                    if file.lower().endswith('.json'):
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, default_folder)
                        # 添加mod名称前缀避免冲突
                        dest_file = os.path.join(dest_en_folder, f"{mod_name}_{rel_path}")
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        shutil.copy2(src_file, dest_file)
        else:
            # 只有文件的情况：只复制default.json
            default_file = os.path.join(source_i18n, 'default.json')
            if os.path.exists(default_file):
                dest_file = os.path.join(dest_en_folder, f"{mod_name}_default.json")
                shutil.copy2(default_file, dest_file)
    
    def _collect_chinese_files(self, source_i18n: str, dest_zh_folder: str, mod_name: str):
        """收集中文文件（zh.json或ZH文件夹中的文件）到项目zh文件夹"""
        if not os.path.exists(source_i18n):
            return
        
        os.makedirs(dest_zh_folder, exist_ok=True)
        
        # 检查i18n文件夹的结构
        has_subdirs = False
        zh_folder = None
        
        for item in os.listdir(source_i18n):
            item_path = os.path.join(source_i18n, item)
            if os.path.isdir(item_path):
                has_subdirs = True
                # 查找zh文件夹（忽略大小写）
                if item.lower() in ['zh', 'chinese']:
                    zh_folder = item_path
        
        if has_subdirs and zh_folder:
            # 有子文件夹的情况：复制ZH文件夹中的所有JSON文件
            for root, dirs, files in os.walk(zh_folder):
                for file in files:
                    if file.lower().endswith('.json'):
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, zh_folder)
                        
                        # 确定目标文件名
                        if rel_path.lower() == 'zh.json':
                            # zh.json对应default.json，所以改为mod_name_default.json
                            dest_file = os.path.join(dest_zh_folder, f"{mod_name}_default.json")
                        else:
                            # 其他文件保持原名，但添加前缀
                            dest_file = os.path.join(dest_zh_folder, f"{mod_name}_{rel_path}")
                        
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        shutil.copy2(src_file, dest_file)
        else:
            # 只有文件的情况：查找所有中文文件
            # 首先查找标准的zh.json等文件
            chinese_files = ['zh.json', 'chinese.json', 'zh-CN.json']
            found_zh_file = False
            for file_name in chinese_files:
                file_path = os.path.join(source_i18n, file_name)
                if os.path.exists(file_path):
                    # zh.json对应default.json，所以改为mod_name_default.json
                    dest_file = os.path.join(dest_zh_folder, f"{mod_name}_default.json")
                    shutil.copy2(file_path, dest_file)
                    found_zh_file = True
                    break
            
            # 查找其他可能的中文文件（如mod_zh.json等）
            for file_name in os.listdir(source_i18n):
                if file_name.endswith('.json') and file_name not in chinese_files:
                    # 检查是否可能是中文文件（包含zh、chinese等关键词）
                    if 'zh' in file_name.lower() or 'chinese' in file_name.lower() or 'cn' in file_name.lower():
                        file_path = os.path.join(source_i18n, file_name)
                        dest_file = os.path.join(dest_zh_folder, f"{mod_name}_{file_name}")
                        shutil.copy2(file_path, dest_file)
                        signal_bus.log_message.emit("DEBUG", f"复制中文文件: {file_name} -> {os.path.basename(dest_file)}", {})

    def _extract_manifest_fields(self, manifest_path: str) -> Dict[str, str]:
        """从manifest.json提取需要翻译的字段"""
        try:
            manifest_data = file_tool.read_json_file(manifest_path)
            translation_data = {}
            
            # 提取Name字段
            if 'Name' in manifest_data and manifest_data['Name']:
                translation_data['Name'] = str(manifest_data['Name'])
            
            # 提取Description字段
            if 'Description' in manifest_data and manifest_data['Description']:
                translation_data['Description'] = str(manifest_data['Description'])
            
            return translation_data
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"提取manifest字段失败: {str(e)}", {})
            return {}
    
    def _backfill_manifest_translation(self, manifest_data: Dict, translated_data: Dict, mod_name: str, output_dir: str):
        """将翻译结果回填到manifest.json"""
        try:
            manifest_path = os.path.join(output_dir, 'manifest.json')
            signal_bus.log_message.emit("DEBUG", f"准备回填manifest: {manifest_path}", {})
            
            if not os.path.exists(manifest_path):
                signal_bus.log_message.emit("WARNING", f"manifest文件不存在: {manifest_path}", {})
                return
            
            # 读取现有的manifest
            manifest = file_tool.read_json_file(manifest_path)
            signal_bus.log_message.emit("DEBUG", f"读取manifest成功，包含字段: {list(manifest.keys()) if isinstance(manifest, dict) else '非字典格式'}", {})
            
            # 查找属于当前mod的翻译
            updated = False
            updated_fields = []
            
            for key, info in manifest_data.items():
                if info['mod_name'] == mod_name:
                    field_name = info['key']
                    signal_bus.log_message.emit("DEBUG", f"处理字段: {field_name}, key={key}", {})
                    
                    if field_name in ['Name', 'Description']:
                        if key in translated_data:
                            # 检查翻译结果是否是中文
                            translated_value = translated_data[key]
                            old_value = manifest.get(field_name, '')
                            manifest[field_name] = translated_value
                            updated = True
                            updated_fields.append(f"{field_name}: '{old_value}' -> '{translated_value}'")
                            signal_bus.log_message.emit("DEBUG", f"更新字段 {field_name}: {old_value} -> {translated_value}", {})
                        else:
                            signal_bus.log_message.emit("WARNING", f"未找到翻译结果: key={key}", {})
            
            # 如果有更新，保存文件
            if updated:
                file_tool.save_json_file(manifest, manifest_path)
                signal_bus.log_message.emit("SUCCESS", f"manifest翻译回填完成: {mod_name}, 更新字段: {', '.join(updated_fields)}", {})
            else:
                signal_bus.log_message.emit("DEBUG", f"manifest没有需要更新的字段: {mod_name}", {})
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"回填manifest翻译失败: {str(e)}", {})
    
    def _backfill_config_translation(self, config_data: Dict, translated_data: Dict, mod_name: str, output_dir: str):
        """将配置菜单翻译结果保存到zh.json或新文件"""
        try:
            i18n_folder = os.path.join(output_dir, 'i18n')
            zh_file = os.path.join(i18n_folder, 'zh.json')
            
            signal_bus.log_message.emit("DEBUG", f"准备处理配置菜单翻译: {mod_name}", {})
            signal_bus.log_message.emit("DEBUG", f"config_data中有 {len(config_data)} 项", {})
            signal_bus.log_message.emit("DEBUG", f"translated_data中有 {len(translated_data)} 项", {})
            
            # 收集属于当前mod的翻译结果
            mod_translations = {}
            for key, info in config_data.items():
                if info['mod_name'] == mod_name and key in translated_data:
                    # 获取原始键名
                    original_key = info['key']
                    mod_translations[original_key] = translated_data[key]
                    signal_bus.log_message.emit("DEBUG", f"配置菜单翻译: {original_key} = {translated_data[key]}", {})
            
            signal_bus.log_message.emit("DEBUG", f"找到 {len(mod_translations)} 项配置菜单翻译", {})
            
            if not mod_translations:
                signal_bus.log_message.emit("DEBUG", f"没有找到 {mod_name} 的配置菜单翻译", {})
                return
            
            # 根据i18n结构决定保存方式
            if os.path.exists(os.path.join(i18n_folder, 'Default')):
                # 文件夹形式：保存为配置菜单翻译.json
                config_file = os.path.join(i18n_folder, '配置菜单翻译.json')
                self._save_config_translation(mod_translations, config_file, is_new_file=True)
                signal_bus.log_message.emit("SUCCESS", f"配置菜单翻译完成：{len(mod_translations)} 项，保存到配置菜单翻译.json", {})
            else:
                # 文件形式：使用已有的追加逻辑
                if os.path.exists(zh_file):
                    self._save_config_translation(mod_translations, zh_file, is_new_file=False)
                    signal_bus.log_message.emit("SUCCESS", f"配置菜单翻译完成：{len(mod_translations)} 项，追加到zh.json", {})
                else:
                    # zh.json不存在，创建新文件
                    self._save_config_translation(mod_translations, zh_file, is_new_file=True)
                    signal_bus.log_message.emit("SUCCESS", f"配置菜单翻译完成：{len(mod_translations)} 项，创建zh.json", {})
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"保存配置菜单翻译失败: {str(e)}", {})
    
    def _perform_quality_check(self, output_folder: str):
        """执行质量检查"""
        try:
            signal_bus.log_message.emit("INFO", "开始质量检查...", {})
            signal_bus.log_message.emit("DEBUG", f"output_folder参数: {output_folder}", {})
            
            # 获取项目的en文件夹路径
            en_folder = self.project_manager.get_folder_path('en')
            # 使用传入的output_folder参数，而不是重新获取
            output_folder_path = output_folder
            
            # 先收集en文件夹中的英文文件（不包括xxx_content.json和xxx_manifest.json）
            merged_en_data = {}
            merged_zh_data = {}
            mod_mapping = {}  # 记录键名到mod和文件的映射
            mod_name_mapping = {}  # 记录英文文件名到mod文件夹名的映射
            
            # 先收集output文件夹中所有的mod文件夹名称
            all_mod_names = set()
            if os.path.exists(output_folder_path):
                for item in os.listdir(output_folder_path):
                    mod_path = os.path.join(output_folder_path, item)
                    if os.path.isdir(mod_path):
                        all_mod_names.add(item)
            
            # 1. 收集项目的en文件夹中的英文文件（不包括xxx_content.json和xxx_manifest.json）
            if os.path.exists(en_folder):
                en_files = [f for f in os.listdir(en_folder) if f.endswith('.json') and not f.endswith('_content.json') and not f.endswith('_manifest.json')]
                signal_bus.log_message.emit("INFO", f"en文件夹中找到 {len(en_files)} 个英文文件", {})
                
                for filename in en_files:
                    file_path = os.path.join(en_folder, filename)
                    try:
                        file_data = file_tool.read_json_file(file_path)
                        signal_bus.log_message.emit("DEBUG", f"读取英文文件 {filename} 成功，包含 {len(file_data)} 项", {})
                        
                        # 生成唯一的键名
                        import hashlib
                        for key, value in file_data.items():
                            # 从文件名提取mod文件夹名（去除前缀和后缀）
                            mod_name = filename
                            # 如果文件名有下划线前缀，去除前缀
                            if '_' in filename:
                                parts = filename.split('_')
                                if len(parts) > 1:
                                    mod_name = parts[0]
                            
                            # 检查提取的mod_name是否在output文件夹的mod列表中
                            actual_mod_name = mod_name
                            if mod_name not in all_mod_names:
                                # 如果不在，尝试找到匹配的mod名称（去除某些后缀等）
                                for mod in all_mod_names:
                                    if mod.lower().startswith(mod_name.lower()) or mod_name.lower().startswith(mod.lower()):
                                        actual_mod_name = mod
                                        break
                            
                            # 使用实际的mod文件夹名_键名的哈希值
                            hash_input = f"{actual_mod_name}_{key}"
                            unique_key = hashlib.md5(hash_input.encode()).hexdigest()
                            
                            merged_en_data[unique_key] = value
                            mod_mapping[unique_key] = {
                                'mod_name': actual_mod_name,
                                'filename': filename,
                                'original_key': key
                            }
                    except Exception as e:
                        signal_bus.log_message.emit("ERROR", f"读取英文文件 {filename} 失败: {str(e)}", {})
                        continue

            
            # 保留en文件夹内容，不再清空
            # 注释：用户需要保留en文件夹的内容用于后续查看
            # if os.path.exists(en_folder):
            #     shutil.rmtree(en_folder)
            # os.makedirs(en_folder, exist_ok=True)
            
            # 确保output文件夹存在
            os.makedirs(output_folder_path, exist_ok=True)
            
            # 保存到项目文件夹
            en_file = os.path.join(en_folder, '质量检查.json')
            zh_file = os.path.join(output_folder_path, '质量检查.json')
            
            # 输出完整路径用于调试
            signal_bus.log_message.emit("DEBUG", f"英文文件完整路径: {os.path.abspath(en_file)}", {})
            signal_bus.log_message.emit("DEBUG", f"中文文件完整路径: {os.path.abspath(zh_file)}", {})
            signal_bus.log_message.emit("DEBUG", f"output文件夹路径: {os.path.abspath(output_folder_path)}", {})
            
            # 2. 收集output各个mod文件夹中的中文文件
            if os.path.exists(output_folder_path):
                mod_folders = [item for item in os.listdir(output_folder_path) if os.path.isdir(os.path.join(output_folder_path, item))]
                signal_bus.log_message.emit("INFO", f"output文件夹中有 {len(mod_folders)} 个mod文件夹: {mod_folders}", {})
                
                for item in mod_folders:
                    mod_path = os.path.join(output_folder_path, item)
                    # 查找mod文件夹中的i18n文件夹
                    i18n_path = os.path.join(mod_path, 'i18n')
                    
                    if not os.path.exists(i18n_path):
                        signal_bus.log_message.emit("DEBUG", f"mod {item} 没有i18n文件夹", {})
                        continue
                    
                    signal_bus.log_message.emit("DEBUG", f"检查mod {item} 的i18n文件夹", {})
                    
                    # 检查是否有zh.json文件
                    zh_file_path = os.path.join(i18n_path, 'zh.json')
                    signal_bus.log_message.emit("DEBUG", f"检查zh.json是否存在: {zh_file_path}", {})
                    if os.path.exists(zh_file_path):
                        signal_bus.log_message.emit("INFO", f"找到zh.json文件: {zh_file_path}", {})
                        # 处理zh.json文件
                        try:
                            zh_data = file_tool.read_json_file(zh_file_path)
                            signal_bus.log_message.emit("DEBUG", f"zh.json包含 {len(zh_data)} 项", {})
                        except Exception as e:
                            signal_bus.log_message.emit("ERROR", f"读取zh.json失败: {str(e)}", {})
                            continue
                        for key, value in zh_data.items():
                            # 使用mod文件夹名_键名的哈希值
                            import hashlib
                            hash_input = f"{item}_{key}"
                            unique_key = hashlib.md5(hash_input.encode()).hexdigest()

                            merged_zh_data[unique_key] = value
                            mod_mapping[unique_key] = {
                                'mod_name': item,
                                'filename': 'zh.json',
                                'original_key': key
                            }
                    else:
                        # 检查是否有zh文件夹（不区分大小写）
                        zh_folder = None
                        for subitem in os.listdir(i18n_path):
                            subitem_path = os.path.join(i18n_path, subitem)
                            if os.path.isdir(subitem_path) and subitem.lower() == 'zh':
                                zh_folder = subitem_path
                                break

                        if zh_folder:
                            # 处理zh文件夹中的所有json文件
                            for filename in os.listdir(zh_folder):
                                if not filename.endswith('.json'):
                                    continue
                                file_path = os.path.join(zh_folder, filename)
                                try:
                                    file_data = file_tool.read_json_file(file_path)
                                except Exception as e:
                                    signal_bus.log_message.emit("ERROR", f"读取文件 {filename} 失败: {str(e)}", {})
                                    continue

                                for key, value in file_data.items():
                                    # 使用mod文件夹名_键名的哈希值
                                    import hashlib
                                    hash_input = f"{item}_{key}"
                                    unique_key = hashlib.md5(hash_input.encode()).hexdigest()

                                    merged_zh_data[unique_key] = value
                                    mod_mapping[unique_key] = {
                                        'mod_name': item,
                                        'filename': f"zh/{filename}",
                                        'original_key': key
                                    }
                        else:
                            signal_bus.log_message.emit("DEBUG", f"mod {item} 没有zh.json或zh文件夹", {})
            
            if not merged_zh_data:
                signal_bus.log_message.emit("WARNING", "没有找到翻译文件，跳过质量检查", {})
                return
            
            # 保存合并后的文件到项目文件夹
            # 确保文件夹存在
            os.makedirs(en_folder, exist_ok=True)
            os.makedirs(output_folder_path, exist_ok=True)
            
            # 检查是否收集到数据
            signal_bus.log_message.emit("INFO", f"收集到 {len(merged_en_data)} 项英文数据，{len(merged_zh_data)} 项中文数据", {})
            
            if not merged_en_data and not merged_zh_data:
                signal_bus.log_message.emit("WARNING", "没有收集到任何数据，跳过质量检查", {})
                return
            
            # 使用file_tool保存文件，同时保存mod_mapping信息
            try:
                signal_bus.log_message.emit("DEBUG", f"准备保存英文文件到: {en_file}", {})
                # 将mod_mapping信息也保存到文件中
                file_data = {
                    'data': merged_en_data,
                    'mod_mapping': mod_mapping
                }
                file_tool.save_json_file(file_data, en_file)
                signal_bus.log_message.emit("INFO", f"保存英文合并文件成功: {en_file}，包含 {len(merged_en_data)} 项", {})
                # 立即验证
                if os.path.exists(en_file):
                    signal_bus.log_message.emit("DEBUG", f"验证英文文件存在", {})
                else:
                    signal_bus.log_message.emit("ERROR", f"英文文件保存后不存在!", {})
            except Exception as e:
                signal_bus.log_message.emit("ERROR", f"保存英文合并文件失败: {str(e)}", {})
                return
            
            try:
                signal_bus.log_message.emit("DEBUG", f"准备保存中文文件到: {zh_file}", {})
                # 将mod_mapping信息也保存到文件中
                file_data = {
                    'data': merged_zh_data,
                    'mod_mapping': mod_mapping
                }
                file_tool.save_json_file(file_data, zh_file)
                signal_bus.log_message.emit("INFO", f"保存中文合并文件成功: {zh_file}，包含 {len(merged_zh_data)} 项", {})
                
                # 立即验证文件是否真的存在
                if os.path.exists(zh_file):
                    file_size = os.path.getsize(zh_file)
                    signal_bus.log_message.emit("DEBUG", f"验证中文文件存在，大小: {file_size} 字节", {})
                else:
                    signal_bus.log_message.emit("ERROR", f"中文文件保存后不存在: {zh_file}!", {})
                    return
                    
                # 列出output文件夹的所有内容
                try:
                    output_files = os.listdir(output_folder_path)
                    signal_bus.log_message.emit("DEBUG", f"output文件夹内容: {output_files}", {})
                except Exception as e:
                    signal_bus.log_message.emit("ERROR", f"列出output文件夹内容失败: {str(e)}", {})
            except Exception as e:
                signal_bus.log_message.emit("ERROR", f"保存中文合并文件失败: {str(e)}", {})
                return
            
            signal_bus.log_message.emit("INFO", f"合并了 {len(merged_en_data)} 项英文和 {len(merged_zh_data)} 项中文到质量检查文件", {})
            
            # 创建独立的质量检查窗口
            self._show_quality_check_dialog(en_file, zh_file, output_folder_path, mod_mapping)
            
            # 清理临时文件
            self._cleanup_temp_files(output_folder_path)
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"质量检查失败: {str(e)}", {})
    
    def _show_quality_check_dialog(self, en_file, zh_file, output_folder, mod_mapping):
        """显示独立的质量检查窗口"""
        try:
            signal_bus.log_message.emit("INFO", "准备显示质量检查窗口", {})
            
            # 将参数保存为实例变量，避免通过信号传递
            self._quality_check_en_file = str(en_file) if en_file else None
            self._quality_check_zh_file = str(zh_file) if zh_file else None
            self._quality_check_output_folder = str(output_folder) if output_folder else None
            self._quality_check_mod_mapping = mod_mapping
            
            # 使用QTimer延迟创建窗口，确保不在信号处理过程中创建
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._delayed_create_quality_check_window)
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"准备质量检查窗口失败: {str(e)}", {})

    def _delayed_create_quality_check_window(self):
        """延迟创建质量检查窗口"""
        try:
            self._create_quality_check_window()
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"准备质量检查窗口失败: {str(e)}", {})
    
    def _create_quality_check_window(self):
        """实际创建质量检查窗口"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QApplication, QWidget
            from ui.quality_check_widget import QualityCheckWidget
            from ui.widgets import BackgroundWidget
            from ui.custom_title_bar import CustomTitleBar
            
            # 创建对话框
            dialog = QDialog()
            dialog.setWindowTitle("质量检查 - 一键更新")
            dialog.setMinimumSize(800, 600)
            # 设置为非模态对话框
            dialog.setModal(False)
            # 设置无边框窗口
            dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            # 设置窗口透明以显示圆角
            dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            
            # 创建主布局（透明）
            main_layout = QVBoxLayout(dialog)
            main_layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建内容区域
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建带背景的中心widget
            # 获取主窗口的背景图片
            main_window = None
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'background_pixmap'):
                    main_window = widget
                    break
            
            # 创建背景widget
            background_widget = BackgroundWidget(
                main_window.background_pixmap if main_window else None, 
                config.theme
            )
            
            # 创建布局
            layout = QVBoxLayout(background_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # 添加自定义标题栏（在背景内）
            title_bar = CustomTitleBar(dialog, show_theme_toggle=False)
            layout.addWidget(title_bar)
            
            # 创建质量检查组件
            quality_widget = QualityCheckWidget()
            
            # 保存output文件夹路径到组件
            quality_widget.output_folder = self._quality_check_output_folder
            quality_widget.mod_mapping = self._quality_check_mod_mapping
            
            # 延迟启动质量检查，传递必要的参数
            from PySide6.QtCore import QTimer
            QTimer.singleShot(300, lambda: quality_widget.set_files_for_check(
                self._quality_check_en_file, 
                self._quality_check_zh_file
            ))
            
            # 添加到布局
            layout.addWidget(quality_widget)
            
            # 将背景widget添加到内容区域
            content_layout.addWidget(background_widget)
            
            # 将内容区域添加到主布局
            main_layout.addWidget(content_widget)
            
            # 保存回调参数
            self._current_quality_widget = quality_widget
            # 保存对话框引用，防止被垃圾回收
            self._quality_check_dialog = dialog
            
            # 连接信号
            quality_widget.check_completed.connect(self._on_quality_check_completed_wrapper)
            
            # 连接窗口关闭事件，清理引用
            dialog.finished.connect(self._on_quality_check_dialog_closed)
            
            # 应用主题样式
            from ui.styles import get_main_window_style
            dialog.setStyleSheet(get_main_window_style(config.theme))
            
            # 显示非模态对话框
            dialog.show()
            
            signal_bus.log_message.emit("SUCCESS", "质量检查窗口已显示", {})
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"显示质量检查窗口失败: {str(e)}", {})
    
    def _on_quality_check_dialog_closed(self):
        """质量检查对话框关闭时清理引用"""
        # 总是自动打开output文件夹
        if hasattr(self, '_quality_check_output_folder') and self._quality_check_output_folder:
            output_folder = self._quality_check_output_folder
            signal_bus.log_message.emit("INFO", f"自动打开output文件夹: {output_folder}", {})
            
            # 使用项目中已有的file_tool.open_folder方法
            if not file_tool.open_folder(output_folder):
                signal_bus.log_message.emit("ERROR", f"打开output文件夹失败", {})
        
        self._quality_check_dialog = None
        self._current_quality_widget = None
        signal_bus.log_message.emit("DEBUG", "质量检查窗口已关闭，引用已清理", {})
    
    def _on_quality_check_completed_wrapper(self, result):
        """质量检查完成的包装方法"""
        if hasattr(self, '_quality_check_output_folder') and hasattr(self, '_quality_check_mod_mapping'):
            self._on_quality_check_completed(result, self._quality_check_output_folder, self._quality_check_mod_mapping)
    
    def _cleanup_temp_files(self, output_folder_path):
        """清理临时文件"""
        try:
            import glob
            # 清理所有带下划线的json文件（除了质量检查.json）
            temp_files = glob.glob(os.path.join(output_folder_path, "*_*.json"))
            for temp_file in temp_files:
                try:
                    # 跳过质量检查文件
                    if os.path.basename(temp_file) != "质量检查.json":
                        os.remove(temp_file)
                        signal_bus.log_message.emit("DEBUG", f"清理临时文件: {os.path.basename(temp_file)}", {})
                except Exception as e:
                    signal_bus.log_message.emit("WARNING", f"清理文件失败: {temp_file}, 错误: {str(e)}", {})
            
            # 清理temp_translation.json
            temp_file = os.path.join(output_folder_path, "temp_translation.json")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    signal_bus.log_message.emit("DEBUG", f"清理临时文件: temp_translation.json", {})
                except Exception as e:
                    signal_bus.log_message.emit("WARNING", f"清理文件失败: {temp_file}, 错误: {str(e)}", {})
            
            signal_bus.log_message.emit("INFO", "临时文件清理完成", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"清理临时文件失败: {str(e)}", {})
    
    def _on_quality_check_completed(self, result, output_folder, mod_mapping):
        """质量检查完成后的回调"""
        try:
            if result.get('成功', False):
                signal_bus.log_message.emit("SUCCESS", f"质量检查完成: {result.get('消息', '')}", {})
                
                # 将编辑后的结果回填到各个mod文件夹
                self._backfill_quality_check_results(result.get('edited_file', ''), output_folder, mod_mapping)
            else:
                signal_bus.log_message.emit("WARNING", f"质量检查失败: {result.get('消息', '')}", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"处理质量检查结果失败: {str(e)}", {})
    
    def _backfill_quality_check_results(self, edited_file, output_folder, mod_mapping):
        """将质量检查编辑后的结果回填到各个mod文件夹"""
        try:
            signal_bus.log_message.emit("DEBUG", f"开始回填质量检查结果: {edited_file}", {})
            
            if not edited_file or not os.path.exists(edited_file):
                signal_bus.log_message.emit("WARNING", "编辑文件不存在，跳过回填", {})
                return
            
            # 读取编辑后的数据
            edited_data = file_tool.read_json_file(edited_file)
            signal_bus.log_message.emit("DEBUG", f"读取到 {len(edited_data)} 项编辑数据", {})
            
            # 按mod和文件分组
            mod_file_data = {}
            for key, value in edited_data.items():
                mapping = mod_mapping.get(key)
                if mapping:
                    mod_name = mapping['mod_name']
                    filename = mapping['filename']
                    original_key = mapping['original_key']
                    
                    if mod_name not in mod_file_data:
                        mod_file_data[mod_name] = {}
                    if filename not in mod_file_data[mod_name]:
                        mod_file_data[mod_name][filename] = {}
                    mod_file_data[mod_name][filename][original_key] = value
            
            # 回填到各个mod文件夹
            for mod_name, file_data in mod_file_data.items():
                mod_path = os.path.join(output_folder, mod_name)
                i18n_path = os.path.join(mod_path, 'i18n')
                
                for filename, data in file_data.items():
                    # 确定目标文件名
                    if filename == 'zh.json':
                        target_file = os.path.join(i18n_path, 'zh.json')
                    else:
                        target_file = os.path.join(i18n_path, filename)
                    
                    if os.path.exists(target_file):
                        file_tool.save_json_file(data, target_file)
                        signal_bus.log_message.emit("SUCCESS", f"回填质量检查结果: {mod_name}/{filename}, {len(data)} 项", {})
            
        # 注意：不清理文件，让质量检查组件自己处理
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"回填质量检查结果失败: {str(e)}", {})
    
    
    
    def trigger_quality_check(self):
        """触发质量检查"""
        try:
            signal_bus.log_message.emit("INFO", "trigger_quality_check被调用", {})
            
            # 检查是否已有质量检查窗口
            if hasattr(self, '_quality_check_dialog') and self._quality_check_dialog:
                # 更新现有窗口的质量检查
                signal_bus.log_message.emit("INFO", "质量检查窗口已存在，更新数据", {})
                self._update_existing_quality_check()
            else:
                # 创建新的质量检查窗口
                output_folder = self.project_manager.get_folder_path('output')
                signal_bus.log_message.emit("DEBUG", f"output_folder: {output_folder}", {})
                # 保存为实例变量，避免通过闭包传递
                self._quality_check_output_folder = output_folder
                # 使用QTimer延迟执行，避免在信号处理过程中直接创建窗口
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, self._delayed_perform_quality_check)
                signal_bus.log_message.emit("DEBUG", "已设置延迟执行质量检查", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"触发质量检查失败: {str(e)}", {})
    
    def _update_existing_quality_check(self):
        """更新现有的质量检查窗口 - 只更新表格中的问题项"""
        try:
            if not (hasattr(self, '_quality_check_dialog') and self._quality_check_dialog and 
                   hasattr(self, '_current_quality_widget') and self._current_quality_widget):
                signal_bus.log_message.emit("ERROR", "质量检查窗口引用无效", {})
                return
            
            # 获取质量检查窗口中显示的问题项
            quality_fixes = getattr(self._current_quality_widget, 'quality_fixes', {})
            
            if not quality_fixes:
                signal_bus.log_message.emit("WARNING", "质量检查窗口没有问题项", {})
                return
            
            signal_bus.log_message.emit("DEBUG", f"质量检查窗口有 {len(quality_fixes)} 个问题项", {})
            
            # 只针对表格中的问题项查找对应的翻译
            translation_results = {}
            output_folder = self.project_manager.get_folder_path('output')
            
            # 遍历每个问题项，查找其最新的翻译
            for key, fix_data in quality_fixes.items():
                # fix_data应该包含原始文件信息
                mod_name = fix_data.get('mod_name', '')
                filename = fix_data.get('filename', '')
                original_key = fix_data.get('original_key', '')
                
                if not mod_name or not original_key:
                    continue
                
                # 构建mod路径
                mod_path = os.path.join(output_folder, mod_name)
                i18n_path = os.path.join(mod_path, 'i18n')
                
                if not os.path.exists(i18n_path):
                    continue
                
                # 根据文件类型查找翻译
                if filename == 'zh.json':
                    zh_file_path = os.path.join(i18n_path, 'zh.json')
                    if os.path.exists(zh_file_path):
                        try:
                            zh_data = file_tool.read_json_file(zh_file_path)
                            if original_key in zh_data:
                                translation_results[key] = zh_data[original_key]
                        except Exception as e:
                            signal_bus.log_message.emit("ERROR", f"读取翻译文件失败: {str(e)}", {})
                elif filename.startswith('zh/'):
                    # ZH文件夹中的文件
                    zh_filename = filename[3:]  # 去掉 'zh/' 前缀
                    zh_folder = None
                    for subitem in os.listdir(i18n_path):
                        subitem_path = os.path.join(i18n_path, subitem)
                        if os.path.isdir(subitem_path) and subitem.lower() == 'zh':
                            zh_folder = subitem_path
                            break
                    
                    if zh_folder:
                        file_path = os.path.join(zh_folder, zh_filename)
                        if os.path.exists(file_path):
                            try:
                                file_data = file_tool.read_json_file(file_path)
                                if original_key in file_data:
                                    translation_results[key] = file_data[original_key]
                            except Exception as e:
                                signal_bus.log_message.emit("ERROR", f"读取翻译文件 {zh_filename} 失败: {str(e)}", {})
            
            # 更新质量检查窗口的新翻译列
            if translation_results:
                self._current_quality_widget.update_translations_from_result(translation_results)
                signal_bus.log_message.emit("INFO", f"更新了质量检查窗口的 {len(translation_results)} 项翻译", {})
            else:
                signal_bus.log_message.emit("WARNING", "没有找到对应的新翻译结果", {})
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"更新质量检查失败: {str(e)}", {})
    
    def _delayed_perform_quality_check(self):
        """延迟执行质量检查"""
        try:
            signal_bus.log_message.emit("DEBUG", "_delayed_perform_quality_check被调用", {})
            if hasattr(self, '_quality_check_output_folder'):
                signal_bus.log_message.emit("DEBUG", f"准备调用_perform_quality_check", {})
                self._perform_quality_check(self._quality_check_output_folder)
            else:
                signal_bus.log_message.emit("ERROR", "没有_quality_check_output_folder属性", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"延迟执行质量检查失败: {str(e)}", {})
    
    def _extract_config_fields(self, content_data: Dict) -> Dict[str, str]:
        """从content.json提取需要翻译的字段"""
        translation_data = {}
        
        if "ConfigSchema" in content_data:
            for field_name, field_data in content_data["ConfigSchema"].items():
                # Name字段
                if name := field_data.get("name"):
                    name_str = str(name)
                    translation_data[f"config.{field_name}.name"] = name_str
                
                # Description字段
                if desc := field_data.get("Description"):
                    desc_str = str(desc)
                    translation_data[f"config.{field_name}.description"] = desc_str
                
                # Section字段
                if section := field_data.get("Section"):
                    section_str = str(section)
                    translation_data[f"config.section.{field_name}.name"] = section_str
                
                # AllowValues字段
                if values := field_data.get("AllowValues"):
                    values_list = self._parse_allow_values(values)
                    for value in values_list:
                        if self._should_translate_value(value) and not self._is_i18n_format(str(value)):
                            translation_data[f"config.{field_name}.values.{value}"] = str(value)
        
        return translation_data
    
    @staticmethod
    def _is_i18n_format(text: str) -> bool:
        """检查文本是否是i18n格式"""
        text = str(text).strip()
        # 检查 {{i18n:...}} 格式
        if text.startswith("{{") and text.endswith("}}"):
            inner = text[2:-2].strip()
            if inner.startswith("i18n:"):
                return True
        return False
    
    @staticmethod
    def _parse_allow_values(allow_values) -> List[str]:
        """解析AllowValues"""
        if isinstance(allow_values, str):
            return [v.strip() for v in allow_values.split(",") if v.strip()]
        if isinstance(allow_values, list):
            return [str(v) for v in allow_values if v is not None]
        return []
    
    @staticmethod
    def _should_translate_value(value: str) -> bool:
        """判断值是否需要翻译"""
        value = str(value).strip()
        if not value:
            return False
        if value.lower() in ("true", "false"):
            return False
        if value.replace(".", "").isdigit():
            return False
        return True
    
    def _update_config_fields(self, content_data: Dict, translation_result: Dict):
        """将翻译结果更新到content.json"""
        if "ConfigSchema" not in content_data:
            return
        
        for field_name, field_data in content_data["ConfigSchema"].items():
            # 更新Name字段
            name_key = f"config.{field_name}.name"
            if name_key in translation_result:
                field_data["name"] = translation_result[name_key]
            
            # 更新Description字段
            desc_key = f"config.{field_name}.description"
            if desc_key in translation_result:
                field_data["Description"] = translation_result[desc_key]
            
            # 更新Section字段
            section_key = f"config.section.{field_name}.name"
            if section_key in translation_result:
                field_data["Section"] = translation_result[section_key]
            
            # 更新AllowValues字段
            if "AllowValues" in field_data and isinstance(field_data["AllowValues"], list):
                for i in range(len(field_data["AllowValues"])):
                    value_key = f"config.{field_name}.values.{i}"
                    if value_key in translation_result:
                        field_data["AllowValues"][i] = translation_result[value_key]
    
    def _rename_translated_files(self, i18n_folder: str, mod_name: str, en_i18n_folder: str = None):
        """重命名翻译结果文件，移除mod名称前缀"""
        if not os.path.exists(i18n_folder):
            return
        
        # 检查原始英文mod的i18n结构
        has_zh_structure = False
        if en_i18n_folder and os.path.exists(en_i18n_folder):
            # 检查是否有Default文件夹
            has_default_folder = False
            for item in os.listdir(en_i18n_folder):
                item_path = os.path.join(en_i18n_folder, item)
                if os.path.isdir(item_path) and item.lower() == 'default':
                    has_default_folder = True
                    break
            
            # 如果有Default文件夹，说明是文件夹结构，需要创建ZH文件夹
            if has_default_folder:
                has_zh_structure = True
                zh_folder = os.path.join(i18n_folder, 'ZH')
                os.makedirs(zh_folder, exist_ok=True)
        
        # 遍历文件夹中的所有文件
        for file_name in os.listdir(i18n_folder):
            if file_name.endswith('.json') and file_name.startswith(mod_name + '_'):
                # 移除mod名称前缀
                original_name = file_name[len(mod_name)+1:]
                
                # 确定新路径
                old_path = os.path.join(i18n_folder, file_name)
                
                if has_zh_structure:
                    # 文件夹结构：文件放在ZH文件夹中
                    if original_name.lower() == 'default.json':
                        new_path = os.path.join(zh_folder, 'zh.json')
                    else:
                        new_path = os.path.join(zh_folder, original_name)
                else:
                    # 文件结构：文件直接放在i18n文件夹中
                    if original_name.lower() == 'default.json':
                        new_path = os.path.join(i18n_folder, 'zh.json')
                    else:
                        new_path = os.path.join(i18n_folder, original_name)
                
                # 如果目标文件已存在，先删除它
                if os.path.exists(new_path):
                    os.remove(new_path)
                    signal_bus.log_message.emit("INFO", f"删除已存在的文件: {os.path.basename(new_path)}", {})
                
                # 重命名文件
                os.rename(old_path, new_path)
    
    def _save_config_translation(self, translation_data: Dict, output_file: str, is_new_file: bool):
        """保存配置菜单翻译结果"""
        
        if is_new_file:
            # 创建新文件
            content = "// 配置菜单翻译\n"
            content += json.dumps(translation_data, ensure_ascii=False, indent=2)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # 读取zh.json的原始数据
            zh_data = file_tool.read_json_file(output_file)
            
            # 去掉已存在的键
            filtered_data = {}
            for key, value in translation_data.items():
                if key not in zh_data:
                    filtered_data[key] = value
            
            if not filtered_data:
                signal_bus.log_message.emit("INFO", "配置菜单翻译结果已全部存在于zh.json中", {})
                return
            
            # 读取zh.json的原始文本内容
            with open(output_file, 'r', encoding='utf-8') as f:
                zh_content = f.read()
            
            # 构建要插入的键值对字符串
            lines = []
            lines.append("    // 配置菜单翻译")
            for key, value in filtered_data.items():
                lines.append(f'    "{key}": {json.dumps(value, ensure_ascii=False)}')
            lines.append("    // ============================")
            insert_content = ',\n'.join(lines) + ',\n'
            
            # 找到第一个键值对的位置（在{之后）
            zh_lines = zh_content.split('\n')
            insert_index = -1
            
            # 查找第一个 { 后的位置
            for i, line in enumerate(zh_lines):
                if '{' in line:
                    # 找到了{，在下一行插入
                    insert_index = i + 1
                    break
            
            if insert_index >= 0 and insert_index < len(zh_lines):
                # 在{后插入内容
                zh_lines.insert(insert_index, insert_content)
                
                # 写回文件
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(zh_lines))
                
                signal_bus.log_message.emit("SUCCESS", f"配置菜单翻译结果已追加到zh.json，共{len(filtered_data)}项", {})
            else:
                # 无法找到插入位置，直接追加
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.write('\n' + insert_content)
                
                signal_bus.log_message.emit("SUCCESS", f"配置菜单翻译结果已追加到zh.json，共{len(filtered_data)}项", {})
    
    def _copy_other_files(self, en_mod_path: str, zh_mod_path: str, output_dir: str):
        """复制其他文件（Portraits和config.json）"""
        try:
            # 清理i18n文件夹中不应该存在的文件
            mod_i18n_dir = os.path.join(output_dir, 'i18n')
            if os.path.exists(mod_i18n_dir):
                # 删除manifest.json
                manifest_file = os.path.join(mod_i18n_dir, 'manifest.json')
                if os.path.exists(manifest_file):
                    os.remove(manifest_file)
                    signal_bus.log_message.emit("DEBUG", f"清理i18n文件夹中的manifest.json", {})
                
                # 删除content.json
                content_file = os.path.join(mod_i18n_dir, 'content.json')
                if os.path.exists(content_file):
                    os.remove(content_file)
                    signal_bus.log_message.emit("DEBUG", f"清理i18n文件夹中的content.json", {})
                
                # 检查是否有ZH文件夹，也清理其中的manifest.json和content.json
                zh_dir = os.path.join(mod_i18n_dir, 'ZH')
                if os.path.exists(zh_dir):
                    zh_manifest = os.path.join(zh_dir, 'manifest.json')
                    if os.path.exists(zh_manifest):
                        os.remove(zh_manifest)
                        signal_bus.log_message.emit("DEBUG", f"清理ZH文件夹中的manifest.json", {})
                    
                    zh_content = os.path.join(zh_dir, 'content.json')
                    if os.path.exists(zh_content):
                        os.remove(zh_content)
                        signal_bus.log_message.emit("DEBUG", f"清理ZH文件夹中的content.json", {})
            
            # 复制Portraits文件夹
            zh_portraits = os.path.join(zh_mod_path, 'assets', 'Portraits')
            if os.path.exists(zh_portraits):
                en_portraits = os.path.join(output_dir, 'assets', 'Portraits')
                try:
                    shutil.rmtree(en_portraits)
                except (PermissionError, OSError):
                    signal_bus.log_message.emit("DEBUG", "删除Portraits文件夹失败，可能不存在", {})
                shutil.copytree(zh_portraits, en_portraits, dirs_exist_ok=True)
                signal_bus.log_message.emit("SUCCESS", "Portraits文件夹复制完成", {})
            
            # 复制config.json文件
            zh_config = os.path.join(zh_mod_path, 'config.json')
            if os.path.exists(zh_config):
                en_config = os.path.join(output_dir, 'config.json')
                shutil.copy2(zh_config, en_config)
                signal_bus.log_message.emit("SUCCESS", "config.json文件复制完成", {})
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"复制其他文件失败: {str(e)}", {})
    
    
    
    def _validate_folder_names(self, en_paths: List[str], zh_paths: List[str]) -> bool:
        """验证多文件夹模式下的文件夹名称是否匹配"""
        en_names = [Path(p).name for p in en_paths]
        zh_names = [Path(p).name for p in zh_paths]
        
        # 简单的名称匹配验证（可以根据需要扩展）
        if len(en_names) != len(zh_names):
            return False
        
        # 检查每个英文名称是否有对应的中文版本
        for en_name in en_names:
            # 移除常见的语言标识符
            en_base = en_name.lower().replace('[en]', '').replace('[english]', '').strip()
            
            found = False
            for zh_name in zh_names:
                zh_base = zh_name.lower().replace('[zh]', '').replace('[chinese]', '').strip()
                if en_base == zh_base:
                    found = True
                    break
            
            if not found:
                signal_bus.log_message.emit("WARNING", f"未找到与 '{en_name}' 对应的中文文件夹", {})
                return False
        
        return True