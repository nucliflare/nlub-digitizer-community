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


def main() -> None:
    logging.getLogger().setLevel(logging.INFO)
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
