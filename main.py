"""VNDB GUI — Visual Novel Filename Generator entry point."""

from src.gui import VNDBGUI

if __name__ == "__main__":
    app = VNDBGUI()
    app.mainloop()