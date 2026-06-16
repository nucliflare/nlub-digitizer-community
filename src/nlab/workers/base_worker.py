from PySide6.QtCore import QObject, Signal


class BaseWorker(QObject):
    """Abstract base for all background workers.

    Usage pattern (in a controller):
        thread = QThread()
        worker = ConcreteWorker(...)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
    """

    finished = Signal()
    error = Signal(str)

    def run(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError
