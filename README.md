# 星露谷翻译工具 v1.1

专业的星露谷游戏文本翻译工具，支持智能翻译、增量翻译、质量检查等功能。

使用教程：https://www.bilibili.com/video/BV15NqbBAEQN

## 🌟 v1.1更新内容
- 一键更新页面，拖入下载的英文mod文件夹和游戏mod目录内的中文mod文件夹
  - 会自动开始检查人名地名，手动确认后，开始翻译 i18n 内的json、manifest.json、content.json
    - 若i18n内是文件形式，会自动将content提取的键值对翻译后追加在zh.json内容上方（会去重，优先使用default或zh中已有的）
    - 若i18n内是文件夹形式，则提取的content键值对会保存在output/mod文件夹/i18n/配置菜单翻译.json，由用户确认添加
  - 自动将中文mod文件夹的**config.json**，以及**中文mod文件夹/assets/Portraits** 覆盖复制到output对应的位置
    - 避免了用户还需手动将美化的精灵图复制到下载的mod中
  - 完成上述流程后，自动开始质量检查，若不需要，直接关闭即可
  - 输出在**项目文件夹/output/mod文件夹**，此文件夹**包含mod所有资源**，只需要将文件夹内的文件复制到游戏mod对应文件夹中即可
- 新增了通过github api自动检查更新的功能
- 将术语表、提示词保存在临时目录 改为 保存在 %HOMEPATH%\Documents\Stardew Valley Translation Tool\resources 中，避免被系统自动清理
- 修改了提示词，避免DeepSeek输出多余解释内容以及自动生成变量

## 🌟 功能特点

- 🤖 **智能翻译**：支持多种翻译API，自动识别和保护游戏变量
- 📚 **增量翻译**：智能跳过已翻译内容，提高效率
- 🔍 **质量检查**：检查中英混杂、变量一致性等问题
- ⚙️ **配置菜单翻译**：专门处理模组配置文件
- ✏️ **手动翻译**：提供友好的手动翻译界面
- 📋 **术语管理**：支持自定义术语表，保证翻译一致性
- 💾 **缓存机制**：自动缓存翻译结果，避免重复翻译
- 🎨 **现代化界面**：基于PySide6的现代化GUI界面
- 🌙 **主题切换**：支持日间/夜间主题切换
- 📊 **进度显示**：实时显示翻译进度和统计信息

## 📦 安装方法

### 方法1：使用可执行文件（推荐）

1. 下载最新版本的 `main.exe`（约26MB）
2. 双击运行即可使用，无需安装Python环境

### 方法2：从源码安装

1. 确保已安装 Python 3.8 或更高版本
2. 克隆或下载本项目
3. 创建虚拟环境（推荐）：
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
5. 运行程序：
   ```bash
   python main.py
   ```

## 🚀 快速开始

1. **创建项目**：点击"新建项目"，选择项目文件夹
2. **准备文件**：将需要翻译的模组文件放入对应文件夹
   - `en/` - 英文原文文件
   - `zh/` - 中文参考文件（可选）
   - `output/` - 翻译输出文件
3. **配置API**：在设置中配置翻译API密钥
4. **开始翻译**：选择相应的翻译功能开始翻译
5. **质量检查**：翻译完成后使用质量检查功能
6. **导出结果**：翻译结果保存在output文件夹中

## 🔧 支持的翻译API

- DeepL
- Google Translate
- 百度翻译
- 有道翻译
- 其他兼容的翻译API

## 📁 项目结构

```
项目文件夹/
├── en/          # 英文原文文件
│   └── default.json
├── zh/          # 中文参考文件
│   └── zh.json
├── output/      # 翻译输出文件
│   └── zh.json
├── cache/       # 翻译缓存
│   └── translation_cache.json
├── manifest/    # 模组清单文件
└── project_config.json  # 项目配置文件
```

## 🎯 使用技巧

### 智能翻译
- 自动识别游戏变量格式：`%object`, `%%`, `{variable}`等
- 支持术语表，确保关键术语翻译一致
- 可配置翻译提示词，提高翻译质量

### 质量检查
- 检查中英混杂问题
- 验证变量一致性
- 检查翻译完整性
- 提供一键修复功能

### 手动翻译
- 高亮显示需要翻译的内容
- 支持原文和译文对照显示
- 提供翻译建议和历史记录

## ⚙️ 高级配置

### 翻译API配置
在设置中可以配置：
- API密钥
- 请求间隔时间
- 重试次数
- 翻译语言对

### 术语管理
- 支持导入/导出术语表
- 可设置术语优先级
- 支持正则表达式匹配

### 缓存设置
- 可配置缓存有效期
- 支持清理缓存
- 可导出/导入缓存

## 🔨 开发指南

### 环境要求
- Python 3.8+
- PySide6
- requests
- pandas

### 构建可执行文件
使用 Nuitka 打包为单文件：
```bash
nuitka --standalone --onefile --windows-console-mode=disable --windows-disable-console --enable-plugin=pyside6 --windows-icon-from-ico="resources/icons/logo.ico" --include-data-dir=resources=resources --output-dir=dist_onefile main.py
```

或使用自动打包脚本：
```bash
python build_tool.py --mode onefile
```

### 项目结构
```
Stardew Valley Translation Tool/
├── main.py              # 主程序入口
├── core/                # 核心功能模块
│   ├── api_client.py    # API客户端
│   ├── translation_engine.py  # 翻译引擎
│   ├── quality_checker.py     # 质量检查
│   └── ...
├── ui/                  # 用户界面
│   ├── main_window.py   # 主窗口
│   ├── widgets.py       # 自定义控件
│   └── tabs/            # 功能页面
├── resources/           # 资源文件
│   ├── icons/           # 图标
│   ├── img/             # 图片
│   ├── default_prompts.json  # 默认提示词
│   └── terminology.json     # 默认术语表
└── requirements.txt     # 依赖列表
```

## 🐛 常见问题

### Q: 翻译API调用失败怎么办？
A: 检查API密钥是否正确，网络连接是否正常，必要时调整请求间隔时间。

### Q: 程序启动失败？
A: 确保Python版本符合要求，所有依赖已正确安装。

### Q: 翻译结果不理想？
A: 尝试调整翻译提示词，使用术语表，或切换到其他翻译API。

### Q: 如何备份项目？
A: 直接复制整个项目文件夹即可，所有配置和缓存都在其中。

## 📝 更新日志

### v2.0.0
- 全新的现代化界面
- 支持单文件打包，无需安装Python
- 优化翻译引擎，提高翻译质量
- 新增主题切换功能
- 改进质量检查算法

### v1.x.x
- 基础翻译功能
- 支持多种翻译API
- 质量检查功能
- 手动翻译界面

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 感谢星露谷社区的支持
- 感谢所有翻译API提供商
- 感谢所有贡献者的努力

---

**如果这个工具对你有帮助，请给个⭐️支持一下！**