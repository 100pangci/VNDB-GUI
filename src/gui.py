"""VNDB GUI - Visual Novel Filename Generator."""

from __future__ import annotations

import os
import sys
import threading
import webbrowser

import customtkinter as ctk

from app_version import get_app_version
from core.vndb_api import VNDBAPIClient, VNDBError, VNDBNotFoundError, VNInfo, VNRelease, PLACEHOLDER
from core.filename_generator import generate_filename, get_release_preview, sanitize_filename

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UI_FONT_FAMILY = "Microsoft YaHei UI"

PROJECT_URL = "https://github.com/100pangci/VNDB-GUI"

# Colors
COLOR_ACTIVE = "#3a7bd5"
COLOR_HOVER = "#2a5bb5"
COLOR_BORDER = "#444444"
COLOR_ZH_BG = "#3a2010"
COLOR_ZH_BORDER = "#5a3020"


def ui_font(size=12, weight="normal"):
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight=weight)


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ReleaseRow(ctk.CTkFrame):
    """A single clickable row in a release list."""

    def __init__(self, master, release: VNRelease, is_selected: bool,
                 on_click, row_index: int, zh_mode: bool = False, **kwargs):
        border = COLOR_ZH_BORDER if zh_mode else COLOR_BORDER
        super().__init__(master, corner_radius=6, border_width=1,
                         border_color=border, **kwargs)

        self.release = release
        self.row_index = row_index
        self.is_selected = is_selected
        self._on_click = on_click
        self.zh_mode = zh_mode

        # Selection indicator
        self.indicator = ctk.CTkLabel(self, text="", width=4, corner_radius=2)
        self.indicator.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(4, 2))

        # Title
        display = release.get_display_title()
        self.title_lbl = ctk.CTkLabel(
            self, text=display, font=ui_font(12, "bold"),
            anchor="w", wraplength=280,
        )
        self.title_lbl.grid(row=0, column=1, sticky="w", padx=(4, 8), pady=(4, 0))

        # Info line: depends on zh_mode
        if zh_mode:
            # Chinese release: show group name + date
            group = release.get_non_developer_group_name()
            if group and group != PLACEHOLDER:
                info = group
            else:
                info = "汉化组未知"
            date_str = release.released or "????-??-??"
            info += f"  |  {date_str}"
        else:
            # Non-Chinese release: show developer + date + platform + languages
            dev = release.get_developer_name()
            if dev and dev != PLACEHOLDER:
                info = dev
            else:
                info = "?"
            date_str = release.released or "????-??-??"
            plat_str = release.get_platforms_display()
            lang_str = release.get_languages_display()
            info += f"  |  {date_str}  |  {plat_str}  |  {lang_str}"

        self.info_lbl = ctk.CTkLabel(
            self, text=info, font=ui_font(11),
            text_color="gray60", anchor="w",
        )
        self.info_lbl.grid(row=1, column=1, sticky="w", padx=(4, 8), pady=(0, 4))

        self._apply_selection()

        # Bind click on entire card
        for widget in (self, self.indicator, self.title_lbl, self.info_lbl):
            widget.bind("<Button-1>", self._handle_click)
            widget.bind("<Enter>", lambda e: self.configure(fg_color="#2a2a2a")
                        if not self.is_selected else None)
            widget.bind("<Leave>", lambda e: self.configure(fg_color="transparent")
                        if not self.is_selected else None)

        self.grid_columnconfigure(1, weight=1)

    def _handle_click(self, event):
        self._on_click(self.row_index)

    def set_selected(self, sel: bool):
        self.is_selected = sel
        self._apply_selection()

    def _apply_selection(self):
        if self.is_selected:
            self.configure(fg_color="#2a3d5a")
            self.indicator.configure(text="▌", text_color=COLOR_ACTIVE, font=ui_font(14))
        else:
            self.configure(fg_color="transparent")
            self.indicator.configure(text="", font=ui_font(14))


