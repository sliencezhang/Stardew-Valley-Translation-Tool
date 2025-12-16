# core/signal_bus.py
from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """全局信号总线"""
    # engine
    translation_started = Signal(str, int)  # 文件开始翻译, 总键值对
    translation_progress = Signal(str, int, str)  # 文件进度: 文件名, 进度值, 状态
    translation_item_added = Signal(str, str, str)  # 添加翻译项: 文件名, 键, 原文
    translation_item_updated = Signal(str, str, str, str, str)  # 更新翻译项: 文件名, 键, 译文, 状态, 原文
    translation_completed = Signal(str, bool, str)  # 翻译完成: 文件名, 是否成功, 消息
    translation_error = Signal(str, str)  # 翻译错误: 文件名, 错误信息
    batch_translated = Signal(int, int)  # 批次翻译完成: 成功数, 总数
    # file_tool，project_manager,tab_smart
    log_message = Signal(str, str, dict)   # 级别('信息', '警告', '错误', '成功'), 消息, 详情
    # settings_dialog
    settingsSaved = Signal(dict)  # 设置保存信号
    cacheCleared = Signal(object)  # 缓存清除信号
    apiTested = Signal(bool, str)  # API测试信号 (成功状态, 消息)
    # project_manager
    terminology_loaded = Signal(int)  # 发送加载的术语数量
    terminology_updated = Signal()  # 术语表已更新，需要重新加载
    prompt_updated = Signal()  # 提示词已更新，需要重新加载
    prompt_built = Signal(int, int, int, dict)  # 发送提示词构建信息：总字符数，术语数，文本数，匹配到的术语表
    error_occurred = Signal(str)  # 发送错误信息
    # widgets
    filesDropped = Signal(list, object)  # 添加来源标识参数
    foldersDropped = Signal(list, object)  # 添加来源标识参数

    # tab_manifest
    manifestExtracted = Signal(dict)  # Manifest数据提取信号
    extractionFailed = Signal(str)  # 提取失败信号
    manifest_translate_request = Signal(dict)  # 触发manifest AI翻译
    manifest_incremental_request = Signal(dict)  # 触发manifest增量翻译

    # tab_smart
    startSmartTranslation = Signal(dict)
    startBackfillTranslation = Signal(dict)

    # tab_quality_check
    runQualityCheck = Signal(dict)
    analyzeQualityResults = Signal(object)
    retranslateQualityIssues = Signal(dict)
    applyQualityFixes = Signal(dict)

    # tab_config
    startConfigTranslation = Signal(dict)




    _managers_initialized = Signal(bool)


# 所有窗口共享同一个实例
signal_bus = SignalBus()