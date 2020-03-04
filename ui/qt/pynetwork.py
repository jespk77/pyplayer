from PyQt5 import QtGui, QtNetwork
from . import log_exception

class NetworkManager:
    def __init__(self, parent):
        self._qt = QtNetwork.QNetworkAccessManager(parent)

    def load(self, url, finished_cb, error_cb=None):
        """ Load data asyncronously from given url, calls 'finished_cb' with the collected data when done
            If an error occurs and 'error_cb' was defined, this is called with the error code
            If 'error_cb' is not defined a RuntimeError is raised instead """
        req = QtNetwork.QNetworkRequest()
        req.setUrl(url)
        reply = self._qt.get(req)
        reply.finished().connect(lambda: NetworkManager._process_reply(reply, finished_cb, error_cb))

    @staticmethod
    def _process_reply(reply, cb, err_cb):
        try:
            if reply.error() == QtNetwork.QNetworkReply.NoError: cb(reply)
            elif err_cb: err_cb(reply.error())
            else: raise RuntimeError(f"Request to '{reply.url()}' failed with code {reply.error()}")
        except Exception as e: log_exception(e)