class VNDBGUI(ctk.CTk):
    def __init__(self):
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
        self._focus_side = "nonzh"  # which side has focus

        # --- Variables ---
        self.query_var = ctk.StringVar(value="")
        self.query_var.trace_add("write", self._on_query_change)

        self.group_var = ctk.StringVar(value="")
        self.group_var.trace_add("write", self._on_manual_change)

        # Internal vars (auto-filled from zh selection, no UI)
        self._patch_date = ""
        self._language = "CHS"

        # ======== Layout ========
        self._build_header()
        self._build_query_row()
        self._build_release_panels()   # two side-by-side scroll panels
        self._build_manual_card()      # only 汉化组 field
        self._build_preview_card()
        self._build_footer()

        self._update_preview()

    # ── UI Builders ──────────────────────────────────────────────────

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(15, 0))

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="VNDB 视觉小说文件名生成器",
            font=ui_font(22, "bold"),
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="输入 VNDB ID（如 v2622）或游戏原名，自动生成标准文件名",
            text_color="gray60",
            font=ui_font(13),
        )
        self.subtitle_label.pack(anchor="w", pady=(2, 0))

    def _build_query_row(self):
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
            fg_color="#2b7a4b",
            hover_color="#1e5f38",
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

    def _build_release_panels(self):
        """Two side-by-side scrollable panels with clickable release rows."""
        self.panel_frame = ctk.CTkFrame(self, corner_radius=10)
        self.panel_frame.pack(fill="both", expand=True, padx=20, pady=(8, 0))
        self.panel_frame.grid_columnconfigure(0, weight=1)
        self.panel_frame.grid_columnconfigure(1, weight=1)
        self.panel_frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self.panel_frame,
            text="选择发行版本",
            font=ui_font(15, "bold"),
        )
        header.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 6))

        # ── Left: Non-Chinese ──
        self.left_frame = ctk.CTkFrame(self.panel_frame, corner_radius=8,
                                       border_width=1, border_color=COLOR_BORDER)
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=(15, 6), pady=(0, 10))
        self.left_frame.grid_rowconfigure(2, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.left_header = ctk.CTkLabel(
            self.left_frame, text="原版发行",
            font=ui_font(13, "bold"),
            fg_color="#2a2a2a", corner_radius=6,
        )
        self.left_header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 4))

        self.left_scroll = ctk.CTkScrollableFrame(
            self.left_frame, corner_radius=6,
            border_width=0,
        )
        self.left_scroll.grid(row=2, column=0, sticky="nsew", padx=4, pady=2)

        self.left_count = ctk.CTkLabel(
            self.left_frame, text="（请先搜索）",
            font=ui_font(11), text_color="gray50",
        )
        self.left_count.grid(row=3, column=0, sticky="w", padx=8, pady=(2, 6))

        # ── Right: Chinese ──
        self.right_frame = ctk.CTkFrame(self.panel_frame, corner_radius=8,
                                        border_width=1, border_color=COLOR_ZH_BORDER)
        self.right_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 15), pady=(0, 10))
        self.right_frame.grid_rowconfigure(2, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.right_header = ctk.CTkLabel(
            self.right_frame, text="汉化版",
            font=ui_font(13, "bold"),
            fg_color=COLOR_ZH_BG, corner_radius=6,
        )
        self.right_header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 4))

        self.right_scroll = ctk.CTkScrollableFrame(
            self.right_frame, corner_radius=6,
            border_width=0,
        )
        self.right_scroll.grid(row=2, column=0, sticky="nsew", padx=4, pady=2)

        self.right_count = ctk.CTkLabel(
            self.right_frame, text="（请先搜索）",
            font=ui_font(11), text_color="gray50",
        )
        self.right_count.grid(row=3, column=0, sticky="w", padx=8, pady=(2, 6))

    def _build_manual_card(self):
        self.manual_card = ctk.CTkFrame(self, corner_radius=10)
        self.manual_card.pack(fill="x", padx=20, pady=(6, 0))
        self.manual_card.grid_columnconfigure(1, weight=1)

        self.manual_label = ctk.CTkLabel(
            self.manual_card,
            text="附加信息（点击汉化版列表自动填入）",
            font=ui_font(15, "bold"),
        )
        self.manual_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 8))

        # Row 1: Group only
        self.group_label = ctk.CTkLabel(self.manual_card, text="汉化组：", font=ui_font(12, "bold"))
        self.group_label.grid(row=1, column=0, sticky="w", padx=(15, 5), pady=(0, 10))
        self.group_entry = ctk.CTkEntry(
            self.manual_card,
            placeholder_text="如：Makura Castle（点击汉化版自动填入）",
            textvariable=self.group_var,
            font=ui_font(12),
            height=30,
        )
        self.group_entry.grid(row=1, column=1, sticky="ew", padx=(0, 15), pady=(0, 10))

    def _build_preview_card(self):
        self.preview_card = ctk.CTkFrame(self, corner_radius=10)
        self.preview_card.pack(fill="x", padx=20, pady=(8, 0))

        self.preview_label = ctk.CTkLabel(
            self.preview_card,
            text="文件名预览",
            font=ui_font(15, "bold"),
        )
        self.preview_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 6))

        self.preview_text = ctk.CTkTextbox(
            self.preview_card,
            font=ui_font(13),
            height=44,
            corner_radius=8,
            wrap="none",
        )
        self.preview_text.grid(row=1, column=0, sticky="ew", padx=(15, 8), pady=(0, 10))
        self.preview_text.insert("1.0", "（等待搜索）")
        self.preview_text.configure(state="disabled")

        self.copy_btn = ctk.CTkButton(
            self.preview_card,
            text="一键复制",
            font=ui_font(13, "bold"),
            height=36,
            width=100,
            fg_color="#2b5797",
            hover_color="#1e3f6f",
            command=self.copy_filename,
        )
        self.copy_btn.grid(row=1, column=1, sticky="ns", padx=(0, 15), pady=(0, 10))

        self.preview_card.grid_columnconfigure(0, weight=1)

    def _build_footer(self):
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(fill="x", padx=20, pady=(6, 10))

        self.info_label = ctk.CTkLabel(
            self.footer_frame,
            text="基于 VNDB API v2 ｜ 自动过滤 Windows 非法字符 ｜ 缺失信息显示「NO DATA」",
            text_color="gray50",
            font=ui_font(11),
        )
        self.info_label.pack(side="left")

        self.project_link_label = ctk.CTkLabel(
            self.footer_frame,
            text=PROJECT_URL,
            text_color="#1f6aa5",
            cursor="hand2",
            font=ui_font(11, "bold"),
        )
        self.project_link_label.pack(side="right")
        self.project_link_label.bind("<Button-1>", lambda e: self.open_project_link())

    # ── List Population ─────────────────────────────────────────────

    def _rebuild_nonzh_rows(self):
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
                             self._on_nonzh_click, i, zh_mode=False)
            row.pack(fill="x", padx=4, pady=2)

    def _rebuild_zh_rows(self):
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
                             self._on_zh_click, i, zh_mode=True)
            row.pack(fill="x", padx=4, pady=2)

    def _refresh_release_lists(self):
        self._rebuild_nonzh_rows()
        self._rebuild_zh_rows()
        self.left_count.configure(text=f"共 {len(self._nonzh_releases)} 个版本")
        self.right_count.configure(text=f"共 {len(self._zh_releases)} 个版本")

        # Update preview based on active release
        active = self._get_active_release()
        self._update_preview(active)

    def _on_nonzh_click(self, idx: int):
        self._focus_side = "nonzh"
        self._selected_nonzh_idx = idx
        self._refresh_release_lists()

    def _on_zh_click(self, idx: int):
        self._focus_side = "zh"
        self._selected_zh_idx = idx

        # Auto-fill Chinese patch info when selecting a zh release
        r = self._zh_releases[idx]
        grp = r.get_non_developer_group_name()
        if grp and grp != PLACEHOLDER:
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

        self._refresh_release_lists()

    # ── Event Handlers ──────────────────────────────────────────────

    def _on_query_change(self, *args):
        pass

    def _on_manual_change(self, *args):
        # Auto-update preview when user manually edits group field
        active = self._get_active_release()
        self._update_preview(active)

    def _get_active_release(self) -> VNRelease | None:
        """Return the release that should be highlighted (focus side)."""
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
        """Return the non-zh release as base for filename generation."""
        if self._nonzh_releases:
            return self._nonzh_releases[self._selected_nonzh_idx]
        # Fallback: use zh release if no non-zh available
        if self._zh_releases:
            return self._zh_releases[self._selected_zh_idx]
        return None

    # ── API Search ──────────────────────────────────────────────────

    def search_api(self):
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

    def _do_search(self, query: str):
        try:
            vn_info = self.api_client.search_vn(query)
        except VNDBNotFoundError as e:
            self.after(0, lambda: self._on_search_error(str(e)))
            return
        except VNDBError as e:
            self.after(0, lambda: self._on_search_error(str(e)))
            return
        except Exception as e:
            self.after(0, lambda: self._on_search_error(f"未知错误：{e}"))
            return

        self.after(0, lambda: self._on_search_success(vn_info))

    def _on_search_success(self, vn_info: VNInfo):
        self._vn_info = vn_info
        self._all_releases = vn_info.releases

        self._nonzh_releases = [r for r in self._all_releases if not r.is_chinese_release()]
        self._zh_releases = [r for r in self._all_releases if r.is_chinese_release()]

        # Sort non-zh: Japanese-language releases first, then by date descending
        def _nonzh_sort_key(r):
            lang_priority = 0 if "ja" in r.languages else 1
            date_parts = (r.released or "").split("-")
            try:
                # Convert date to comparable integer (YYYYMMDD), descending
                date_val = sum(int(p) * (10000 // (10 ** i)) for i, p in enumerate(date_parts[:3]))
            except (ValueError, IndexError):
                date_val = 0
            return (lang_priority, -date_val)

        self._nonzh_releases.sort(key=_nonzh_sort_key)
        self._zh_releases.sort(key=lambda r: r.released or "", reverse=True)

        self._selected_nonzh_idx = 0
        self._selected_zh_idx = 0
        self._focus_side = "zh" if self._zh_releases else "nonzh"

        # Auto-fill from the first zh release if available
        if self._zh_releases:
            r = self._zh_releases[0]
            grp = r.get_non_developer_group_name()
            if grp and grp != PLACEHOLDER:
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

        self._refresh_release_lists()

        self._searching = False
        self.search_btn.configure(state="normal", text="搜索 API")

        self.status_indicator.configure(
            text=f"✓ 找到 {len(self._all_releases)} 个发行版本（非中文 {len(self._nonzh_releases)}，中文 {len(self._zh_releases)}）",
            text_color="#2b7a4b",
        )

    def _on_search_error(self, error_msg: str):
        self._searching = False
        self.search_btn.configure(state="normal", text="搜索 API")
        self.status_indicator.configure(text=f"✗ {error_msg}", text_color="#d32f2f")
        self._vn_info = None
        self._all_releases = []
        self._nonzh_releases = []
        self._zh_releases = []
        self._refresh_release_lists()

    # ── Preview ─────────────────────────────────────────────────────

    def _update_preview(self, *args):
        """Update preview using non-zh release as base + zh-side group/lang info."""
        if not self._vn_info:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "（等待搜索）")
            self.preview_text.configure(state="disabled")
            return

        # Always use non-zh release as the base for developer/date/title/platform
        base = self._get_base_release()
        if not base:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "（请选择原版发行）")
            self.preview_text.configure(state="disabled")
            return

        # Use group from UI, internal patch_date/language from zh selection
        filename = generate_filename(
            self._vn_info,
            base,
            group_name=self.group_var.get(),
            patch_date=self._patch_date,
            language=self._language,
        )

        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", filename)
        self.preview_text.configure(state="disabled")

    def copy_filename(self):
        content = self.preview_text.get("1.0", "end-1c")
        if content and content not in ("（等待搜索）", "（请选择发行版本）"):
            self.clipboard_clear()
            self.clipboard_append(content)
            self.status_indicator.configure(text="✓ 已复制到剪贴板", text_color="#2b7a4b")
            self.after(3000, lambda: self._reset_status_text())

    def _reset_status_text(self):
        if self._vn_info and self._all_releases:
            self.status_indicator.configure(
                text=f"✓ 找到 {len(self._all_releases)} 个发行版本",
                text_color="#2b7a4b",
            )
        else:
            self.status_indicator.configure(text="", text_color="gray50")

    def _set_status(self, text: str, is_error: bool = False):
        color = "#d32f2f" if is_error else "gray60"
        self.status_indicator.configure(text=text, text_color=color)

    def open_project_link(self):
        webbrowser.open_new_tab(PROJECT_URL)


if __name__ == "__main__":
    app = VNDBGUI()
    app.mainloop()