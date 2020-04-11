from PyQt5 import QtCore
from . import log_exception

class NetworkRequest(QtCore.QThread):
    completed_event = QtCore.pyqtSignal(object)
    STATUS_OK = 200

    def __init__(self, url):
        QtCore.QThread.__init__(self)
        self._url = url
        self._request = None

    @property
    def url(self): return self._url
    @property
    def status(self): return self._request.status_code if self._request else None
    @property
    def data(self): return self._request.content if self._request else None
    @property
    def error(self): return self._request is not None and self.status != self.STATUS_OK

    def is_completed(self): return self.status is not None

    def run(self):
        import requests
        self._request = requests.get(self.url)
        try: self.completed_event.emit(self)
        except Exception as e: log_exception(e)

class NetworkManager:
    def __init__(self):
        self._requests = {}

    def has_request(self, url): return url in self._requests

    def request_get(self, url, finished_cb):
        print("INFO", "Initializing request to", url)
        req = NetworkRequest(url)
        if self.has_request(url): raise RuntimeError(f"Another request to '{url}' still pending!")
        self._requests[url] = req, finished_cb
        req.completed_event.connect(self._request_finished)
        req.start()

    def _request_finished(self, request):
        print("INFO", "Request to", request.url, "finished")
        entry = self._requests.get(request.url)
        if entry:
            try:
                del self._requests[request.url]
                entry[1](request.status, request.data)
            except Exception as e:
                print("ERROR", "Exception occured while handling network request:")
                log_exception(e)