from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget

log = logging.getLogger(__name__)

# src/nlab/utils/windows_icon.py -> parents[3] is the project root when
# running from source. Resolved once here so callers at any module depth
# don't need to recompute it relative to their own file.
DEFAULT_ICO_PATH = Path(__file__).resolve().parents[3] / "resources" / "icons" / "ewt.ico"

_WM_SETICON = 0x0080
_ICON_SMALL = 0
_ICON_BIG = 1
_IMAGE_ICON = 1
_LR_LOADFROMFILE = 0x10
_SM_CXICON = 11
_SM_CYICON = 12
_SM_CXSMICON = 49
_SM_CYSMICON = 50


def apply_taskbar_icon(widget: QWidget, ico_path: Path = DEFAULT_ICO_PATH) -> None:
    """Force a window's taskbar icon on Windows by loading it natively.

    QWidget.setWindowIcon() alone sets a perfectly valid HICON (confirmed via
    WM_GETICON) and is enough for the titlebar — but Qt synthesizes that HICON
    from a QImage buffer via CreateIconIndirect, and the Windows shell's
    taskbar-icon pipeline has been observed to silently reject that synthesized
    icon in favor of the host executable's own icon (python.exe), even though
    the window itself reports the correct icon. Loading the .ico natively via
    LoadImage(LR_LOADFROMFILE) and applying it with WM_SETICON sidesteps that.

    No-op on non-Windows platforms or if ico_path doesn't exist.
    """
    if sys.platform != "win32":
        return
    if not ico_path.is_file():
        log.warning("Taskbar icon file not found: %s", ico_path)
        return

    import ctypes

    user32 = ctypes.windll.user32
    hwnd = int(widget.winId())
    cx_big = user32.GetSystemMetrics(_SM_CXICON)
    cy_big = user32.GetSystemMetrics(_SM_CYICON)
    cx_small = user32.GetSystemMetrics(_SM_CXSMICON)
    cy_small = user32.GetSystemMetrics(_SM_CYSMICON)

    path = str(ico_path)
    hicon_big = user32.LoadImageW(None, path, _IMAGE_ICON, cx_big, cy_big, _LR_LOADFROMFILE)
    hicon_small = user32.LoadImageW(None, path, _IMAGE_ICON, cx_small, cy_small, _LR_LOADFROMFILE)

    if not hicon_big or not hicon_small:
        log.warning("LoadImageW failed for taskbar icon: %s", ico_path)
        return

    user32.SendMessageW(hwnd, _WM_SETICON, _ICON_BIG, hicon_big)
    user32.SendMessageW(hwnd, _WM_SETICON, _ICON_SMALL, hicon_small)
