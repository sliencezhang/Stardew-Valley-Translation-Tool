# core/translation_executor.py
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import traceback
from PySide6.QtWidgets import QApplication

from core.signal_bus import signal_bus
from core.translation_engine import TranslationEngine
from core.translation_cache import TranslationCache
from core.file_tool import file_tool


class TranslationExecutor:
    """统一的翻译执行器 - 处理增量翻译、缓存和进度跟踪"""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.engine = TranslationEngine()
        # 只有在有项目时才创建缓存
        self.cache = TranslationCache(project_manager) if project_manager and project_manager.current_project else None
        self.current_context = ""
        self.task_name = ""
        self._is_running = True
        
    def stop(self):
        """停止所有翻译任务"""
        self._is_running = False
    
    def _batch_translate_texts(self, texts: List[str], keys: List[str], source_file: str, 
                              use_cache: bool = True) -> Tuple[Dict[str, str], Dict[str, str]]:
        """批量翻译文本并返回翻译结果和缓存更新"""
        if not texts or not self._is_running:
            return {}, {}
        
        batch_size = self.engine.batch_size
        translations = {}
        cache_updates = {}
        
        signal_bus.log_message.emit("INFO", f"批量翻译: {len(texts)} 个文本，批次大小: {batch_size}", {})
        
        for i in range(0, len(texts), batch_size):
            if not self._is_running:
                break
                
            batch_texts = texts[i:i + batch_size]
            batch_keys = keys[i:i + batch_size]
            
            current_batch = i // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size
            remaining_batches = total_batches - current_batch
            signal_bus.log_message.emit("INFO", "=" * 70, {})
            signal_bus.log_message.emit("INFO", f"翻译批次 {current_batch}/{total_batches}: {len(batch_texts)} 个文本 (剩余{remaining_batches}批次)", {})
            
            try:
                batch_translations = self.engine.translate_texts(batch_texts)
                batch_cache_updates = {}
                
                for j, (key, original_text) in enumerate(zip(batch_keys, batch_texts)):
                    if j < len(batch_translations) and batch_translations[j].strip():
                        translated_value = batch_translations[j]
                        translations[key] = translated_value
                        signal_bus.translation_item_updated.emit(source_file, key, translated_value, "成功", original_text)
                        
                        if use_cache:
                            batch_cache_updates[original_text] = translated_value
                    else:
                        translations[key] = original_text
                        signal_bus.translation_item_updated.emit(source_file, key, original_text, "失败", original_text)
                
                # 批量更新缓存
                if use_cache and self.cache and batch_cache_updates:
                    original_texts = list(batch_cache_updates.keys())
                    translated_texts = list(batch_cache_updates.values())
                    self.cache.batch_set_cached(original_texts, translated_texts)
                    
            except Exception as e:
                signal_bus.log_message.emit("ERROR", f"批次翻译失败: {e}", {})
                traceback.print_exc()
                # 批次失败时，使用原文
                for key, original_text in zip(batch_keys, batch_texts):
                    translations[key] = original_text
                    signal_bus.translation_item_updated.emit(source_file, key, original_text, "失败", original_text)
        
        return translations, cache_updates
    
    def _save_output_file(self, data: Dict, output_file: str, original_path: str = None) -> bool:
        """保存输出文件"""
        if not output_file or not output_file.strip():
            signal_bus.log_message.emit("WARNING", "输出文件路径为空，跳过保存", {})
            return False
            
        try:
            output_dir = os.path.dirname(output_file)
            if output_dir and output_dir.strip():
                os.makedirs(output_dir, exist_ok=True)
                file_tool.save_json_file(data, output_file, original_path=original_path)
                signal_bus.log_message.emit("SUCCESS", f"文件已保存: {output_file}", {})
                return True
            else:
                signal_bus.log_message.emit("WARNING", f"输出目录为空，跳过保存: {output_file}", {})
                return False
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"保存文件失败: {e}", {})
            traceback.print_exc()
            return False
    
    def _process_incremental_and_cache(self, data: Dict, incremental_data: Dict = None, 
                                      use_cache: bool = True) -> Tuple[Dict, List[str], List[str]]:
        """处理增量翻译和缓存，返回结果和需要翻译的文本及键"""
        result = {}
        need_translate = []
        need_translate_keys = []
        
        for key, value in data.items():
            # 1. 检查增量翻译
            if incremental_data and key in incremental_data:
                translated_value = incremental_data[key]
                result[key] = translated_value
                signal_bus.translation_item_updated.emit(self.task_name, key, translated_value, "增量翻译", value)
                continue
            
            # 2. 检查缓存
            if use_cache and self.cache and isinstance(value, str) and value.strip():
                cached = self.cache.get_cached_translation(value)
                if cached:
                    result[key] = cached
                    signal_bus.translation_item_updated.emit(self.task_name, key, cached, "命中缓存", value)
                    continue
            
            # 3. 收集需要AI翻译的文本
            if isinstance(value, str) and value.strip():
                need_translate.append(value)
                need_translate_keys.append(key)
                signal_bus.translation_item_updated.emit(self.task_name, key, "", "等待翻译", value)
            else:
                result[key] = value
        
        return result, need_translate, need_translate_keys
        
    def execute_task(self, task_type: str, params: Dict) -> Dict[str, Any]:
        """执行翻译任务"""

        task_handlers: Dict[str, Any] = {
            "smart_translation": self._execute_smart_translation,
            "quality_review": self._execute_quality_review,
            "manifest": self._execute_manifest_translation,
            "manifest_incremental": self._execute_manifest_incremental_translation,
            "config_menu": self._execute_config_menu_translation,
            "one_click_update": self._execute_one_click_update,
        }
        
        self._is_running = True
        self.task_name = task_type
        
        handler = task_handlers.get(task_type)
        if not handler:
            return {'成功': False, '消息': f'未知任务类型: {task_type}'}
        
        # 显式调用以避免类型检查警告
        if task_type == "smart_translation":
            return self._execute_smart_translation(params)
        elif task_type == "quality_review":
            return self._execute_quality_review(params)
        elif task_type == "manifest":
            return self._execute_manifest_translation(params)
        elif task_type == "manifest_incremental":
            return self._execute_manifest_incremental_translation(params)
        elif task_type == "config_menu":
            return self._execute_config_menu_translation(params)
        elif task_type == "one_click_update":
            return self._execute_one_click_update(params)
        else:
            return {'成功': False, '消息': f'未知任务类型: {task_type}'}
    
    def _execute_smart_translation(self, params: Dict) -> Dict[str, Any]:
        """执行智能翻译（整个文件夹）"""
        try:
            source_folder = params.get('原始文件夹', '')
            output_folder = params.get('输出文件夹', '')
            zh_folder = self.project_manager.get_folder_path('zh') if self.project_manager else None

            # 获取所有源文件
            source_files = file_tool.get_all_json_files(source_folder)
            if not source_files:
                return {'成功': False, '消息': '未找到源文件'}
            
            signal_bus.log_message.emit("SUCCESS", f"📁 找到 {len(source_files)} 个源文件", {})
            
            # 翻译状态跟踪
            success_files = 0
            total_files = len(source_files)
            
            # 提前添加所有文件到进度跟踪
            for i, src_file in enumerate(source_files):
                # 使用唯一文件名（包含相对路径）避免重复
                unique_filename = str(Path(src_file).relative_to(source_folder))
                
                # 读取文件获取总项数
                try:
                    data = file_tool.read_json_file(src_file)
                    total_items = len(data) if isinstance(data, dict) else 0
                except:
                    total_items = 0
                
                # 添加文件到进度跟踪
                signal_bus.translation_started.emit(unique_filename, total_items)
                signal_bus.translation_progress.emit(unique_filename, 0, "等待翻译")
            
            # 文件处理循环
            for i, src_file in enumerate(source_files):
                if not self._is_running:
                    return {'成功': False, '消息': '用户停止', '成功文件': success_files}
                
                # 使用唯一文件名（包含相对路径）避免重复
                unique_filename = str(Path(src_file).relative_to(source_folder))

                # 不重复发送translation_started信号，避免覆盖总数
                signal_bus.log_message.emit("INFO", f"处理文件 {i + 1}/{total_files}: {unique_filename}", {})
                
                try:
                    # 发送文件进度（开始）
                    signal_bus.translation_progress.emit(unique_filename, 0, "开始处理")
                    
                    # 读取源文件
                    data = file_tool.read_json_file(src_file)
                    
                    if not isinstance(data, dict):
                        signal_bus.log_message.emit("ERROR", f"文件 {unique_filename} 不是有效的字典格式", {})
                        signal_bus.translation_progress.emit(unique_filename, 0, "格式错误")
                        continue

                    signal_bus.log_message.emit("INFO", f"{unique_filename} 拥有{len(data)}个键", {})
                    
                    # 检查是否有对应的中文文件进行增量翻译
                    zh_file_path = None
                    
                    if zh_folder and os.path.exists(zh_folder):
                        rel_path = Path(src_file).relative_to(source_folder)
                        
                        # 处理多文件夹模式下的文件名
                        if rel_path.name.lower() == 'default.json':
                            zh_rel_path = rel_path.with_name('zh.json')
                        elif rel_path.name.endswith('_default.json'):
                            # 多文件夹模式：{mod_name}_default.json -> {mod_name}_default.json
                            zh_rel_path = rel_path
                        else:
                            zh_rel_path = rel_path
                            
                        zh_file_path = Path(zh_folder) / zh_rel_path
                    
                    # 如果有中文文件，进行增量翻译
                    incremental_data = {}
                    if zh_file_path and zh_file_path.exists():
                        signal_bus.translation_progress.emit(unique_filename, 10, "增量翻译")
                        
                        # 读取中文文件
                        zh_data = file_tool.read_json_file(str(zh_file_path))
                        
                        # 准备增量翻译数据
                        for key, en_value in data.items():
                            if key in zh_data:
                                zh_value = zh_data[key]
                                if zh_value and zh_value.strip():
                                    incremental_data[key] = zh_value
                    
                    # 计算输出文件路径
                    rel_path = Path(src_file).relative_to(source_folder)
                    if rel_path.name.lower() == 'default.json':
                        output_file = Path(output_folder) / rel_path.parent / 'zh.json'
                    else:
                        output_file = Path(output_folder) / rel_path
                    
                    # 确保输出目录存在
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 执行翻译，直接传递原始文件路径
                    result = self._translate_dict(
                        data=data,
                        output_file=str(output_file),
                        source_file=unique_filename,
                        incremental_data=incremental_data,
                        use_cache=True,
                        original_path=src_file  # 直接传递原始文件路径
                    )
                    
                    # 统一处理结果
                    if result.get('成功'):
                        success_files += 1
                        status_msg = f"翻译完成: {unique_filename}"
                        signal_bus.translation_progress.emit(unique_filename, 100, "完成")
                        
                        if os.path.exists(output_file):
                            signal_bus.log_message.emit("SUCCESS", 
                                f"{status_msg} → {output_file}", {})
                    else:
                        signal_bus.translation_progress.emit(unique_filename, 0, "错误")
                        signal_bus.log_message.emit("ERROR", f"翻译失败: {unique_filename}", {})
                        
                except Exception as e:
                    signal_bus.translation_progress.emit(unique_filename, 0, "错误")
                    signal_bus.log_message.emit("ERROR", 
                        f"处理文件 {unique_filename} 失败: {str(e)}", {})
                    traceback.print_exc()
            
            # 完成操作
            success = success_files > 0 or total_files == 0
            result_data = {
                '成功': success,
                '成功文件': success_files,
                '总文件数': total_files,
                '输出文件夹': str(output_folder)
            }
            
            if success:
                message = f"🎉 智能翻译完成！成功 {success_files}/{total_files} 个文件"
                signal_bus.log_message.emit("SUCCESS", message, {})
                
                # 统计输出文件
                output_files = file_tool.get_all_json_files(output_folder)
                signal_bus.log_message.emit("INFO", f"📁 生成 {len(output_files)} 个翻译文件", {})
            
            return result_data
            
        except Exception as e:
            error_msg = f"智能翻译失败: {str(e)}"
            signal_bus.log_message.emit("ERROR", error_msg, {})
            traceback.print_exc()
            return {'成功': False, '消息': error_msg}
    
    def _execute_quality_review(self, params: Dict) -> Dict[str, Any]:
        """执行质量检查重新翻译"""
        issues = params.get('问题列表', [])
        if not issues:
            return {'成功': False, '消息': '没有需要重新翻译的问题'}
        
        # 发送开始信号
        signal_bus.translation_started.emit("质量矫正翻译", len(issues))
        
        # 收集需要翻译的文本和对应的问题索引
        need_translate = []
        need_translate_indices = []
        need_translate_keys = []
        
        for i, issue in enumerate(issues):
            english = issue.get('英文', '')
            if english and english.strip():
                need_translate.append(english)
                need_translate_indices.append(i)
                need_translate_keys.append(issue.get('键', ''))
                # 添加到详细进度（等待翻译）
                signal_bus.translation_item_updated.emit("质量矫正翻译", issue.get('键', ''), "", "等待翻译", english)
        
        # 批量翻译
        translated_texts = []
        if need_translate and self._is_running:
            translations, _ = self._batch_translate_texts(
                need_translate, need_translate_keys, "质量矫正翻译", use_cache=False
            )
            
            # 按原始顺序排列翻译结果
            for i, key in enumerate(need_translate_keys):
                if key in translations:
                    translated_texts.append(translations[key])
                else:
                    translated_texts.append("")
        
        # 构建结果列表
        translated_issues = []
        translate_index = 0
        
        for issue in issues:
            english = issue.get('英文', '')
            if english and english.strip():
                # 使用翻译结果
                if translate_index < len(translated_texts) and translated_texts[translate_index].strip():
                    translated = translated_texts[translate_index]
                else:
                    # 翻译失败，使用原中文
                    translated = issue.get('中文', '')
                translate_index += 1
            else:
                # 空的英文文本，使用原中文
                translated = issue.get('中文', '')
            
            # 添加到结果列表
            translated_issues.append({
                '键': issue.get('键', ''),
                '英文': issue.get('英文', ''),
                '中文': issue.get('中文', ''),
                '新翻译': translated,
                '问题类型': issue.get('问题类型', ''),
                '原始文件': issue.get('原始文件', '')
            })
        
        return {
            '成功': True,
            '翻译问题列表': translated_issues,
            '总问题数': len(issues),
            '翻译数': len(translated_issues)
        }

    def _execute_manifest_translation(self, params: Dict) -> Dict[str, Any]:
        """执行manifest翻译"""
        # 处理参数
        if not isinstance(params, dict):
            return {'成功': False, '消息': '无效的参数格式'}

        folder_paths = params.get('文件夹路径', [])
        project_path = params.get('项目路径')

        if not folder_paths:
            return {'成功': False, '消息': '请先拖放包含manifest.json的文件夹'}

        if not project_path:
            return {'成功': False, '消息': '项目路径不存在'}

        # 提取manifest数据
        manifest_data = self._extract_manifest_data(folder_paths)

        if not manifest_data:
            return {'成功': False, '消息': '未找到manifest文件'}

        signal_bus.log_message.emit("INFO", f"找到 {len(manifest_data)} 个manifest文件", {})

        # 输出文件夹
        output_dir = Path(project_path) / "manifest"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        success_count = 0
        for mod_name, data in manifest_data.items():
            display_name = f"{mod_name}/manifest.json"
            
            try:
                # 准备需要翻译的字段
                fields_to_translate = {}
                
                if data.get('Name') and data['Name'].strip():
                    fields_to_translate['Name'] = data['Name']
                
                if data.get('Description') and data['Description'].strip():
                    fields_to_translate['Description'] = data['Description']

                if not fields_to_translate:
                    signal_bus.log_message.emit("INFO", f"{mod_name} 没有需要翻译的字段", {})
                    continue

                # 发送开始信号
                signal_bus.translation_started.emit(display_name, len(fields_to_translate))
                signal_bus.translation_progress.emit(display_name, 0, "开始处理")

                # 处理缓存和翻译
                result, need_translate, need_translate_keys = self._process_incremental_and_cache(
                    fields_to_translate, use_cache=True
                )
                
                # 批量翻译
                if need_translate and self._is_running:
                    translations, _ = self._batch_translate_texts(
                        need_translate, need_translate_keys, display_name, use_cache=True
                    )
                    result.update(translations)

                # 更新原始数据
                manifest_copy = data['manifest_data'].copy()
                for field_name, translated_value in result.items():
                    if translated_value and translated_value.strip():
                        manifest_copy[field_name] = translated_value

                # 保存文件
                mod_output_dir = output_dir / mod_name
                mod_output_dir.mkdir(exist_ok=True, parents=True)
                mod_output_file = mod_output_dir / "manifest.json"
                
                if not file_tool.save_json_file(manifest_copy, str(mod_output_file), original_path=data['manifest_path']):
                    raise Exception("保存文件失败")

                success_count += 1
                signal_bus.translation_progress.emit(display_name, 100, "完成")
                signal_bus.translation_completed.emit(display_name, True, "翻译完成")

            except Exception as e:
                signal_bus.log_message.emit("ERROR", f"模块 {mod_name} 翻译失败: {e}", {})
                traceback.print_exc()
                signal_bus.translation_progress.emit(display_name, 0, "失败")
                signal_bus.translation_completed.emit(display_name, False, "翻译失败")
        
        # 统计实际翻译的字段数量
        total_fields = sum(
            (1 if data.get('Name') and data['Name'].strip() else 0) +
            (1 if data.get('Description') and data['Description'].strip() else 0)
            for data in manifest_data.values()
        )
        
        return {
            '成功': success_count > 0,
            '输出文件夹': str(output_dir),
            '翻译数': total_fields,
            '成功数': success_count,
            '总数': len(manifest_data),
            '消息': f'Manifest翻译完成，成功处理 {success_count}/{len(manifest_data)} 个模块'
        }

    def _execute_manifest_incremental_translation(self, params: Dict) -> Dict[str, Any]:
        """执行manifest增量翻译 - 用中文manifest更新英文manifest"""
        try:
            en_folders = params.get('英文文件夹', [])
            zh_folders = params.get('中文文件夹', [])
            project_path = params.get('项目路径')

            if not en_folders or not zh_folders:
                return {'成功': False, '消息': '请同时拖放英文和中文文件夹'}

            if not project_path:
                return {'成功': False, '消息': '项目路径不存在'}

            # 提取英文和中文manifest数据
            en_manifest_data = self._extract_manifest_data(en_folders)
            zh_manifest_data = self._extract_manifest_data(zh_folders)

            if not en_manifest_data:
                return {'成功': False, '消息': '未找到英文manifest文件'}

            if not zh_manifest_data:
                return {'成功': False, '消息': '未找到中文manifest文件'}

            signal_bus.log_message.emit("INFO", f"🔍 找到 {len(en_manifest_data)} 个英文manifest，{len(zh_manifest_data)} 个中文manifest", {})

            # 输出文件夹
            output_dir = Path(project_path) / "manifest"
            output_dir.mkdir(exist_ok=True, parents=True)

            success_count = 0
            updated_fields_count = 0

            # 如果只有一个文件夹，直接匹配
            if len(en_folders) == 1 and len(zh_folders) == 1:
                en_mod_name = list(en_manifest_data.keys())[0]
                zh_mod_name = list(zh_manifest_data.keys())[0]
                
                display_name = f"{en_mod_name}/manifest.json"
                signal_bus.translation_started.emit(display_name, 2)
                
                en_data = en_manifest_data[en_mod_name]
                zh_data = zh_manifest_data[zh_mod_name]
                
                manifest_copy = en_data['manifest_data'].copy()
                
                # 更新Name和Description
                if zh_data.get('Name'):
                    manifest_copy['Name'] = zh_data['Name']
                    signal_bus.translation_item_updated.emit(display_name, 'Name', zh_data['Name'], "增量翻译", en_data.get('Name', ''))
                    updated_fields_count += 1
                
                if zh_data.get('Description'):
                    manifest_copy['Description'] = zh_data['Description']
                    signal_bus.translation_item_updated.emit(display_name, 'Description', zh_data['Description'], "增量翻译", en_data.get('Description', ''))
                    updated_fields_count += 1
                
                # 保存文件
                mod_output_dir = output_dir / en_mod_name
                mod_output_dir.mkdir(exist_ok=True, parents=True)
                mod_output_file = mod_output_dir / "manifest.json"
                
                file_tool.save_json_file(manifest_copy, str(mod_output_file), original_path=en_data['manifest_path'])
                
                success_count += 1
                signal_bus.translation_progress.emit(display_name, 100, "完成")
                signal_bus.translation_completed.emit(display_name, True, "增量翻译完成")
            else:
                # 多个文件夹，需要匹配文件夹名
                for en_mod_name, en_data in en_manifest_data.items():
                    # 查找匹配的中文manifest
                    zh_data = zh_manifest_data.get(en_mod_name)
                    
                    if not zh_data:
                        signal_bus.log_message.emit("WARNING", f"未找到匹配的中文manifest: {en_mod_name}", {})
                        continue
                    
                    display_name = f"{en_mod_name}/manifest.json"
                    signal_bus.translation_started.emit(display_name, 2)
                    
                    manifest_copy = en_data['manifest_data'].copy()
                    
                    # 更新Name和Description
                    fields_updated = 0
                    if zh_data.get('Name'):
                        manifest_copy['Name'] = zh_data['Name']
                        signal_bus.translation_item_updated.emit(display_name, 'Name', zh_data['Name'], "增量翻译", en_data.get('Name', ''))
                        fields_updated += 1
                    
                    if zh_data.get('Description'):
                        manifest_copy['Description'] = zh_data['Description']
                        signal_bus.translation_item_updated.emit(display_name, 'Description', zh_data['Description'], "增量翻译", en_data.get('Description', ''))
                        fields_updated += 1
                    
                    if fields_updated == 0:
                        signal_bus.log_message.emit("WARNING", f"{en_mod_name} 没有可更新的字段", {})
                        continue
                    
                    # 保存文件
                    mod_output_dir = output_dir / en_mod_name
                    mod_output_dir.mkdir(exist_ok=True, parents=True)
                    mod_output_file = mod_output_dir / "manifest.json"
                    
                    file_tool.save_json_file(manifest_copy, str(mod_output_file), original_path=en_data['manifest_path'])
                    
                    success_count += 1
                    updated_fields_count += fields_updated
                    signal_bus.translation_progress.emit(display_name, 100, "完成")
                    signal_bus.translation_completed.emit(display_name, True, "增量翻译完成")

            return {
                '成功': success_count > 0,
                '输出文件夹': str(output_dir),
                '翻译数': updated_fields_count,
                '成功数': success_count,
                '总数': len(en_manifest_data),
                '消息': f'Manifest增量翻译完成，成功处理 {success_count}/{len(en_manifest_data)} 个模块，更新 {updated_fields_count} 个字段'
            }

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"Manifest增量翻译失败: {e}", {})
            import traceback
            traceback.print_exc()
            return {'成功': False, '消息': f'Manifest增量翻译失败: {str(e)}'}

    @staticmethod
    def _extract_manifest_data(folder_paths: List[str]) -> Dict[str, Dict[str, str]]:
        """提取manifest数据"""
        seen_folders = set()
        manifest_data = {}

        for folder in map(Path, folder_paths):
            if folder.exists():
                # 查找 manifest.json
                manifest_files = list(folder.rglob("manifest.json"))
                
                for manifest_path in manifest_files:
                    mod_folder = manifest_path.parent.name

                    if mod_folder in seen_folders:
                        continue
                    seen_folders.add(mod_folder)

                    try:
                        data = file_tool.read_json_file(str(manifest_path))
                        manifest_data[mod_folder] = {
                            'Name': data.get("Name", ""),
                            'Description': data.get("Description", ""),
                            'manifest_path': str(manifest_path),
                            'manifest_data': data
                        }
                    except Exception as e:
                        signal_bus.log_message.emit("WARNING", f"🔍 读取 manifest 失败: {e}", {})
                        continue

        signal_bus.log_message.emit("INFO", f"🔍 提取完成，找到 {len(manifest_data)} 个模块", {})
        return manifest_data

    

    def _execute_config_menu_translation(self, params: Dict) -> Dict[str, Any]:
        """执行配置菜单翻译"""
        try:
            mod_folders = params.get('mod文件夹', [])

            if not mod_folders:
                return {'成功': False, '消息': '请先拖放包含content.json的mod文件夹'}

            output_folder = self.project_manager.get_folder_path('output')
            
            total_translated = 0
            
            # 处理每个mod文件夹
            for mod_folder_path in mod_folders:
                mod_name = os.path.basename(mod_folder_path)
                content_file = os.path.join(mod_folder_path, 'content.json')
                
                if not os.path.exists(content_file):
                    signal_bus.log_message.emit("WARNING", f"跳过 {mod_name}：未找到content.json", {})
                    continue
                
                # 读取content.json并提取翻译数据
                content_data = file_tool.read_json_file(content_file)
                translation_data = self._extract_config_fields(content_data)
                
                if not translation_data:
                    signal_bus.log_message.emit("INFO", f"跳过 {mod_name}：没有需要翻译的配置项", {})
                    continue
                
                # 输出文件
                output_file = os.path.join(output_folder, f"{mod_name}_zh.json")
                
                # 发送开始信号，使用文件名
                signal_bus.translation_started.emit(f"{mod_name}_zh.json", len(translation_data))
                
                # 执行翻译
                result = self._translate_dict(
                    data=translation_data,
                    output_file=output_file,
                    source_file=f"{mod_name}_zh.json",
                    incremental_data=None,
                    use_cache=True
                )
                
                if result.get('成功'):
                    total_translated += len(translation_data)
                    signal_bus.log_message.emit("SUCCESS", f"{mod_name} 翻译完成：{len(translation_data)} 项", {})
                else:
                    signal_bus.log_message.emit("ERROR", f"{mod_name} 翻译失败", {})
            
            if total_translated > 0:
                return {
                    '成功': True,
                    '输出文件夹': output_folder,
                    '翻译数': total_translated,
                    '消息': f'配置菜单翻译完成，处理了 {total_translated} 个配置项'
                }
            else:
                return {'成功': False, '消息': '没有找到可翻译的配置项'}

        except Exception as e:
            return {'成功': False, '消息': f'配置菜单翻译失败: {str(e)}'}
    
    
    
    def _translate_dict(self, data: Dict, output_file: str, source_file: str = "", 
                       incremental_data: Dict = None, use_cache: bool = True, original_path: str = None) -> Dict[str, Any]:
        """翻译字典数据"""
        if not isinstance(data, dict):
            return {'成功': False, '消息': '输入数据不是字典格式'}
        
        self.task_name = source_file
        total_items = len(data)
        completed_items = 0
        
        # 处理增量翻译和缓存，收集需要翻译的文本
        result, need_translate, need_translate_keys = self._process_incremental_and_cache(
            data, incremental_data, use_cache
        )
        
        # 批量AI翻译
        if need_translate and self._is_running:
            translations, _ = self._batch_translate_texts(
                need_translate, need_translate_keys, source_file, use_cache
            )
            result.update(translations)
        
        # 保存文件
        if not self._save_output_file(result, output_file, original_path):
            return {'成功': False, '消息': "保存文件失败"}
        
        # 发送完成信号
        signal_bus.translation_progress.emit(source_file, 100, "完成")
        
        return {
            '成功': True,
            '输出文件': output_file
        }
    
    def _extract_config_fields(self, content_data: Dict) -> Dict[str, str]:
        """从content.json提取需要翻译的字段"""
        translation_data = {}
        
        if "ConfigSchema" in content_data:
            for field_name, field_data in content_data["ConfigSchema"].items():
                # Name字段
                if name := field_data.get("name"):
                    name_str = str(name)
                    # 过滤掉i18n格式
                    if not self._is_i18n_format(name_str):
                        translation_data[f"config.{field_name}.name"] = name_str
                
                # Description字段
                if desc := field_data.get("Description"):
                    desc_str = str(desc)
                    # 过滤掉i18n格式
                    if not self._is_i18n_format(desc_str):
                        translation_data[f"config.{field_name}.description"] = desc_str
                
                # Section字段
                if section := field_data.get("Section"):
                    section_str = str(section)
                    # 过滤掉i18n格式
                    if not self._is_i18n_format(section_str):
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
    
    def _execute_one_click_update(self, params: Dict) -> Dict[str, Any]:
        """执行一键更新任务"""
        try:
            from core.one_click_update_processor import OneClickUpdateProcessor
            
            processor = OneClickUpdateProcessor(self.project_manager)
            # 保存处理器引用以便主线程访问
            self._current_processor = processor
            result = processor.process(params)
            # 不立即清理引用，让质量检查完成后再清理
            return result
            
        except Exception as e:
            error_msg = f"一键更新失败: {str(e)}"
            signal_bus.log_message.emit("ERROR", error_msg, {})
            # 清理引用
            self._current_processor = None
            return {'成功': False, '消息': error_msg}
            return False
        return True