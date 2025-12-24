#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径工具模块 - 解决Nuitka单文件模式路径问题
"""

import os
import sys
from pathlib import Path
from typing import Optional

def is_frozen() -> bool:
    """检查是否在打包环境中运行"""
    return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')

def is_nuitka_onefile() -> bool:
    """检查是否在Nuitka单文件模式下运行"""
    if getattr(sys, 'frozen', False):
        # Nuitka会设置sys.frozen = True
        # 检查是否在临时目录（Nuitka单文件特征）
        exe_path = str(sys.executable).lower()
        temp_indicators = [
            'temp', 
            'onefil', 
            'onefile_temp', 
            'onefile-build',
            'appdata\\local\\temp'
        ]
        return any(indicator in exe_path for indicator in temp_indicators)
    return False

def is_pyinstaller() -> bool:
    """检查是否在PyInstaller打包环境中运行"""
    return hasattr(sys, '_MEIPASS')

def get_real_executable_path() -> Optional[Path]:
    """获取真实的可执行文件路径（处理打包环境）"""
    try:
        if is_nuitka_onefile():
            # Nuitka单文件模式：使用Windows API获取真实路径
            if sys.platform == 'win32':
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # 获取当前进程的完整路径
                    GetModuleFileNameW = ctypes.windll.kernel32.GetModuleFileNameW
                    buffer = ctypes.create_unicode_buffer(260)
                    GetModuleFileNameW(None, buffer, 260)
                    
                    actual_path = Path(buffer.value)
                    if actual_path.exists():
                        return actual_path.resolve()
                except:
                    pass
            
            # 尝试通过命令行参数
            if len(sys.argv) > 0 and sys.argv[0]:
                arg_path = Path(sys.argv[0])
                if arg_path.exists():
                    return arg_path.resolve()
        
        # 普通情况或PyInstaller
        exe_path = Path(sys.executable)
        if exe_path.exists():
            return exe_path.resolve()
        
        return None
        
    except Exception:
        return None

def get_application_directory() -> Path:
    """获取应用程序所在目录"""
    try:
        real_exe = get_real_executable_path()
        if real_exe and real_exe.is_file():
            return real_exe.parent
        
        # 回退方案
        if is_frozen():
            # 打包环境：使用exe所在目录
            exe_dir = Path(sys.executable).parent
            if exe_dir.exists():
                return exe_dir
        else:
            # 开发环境：使用当前工作目录
            return Path.cwd()
        
        # 最终回退：用户文档目录
        return Path.home() / "Documents" / "StardewTranslator"
        
    except Exception:
        return Path.home() / "Documents" / "StardewTranslator"

def get_resource_path(relative_path: str) -> Path:
    """获取资源文件路径（兼容打包环境）"""
    base_dir = get_application_directory()
    
    if is_pyinstaller():
        # PyInstaller：资源在sys._MEIPASS中
        try:
            base_path = Path(sys._MEIPASS)
            resource_path = base_path / relative_path
            if resource_path.exists():
                return resource_path
        except:
            pass
    
    # 普通情况或Nuitka
    resource_path = base_dir / relative_path
    return resource_path

def get_user_data_directory() -> Path:
    """获取用户数据目录"""
    if sys.platform == 'win32':
        # Windows：使用AppData/Local
        appdata = os.environ.get('LOCALAPPDATA', '')
        if appdata:
            return Path(appdata) / 'StardewTranslator'
    
    # 其他平台或失败：使用用户主目录
    return Path.home() / '.stardewtranslator'

# 测试函数
def test_path_functions():
    """测试路径函数"""
    print("=" * 60)
    print("路径工具测试")
    print("=" * 60)
    
    print(f"1. 是否打包: {is_frozen()}")
    print(f"2. 是否Nuitka单文件: {is_nuitka_onefile()}")
    print(f"3. 是否PyInstaller: {is_pyinstaller()}")
    
    real_exe = get_real_executable_path()
    print(f"4. 真实exe路径: {real_exe}")
    
    app_dir = get_application_directory()
    print(f"5. 应用目录: {app_dir}")
    
    user_data = get_user_data_directory()
    print(f"6. 用户数据目录: {user_data}")
    
    print("\n7. 资源路径测试:")
    test_resources = ['resources/icons/logo.ico', 'resources/default_prompts.json']
    for resource in test_resources:
        path = get_resource_path(resource)
        exists = path.exists()
        print(f"   {resource}: {path} {'✅' if exists else '❌'}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    test_path_functions()
