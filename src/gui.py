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

PROJECT_URL = "https://github.com/yourname/vndb-gui"


def ui_font(size=12, weight="normal"):
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight=weight)


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class VNDBGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("820x760")
        self.minsize(720, 680)
        self.title(f"VNDB 文件名生成器 — {get_app_version()}")

        self.api_client = VNDBAPIClient()

        # --- State ---
        self._vn_info: VNInfo | None = None
        self._releases: list[VNRelease] = []
        self._searching = False

        # --- Variables ---
        self.query_var = ctk.StringVar(value="")
        self.query_var.trace_add("write", self._on_query_change)

        self.release_var = ctk.StringVar(value="")
        self.release_var.trace_add("write", self._on_release_change)

        self.group_var = ctk.StringVar(value="")
        self.group_var.trace_add("write", self._on_manual_change)

        self.patch_date_var = ctk.StringVar(value="")
        self.patch_date_var.trace_add("write", self._on_manual_change)

        self.language_var = ctk.StringVar(value="CHS")
        self.language_var.trace_add("write", self._on_manual_change)

        # ======== Header ========
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 5))

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

        # ======== Query Card ========
        self.query_card = ctk.CTkFrame(self, corner_radius=10)
        self.query_card.pack(fill="x", padx=20, pady=(15, 5))

        self.query_label = ctk.CTkLabel(
            self.query_card,
            text="搜索 VNDB",
            font=ui_font(15, "bold"),
        )
        self.query_label.grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(12, 8))

        self.query_entry = ctk.CTkEntry(
            self.query_card,
            placeholder_text="输入 VNDB ID（如 v2622）或游戏原名…",
            textvariable=self.query_var,
            font=ui_font(13),
            height=36,
        )
        self.query_entry.grid(row=1, column=0, sticky="ew", padx=(15, 8), pady=(0, 12))
        self.query_entry.bind("<Return>", lambda e: self.search_api())

        self.search_btn = ctk.CTkButton(
            self.query_card,
            text="搜索 API",
            font=ui_font(13, "bold"),
            height=36,
            width=120,
            fg_color="#2b7a4b",
            hover_color="#1e5f38",
            command=self.search_api,
        )
        self.search_btn.grid(row=1, column=1, sticky="w", pady=(0, 12))

        self.chinese_patch_btn = ctk.CTkButton(
            self.query_card,
            text="汉化版发布",
            font=ui_font(12, "bold"),
            height=36,
            width=110,
            fg_color="#7a4b2b",
            hover_color="#5f381e",
            command=self.auto_fill_chinese_patch,
            state="disabled",
        )
        self.chinese_patch_btn.grid(row=1, column=2, sticky="w", padx=(5, 8), pady=(0, 12))

        self.status_indicator = ctk.CTkLabel(
            self.query_card,
            text="",
            font=ui_font(11),
            text_color="gray50",
        )
        self.status_indicator.grid(row=1, column=3, sticky="w", padx=(8, 15), pady=(0, 12))

        self.query_card.grid_columnconfigure(0, weight=1)

        # ======== Release Selection Card ========
        self.release_card = ctk.CTkFrame(self, corner_radius=10)
        self.release_card.pack(fill="x", padx=20, pady=5)

        self.release_label = ctk.CTkLabel(
            self.release_card,
            text="选择发行版本",
            font=ui_font(15, "bold"),
        )
        self.release_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 6))

        self.release_combo = ctk.CTkOptionMenu(
            self.release_card,
            variable=self.release_var,
            values=["（请先搜索）"],
            font=ui_font(12),
            width=500,
            dynamic_resizing=False,
        )
        self.release_combo.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 12))

        self.release_card.grid_columnconfigure(0, weight=1)

        # ======== Release Info Display ========
        self.info_card = ctk.CTkFrame(self, corner_radius=10)
        self.info_card.pack(fill="x", padx=20, pady=5)
        self.info_card.grid_columnconfigure(1, weight=1)

        # Row 0: Developer
        self.dev_label = ctk.CTkLabel(self.info_card, text="开发商：", font=ui_font(12, "bold"))
        self.dev_label.grid(row=0, column=0, sticky="w", padx=(15, 5), pady=(10, 4))
        self.dev_value = ctk.CTkLabel(self.info_card, text="—", font=ui_font(12))
        self.dev_value.grid(row=0, column=1, sticky="w", padx=(0, 15), pady=(10, 4))

        # Row 1: Release Date
        self.date_label = ctk.CTkLabel(self.info_card, text="发售日期：", font=ui_font(12, "bold"))
        self.date_label.grid(row=1, column=0, sticky="w", padx=(15, 5), pady=4)
        self.date_value = ctk.CTkLabel(self.info_card, text="—", font=ui_font(12))
        self.date_value.grid(row=1, column=1, sticky="w", padx=(0, 15), pady=4)

        # Row 2: Platform
        self.platform_label = ctk.CTkLabel(self.info_card, text="平台：", font=ui_font(12, "bold"))
        self.platform_label.grid(row=2, column=0, sticky="w", padx=(15, 5), pady=4)
        self.platform_value = ctk.CTkLabel(self.info_card, text="—", font=ui_font(12))
        self.platform_value.grid(row=2, column=1, sticky="w", padx=(0, 15), pady=4)

        # Row 3: Languages
        self.lang_info_label = ctk.CTkLabel(self.info_card, text="语言：", font=ui_font(12, "bold"))
        self.lang_info_label.grid(row=3, column=0, sticky="w", padx=(15, 5), pady=(4, 10))
        self.lang_info_value = ctk.CTkLabel(self.info_card, text="—", font=ui_font(12))
        self.lang_info_value.grid(row=3, column=1, sticky="w", padx=(0, 15), pady=(4, 10))

        # ======== Manual Input Card ========
        self.manual_card = ctk.CTkFrame(self, corner_radius=10)
        self.manual_card.pack(fill="x", padx=20, pady=5)
        self.manual_card.grid_columnconfigure(1, weight=1)
        self.manual_card.grid_columnconfigure(3, weight=1)

        self.manual_label = ctk.CTkLabel(
            self.manual_card,
            text="附加信息（可选）",
            font=ui_font(15, "bold"),
        )
        self.manual_label.grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(12, 8))

        # Row 1: Group + Patch Date
        self.group_label = ctk.CTkLabel(self.manual_card, text="汉化组：", font=ui_font(12, "bold"))
        self.group_label.grid(row=1, column=0, sticky="w", padx=(15, 5), pady=(0, 10))
        self.group_entry = ctk.CTkEntry(
            self.manual_card,
            placeholder_text="如：Makura Castle",
            textvariable=self.group_var,
            font=ui_font(12),
            height=32,
        )
        self.group_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))

        self.patch_date_label = ctk.CTkLabel(self.manual_card, text="汉化发布日：", font=ui_font(12, "bold"))
        self.patch_date_label.grid(row=1, column=2, sticky="w", padx=(5, 5), pady=(0, 10))
        self.patch_date_entry = ctk.CTkEntry(
            self.manual_card,
            placeholder_text="YYYYMMDD",
            textvariable=self.patch_date_var,
            font=ui_font(12),
            height=32,
        )
        self.patch_date_entry.grid(row=1, column=3, sticky="ew", padx=(0, 15), pady=(0, 10))

        # Row 2: Language
        self.language_label = ctk.CTkLabel(self.manual_card, text="语言：", font=ui_font(12, "bold"))
        self.language_label.grid(row=2, column=0, sticky="w", padx=(15, 5), pady=(0, 12))
        self.language_entry = ctk.CTkEntry(
            self.manual_card,
            placeholder_text="如：CHS、CHT、EN",
            textvariable=self.language_var,
            font=ui_font(12),
            height=32,
        )
        self.language_entry.grid(row=2, column=1, sticky="ew", padx=(0, 15), pady=(0, 12))

        # ======== Preview Card ========
        self.preview_card = ctk.CTkFrame(self, corner_radius=10)
        self.preview_card.pack(fill="x", padx=20, pady=(10, 5))

        self.preview_label = ctk.CTkLabel(
            self.preview_card,
            text="文件名预览",
            font=ui_font(15, "bold"),
        )
        self.preview_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 8))

        self.preview_text = ctk.CTkTextbox(
            self.preview_card,
            font=ui_font(13),
            height=50,
            corner_radius=8,
            wrap="none",
        )
        self.preview_text.grid(row=1, column=0, sticky="ew", padx=(15, 8), pady=(0, 12))
        self.preview_text.insert("1.0", "（等待搜索）")
        self.preview_text.configure(state="disabled")

        self.copy_btn = ctk.CTkButton(
            self.preview_card,
            text="一键复制",
            font=ui_font(13, "bold"),
            height=40,
            width=110,
            fg_color="#2b5797",
            hover_color="#1e3f6f",
            command=self.copy_filename,
        )
        self.copy_btn.grid(row=1, column=1, sticky="ns", padx=(0, 15), pady=(0, 12))

        self.preview_card.grid_columnconfigure(0, weight=1)

        # ======== Footer ========
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(fill="x", padx=20, pady=(5, 10))

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

        self._update_preview()

    # ======== Event Handlers ========

    def _on_query_change(self, *args):
        """Triggered when query text changes."""
        pass

    def _on_release_change(self, *args):
        """When release selection changes, update info display and preview."""
        self._update_release_info()
        self._update_preview()

    def _on_manual_change(self, *args):
        """When manual fields change, update preview."""
        self._update_preview()

    # ======== API Search ========

    def search_api(self):
        query = self.query_var.get().strip()
        if not query:
            self._set_status("请输入 VNDB ID 或游戏名称", is_error=True)
            return

        if self._searching:
            return

        self._searching = True
        self.search_btn.configure(state="disabled", text="搜索中…")
        self.chinese_patch_btn.configure(state="disabled")
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
        self._releases = vn_info.releases

        # Populate release dropdown
        if self._releases:
            release_labels = []
            for i, r in enumerate(self._releases):
                label = get_release_preview(r)
                release_labels.append(label)

            self.release_combo.configure(values=release_labels)
            self.release_var.set(release_labels[0])
        else:
            self.release_combo.configure(values=["（无发行版本）"])
            self.release_var.set("（无发行版本）")

        self._searching = False
        self.search_btn.configure(state="normal", text="搜索 API")

        # Enable Chinese patch button if VN has ID
        if self._vn_info and self._vn_info.id:
            self.chinese_patch_btn.configure(state="normal")
        else:
            self.chinese_patch_btn.configure(state="disabled")

        self.status_indicator.configure(
            text=f"✓ 找到 {len(self._releases)} 个发行版本",
            text_color="#2b7a4b",
        )
        self._update_release_info()
        self._update_preview()

    def _on_search_error(self, error_msg: str):
        self._searching = False
        self.search_btn.configure(state="normal", text="搜索 API")
        self.chinese_patch_btn.configure(state="disabled")
        self.status_indicator.configure(text=f"✗ {error_msg}", text_color="#d32f2f")
        self._vn_info = None
        self._releases = []
        self.release_combo.configure(values=["（请先搜索）"])
        self.release_var.set("（请先搜索）")
        self._clear_release_info()
        self._update_preview()

    # ======== Chinese Patch Auto-Fill ========

    def auto_fill_chinese_patch(self):
        """Search for Chinese patch releases and show selection dialog."""
        if not self._vn_info or not self._vn_info.id:
            return

        self.status_indicator.configure(text="正在查找汉化版…", text_color="gray60")

        thread = threading.Thread(target=self._do_chinese_patch_search, daemon=True)
        thread.start()

    def _do_chinese_patch_search(self):
        try:
            chinese_releases = self.api_client.get_chinese_patch_releases(self._vn_info.id)
        except Exception as e:
            self.after(0, lambda: self._set_status(f"查找汉化版失败：{e}", is_error=True))
            return

        self.after(0, lambda: self._on_chinese_patch_found(chinese_releases))

    def _on_chinese_patch_found(self, chinese_releases: list[VNRelease]):
        if not chinese_releases:
            self._set_status("未找到任何汉化发行版本", is_error=True)
            return

        # Sort by release date descending (newest first)
        chinese_releases.sort(key=lambda r: r.released or "", reverse=True)

        # Show selection dialog
        self._show_chinese_patch_dialog(chinese_releases)

    def _show_chinese_patch_dialog(self, releases: list[VNRelease]):
        """Show a popup dialog to let the user choose a Chinese release."""

        dialog = ctk.CTkToplevel(self)
        dialog.title("选择汉化版本")
        dialog.geometry("680x420")
        dialog.resizable(True, True)
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 680) // 2
        y = self.winfo_y() + (self.winfo_height() - 420) // 2
        dialog.geometry(f"+{x}+{y}")

        # Header
        header = ctk.CTkLabel(
            dialog,
            text=f"共找到 {len(releases)} 个汉化版本，请选择一项：",
            font=ui_font(14, "bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=20, pady=(15, 5))

        # Scrollable frame for release list
        scroll_frame = ctk.CTkScrollableFrame(dialog, corner_radius=8)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        selected_var = ctk.StringVar(value=releases[0].id)

        for r in releases:
            pub = r.get_publisher_name()
            pub_text = pub if pub != PLACEHOLDER else "（未知汉化组）"
            date_text = r.released if r.released else "（日期未知）"
            lang_text = "简体中文" if "zh-Hans" in r.languages else "繁体中文" if "zh-Hant" in r.languages else "中文"

            # Card frame
            card = ctk.CTkFrame(scroll_frame, corner_radius=8, border_width=1, border_color="#333333")
            card.pack(fill="x", padx=5, pady=4)

            # Radio button
            radio = ctk.CTkRadioButton(
                card,
                text="",
                variable=selected_var,
                value=r.id,
                font=ui_font(13),
            )
            radio.grid(row=0, column=0, rowspan=3, padx=(10, 5), pady=8)

            # Info
            title_label = ctk.CTkLabel(
                card,
                text=f"📅 {date_text}  |  {lang_text}",
                font=ui_font(13, "bold"),
                anchor="w",
            )
            title_label.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(6, 0))

            group_label = ctk.CTkLabel(
                card,
                text=f"🏢 {pub_text}",
                font=ui_font(12),
                text_color="gray70",
                anchor="w",
            )
            group_label.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(0, 2))

            subtitle_label = ctk.CTkLabel(
                card,
                text=f"📖 {r.title}",
                font=ui_font(11),
                text_color="gray50",
                anchor="w",
            )
            subtitle_label.grid(row=2, column=1, sticky="w", padx=(0, 10), pady=(0, 6))

            card.grid_columnconfigure(1, weight=1)

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ui_font(13),
            width=100,
            fg_color="#555555",
            hover_color="#444444",
            command=dialog.destroy,
        )
        cancel_btn.pack(side="right", padx=(10, 0))

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="确认选择",
            font=ui_font(13, "bold"),
            width=120,
            fg_color="#2b7a4b",
            hover_color="#1e5f38",
            command=lambda: self._apply_chinese_patch(releases, selected_var.get(), dialog),
        )
        confirm_btn.pack(side="right")

    def _apply_chinese_patch(
        self,
        releases: list[VNRelease],
        selected_id: str,
        dialog: ctk.CTkToplevel | None = None,
    ):
        """Apply the selected Chinese release info to the form."""
        # Find the selected release
        target = None
        for r in releases:
            if r.id == selected_id:
                target = r
                break
        if not target:
            return

        # Auto-fill fields
        publisher = target.get_publisher_name()
        if publisher and publisher != PLACEHOLDER:
            self.group_var.set(publisher)

        patch_date = target.format_released()
        if patch_date and patch_date != PLACEHOLDER:
            self.patch_date_var.set(patch_date)

        if "zh-Hans" in target.languages:
            self.language_var.set("CHS")
        elif "zh-Hant" in target.languages:
            self.language_var.set("CHT")
        elif "zh" in target.languages:
            self.language_var.set("CHS")

        # Try to select matching release in dropdown
        matched_in_list = False
        for r in self._releases:
            if r.id == target.id and get_release_preview(r):
                self.release_var.set(get_release_preview(r))
                matched_in_list = True
                break

        if dialog:
            dialog.destroy()

        msg = f"✓ 已填入汉化版信息（{target.released or '日期未知'} - {publisher if publisher != PLACEHOLDER else '未知组'}）"
        self.status_indicator.configure(text=msg, text_color="#2b7a4b")

    # ======== Release Info Display ========

    def _update_release_info(self):
        if not self._vn_info or not self._releases:
            self._clear_release_info()
            return

        selected_idx = self._get_selected_release_index()
        if selected_idx is None:
            self._clear_release_info()
            return

        release = self._releases[selected_idx]
        developer = release.get_developer_name()
        self.dev_value.configure(text=developer)
        self.date_value.configure(text=release.released or PLACEHOLDER)
        self.platform_value.configure(
            text=", ".join(release.platforms) if release.platforms else PLACEHOLDER
        )
        self.lang_info_value.configure(
            text=", ".join(release.languages) if release.languages else PLACEHOLDER
        )

    def _clear_release_info(self):
        self.dev_value.configure(text="—")
        self.date_value.configure(text="—")
        self.platform_value.configure(text="—")
        self.lang_info_value.configure(text="—")

    def _get_selected_release_index(self) -> int | None:
        """Get the index of the currently selected release."""
        if not self._releases:
            return None
        selected = self.release_var.get()
        for i, r in enumerate(self._releases):
            if get_release_preview(r) == selected:
                return i
        return None

    # ======== Preview ========

    def _update_preview(self):
        if not self._vn_info or not self._releases:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "（等待搜索）")
            self.preview_text.configure(state="disabled")
            return

        selected_idx = self._get_selected_release_index()
        if selected_idx is None:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "（请选择发行版本）")
            self.preview_text.configure(state="disabled")
            return

        release = self._releases[selected_idx]
        filename = generate_filename(
            self._vn_info,
            release,
            group_name=self.group_var.get(),
            patch_date=self.patch_date_var.get(),
            language=self.language_var.get(),
        )

        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", filename)
        self.preview_text.configure(state="disabled")

    def copy_filename(self):
        content = self.preview_text.get("1.0", "end-1c")
        if content and content != "（等待搜索）" and content != "（请选择发行版本）":
            self.clipboard_clear()
            self.clipboard_append(content)
            self.status_indicator.configure(text="✓ 已复制到剪贴板", text_color="#2b7a4b")
            self.after(3000, lambda: self._reset_status_text())

    def _reset_status_text(self):
        if self._vn_info and self._releases:
            self.status_indicator.configure(
                text=f"✓ 找到 {len(self._releases)} 个发行版本",
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