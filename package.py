#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
from pathlib import Path

def create_package():
    """创建应用程序包"""
    print("开始打包星露谷翻译工具...")
    
    # 项目根目录
    project_root = Path(__file__).parent
    build_dir = project_root / "package_build"
    dist_dir = project_root / "package_dist"
    
    # 清理旧目录
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # 创建目录结构
    build_dir.mkdir(exist_ok=True)
    dist_dir.mkdir(exist_ok=True)
    
    # 复制Python文件
    print("复制Python文件...")
    
    # 复制core目录
    core_src = project_root / "core"
    core_dst = build_dir / "core"
    if core_src.exists():
        shutil.copytree(core_src, core_dst, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
    
    # 复制ui目录
    ui_src = project_root / "ui"
    ui_dst = build_dir / "ui"
    if ui_src.exists():
        shutil.copytree(ui_src, ui_dst, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
    
    # 复制resources目录
    resources_src = project_root / "resources"
    resources_dst = build_dir / "resources"
    if resources_src.exists():
        shutil.copytree(resources_src, resources_dst)
    
    # 复制main.py
    shutil.copy2(project_root / "main.py", build_dir / "main.py")
    
    # 创建requirements.txt
    print("创建依赖文件...")
    requirements = [
        "PySide6==6.10.1",
        "requests==2.32.5",
        "hjson==3.1.0"
    ]
    
    with open(build_dir / "requirements.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(requirements))
    
    # 创建启动脚本
    print("创建启动脚本...")
    
    # Windows批处理文件
    bat_content = """@echo off
echo 正在启动星露谷翻译工具...
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python。请安装Python 3.8或更高版本。
    pause
    exit /b 1
)

REM 检查依赖
if not exist "requirements.txt" (
    echo 错误: 未找到requirements.txt
    pause
    exit /b 1
)

echo 检查依赖项...
pip install -r requirements.txt --quiet

echo 启动应用程序...
python main.py

pause
"""
    
    with open(build_dir / "start.bat", "w", encoding="gbk") as f:
        f.write(bat_content)
    
    # PowerShell脚本
    ps_content = """# PowerShell启动脚本
Write-Host "正在启动星露谷翻译工具..." -ForegroundColor Green
Write-Host ""

# 检查Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python版本: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "错误: 未找到Python。请安装Python 3.8或更高版本。" -ForegroundColor Red
    Read-Host "按Enter键退出"
    exit 1
}

# 检查依赖
if (-not (Test-Path "requirements.txt")) {
    Write-Host "错误: 未找到requirements.txt" -ForegroundColor Red
    Read-Host "按Enter键退出"
    exit 1
}

Write-Host "检查依赖项..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet

Write-Host "启动应用程序..." -ForegroundColor Green
python main.py

Read-Host "按Enter键退出"
"""
    
    with open(build_dir / "start.ps1", "w", encoding="utf-8") as f:
        f.write(ps_content)
    
    # 创建README
    readme_content = """# 星露谷翻译工具

## 说明
这是一个用于星露谷物语游戏文本翻译的专业工具。

## 系统要求
- Windows 7/8/10/11
- Python 3.8或更高版本
- 网络连接（用于翻译API）

## 安装和运行

### 方法1：使用批处理文件（推荐）
1. 双击 `start.bat`
2. 程序会自动检查并安装依赖
3. 应用程序将自动启动

### 方法2：使用PowerShell
1. 右键点击 `start.ps1`，选择"使用PowerShell运行"
2. 如果出现安全提示，输入 `Y` 确认
3. 程序会自动运行

### 方法3：手动运行
1. 打开命令提示符或PowerShell
2. 进入本目录：`cd "路径到此文件夹"`
3. 安装依赖：`pip install -r requirements.txt`
4. 运行程序：`python main.py`

## 功能特点
- 智能翻译游戏文本
- 术语一致性管理
- 质量检查
- 批量处理
- 用户友好的界面

## 注意事项
- 首次运行会自动安装所需依赖
- 确保有稳定的网络连接
- 建议在运行前备份游戏文件

## 支持
如有问题，请检查日志文件或联系开发者。
"""
    
    with open(build_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # 创建压缩包
    print("创建发布包...")
    import zipfile
    
    zip_path = dist_dir / "StardewValleyTranslationTool.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, build_dir)
                zipf.write(file_path, arcname)
    
    print(f"\n✅ 打包完成！")
    print(f"📦 发布包位置: {zip_path}")
    print(f"📁 构建目录: {build_dir}")
    print(f"\n运行方式:")
    print("1. 解压 StardewValleyTranslationTool.zip")
    print("2. 双击 start.bat 运行程序")
    
    return True

def main():
    try:
        create_package()
        return 0
    except Exception as e:
        print(f"❌ 打包失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())