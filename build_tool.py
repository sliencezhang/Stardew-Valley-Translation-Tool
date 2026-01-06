#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星露谷翻译工具 - 简化版 Nuitka 打包脚本
打包为单个可执行文件,资源文件夹外置,无控制台窗口
"""
import subprocess
import sys
import shutil
from pathlib import Path
from version import VERSION


def check_nuitka():
    """检查 Nuitka 是否可用"""
    try:
        result = subprocess.run([sys.executable, '-m', 'nuitka', '--version'],
                                capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            print(f"[OK] Nuitka: {result.stdout.splitlines()[0]}")
            return True
        else:
            print("[ERROR] Nuitka 未安装或不可用")
            return False
    except:
        print("[ERROR] Nuitka 未安装")
        return False


def build():
    """执行 Nuitka 打包"""

    # 检查 Nuitka
    if not check_nuitka():
        print("请安装 Nuitka: pip install nuitka")
        return 1

    # 获取项目根目录
    project_root = Path(__file__).parent
    main_file = project_root / "main.py"
    icon_file = project_root / "resources" / "icons" / "logo.ico"
    output_filename = f"星露谷翻译工具_v{VERSION}.exe"
    dist_dir = project_root / "dist"

    # 清理 dist 目录（如果存在）
    if dist_dir.exists():
        print("=" * 60)
        print("正在清理 dist 目录...")
        try:
            shutil.rmtree(dist_dir)
            print("dist 目录清理完成")
        except Exception as e:
            print(f"清理 dist 目录时出错: {e}")
            print("尝试继续打包...")
        print("=" * 60)

    # Nuitka 打包命令
    cmd = [
        sys.executable,
        "-m", "nuitka",
        "--standalone",  # 独立模式
        "--onefile",  # 打包为单文件
        "--windows-disable-console",  # 禁用控制台窗口
        "--enable-plugin=pyside6",  # 启用 PySide6 插件
        f"--windows-icon-from-ico={icon_file}",  # 设置图标
        "--lto=yes",  # 启用链接时优化(压缩)
        # "--include-data-dir=resources=resources",  # 不包含resources文件夹
        "--output-dir=dist",  # 输出目录
        f"--output-filename={output_filename}",  # 输出文件名
        "--company-name=Silence",
        "--product-name=Stardew Valley Translation Tool",
        f"--file-version={VERSION}",
        f"--product-version={VERSION}",
        "--file-description=Stardew Valley Translation Tool",
        "--assume-yes-for-downloads",  # 自动确认下载
        "--show-progress",  # 显示进度
        "--show-memory",  # 显示内存使用
        str(main_file)
    ]

    print("=" * 60)
    print("开始打包...")
    print("=" * 60)
    print(f"主文件: {main_file}")
    print(f"图标: {icon_file}")
    print(f"输出目录: {project_root / 'dist'}")
    print("=" * 60)

    try:
        # 执行打包命令
        result = subprocess.run(cmd, cwd=project_root, check=True)

        print("\n" + "=" * 60)
        print("打包完成!")
        print("=" * 60)
        print(f"可执行文件位于: {project_root / 'dist' / output_filename}")
        
        # 复制 resources 文件夹到 dist 目录
        resources_src = project_root / "resources"
        resources_dst = dist_dir / "resources"
        if resources_src.exists():
            print("=" * 60)
            print("正在复制 resources 文件夹...")
            try:
                if resources_dst.exists():
                    shutil.rmtree(resources_dst)
                shutil.copytree(resources_src, resources_dst)
                print(f"resources 文件夹已复制到: {resources_dst}")
            except Exception as e:
                print(f"复制 resources 文件夹时出错: {e}")
            print("=" * 60)
        
        print("=" * 60)

        return result.returncode

    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print(f"打包失败: {e}")
        print("=" * 60)
        return e.returncode
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"发生错误: {e}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(build())