import threading, time

class PyWorker:
    def __init__(self, window, worker_id, auto_activate=True):
        self._window = window
        self._thread = threading.Thread(name=worker_id, target=self._execute)
        if auto_activate: self.activate()

    def activate(self): self._thread.start()

    def wait(self, timeout=None):
        self._thread.join(timeout)
        return self.running

    @property
    def worker_id(self): return self._thread.name
    @property
    def running(self): return self._thread.is_alive()

    @staticmethod
    def sleep(seconds): time.sleep(seconds)

    def _execute(self):
        self._window.schedule_task(func=self.start)
        try:
            self.run()
        except Exception as e:
            print("ERROR", f"Executing worker '{self.worker_id}'", e)
            self._window.schedule_task(func=self.error, e=e)
        else:
            self._window.schedule_task(func=self.complete)

    def start(self):
        """
            Executed before the worker is started
            Runs on the window thread: direct control of window elements possible
        """
        pass

    def run(self):
        """
            Main execution of the worker
            Runs on its own thread: blocking functions should only be used here
        """
        pass

    def complete(self):
        """
            Executed if the worker completed successfully
            Runs on the window thread: direct control of window elements possible
        """
        pass

    def error(self, error):
        """
            Executed if the worker completed with an error
            Runs on the window thread: direct control of window elements possible
        """
        pass

class PyWaitCondition:
    def __init__(self):
        self._lock = threading.Lock()
        self._event = threading.Event()

    def __enter__(self): self._lock.__enter__()
    def __exit__(self, *args): self._lock.__exit__(*args)

    def notify(self):
        """ Wakes up all threads waiting on this WaitCondition """
        print("VERBOSE", "Notifying waiting threads")
        self._event.set()

    def wait(self, sec=0, min=0):
        """
         Wait for specified time or when it gets woken by another thread
         Note: the internal lock must be owned by the caller: this function can only be called within a with block
         Returns true if it was awoken or false if the wait time has passed
        """
        timeout = min * 60 + sec
        print("VERBOSE", f"Pausing process for {timeout}s or until notify happens")

        self._event.clear()
        self._lock.release()
        res = self._event.wait(timeout)
        print("VERBOSE", "Timeout expired or notify received, reacquiring lock and returning control back to owner")
        self._lock.acquire()
        return res