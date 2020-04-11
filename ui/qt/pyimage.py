from PyQt5 import QtCore, QtGui

from . import log_exception

def PyImage(parent, file=None, url=None, data=None):
    if file:
        print("VERBOSE", "Loading image from file", file)
        img = _PyImage(parent)
        img.load_image(file)
        return img

    if url:
        print("VERBOSE", "Loading image from url", url)
        from . import network_manager
        img = _PyImage(parent)
        def _load_image(status, data):
            if status == 200:
                print("VERBOSE", "PyImage: fromURL: status OK")
                img.load_image(QtCore.QByteArray(data))
            else: print("WARNING", "PyImage fromURL: status", status)
        network_manager.request_get(url, _load_image)
        return img

    if data:
        print("VERBOSE", "Loading image from bytes")
        img = _PyImage(parent)
        img.load_image(QtCore.QByteArray(data))
        return img
    raise ValueError("No image data specified")


class _PyImage:
    """
     Wrapper class for images
     Should not be constructed on its own, use the constructor helper 'PyImage' instead
    """
    def __init__(self, parent):
        self._parent = parent
        self._animated = False
        self._img = self._buffer = self._data = None

    def load_image(self, data):
        try:
            self._data = data
            if isinstance(data, QtCore.QByteArray):
                self._buffer = QtCore.QBuffer(data)
                self._buffer.open(QtCore.QBuffer.ReadOnly)
            else: self._buffer = data

            reader = QtGui.QImageReader(self._buffer)
            if reader.canRead():
                self._animated = reader.imageCount() > 1
                if self._animated:
                    self._img = QtGui.QMovie()
                    self._img.setDevice(self._buffer)
                else: self._img = QtGui.QPixmap(reader.read())

            if not self._img: print("ERROR", "Invalid image data received")
            else: self._parent.set_image(self)
        except Exception as e: log_exception(e)

    @property
    def animated(self): return self._animated

    @property
    def data(self): return self._img

    def start(self):
        """ Start the animation """
        if self.animated: self._img.start()

    def stop(self):
        """ Stop the animation """
        if self.animated: self._img.stop()