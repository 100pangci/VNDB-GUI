"""VNDB GUI 界面共享工具 — 字体、格式模板、对话框居中。"""

from __future__ import annotations

import customtkinter as ctk

from core.colors_common import COLOR_ACTIVE

UI_FONT_FAMILY = "Microsoft YaHei UI"
DEFAULT_FORMAT_TEMPLATE = "[{developer}][{date}]{title}[{vid}][{platform}][{group}][{patch_date}][{language}]"


def ui_font(size=12, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight=weight)


def center_dialog(dialog: ctk.CTkToplevel) -> None:
    dialog.update_idletasks()
    pw = dialog.master.winfo_width()
    ph = dialog.master.winfo_height()
    px = dialog.master.winfo_x()
    py = dialog.master.winfo_y()
    w = dialog.winfo_width()
    h = dialog.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    dialog.geometry(f"+{x}+{y}")
