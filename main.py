# main.py
import sys
from pathlib import Path
# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon


def setup_application():
    """设置应用程序"""
    # 创建QApplication实例
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("星露谷翻译工具")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("StardewTranslator")

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 设置应用程序图标
    icon_path = current_dir / "resources" / "icons" / "logo.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    # ============ 图标设置结束 ============

    return app


def check_dependencies():
    """检查依赖项"""
    try:
        import PySide6
        import requests
        import hjson
        print("✅ 所有依赖项检查通过")
        return True
    except ImportError as e:
        error_msg = f"❌ 缺少依赖项: {e}\n\n⚠️ 请安装所需的依赖包：\npip install PySide6 requests hjson"
        print(error_msg)
        return False


def show_splash_info():
    """显示启动信息"""
    print("=" * 50)
    print("🌟 星露谷翻译工具")
    print("=" * 50)
    print("正在启动...")


def main():
    """主函数"""
    # 显示启动信息
    show_splash_info()

    # 检查依赖项
    if not check_dependencies():
        sys.exit(1)

    # 创建应用程序
    app = setup_application()

    try:
        # 导入主窗口
        from ui.main_window import StardewTranslationTool

        # 创建主窗口
        main_window = StardewTranslationTool()
        main_window.show()
        
        # 添加退出时的缓存保护
        def handle_exit():
            """处理程序退出，确保缓存保存"""
            try:
                # 如果有翻译执行器，确保其缓存已保存
                if hasattr(main_window, 'translation_executor') and main_window.translation_executor:
                    if hasattr(main_window.translation_executor, 'cache') and main_window.translation_executor.cache:
                        # 强制保存缓存
                        main_window.translation_executor.cache.save_cache()
                        print("✅ 缓存已安全保存")
            except Exception as e:
                print(f"⚠️ 退出时保存缓存失败: {e}")
        
        # 连接退出信号
        app.aboutToQuit.connect(handle_exit)
        
        # 运行应用程序
        return_code = app.exec()

        # logger.info(f"应用程序退出，返回码: {return_code}")
        return return_code

    except Exception as e:
        print(f"应用程序启动失败: {e}")
        import traceback
        traceback.print_exc()

        from ui.custom_message_box import CustomMessageBox
        CustomMessageBox.critical(
            None,
            "启动失败",
            f"应用程序启动失败:\n\n{str(e)}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())