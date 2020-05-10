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
        finally:
            try: self._task.complete()
            except Exception as e:
                print("ERROR", f"On completion of worker '{self._task.worker_id}':", e)
                self.errored.emit(e)
        self._task = None


class PyWorker:
    def __init__(self, worker_id, auto_activate=True):
        self._id = worker_id
        self._qt = _Task(self)
        self._qt.errored.connect(self.error)
        if auto_activate: self.activate()

    def activate(self): self._qt.start()

    @property
    def worker_id(self): return self._id
    @property
    def running(self): return self._qt.isRunning()

    def sleep(self, secs):
        QtCore.QThread.sleep(secs)

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

class PyWaitCondition:
    def __init__(self):
        self._mutex = QtCore.QMutex()
        self._qt = QtCore.QWaitCondition()

    def __enter__(self): self.lock()
    def __exit__(self, exc_type, exc_val, exc_tb): self.unlock()

    def lock(self, ms=0, sec=0):
        """
         Attempt to lock the associated mutex for specified wait time
         If no or negative delay specified, it will wait forever until locked
         Returns true if the lock was succesfully obtained
        """
        self._mutex.tryLock(sec*1000+ms)

    def unlock(self):
        """ Unlock associated mutex """
        self._mutex.unlock()

    def notify_one(self):
        """ Wakes up one thread waiting on this WaitCondition """
        self._qt.wakeOne()

    def notify_all(self):
        """ Wakes up all threads waiting on this WaitCondition """
        self._qt.wakeAll()

    def wait(self, ms=0, sec=0, min=0):
        """
         Wait for specified time or when it gets woken by another thread
         Note: the lock associated with this instance must be owned by the caller
         Returns true if it was awoken or false if the wait time has passed
        """
        #self.lock()
        res = self._qt.wait(self._mutex, min*60000+sec*1000+ms)
        #self.unlock()
        return res