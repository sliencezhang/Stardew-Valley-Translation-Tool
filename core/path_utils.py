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
    # return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')
    return True

def is_nuitka_onefile() -> bool:
    """检查是否在Nuitka单文件模式下运行"""
    # 首先检查sys.frozen
    if getattr(sys, 'frozen', False):
        # Nuitka会设置sys.frozen = True
        # 检查是否在临时目录（Nuitka单文件特征）
        exe_path = str(sys.executable).lower()
        temp_indicators = [
            'temp', 
            'onefil', 
            'onefile_temp', 
            'onefile-build',
            'appdata\\local\\temp',
            'onefil~1',  # 短文件名格式
            '\\temp\\',
            'local\\temp\\'
        ]
        
        # 检查是否包含临时目录标识
        is_temp = any(indicator in exe_path for indicator in temp_indicators)
        
        # 额外检查：检查当前工作目录是否也是临时目录
        import os
        cwd = os.getcwd().lower()
        is_cwd_temp = any(indicator in cwd for indicator in temp_indicators)
        
        return is_temp or is_cwd_temp
    
    # 如果sys.frozen不是True，但路径中包含临时目录特征，也可能是Nuitka
    exe_path = str(sys.executable).lower()
    if 'onefil' in exe_path or 'onefile' in exe_path:
        return True
        
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
    
    if is_pyinstaller():
        # PyInstaller：资源在sys._MEIPASS中
        try:
            base_path = Path(sys._MEIPASS)
            resource_path = base_path / relative_path
            if resource_path.exists():
                return resource_path
        except:
            pass
    
    if is_nuitka_onefile():
        # Nuitka单文件：资源在exe所在目录的resources子目录中
        exe_dir = Path(sys.executable).parent
        resource_path = exe_dir / "resources" / relative_path
        return resource_path
    
    # 开发环境或其他情况
    if is_frozen():
        # 其他打包环境：使用exe所在目录
        base_dir = Path(sys.executable).parent
    else:
        # 开发环境：使用项目根目录
        base_dir = Path(__file__).parent.parent
    
    resource_path = base_dir / relative_path
    return resource_path

def get_writable_resource_path(relative_path: str) -> Path:
    """获取可写的资源文件路径
    
    开发环境：返回 resources 目录下的路径
    打包环境：返回用户数据目录下的 resources 子目录路径
    
    Args:
        relative_path: 相对路径，如 "terminology.json"
        
    Returns:
        Path: 可写的文件路径
    """
    if is_frozen() or is_nuitka_onefile():
        # 打包环境：保存到用户数据目录下的 resources 子目录
        user_dir = get_user_data_directory()
        return user_dir / "resources" / relative_path
    else:
        # 开发环境：保存到 resources 目录
        project_root = Path(__file__).parent.parent
        return project_root / "resources" / relative_path

def get_readable_resource_path(relative_path: str) -> Path:
    """获取可读的资源文件路径
    
    打包环境：始终从用户数据目录下的resources子目录读取
    开发环境：直接从 resources 读取
    
    Args:
        relative_path: 相对路径，如 "terminology.json"
        
    Returns:
        Path: 可读的文件路径
    """
    if is_frozen() or is_nuitka_onefile():
        # 打包环境：始终从用户数据目录下的resources子目录读取
        user_dir = get_user_data_directory()
        user_path = user_dir / "resources" / relative_path
        return user_path
    else:
        # 开发环境：直接从 resources 读取
        project_root = Path(__file__).parent.parent
        return project_root / "resources" / relative_path

def get_user_data_directory() -> Path:
    """获取用户数据目录"""
    # 使用用户文档目录下的"Stardew Valley Translation Tool"路径
    documents_dir = Path.home() / 'Documents' / 'Stardew Valley Translation Tool'
    return documents_dir

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
