"""模态对话框 — 多结果选择与自定义格式编辑。"""

from __future__ import annotations

import customtkinter as ctk

from core import colors_dark, colors_light
from core.colors_common import COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_ERROR, COLOR_VAR_LINK
from core.vndb_api import VNCandidate
from ui_helpers import ui_font, center_dialog, DEFAULT_FORMAT_TEMPLATE


class CandidateDialog(ctk.CTkToplevel):
    """Modal dialog to let the user pick from multiple VN search results."""

    def __init__(self, parent, candidates: list[VNCandidate]):
        super().__init__(parent)
        self.title("选择视觉小说")
        self.geometry("600x420")
        self.minsize(400, 300)
        self.transient(parent)
        self.grab_set()

        self._candidates = candidates
        self._selected: VNCandidate | None = None
        self._is_dark = getattr(parent, '_is_dark', True)

        self._build_ui()

        self.after(100, lambda: center_dialog(self))

    def _build_ui(self):
        C = colors_dark if self._is_dark else colors_light

        ctk.CTkLabel(
            self,
            text="找到多个匹配结果，请选择一个：",
            font=ui_font(14, "bold"),
        ).pack(anchor="w", padx=20, pady=(16, 6))

        self.list_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        for idx, cand in enumerate(self._candidates):
            display = cand.get_display_title()
            extra = cand.alttitle or cand.title
            if extra and extra != display:
                text = f"{display}  ({extra})"
            else:
                text = display
            text += f"  [{cand.id}]"

            btn = ctk.CTkButton(
                self.list_frame,
                text=text,
                font=ui_font(12),
                anchor="w",
                height=32,
                fg_color="transparent",
                hover_color=C.COLOR_CANDIDATE_HOVER,
                text_color=C.COLOR_CANDIDATE_TEXT,
                command=lambda c=cand: self._on_select(c),
            )
            btn.pack(fill="x", padx=4, pady=2)

        self.cancel_btn = ctk.CTkButton(
            self,
            text="取消",
            font=ui_font(13),
            fg_color=C.COLOR_CANCEL_BG,
            hover_color=C.COLOR_CANCEL_HOVER,
            width=100,
            command=self._on_cancel,
        )
        self.cancel_btn.pack(pady=(0, 14))

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_select(self, cand: VNCandidate):
        self._selected = cand
        self.destroy()

    def _on_cancel(self):
        self._selected = None
        self.destroy()

    def get_selected(self) -> VNCandidate | None:
        return self._selected


class CustomFormatDialog(ctk.CTkToplevel):
    """Dialog for editing the custom filename format template."""

    def __init__(self, parent, template_var: ctk.StringVar, on_save):
        super().__init__(parent)
        self.title("自定义拼接格式")
        self.geometry("600x200")
        self.minsize(500, 180)
        self.transient(parent)
        self.grab_set()

        self._template_var = template_var
        self._on_save = on_save
        self._is_dark = getattr(parent, '_is_dark', True)
        self._saved_format = getattr(parent, '_saved_format', "")
        self._original_template = template_var.get()

        self._build_ui()

        self.after(100, lambda: center_dialog(self))

    def _build_ui(self):
        C = colors_dark if self._is_dark else colors_light

        ctk.CTkLabel(
            self,
            text="自定义文件名拼接格式",
            font=ui_font(15, "bold"),
        ).pack(anchor="w", padx=20, pady=(16, 4))

        var_frame = ctk.CTkFrame(self, fg_color="transparent")
        var_frame.pack(anchor="w", padx=20, pady=(0, 8))
        ctk.CTkLabel(
            var_frame,
            text="可用变量：",
            font=ui_font(11),
            text_color="gray50",
        ).pack(side="left")
        for var_name in ["{developer}", "{date}", "{title}", "{vid}", "{platform}", "{group}", "{patch_date}", "{language}"]:
            lbl = ctk.CTkLabel(
                var_frame,
                text=var_name,
                font=ctk.CTkFont(family="Microsoft YaHei UI", size=11, underline=True),
                text_color=COLOR_VAR_LINK,
                cursor="hand2",
            )
            lbl.pack(side="left", padx=(0, 6))
            lbl.bind("<Button-1>", lambda e, v=var_name: self._insert_variable(v))

        self.format_entry = ctk.CTkEntry(
            self,
            textvariable=self._template_var,
            font=ui_font(13),
            height=36,
        )
        self.format_entry.pack(fill="x", padx=20, pady=(0, 12))
        self.format_entry.bind("<Return>", lambda e: self._do_save())

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 14))

        ctk.CTkButton(
            btn_row,
            text="保存",
            font=ui_font(13, "bold"),
            height=34,
            width=90,
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            command=self._do_save,
        ).pack(side="left", padx=(0, 8))

        self.restore_btn = ctk.CTkButton(
            btn_row,
            text="恢复默认",
            font=ui_font(13, "bold"),
            height=34,
            width=100,
            fg_color=C.COLOR_CANCEL_BG,
            hover_color=C.COLOR_CANCEL_HOVER,
            command=self._do_restore,
        )
        self.restore_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="取消",
            font=ui_font(13),
            height=34,
            width=80,
            fg_color="gray50",
            hover_color="gray40",
            command=self._do_cancel,
        ).pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._do_cancel)

    def _insert_variable(self, var_name):
        current = self._template_var.get()
        self._template_var.set(current + var_name)
        self.format_entry.focus()
        self.format_entry.icursor(len(current) + len(var_name))

    def _do_cancel(self):
        self._template_var.set(self._original_template)
        self.destroy()

    def _do_save(self):
        self._on_save(self._template_var.get())
        self.destroy()

    def _do_restore(self):
        self._template_var.set(DEFAULT_FORMAT_TEMPLATE)
        self._do_save()
