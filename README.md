# VNDB-GUI

VNDB 视觉小说文件名生成器 — 基于 [VNDB API v2 (kana)](https://api.vndb.org/kana) 的桌面工具，自动生成标准化的文件名。

## 功能特点

- **搜索 VNDB** — 输入 VNDB ID（如 `v2622`）或游戏原名，自动获取发行版本列表
- **双列布局** — 左侧「原版发行」显示非中文版本，右侧「中文发行」显示中文版本
- **智能预览** — 原版发行提供开发商/发售日期/平台/语言信息；中文发行提供汉化组/补丁日期信息
- **文件名生成** — 自动生成标准格式文件名：
  ```
  [开发商][发售日期]原版标题[vID][平台][汉化组][汉化补丁日期][CHS]
  ```
- **一键复制** — 点击「一键复制」按钮将文件名复制到剪贴板
- **自动过滤** — Windows 非法字符自动替换为全角等效字符（`:?/\*"<>|`）

## 文件名格式

```
[developer][YYYYMMDD]original_title[vVNDB_ID][platform][group][patch_date][language]
```

例如：
```
[ゆずソフト][20160729]千恋＊万花[v19073][Windows][落樱汉化组][20171111][CHS]
```

## 使用方法

1. **搜索** — 在输入框中输入 VNDB ID（如 `v19073`）或游戏原名，点击「搜索 API」
2. **选择原版发行** — 在左侧列表选择非中文发行版本（开发商/日期/标题/平台来自此版本）
3. **选择中文发行版** — 在右侧列表选择对应的中文发行版本（汉化组/补丁日期/语言自动填入）
4. **预览与复制** — 确认文件名无误后点击「一键复制」

### 手动编辑

汉化组名称可手动编辑修改。「附加信息」区域中的汉化组字段支持自由填写。

## 安装与运行

### 环境要求

- Python 3.8+
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — 现代化 Tkinter UI 库
- [requests](https://pypi.org/project/requests/) — HTTP 请求库

### 安装依赖

```bash
pip install customtkinter requests
```

### 运行

```bash
python src/gui.py
```

或直接运行 `main.py`：

```bash
python main.py
```

## 项目结构

```
VNDB-GUI/
├── src/
│   ├── gui.py                     # 主界面 (CustomTkinter)
│   ├── app_version.py             # 版本信息
│   ├── core/
│   │   ├── vndb_api.py            # VNDB API 客户端 (数据模型 + 查询)
│   │   └── filename_generator.py  # 文件名生成逻辑
├── main.py                        # 入口文件
├── version.txt                    # 版本号
└── README.md
```

## 数据来源

所有数据来自 [VNDB](https://vndb.org/) 的 [API v2 (kana)](https://api.vndb.org/kana)。搜索时按以下字段查询：
- **Visual Novel**: `id, title, alttitle, titles{lang, title, latin}, image`
- **Release**: `id, title, alttitle, released, platforms, languages{lang}, producers{id, name, developer, publisher}, media{medium, qty}`