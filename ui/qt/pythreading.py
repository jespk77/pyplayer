import threading

class PySingleLock:
    """
        Basic synchronization object, similar to threading.Lock but intended to be used with PyWorkers
        Only allows one 'lock()' at a time
    """
    def __init__(self):
        if not hasattr(self, "_lock"): self._lock = threading.Lock()

    def __enter__(self): self.lock()
    def __exit__(self, exc_type, exc_val, exc_tb): self.unlock()

    def lock(self, timeout=None):
        """
            Try to get the key for this lock
            If 'timeout' is specified and a number >= 0 and indicates the number of seconds to wait
            If 'timeout' is less than 0 or not given, this function will block until the lock becomes available
            Returns True if the key was obtained, False otherwise
        """
        block = timeout is not None and timeout >= 0
        return self._lock.acquire(block, timeout if block else -1)

    def unlock(self):
        """ Return the key for this lock so that other threads can get it """
        self._lock.release()

class PyLock(PySingleLock):
    """
        Similar to PySingleLock but allows multiple 'lock()' calls from the same thread
    """
    def __init__(self):
        self._lock = threading.RLock()
        PySingleLock.__init__(self)