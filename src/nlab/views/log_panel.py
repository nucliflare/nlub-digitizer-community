from __future__ import annotations

import html
import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit


class _LogEmitter(QObject):
    message = Signal(str, int)  # (formatted_text, levelno)


class LogHandler(logging.Handler):
    """Thread-safe logging handler that routes formatted records to a Qt signal.

    Formatting happens on the emitting thread; the signal carries only the
    already-rendered string so the main thread never touches LogRecord internals.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self._emitter = _LogEmitter()
        self.message_emitted = self._emitter.message
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._emitter.message.emit(self.format(record), record.levelno)
        except Exception:
            self.handleError(record)


class LogConsole(QPlainTextEdit):
    """Read-only dark-themed console that displays Python log records.

    Installs its own LogHandler into the root logger on construction.
    The handler level is always DEBUG; the root logger's level acts as the gate.
    """

    _COLORS: dict[int, str] = {
        logging.DEBUG:    "#7ec8e3",
        logging.INFO:     "#d4d4d4",
        logging.WARNING:  "#f0c040",
        logging.ERROR:    "#f04040",
        logging.CRITICAL: "#ff6060",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5_000)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setStyleSheet("QPlainTextEdit { background:#1e1e1e; color:#d4d4d4; border:none; }")

        self._handler = LogHandler()
        self._handler.message_emitted.connect(self._append)
        logging.getLogger().addHandler(self._handler)

    @property
    def handler(self) -> LogHandler:
        return self._handler

    def _append(self, text: str, levelno: int) -> None:
        color = self._COLORS.get(levelno, "#d4d4d4")
        self.appendHtml(f'<span style="color:{color};">{html.escape(text)}</span>')
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())
