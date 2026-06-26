import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from nlab import __version__
from nlab.app import MainAppWindow
from nlab.views.connection_dialog import ConnectionDialog

# Registers compiled Qt resources (icons, images) with the Qt resource system.
# Must happen before any QPixmap(":/...") call.
# `del _rc` removes only the local name; the module stays in sys.modules and
# the Qt registration remains active.
try:
    from nlab.ui import resources_rc as _rc

    del _rc
except ImportError:
    pass  # not compiled yet — run scripts/build_ui.py


log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(":/icons/ewt.ico"))
    app.setApplicationName("Nuclear Lab Digitizer")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("EWT")
    app.setOrganizationDomain("ewt.local")  # scopes QSettings on all platforms

    splash = _show_splash()

    dialog = ConnectionDialog()
    if splash is not None:
        splash.finish(dialog)  # splash closes as soon as the dialog is shown

    if dialog.exec() != ConnectionDialog.DialogCode.Accepted:
        sys.exit(0)

    log.info("Application starting — v%s, host=%s, port=%d, channels=%d",
             __version__, dialog.ip, dialog.port, dialog.channels)
    window = MainAppWindow(host=dialog.ip, port=dialog.port, channels=dialog.channels)

    window.show()
    sys.exit(app.exec())


def _show_splash() -> QSplashScreen | None:
    pixmap = QPixmap(":/ewt.png")
    if pixmap.isNull():
        return None
    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    QApplication.processEvents()
    return splash


if __name__ == "__main__":
    main()
