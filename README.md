# VNDB-GUI

> VNDB 视觉小说文件名生成器 — 基于 [VNDB API v2 (kana)](https://api.vndb.org/kana) 的桌面工具，自动生成标准化的文件名。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MPL--2.0-orange)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

---

## ✨ 功能特点

### 📦 核心功能

- **🔍 智能搜索** — 输入 VNDB ID（如 `v2622`）或游戏原名，自动获取视觉小说信息及所有发行版本
- **📋 多结果选择** — 标题搜索返回多个匹配时，弹出候选列表供用户精确选择
- **🔄 双列布局** — 左侧「非中文发行」显示非中文版本，右侧「中文发行」显示中文版本，一目了然
- **🧠 智能排序** — 非中文发行优先按日语语言排序，再按日期降序排列；中文发行按日期降序排列
- **🏷️ 文件名生成** — 自动生成标准格式文件名，格式如下：

  ```
  [开发商][发售日期]原版标题[vID][平台][汉化组][汉化补丁日期][语言标签]
  ```

- **📋 一键复制** — 点击「一键复制」按钮将文件名复制到剪贴板
- **📋 简要标题** — 点击「复制简要标题」以 `【汉化组】游戏原名` 格式复制简化版标题
- **🔗 页面链接** — 「复制页面链接」按钮：单击复制 VNDB 页面地址（如 `https://vndb.org/v57740`），再次点击直接打开浏览器访问
- **🛡️ 非法字符替换** — Windows 非法字符自动替换为全角等效字符（`:?/\*"<>|`），可通过开关自由关闭

### 🎯 高级功能

- **🎭 标题模式切换** — 可选择使用「游戏原名」或「发行版标题」作为文件名中的标题
- **✏️ 汉化组手动编辑** — 汉化组名称支持自由编辑修改，预览实时更新
- **🧩 自定义拼接格式** — 通过底栏按钮打开格式编辑器，使用 `{developer}` `{date}` `{title}` `{vid}` `{platform}` `{group}` `{patch_date}` `{language}` 等变量自由组合文件名格式，点击变量标签即可插入
- **🖱️ 鼠标滚轮支持** — 发行版本列表支持鼠标滚轮流畅滚动
- **🌓 主题切换** — 默认跟随系统自动切换深色/浅色模式，也可通过顶栏开关手动覆盖
- **💾 配置持久化** — 主题偏好和自定义格式模板自动保存到 `~/.vndb-gui/config.json`，重启后恢复
- **⛔ 错误处理** — 完善的错误处理机制：网络超时、连接失败、未找到、请求频率限制等均有友好提示

---

## 📁 文件名格式

```
[developer][YYYYMMDD]original_title[vVNDB_ID][platform][group][patch_date][language]
```

### 示例

| 字段 | 值 |
|------|------|
| 开发商 | ゆずソフト |
| 发售日期 | 20160729 |
| 游戏标题 | 千恋＊万花 |
| VNDB ID | v19073 |
| 平台 | Windows |
| 汉化组 | 落樱汉化组 |
| 补丁日期 | 20171111 |
| 语言 | CHS |

生成的文件名：

```
[ゆずソフト][20160729]千恋＊万花[v19073][Windows][落樱汉化组][20171111][CHS]
```

### 多平台示例

```
[ALcot][20090918]幼なじみは大統領 My girlfriend is the PRESIDENT.[v2622][Windows][Makura Castle][20130314][CHS]
```

当缺失信息时，对应字段显示 `[NO DATA]`。

---

## 🚀 使用方法

### 基本流程

1. **🔎 搜索** — 在输入框中输入 VNDB ID（如 `v19073`）或游戏原名，点击「搜索 API」或按 Enter 键
2. **🎯 选择原版发行** — 在左侧「非中文发行」列表点击选择非中文版本（开发商、日期、标题、平台来自此版本）
3. **🇨🇳 选择中文发行版** — 搜索完成后首个中文版本的汉化组、补丁日期、语言会自动填入；也可在右侧「中文发行」列表点击其他版本切换
4. **📋 预览与复制** — 确认文件名预览无误后点击「一键复制」，或点击「复制简要标题」获取简化版，也可点击「复制页面链接」快速获取当前 VN 的 VNDB 页面地址

### 标题模式

- **游戏标题**（默认）— 使用视觉小说在 VNDB 上的原始日文标题
- **发行版标题** — 使用所选发行版本的标题（适用于发行版标题与游戏标题不同的情况）

### 手动编辑

汉化组名称可在「附加信息」区域自由编辑修改，预览将实时更新。

### 自定义格式

点击底部「自定义拼接格式」按钮打开格式编辑器，可使用以下变量自由组合文件名：

| 变量 | 含义 | 示例值 |
|------|------|--------|
| `{developer}` | 开发商 | ゆずソフト |
| `{date}` | 发售日期 | 20160729 |
| `{title}` | 游戏标题 | 千恋＊万花 |
| `{vid}` | VNDB ID | v19073 |
| `{platform}` | 平台 | Windows |
| `{group}` | 汉化组 | 落樱汉化组 |
| `{patch_date}` | 补丁日期 | 20171111 |
| `{language}` | 语言 | CHS |

点击变量标签可快速插入，按 Enter 保存。保存后自定义格式会覆盖默认格式。点击「恢复默认」可重置为预设模板。

---

## 📦 安装与运行

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
python main.py
```

或直接运行 GUI 模块：

```bash
python src/gui.py
```

---

## 🔨 打包为可执行文件

项目提供了 Windows 和 Linux 两种打包脚本，均使用 PyInstaller 打包为单个可执行文件。

### Windows

```batch
build_gui_exe.bat
```

打包完成后，可执行文件生成在 `release\` 目录下。

如需指定版本号（默认为 `dev`）：

```batch
set VNDB_GUI_VERSION=1.0.0
build_gui_exe.bat
```

### Linux

```bash
chmod +x build_gui_linux.sh
./build_gui_linux.sh
```

可选指定版本号：

```bash
VNDB_GUI_VERSION=1.0.0 ./build_gui_linux.sh
```

打包完成后，可执行文件生成在 `release/` 目录下。

---

## 📂 项目结构

```
VNDB-GUI/
├── src/
│   ├── gui.py                         # 主窗口 (VNDBGUI) — 界面布局与事件处理
│   ├── ui_helpers.py                  # 共享 UI 工具 (字体、对话框居中、格式模板)
│   ├── widgets.py                     # 可复用组件 (ReleaseRow 发行版本行)
│   ├── dialogs.py                     # 模态对话框 (候选选择、自定义格式编辑)
│   ├── app_version.py                 # 版本信息读取
│   ├── core/
│   │   ├── __init__.py
│   │   ├── colors_common.py           # 通用配色常量 (语义颜色、功能按钮色)
│   │   ├── colors_dark.py             # 深色主题配色方案
│   │   ├── colors_light.py            # 浅色主题配色方案
│   │   ├── vndb_api.py                # VNDB API v2 客户端 (数据模型 + 查询)
│   │   └── filename_generator.py      # 文件名生成与非法字符过滤
├── test/
│   ├── test_api.py
│   ├── test_api2.py
│   ├── test_api3.py
│   └── test_debug_v50215.py
├── main.py                            # 程序入口
├── version.txt                        # 版本号 (当前: 1.0.0)
├── build_gui_exe.bat                  # Windows 打包脚本 (PyInstaller)
├── build_gui_linux.sh                 # Linux 打包脚本 (PyInstaller)
├── LICENSE                            # MPL-2.0 开源协议
└── README.md                          # 本文件
```

---

## 🏗️ 技术架构

### 模块说明

| 模块 | 文件 | 职责 |
|------|------|------|
| **主窗口** | `src/gui.py` | `VNDBGUI` 主窗口类 — 界面布局、搜索调度、预览生成、复制操作 |
| **UI 工具** | `src/ui_helpers.py` | 共享字体工厂 `ui_font()`、对话框居中 `center_dialog()`、默认格式模板 |
| **组件** | `src/widgets.py` | `ReleaseRow` 可复用组件 — 发行版本列表中可点击的每一行 |
| **对话框** | `src/dialogs.py` | `CandidateDialog` 多结果选择、`CustomFormatDialog` 自定义格式编辑 |
| **API 客户端** | `src/core/vndb_api.py` | VNDB API v2 的 HTTP 客户端，处理认证、分页、错误映射。包含数据模型（`VNInfo`、`VNRelease`、`VNCandidate` 等） |
| **文件名生成器** | `src/core/filename_generator.py` | 根据 VN 信息和发行版本生成标准文件名，包含 Windows 非法字符替换逻辑 |
| **配色方案** | `src/core/colors_{common,dark,light}.py` | 通用/深色/浅色主题配色常量集中管理 |
| **版本管理** | `src/app_version.py` | 支持从文件、环境变量读取版本号，兼容 PyInstaller 打包后的资源路径 |

### 数据模型

```
VNCandidate       — 搜索结果候选（轻量级 VN 信息）
VNInfo            — 完整 VN 信息（含关联发行版本列表）
VNRelease         — 单个发行版本（含开发商、平台、语言、媒体信息）
Producer          — 厂商信息（开发商/发行商标记）
```

### API 查询字段

搜索时按以下字段从 VNDB API 获取数据：

- **Visual Novel**: `id, title, alttitle, titles{lang, title, latin}, image{url,dims,sexual,violence,votecount}`
- **Release**: `id, title, alttitle, released, platforms, languages{lang}, producers{id, name, original, developer, publisher}, media{medium, qty}, extlinks{url, label}`

### 错误处理

| 错误类型 | 触发条件 | 处理方式 |
|----------|----------|----------|
| `VNDBNotFoundError` | VN 未找到 | 界面显示未找到提示 |
| `VNDBMultipleResultsError` | 标题搜索返回多个结果 | 弹出候选对话框让用户选择 |
| `VNDBError` | 网络超时/连接失败/频率限制 | 界面显示具体错误描述 |

### 平台映射

VNDB API 返回的平台代码（如 `win`）自动映射为完整名称：

`win` → `Windows` · `lin` → `Linux` · `mac` → `MacOS` · `swi` → `Switch` · `ps4` → `PlayStation 4` · 等（共 20+ 平台）

### 语言解析

中文语言代码按以下规则解析为文件名标签：

- `zh-Hans` → `CHS`（简体中文）
- `zh-Hant` → `CHT`（繁体中文）
- `zh` → `CHS`（默认简体）
- 其他语言保留原始代码

---

## 🔗 数据来源

所有数据来自 [VNDB](https://vndb.org/) 的 [API v2 (kana)](https://api.vndb.org/kana)。

---

## 📜 许可证

本项目使用 [Mozilla Public License Version 2.0](https://mozilla.org/MPL/2.0/) (MPL-2.0) 开源协议。

详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献

欢迎提交 Issue 或 Pull Request！

- GitHub 仓库: [https://github.com/100pangci/VNDB-GUI](https://github.com/100pangci/VNDB-GUI)
- 项目主页: [https://github.com/100pangci/VNDB-GUI](https://github.com/100pangci/VNDB-GUI)