"""VNDB GUI - Visual Novel Filename Generator."""

from __future__ import annotations

import json
import os
import threading
import webbrowser
from typing import Callable, Any

import customtkinter as ctk

from app_version import get_app_version
from core.vndb_api import (
    VNDBAPIClient,
    VNDBError,
    VNDBNotFoundError,
    VNDBMultipleResultsError,
    VNCandidate,
    VNInfo,
    VNRelease,
    PLACEHOLDER,
)
from core.filename_generator import generate_filename, sanitize_filename
from core import colors_dark, colors_light
from core.colors_common import (
    COLOR_ACTIVE, COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_ERROR, COLOR_LINK,
    COLOR_COPY_BTN, COLOR_COPY_BTN_HOVER,
    COLOR_SIMPLE_COPY_BTN, COLOR_SIMPLE_COPY_BTN_HOVER,
    COLOR_LINK_BTN, COLOR_LINK_BTN_HOVER,
)
from ui_helpers import ui_font, DEFAULT_FORMAT_TEMPLATE
from widgets import ReleaseRow
from dialogs import CandidateDialog, CustomFormatDialog

APP_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_URL = "https://github.com/100pangci/VNDB-GUI"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".vndb-gui")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

ctk.set_default_color_theme("blue")


def _parse_date_to_int(released: str | None) -> int:
    """Parse 'YYYY-MM-DD' to int YYYYMMDD. Returns 0 for TBA/missing.

    Handles partial dates like '2026' or '2025-09'.
    Missing month/day parts are padded with '99' so that year-only
    (e.g. '2026') sorts at the END of that year, after any fully-specified
    dates like 2025-09-26.
    """
    if not released:
        return 0
    parts = released.split("-")
    parts = [p for p in parts if p]
    try:
        while len(parts) < 3:
            parts.append("99")
        return sum(int(p) * (10000 // (100 ** i)) for i, p in enumerate(parts[:3]))
    except (ValueError, IndexError):
        return 0


def _nonzh_sort_key(r: VNRelease) -> tuple:
    """Sort: ja first → en second → others; then ascending by date; TBA last."""
    has_ja = "ja" in r.languages
    has_en = "en" in r.languages
    if has_ja:
        lang_prio = 0
    elif has_en:
        lang_prio = 1
    else:
        lang_prio = 2
    date_val = _parse_date_to_int(r.released)
    tba = 1 if date_val == 0 else 0
    return (lang_prio, tba, date_val)


def _zh_sort_key(r: VNRelease) -> tuple:
    """Descending by date (newest first); TBA last."""
    date_val = _parse_date_to_int(r.released)
    tba = 1 if date_val == 0 else 0
    return (tba, -date_val)


class VNDBGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.geometry("960x820")
        self.minsize(840, 740)
        self.title(f"VNDB 文件名生成器 — {get_app_version()}")

        self.api_client = VNDBAPIClient()

        # --- State ---
        self._vn_info: VNInfo | None = None
        self._all_releases: list[VNRelease] = []
        self._nonzh_releases: list[VNRelease] = []
        self._zh_releases: list[VNRelease] = []
        self._searching = False

        # Selection state
        self._selected_nonzh_idx = 0
        self._selected_zh_idx = 0
        self._focus_side = "nonzh"

        # --- Variables ---
        self.query_var = ctk.StringVar(value="")
        self.query_var.trace_add("write", self._on_query_change)

        self.group_var = ctk.StringVar(value="")
        self.group_var.trace_add("write", self._on_manual_change)

        self._patch_date = ""
        self._language = "CHS"

        self._use_release_title = False
        self._sanitize_enabled = True
        self._suppress_manual_change = False

        self._is_dark = True
        self._appearance_mode = "System"

        self._custom_format_template = ctk.StringVar(value=DEFAULT_FORMAT_TEMPLATE)
        self._saved_format = ""
        self._pending_vndb_link_after: str | None = None
        self._link_btn_waiting = False

        self._load_config()

        self._build_header()
        self._build_query_row()
        self._build_release_panels()
        self._build_manual_card()
        self._build_preview_card()
        self._build_footer()

        self._update_preview()

    # ── Theme ───────────────────────────────────────────────────────

    def _toggle_theme(self) -> None:
        """切换深色/浅色主题并保存配置。"""
        self._is_dark = not self.theme_switch.get()
        self._appearance_mode = "Dark" if self._is_dark else "Light"
        ctk.set_appearance_mode(self._appearance_mode)
        self.theme_switch.configure(text="☀ 浅色" if self._is_dark else "🌙 深色")
        self._save_config()
        self._apply_theme_colors()
        self._refresh_release_lists()

    def _apply_theme_colors(self) -> None:
        """根据当前主题模式更新各组件的颜色。"""
        C = colors_dark if self._is_dark else colors_light

        self.panel_divider.configure(fg_color=C.COLOR_BORDER)
        self.left_frame.configure(border_color=C.COLOR_BORDER)
        self.right_frame.configure(border_color=C.COLOR_ZH_BORDER)
        self.left_header.configure(fg_color=C.COLOR_LEFT_HEADER_BG)
        self.right_header.configure(fg_color=C.COLOR_ZH_BG)
        self.left_scroll.configure(fg_color=C.COLOR_SCROLL_BG)
        self.right_scroll.configure(fg_color=C.COLOR_SCROLL_BG)
        self.manual_card.configure(border_color=C.COLOR_BORDER)
        self.subtitle_label.configure(text_color=C.COLOR_SUBTITLE_TEXT)
        if hasattr(self, 'custom_format_btn'):
            self.custom_format_btn.configure(
                border_color=C.COLOR_BORDER,
                hover_color=C.COLOR_CANDIDATE_HOVER,
                text_color=C.COLOR_FOOTER_BTN_TEXT,
            )

    # ── Custom Format ───────────────────────────────────────────────

    def _open_format_dialog(self) -> None:
        """打开自定义拼接格式对话框。"""
        CustomFormatDialog(self, self._custom_format_template, self._on_format_saved)

    def _on_format_saved(self, template: str) -> None:
        """保存用户自定义的格式模板并刷新预览。"""
        self._saved_format = template
        self._save_config()
        self._update_preview()

    def _load_config(self) -> None:
        """从 ~/.vndb-gui/config.json 加载外观与格式配置。"""
        try:
            if not os.path.exists(CONFIG_PATH):
                ctk.set_appearance_mode("System")
                return
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            mode = cfg.get("appearance_mode", "System")
            self._appearance_mode = mode
            ctk.set_appearance_mode(mode)
            self._is_dark = (ctk.get_appearance_mode() == "Dark")

            saved = cfg.get("format_template", "")
            if saved:
                self._custom_format_template.set(saved)
                self._saved_format = saved
        except (OSError, json.JSONDecodeError):
            ctk.set_appearance_mode("System")

    def _save_config(self) -> None:
        """保存当前外观与格式配置到 ~/.vndb-gui/config.json。"""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            cfg = {
                "appearance_mode": self._appearance_mode,
                "format_template": self._saved_format,
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ── UI Builders ──────────────────────────────────────────────────

    def _build_header(self) -> None:
        """构建顶部标题栏，含标题标签和主题切换开关。"""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(15, 0))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="VNDB 视觉小说文件名生成器",
            font=ui_font(22, "bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.theme_switch = ctk.CTkSwitch(
            self.header_frame,
            text="☀ 浅色" if self._is_dark else "🌙 深色",
            font=ui_font(12),
            command=self._toggle_theme,
            progress_color=COLOR_ACTIVE,
        )
        self.theme_switch.grid(row=0, column=1, sticky="e", padx=(10, 0))
        if self._is_dark:
            self.theme_switch.deselect()
        else:
            self.theme_switch.select()

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="输入 VNDB ID（如 v2622）或游戏原名，自动生成标准文件名",
            text_color="gray60",
            font=ui_font(13),
        )
        self.subtitle_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def _build_query_row(self) -> None:
        """构建搜索输入栏、搜索按钮和状态指示器。"""
        self.query_card = ctk.CTkFrame(self, corner_radius=10)
        self.query_card.pack(fill="x", padx=20, pady=(12, 0))
        self.query_card.grid_columnconfigure(0, weight=1)

        self.query_entry = ctk.CTkEntry(
            self.query_card,
            placeholder_text="输入 VNDB ID（如 v2622）或游戏原名…",
            textvariable=self.query_var,
            font=ui_font(13),
            height=36,
        )
        self.query_entry.grid(row=0, column=0, sticky="ew", padx=(15, 8), pady=(10, 10))
        self.query_entry.bind("<Return>", lambda e: self.search_api())

        self.search_btn = ctk.CTkButton(
            self.query_card,
            text="搜索 API",
            font=ui_font(13, "bold"),
            height=36,
            width=110,
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            command=self.search_api,
        )
        self.search_btn.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(10, 10))

        self.status_indicator = ctk.CTkLabel(
            self.query_card,
            text="",
            font=ui_font(11),
            text_color="gray50",
        )
        self.status_indicator.grid(row=0, column=2, sticky="w", padx=(8, 15), pady=(10, 10))

    def _build_release_panels(self) -> None:
        """Two side-by-side scrollable panels with clickable release rows."""
        C = colors_dark if self._is_dark else colors_light

        self.panel_frame = ctk.CTkFrame(self, corner_radius=10)
        self.panel_frame.pack(fill="both", expand=True, padx=20, pady=(8, 0))
        self.panel_frame.grid_columnconfigure(0, weight=1)
        self.panel_frame.grid_columnconfigure(2, weight=1)
        self.panel_frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self.panel_frame,
            text="选择发行版本",
            font=ui_font(15, "bold"),
        )
        header.grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(10, 6))

        # Vertical divider
        self.panel_divider = ctk.CTkFrame(
            self.panel_frame, width=2, corner_radius=0,
            fg_color=C.COLOR_BORDER,
        )
        self.panel_divider.grid(row=1, column=1, sticky="ns", padx=0, pady=(0, 10))

        # Left: Non-Chinese
        self.left_frame = ctk.CTkFrame(self.panel_frame, corner_radius=8,
                                       border_width=1, border_color=C.COLOR_BORDER)
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=(15, 8), pady=(0, 10))
        self.left_frame.grid_rowconfigure(2, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.left_header = ctk.CTkLabel(
            self.left_frame, text="非中文发行",
            font=ui_font(13, "bold"),
            fg_color=C.COLOR_LEFT_HEADER_BG, corner_radius=6,
        )
        self.left_header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 4))

        self.left_scroll = ctk.CTkScrollableFrame(
            self.left_frame, corner_radius=6,
            border_width=0,
            fg_color=C.COLOR_SCROLL_BG,
        )
        self.left_scroll.grid(row=2, column=0, sticky="nsew", padx=4, pady=2)
        self._bind_scroll_wheel(self.left_scroll)

        self.left_count = ctk.CTkLabel(
            self.left_frame, text="（请先搜索）",
            font=ui_font(11), text_color="gray50",
        )
        self.left_count.grid(row=3, column=0, sticky="w", padx=8, pady=(2, 6))

        # Right: Chinese
        self.right_frame = ctk.CTkFrame(self.panel_frame, corner_radius=8,
                                        border_width=1, border_color=C.COLOR_ZH_BORDER)
        self.right_frame.grid(row=1, column=2, sticky="nsew", padx=(8, 15), pady=(0, 10))
        self.right_frame.grid_rowconfigure(2, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.right_header = ctk.CTkLabel(
            self.right_frame, text="中文发行",
            font=ui_font(13, "bold"),
            fg_color=C.COLOR_ZH_BG, corner_radius=6,
        )
        self.right_header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 4))

        self.right_scroll = ctk.CTkScrollableFrame(
            self.right_frame, corner_radius=6,
            border_width=0,
            fg_color=C.COLOR_SCROLL_BG,
        )
        self.right_scroll.grid(row=2, column=0, sticky="nsew", padx=4, pady=2)
        self._bind_scroll_wheel(self.right_scroll)

        self.right_count = ctk.CTkLabel(
            self.right_frame, text="（请先搜索）",
            font=ui_font(11), text_color="gray50",
        )
        self.right_count.grid(row=3, column=0, sticky="w", padx=(8, 2), pady=(2, 6))

    def _build_manual_card(self) -> None:
        """构建手动输入区域，含标题模式选择和汉化组输入框。"""
        C = colors_dark if self._is_dark else colors_light
        self.manual_card = ctk.CTkFrame(self, corner_radius=10, border_width=1, border_color=C.COLOR_BORDER)
        self.manual_card.pack(fill="x", padx=20, pady=(6, 0))
        self.manual_card.grid_columnconfigure(2, weight=1)

        self.manual_header_frame = ctk.CTkFrame(self.manual_card, fg_color="transparent")
        self.manual_header_frame.grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(10, 8))

        self.title_mode_var = ctk.StringVar(value="游戏标题")
        self.title_mode_btn = ctk.CTkSegmentedButton(
            self.manual_header_frame,
            values=["游戏标题", "发行版标题"],
            variable=self.title_mode_var,
            font=ui_font(11),
            height=26,
            command=self._on_title_mode_change,
        )
        self.title_mode_btn.pack(side="left", padx=(0, 12))

        self.manual_label = ctk.CTkLabel(
            self.manual_header_frame,
            text="附加信息（点击中文发行列表自动填入）",
            font=ui_font(15, "bold"),
        )
        self.manual_label.pack(side="left")

        self.group_label = ctk.CTkLabel(self.manual_card, text="汉化组：", font=ui_font(12, "bold"))
        self.group_label.grid(row=1, column=0, sticky="w", padx=(15, 5), pady=(0, 10))
        self.group_entry = ctk.CTkEntry(
            self.manual_card,
            placeholder_text="如：Makura Castle（点击中文发行列表自动填入）",
            textvariable=self.group_var,
            font=ui_font(12),
            height=30,
        )
        self.group_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0, 15), pady=(0, 10))

    def _build_preview_card(self) -> None:
        """构建文件名预览区域，含预览文本框、复制按钮和非法字符替换开关。"""
        self.preview_card = ctk.CTkFrame(self, corner_radius=10)
        self.preview_card.pack(fill="x", padx=20, pady=(8, 0))
        self.preview_card.grid_columnconfigure(0, weight=1)

        self.preview_header_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.preview_header_frame.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 6))

        self.preview_label = ctk.CTkLabel(
            self.preview_header_frame,
            text="文件名预览",
            font=ui_font(15, "bold"),
        )
        self.preview_label.pack(side="left")

        self.link_copy_btn = ctk.CTkButton(
            self.preview_header_frame,
            text="复制页面链接",
            font=ui_font(12, "bold"),
            height=28,
            width=100,
            fg_color=COLOR_LINK_BTN,
            hover_color=COLOR_LINK_BTN_HOVER,
            command="",
        )
        self.link_copy_btn.pack(side="left", padx=(6, 0))
        self.link_copy_btn.bind("<Button-1>", self._on_vndb_link_click)

        self.sanitize_switch = ctk.CTkSwitch(
            self.preview_card,
            text="非法字符替换",
            font=ui_font(12),
            command=self._on_sanitize_toggle,
        )
        self.sanitize_switch.grid(row=0, column=1, sticky="e", padx=(0, 15), pady=(10, 6))
        self.sanitize_switch.select()

        self.preview_text = ctk.CTkTextbox(
            self.preview_card,
            font=ui_font(13),
            height=44,
            corner_radius=8,
            wrap="none",
        )
        self.preview_text.grid(row=1, column=0, sticky="nsew", padx=(15, 8), pady=(0, 10))
        self.preview_text.insert("1.0", "（等待搜索）")
        self.preview_text.configure(state="disabled")

        self.btn_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.btn_frame.grid(row=1, column=1, sticky="ns", padx=(0, 15), pady=(0, 10))

        self.copy_btn = ctk.CTkButton(
            self.btn_frame,
            text="一键复制",
            font=ui_font(13, "bold"),
            height=36,
            width=100,
            fg_color=COLOR_COPY_BTN,
            hover_color=COLOR_COPY_BTN_HOVER,
            command=self.copy_filename,
        )
        self.copy_btn.pack(fill="x", pady=(0, 4))

        self.simple_copy_btn = ctk.CTkButton(
            self.btn_frame,
            text="复制简要标题",
            font=ui_font(13, "bold"),
            height=36,
            width=100,
            fg_color=COLOR_SIMPLE_COPY_BTN,
            hover_color=COLOR_SIMPLE_COPY_BTN_HOVER,
            command=self.copy_simplified_title,
        )
        self.simple_copy_btn.pack(fill="x")

    def _build_footer(self) -> None:
        """构建底部栏，含自定义格式按钮、版权信息和项目链接。"""
        C = colors_dark if self._is_dark else colors_light
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(fill="x", padx=20, pady=(6, 10))

        self.custom_format_btn = ctk.CTkButton(
            self.footer_frame,
            text="自定义拼接格式",
            font=ui_font(12),
            height=30,
            width=140,
            fg_color="transparent",
            border_width=1,
            border_color=C.COLOR_BORDER,
            hover_color=C.COLOR_FOOTER_BTN_HOVER,
            text_color=C.COLOR_FOOTER_BTN_TEXT,
            command=self._open_format_dialog,
        )
        self.custom_format_btn.pack(side="left")

        self.info_label = ctk.CTkLabel(
            self.footer_frame,
            text="基于 VNDB API v2 ｜ 自动过滤 Windows 非法字符 ｜ 缺失信息显示「NO DATA」",
            text_color="gray50",
            font=ui_font(11),
        )
        self.info_label.pack(side="left", padx=(15, 0))

        self.project_link_label = ctk.CTkLabel(
            self.footer_frame,
            text=PROJECT_URL,
            text_color=COLOR_LINK,
            cursor="hand2",
            font=ui_font(11, "bold"),
        )
        self.project_link_label.pack(side="right")
        self.project_link_label.bind("<Button-1>", lambda e: self.open_project_link())

    # ── List Population ─────────────────────────────────────────────

    def _rebuild_nonzh_rows(self) -> None:
        """Clear and rebuild the non-zh scrollable row list."""
        for w in self.left_scroll.winfo_children():
            w.destroy()

        if not self._nonzh_releases:
            lbl = ctk.CTkLabel(self.left_scroll, text="（无发行版本）",
                               font=ui_font(12), text_color="gray50")
            lbl.pack(pady=20)
            return

        for i, r in enumerate(self._nonzh_releases):
            row = ReleaseRow(self.left_scroll, r, i == self._selected_nonzh_idx,
                             self._on_nonzh_click, i, zh_mode=False,
                             is_dark=self._is_dark)
            row.pack(fill="x", padx=4, pady=1)

    def _rebuild_zh_rows(self) -> None:
        """Clear and rebuild the zh scrollable row list."""
        for w in self.right_scroll.winfo_children():
            w.destroy()

        if not self._zh_releases:
            lbl = ctk.CTkLabel(self.right_scroll, text="（无中文版本）",
                               font=ui_font(12), text_color="gray50")
            lbl.pack(pady=20)
            return

        for i, r in enumerate(self._zh_releases):
            row = ReleaseRow(self.right_scroll, r, i == self._selected_zh_idx,
                             self._on_zh_click, i, zh_mode=True,
                             is_dark=self._is_dark)
            row.pack(fill="x", padx=4, pady=1)

    def _refresh_release_lists(self) -> None:
        """刷新两栏发行版本列表并重置滚动位置。"""
        self._rebuild_nonzh_rows()
        self._rebuild_zh_rows()
        self.left_count.configure(text=f"共 {len(self._nonzh_releases)} 个版本")
        self.right_count.configure(text=f"共 {len(self._zh_releases)} 个版本")

        self.left_scroll._parent_canvas.yview_moveto(0)
        self.right_scroll._parent_canvas.yview_moveto(0)

        active = self._get_active_release()
        self._update_preview(active)

    def _on_nonzh_click(self, idx: int) -> None:
        """点击非中文版本的行，切换焦点并更新预览。"""
        self._focus_side = "nonzh"
        self._selected_nonzh_idx = idx
        r = self._nonzh_releases[idx]
        if r.languages:
            self._language = r.languages[0].upper()
        self._update_selection_on_side("nonzh")
        self._update_selection_on_side("zh")
        self.left_count.configure(text=f"共 {len(self._nonzh_releases)} 个版本")
        self.right_count.configure(text=f"共 {len(self._zh_releases)} 个版本")
        active = self._get_active_release()
        self._update_preview(active)

    def _on_zh_click(self, idx: int) -> None:
        """点击中文版本的行，自动填入汉化组、补丁日期和语言信息。"""
        self._focus_side = "zh"
        self._selected_zh_idx = idx

        r = self._zh_releases[idx]
        grp = r.get_non_developer_group_name()
        self._suppress_manual_change = True
        if grp:
            self.group_var.set(grp)
        self._suppress_manual_change = False
        patch_date = r.format_released()
        if patch_date and patch_date != PLACEHOLDER:
            self._patch_date = patch_date
        if "zh-Hans" in r.languages:
            self._language = "CHS"
        elif "zh-Hant" in r.languages:
            self._language = "CHT"
        elif "zh" in r.languages:
            self._language = "CHS"

        self._update_selection_on_side("nonzh")
        self._update_selection_on_side("zh")
        self.left_count.configure(text=f"共 {len(self._nonzh_releases)} 个版本")
        self.right_count.configure(text=f"共 {len(self._zh_releases)} 个版本")
        active = self._get_active_release()
        self._update_preview(active)

    def _update_selection_on_side(self, side: str) -> None:
        """Update selection visuals on existing rows without destroying/recreating widgets."""
        scroll = self.left_scroll if side == "nonzh" else self.right_scroll
        selected_idx = self._selected_nonzh_idx if side == "nonzh" else self._selected_zh_idx
        for child in scroll.winfo_children():
            if isinstance(child, ReleaseRow):
                child.set_selected(child.row_index == selected_idx)
            elif hasattr(child, 'winfo_children'):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, ReleaseRow):
                        grandchild.set_selected(grandchild.row_index == selected_idx)

    # ── Event Handlers ──────────────────────────────────────────────

    @staticmethod
    def _bind_scroll_wheel(scroll_frame: ctk.CTkScrollableFrame) -> None:
        """Bind mouse wheel on the scrollable frame for smooth scrolling."""
        def _on_mousewheel(event):
            scroll_frame._parent_canvas.yview_scroll(int(-9 * (event.delta / 120)), "units")
        scroll_frame.bind("<MouseWheel>", _on_mousewheel, add=True)

    def _on_query_change(self, *args) -> None:
        """搜索框文本变化时的回调（当前无操作，保留供扩展）。"""
        pass

    def _on_manual_change(self, *args) -> None:
        """手动输入框内容变化时刷新预览。"""
        if self._suppress_manual_change:
            return
        active = self._get_active_release()
        self._update_preview(active)

    def _on_title_mode_change(self, value: str) -> None:
        """标题模式切换时刷新预览。"""
        self._use_release_title = (value == "发行版标题")
        active = self._get_active_release()
        self._update_preview(active)

    def _on_sanitize_toggle(self) -> None:
        """非法字符替换开关切换时刷新预览。"""
        self._sanitize_enabled = bool(self.sanitize_switch.get())
        active = self._get_active_release()
        self._update_preview(active)

    def _get_active_release(self) -> VNRelease | None:
        """返回当前焦点所在的发行版本对象。"""
        if self._focus_side == "nonzh" and self._nonzh_releases:
            return self._nonzh_releases[self._selected_nonzh_idx]
        if self._focus_side == "zh" and self._zh_releases:
            return self._zh_releases[self._selected_zh_idx]
        if self._nonzh_releases:
            return self._nonzh_releases[self._selected_nonzh_idx]
        if self._zh_releases:
            return self._zh_releases[self._selected_zh_idx]
        return None

    def _get_base_release(self) -> VNRelease | None:
        """返回用于生成文件名的基准发行版本（优先非中文版）。"""
        if self._nonzh_releases:
            return self._nonzh_releases[self._selected_nonzh_idx]
        if self._zh_releases:
            return self._zh_releases[self._selected_zh_idx]
        return None

    # ── API Search ──────────────────────────────────────────────────

    def _run_api_call(self, fn: Callable, on_success: Callable, *args) -> None:
        """在线程中执行 API 调用并统一处理异常。"""
        try:
            result = fn(*args)
        except VNDBMultipleResultsError as e:
            err_msg = str(e)
            candidates = e.candidates
            self.after(0, lambda: self._on_multiple_candidates(err_msg, candidates))
            return
        except VNDBNotFoundError as e:
            err_msg = str(e)
            self.after(0, lambda err_msg=err_msg: self._on_search_error(err_msg))
            return
        except VNDBError as e:
            err_msg = str(e)
            self.after(0, lambda err_msg=err_msg: self._on_search_error(err_msg))
            return
        except Exception as e:
            err_msg = f"未知错误：{e}"
            self.after(0, lambda err_msg=err_msg: self._on_search_error(err_msg))
            return
        self.after(0, lambda: on_success(result))

    def search_api(self) -> None:
        """触发 VNDB API 搜索，在新线程中执行。"""
        query = self.query_var.get().strip()
        if not query:
            self._set_status("请输入 VNDB ID 或游戏名称", is_error=True)
            return
        if self._searching:
            return

        self._searching = True
        self.search_btn.configure(state="disabled", text="搜索中…")
        self.status_indicator.configure(text="正在查询 VNDB API…", text_color="gray60")

        thread = threading.Thread(target=self._do_search, args=(query,), daemon=True)
        thread.start()

    def _do_search(self, query: str) -> None:
        """在线程中执行搜索，使用 _run_api_call 处理异常。"""
        self._run_api_call(self.api_client.search_vn, self._on_search_success, query)

    def _on_multiple_candidates(self, message: str, candidates: list[VNCandidate]) -> None:
        """弹出多结果选择对话框，让用户手动选择目标 VN。"""
        dialog = CandidateDialog(self, candidates)
        self.wait_window(dialog)
        selected = dialog.get_selected()
        if selected is None:
            self._searching = False
            self.search_btn.configure(state="normal", text="搜索 API")
            self.status_indicator.configure(text="已取消选择", text_color="gray60")
            return

        self.status_indicator.configure(
            text=f"正在获取 {selected.id}…",
            text_color="gray60",
        )
        thread = threading.Thread(
            target=self._do_fetch_selected,
            args=(selected.id,),
            daemon=True,
        )
        thread.start()

    def _do_fetch_selected(self, vn_id: str) -> None:
        """在线程中获取选择的 VN，使用 _run_api_call 处理异常。"""
        self._run_api_call(self.api_client.fetch_vn_by_id, self._on_search_success, vn_id)

    def _on_search_success(self, vn_info: VNInfo) -> None:
        """搜索成功后的 UI 更新：分类版本列表、排序、自动选择中文版本。"""
        self._vn_info = vn_info
        self._all_releases = vn_info.releases

        self._nonzh_releases = [r for r in self._all_releases if not r.is_chinese_release()]
        self._zh_releases = [r for r in self._all_releases if r.is_chinese_release()]

        self._nonzh_releases.sort(key=_nonzh_sort_key)
        self._zh_releases.sort(key=_zh_sort_key)

        self._selected_nonzh_idx = 0
        self._selected_zh_idx = 0
        self._focus_side = "zh" if self._zh_releases else "nonzh"

        if self._zh_releases:
            r = self._zh_releases[0]
            grp = r.get_non_developer_group_name()
            if grp:
                self.group_var.set(grp)
            patch_date = r.format_released()
            if patch_date and patch_date != PLACEHOLDER:
                self._patch_date = patch_date
            if "zh-Hans" in r.languages:
                self._language = "CHS"
            elif "zh-Hant" in r.languages:
                self._language = "CHT"
            elif "zh" in r.languages:
                self._language = "CHS"
        elif self._nonzh_releases:
            r = self._nonzh_releases[0]
            if r.languages:
                self._language = r.languages[0].upper()

        self._refresh_release_lists()

        self._searching = False
        self.search_btn.configure(state="normal", text="搜索 API")

        self.status_indicator.configure(
            text=f"✓ 找到 {len(self._all_releases)} 个发行版本（非中文 {len(self._nonzh_releases)}，中文 {len(self._zh_releases)}）",
            text_color=COLOR_SUCCESS,
        )

    def _on_search_error(self, error_msg: str) -> None:
        """搜索或获取失败时重置状态并显示错误信息。"""
        self._searching = False
        self.search_btn.configure(state="normal", text="搜索 API")
        self.status_indicator.configure(text=f"✗ {error_msg}", text_color=COLOR_ERROR)
        self._vn_info = None
        self._all_releases = []
        self._nonzh_releases = []
        self._zh_releases = []
        self._refresh_release_lists()

    # ── Preview ─────────────────────────────────────────────────────

    def _generate_custom_filename(self, template: str, vn_info: VNInfo, release: VNRelease) -> str:
        """根据用户自定义模板生成文件名，替换模板中的占位变量。"""
        if "{patch_date}" not in template:
            active = self._get_active_release()
            date_val = active.format_released() if active else release.format_released()
        else:
            date_val = release.format_released()
        parts: dict[str, str] = {
            "developer": release.get_developer_name() or PLACEHOLDER,
            "date": date_val,
            "title": vn_info.get_original_title() if not self._use_release_title else release.get_display_title(),
            "vid": f"v{vn_info.id.lstrip('v')}" if vn_info.id else PLACEHOLDER,
            "platform": release.get_platforms_display().replace(", ", "_") if release.get_platforms_display() != PLACEHOLDER else PLACEHOLDER,
            "group": self.group_var.get().strip() or PLACEHOLDER,
            "patch_date": self._patch_date if self._patch_date else "",
            "language": self._language.upper(),
        }
        result = template
        for key, value in parts.items():
            result = result.replace("{" + key + "}", sanitize_filename(value, enabled=self._sanitize_enabled))
        return result

    def _update_preview(self, *args) -> None:
        """刷新文件名预览文本框的内容。"""
        if not self._vn_info:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "（等待搜索）")
            self.preview_text.configure(state="disabled")
            return

        base = self._get_base_release()
        if not base:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "（请选择原版发行）")
            self.preview_text.configure(state="disabled")
            return

        if self._saved_format:
            filename = self._generate_custom_filename(self._saved_format, self._vn_info, base)
        else:
            filename = generate_filename(
                self._vn_info,
                base,
                group_name=self.group_var.get(),
                patch_date=self._patch_date,
                language=self._language,
                use_release_title=self._use_release_title,
                sanitize=self._sanitize_enabled,
            )

        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", filename)
        self.preview_text.configure(state="disabled")

    def copy_filename(self) -> None:
        """将当前预览的文件名复制到剪贴板。"""
        content = self.preview_text.get("1.0", "end-1c")
        if content and content not in ("（等待搜索）", "（请选择发行版本）"):
            self.clipboard_clear()
            self.clipboard_append(content)
            self.status_indicator.configure(text="✓ 已复制到剪贴板", text_color=COLOR_SUCCESS)
            self.after(3000, lambda: self._reset_status_text())

    def copy_simplified_title(self) -> None:
        """复制简化标题（【汉化组】游戏原名）到剪贴板。"""
        if not self._vn_info:
            return

        base = self._get_base_release()
        if not base:
            return

        if self._use_release_title:
            title = base.get_display_title()
        else:
            title = self._vn_info.get_original_title()

        group = self.group_var.get().strip()

        simplified = f"【{group}】{title}" if group else title
        simplified = sanitize_filename(simplified, enabled=self._sanitize_enabled)

        self.clipboard_clear()
        self.clipboard_append(simplified)
        self.status_indicator.configure(text="✓ 已复制简要标题", text_color=COLOR_SUCCESS)
        self.after(3000, lambda: self._reset_status_text())

    def _get_vndb_url(self) -> str | None:
        if not self._vn_info or not self._vn_info.id:
            return None
        return f"https://vndb.org/{self._vn_info.id}"

    def _on_vndb_link_click(self, event: Any) -> None:
        if self._link_btn_waiting:
            if self._pending_vndb_link_after:
                self.after_cancel(self._pending_vndb_link_after)
                self._pending_vndb_link_after = None
            self._link_btn_waiting = False
            self.link_copy_btn.configure(text="复制页面链接")
            self._open_vndb_link()
        else:
            self._copy_vndb_link()
            self._link_btn_waiting = True
            self.link_copy_btn.configure(text="再次点击打开链接")
            self._pending_vndb_link_after = self.after(3000, self._reset_link_btn)

    def _open_vndb_link(self) -> None:
        url = self._get_vndb_url()
        if url:
            webbrowser.open_new_tab(url)

    def _copy_vndb_link(self) -> None:
        url = self._get_vndb_url()
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            self.status_indicator.configure(text="✓ 已复制VNDB链接", text_color=COLOR_SUCCESS)
            self.after(3000, lambda: self._reset_status_text())

    def _reset_link_btn(self) -> None:
        self._pending_vndb_link_after = None
        self._link_btn_waiting = False
        self.link_copy_btn.configure(text="复制页面链接")

    def _reset_status_text(self) -> None:
        """3 秒后将状态文字重置为版本计数。"""
        if self._vn_info and self._all_releases:
            self.status_indicator.configure(
                text=f"✓ 找到 {len(self._all_releases)} 个发行版本",
                text_color=COLOR_SUCCESS,
            )
        else:
            self.status_indicator.configure(text="", text_color="gray50")

    def _set_status(self, text: str, is_error: bool = False) -> None:
        """设置状态指示器的文字和颜色。"""
        color = COLOR_ERROR if is_error else "gray60"
        self.status_indicator.configure(text=text, text_color=color)

    def open_project_link(self) -> None:
        """在浏览器中打开项目 GitHub 链接。"""
        webbrowser.open_new_tab(PROJECT_URL)


if __name__ == "__main__":
    app = VNDBGUI()
    app.mainloop()
