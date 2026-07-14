"""可复用的自定义 UI 组件。"""

from __future__ import annotations

import customtkinter as ctk

from core import colors_dark, colors_light
from core.colors_common import COLOR_ACTIVE
from core.vndb_api import VNRelease, PLACEHOLDER
from ui_helpers import ui_font


class ReleaseRow(ctk.CTkFrame):
    """A single clickable row in a release list.

    No border_width is used — CTkFrame's Canvas borders have rendering bugs
    on Windows with DPI scaling. Visual row separation is achieved via
    parent scrollable frame's background showing through the pady gap.
    """

    def __init__(self, master, release: VNRelease, is_selected: bool,
                 on_click, row_index: int, zh_mode: bool = False,
                 is_dark: bool = True, **kwargs):
        super().__init__(master, corner_radius=6, border_width=0, **kwargs)

        self.release = release
        self.row_index = row_index
        self.is_selected = is_selected
        self._on_click = on_click
        self.zh_mode = zh_mode
        self.is_dark = is_dark

        self.grid_columnconfigure(1, weight=1)

        # Selection indicator — fixed width, left side
        self.indicator = ctk.CTkLabel(self, text="", width=4, corner_radius=2)
        self.indicator.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(4, 2))

        # Title
        display = release.get_display_title()
        self.title_lbl = ctk.CTkLabel(
            self, text=display, font=ui_font(12, "bold"),
            anchor="w",
        )
        self.title_lbl.grid(row=0, column=1, sticky="ew", padx=(4, 8), pady=(4, 0))

        # Info line: depends on zh_mode
        if zh_mode:
            group = release.get_non_developer_group_name()
            if group and group != PLACEHOLDER:
                info = group
            else:
                info = "无汉化组数据"
            date_str = release.released or "????-??-??"
            info += f"  |  {date_str}"
        else:
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
        self.info_lbl.grid(row=1, column=1, sticky="ew", padx=(4, 8), pady=(0, 4))

        self._apply_selection()

        # Click handling: bind on self + all major children
        self.bind("<Button-1>", self._handle_click)
        self.indicator.bind("<Button-1>", self._handle_click)
        self.title_lbl.bind("<Button-1>", self._handle_click, add=True)
        self.info_lbl.bind("<Button-1>", self._handle_click, add=True)

    def _handle_click(self, event):
        self._on_click(self.row_index)

    def set_selected(self, sel: bool):
        self.is_selected = sel
        self._apply_selection()

    def _apply_selection(self):
        C = colors_dark if self.is_dark else colors_light
        selected_bg = C.COLOR_ROW_SELECTED_BG
        normal_bg = C.COLOR_ROW_NORMAL_BG
        if self.is_selected:
            self.configure(fg_color=selected_bg)
            self.indicator.configure(text="▌", text_color=COLOR_ACTIVE, font=ui_font(14))
        else:
            self.configure(fg_color=normal_bg)
            self.indicator.configure(text="", font=ui_font(14))
