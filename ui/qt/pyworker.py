from PyQt5 import QtCore

class _Task(QtCore.QThread):
    def __init__(self, task):
        QtCore.QThread.__init__(self)
        self._task = task
        self._error = None

    def start(self, priority=None):
        try:
            self._task.start()
            QtCore.QThread.start(self)
        except Exception as e:
            print("ERROR", f"Failed to start worker '{self._task.worker_id}':", e)
            self._on_error(e)
            self._task = None

    def run(self):
        try: self._task.run()
        except Exception as e:
            print("ERROR", f"During execution of worker '{self._task.worker_id}':", e)
            self._on_error(e)

        if not self._error:
            try: self._task.complete()
            except Exception as e:
                print("ERROR", f"On completion of worker '{self._task.worker_id}':", e)
                self._on_error(e)
        self._task = None

    def _on_error(self, error):
        self._error = error
        try: self._task.error(error)
        except Exception as e:
            e.__suppress_context__ = True
            print("ERROR", "During handling of previous error:", e)


class PyWorker:
    def __init__(self, worker_id, auto_activate=True):
        self._id = worker_id
        self._qt = _Task(self)
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

class PyLock:
    """ Basic syncronization object, similar to threading.Lock but intended to be used with PyWorkers"""
    def __init__(self):
        self._qt = QtCore.QMutex()

    def __enter__(self): self.lock()
    def __exit__(self, exc_type, exc_val, exc_tb): self.unlock()

    def lock(self, timeout=None):
        if timeout is not None: self._qt.tryLock(timeout)
        else: self._qt.lock()

    def unlock(self):
        self._qt.unlock()

class PyWaitCondition:
    def __init__(self):
        self._lock = PyLock()
        self._qt = QtCore.QWaitCondition()

    def __enter__(self): self.lock()
    def __exit__(self, exc_type, exc_val, exc_tb): self.unlock()

    def lock(self, ms=0, sec=0):
        """
         Attempt to lock the associated mutex for specified wait time
         If no or negative delay specified, it will wait forever until locked
         Returns true if the lock was succesfully obtained
        """
        self._lock.lock(sec*1000+ms)

    def unlock(self):
        """ Unlock associated mutex """
        self._lock.unlock()

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
        res = self._qt.wait(self._lock._qt, min*60000+sec*1000+ms)
        return res