from PyQt5 import QtCore

class _Task(QtCore.QObject):
    def __init__(self, task):
        QtCore.QObject.__init__(self)
        self._thread = QtCore.QThread()
        self.moveToThread(self._thread)
        self._task = task
        self._error = None
        self._thread.started.connect(self.run)
        self._thread.finished.connect(self.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

    def start(self, priority=None):
        if priority is not None: self._thread.start(priority)
        else: self._thread.start()
    def isRunning(self): return self._thread.isRunning()

    def _on_start(self):
        try:
            self._task.start()
        except Exception as e:
            print("ERROR", f"Failed to start worker '{self._task.worker_id}':", e)
            self._on_error(e)
            self._task = None

    def run(self):
        self._on_start()
        try: self._task.run()
        except Exception as e:
            print("ERROR", f"During execution of worker '{self._task.worker_id}':", e)
            self._on_error(e)
        self._on_finished()

    def _on_error(self, error):
        self._error = error
        try: self._task.error(error)
        except Exception as e:
            e.__suppress_context__ = True
            print("ERROR", "During handling of previous error:", e)

    def _on_finished(self):
        if not self._error:
            try: self._task.complete()
            except Exception as e:
                print("ERROR", f"On completion of worker '{self._task.worker_id}':", e)
                self._on_error(e)

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

class PyWaitCondition:
    def __init__(self):
        self._lock = QtCore.QMutex()
        self._qt = QtCore.QWaitCondition()

    def __enter__(self): self.lock()
    def __exit__(self, exc_type, exc_val, exc_tb): self.unlock()

    def lock(self, ms=0, sec=0):
        """
         Attempt to lock the associated mutex for specified wait time
         If none or negative delay specified, it will wait forever until locked
         Returns True if the lock was successfully obtained
        """
        time = sec*1000+ms
        if time > 0: self._lock.tryLock(time)
        else: self._lock.lock()

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
        res = self._qt.wait(self._lock, min * 60000 + sec * 1000 + ms)
        return res