from PyQt5 import QtCore

class _Task(QtCore.QThread):
    errored = QtCore.pyqtSignal(BaseException)

    def __init__(self, task):
        QtCore.QThread.__init__(self)
        self._task = task

    def start(self, priority=None):
        try:
            self._task.start()
            QtCore.QThread.start(self)
        except Exception as e:
            print("ERROR", f"Failed to start worker '{self._task.worker_id}':", e)
            self.errored.emit(e)
            self._task = None

    def run(self):
        try: self._task.run()
        except Exception as e:
            print("ERROR", f"During execution of worker '{self._task.worker_id}':", e)
            self.errored.emit(e)
            self._task = None
            return

        try: self._task.complete()
        except Exception as e:
            print("ERROR", f"On completion of worker '{self._task.worker_id}':", e)
            self.errored.emit(e)

        self._task = None


class PyWorker:
    def __init__(self, worker_id):
        self._id = worker_id
        self._qt = _Task(self)
        self._qt.errored.connect(self.error)
        self._qt.start()

    @property
    def worker_id(self): return self._id

    def start(self):
        """ Executed before the worker is started """
        pass

    def run(self):
        """ Main execution of the worker """
        pass

    def complete(self):
        """ Executed after the worker completed, only on success """
        pass

    def error(self, error):
        """ Executed only on error, either during 'start' or 'run' """
        pass