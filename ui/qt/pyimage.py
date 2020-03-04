from PyQt5 import QtGui

class PyImage:
    def __init__(self, parent, img=None, url=None):
        self._img_data = None
        self._is_animated = False

        if url:
            parent.network_manager.load(url, self._set_image)
            self._img_data = "..."

        if not self._img_data and img:
            img_data = QtGui.QImageReader(img)
            if img_data.canRead():
                self._is_animated = img_data.supportsAnimation()
                self._img_data = QtGui.QMovie(img) if self.animated else QtGui.QPixmap.fromImage(img_data.read())
            else: raise FileNotFoundError(img)

        if not self._img_data: raise ValueError("Must specify either a url or a local path")

    def _set_image(self, data):
        img = QtGui.QImageReader(data)
        if img.canRead():
            self._is_animated = img.supportsAnimation()
            self._img_data = QtGui.QMovie(data) if self.animated else QtGui.QPixmap.fromImage(img.read())
        else:
            print("ERROR", "Failed to read image data")
            self._img_data = None

    def _image_failed(self, error):
        print("ERROR", f"Failed to get data: {error}")
        self._img_data = None

    @property
    def animated(self): return self._is_animated

    @property
    def is_ready(self): return self._img_data != "..."

    @property
    def data(self): return self._img_data