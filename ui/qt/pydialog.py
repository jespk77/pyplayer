import os
from PyQt5 import QtGui, QtWidgets

from . import pyevents, pywindow

class PyDialog:
    """
     Basic dialog that show a message to the user
    """
    def __init__(self, parent, message=None):
        if not isinstance(parent, pywindow.PyWindow): raise TypeError("Parent must be a PyWindow")
        self._parent = parent
        if not hasattr(self, "_qt"):
            self._qt = QtWidgets.QMessageBox(parent.qt_window)
            self._qt.setText(message)
        self.qt_dialog.accepted.connect(self._on_submit)
        self._event_handler = pyevents.PyDialogEvent(self)

    @property
    def qt_dialog(self): return self._qt
    @property
    def parent(self): return self._parent
    @property
    def events(self): return self._event_handler

    def open(self): self.qt_dialog.open()
    def close(self): self.qt_dialog.close()

    def _on_submit(self): self._event_handler.call_event("submit", value=True)
    def _on_cancel(self): self._event_handler.call_event("cancel")


class PyFileDialog(PyDialog):
    """
     Dialog that allows the user to select a file or directory
     Submission event provides the file or directory selected
    """
    def __init__(self, parent, mode=None, text="", directory=""):
        self._qt = QtWidgets.QFileDialog(parent.qt_window, caption=text, directory=directory)
        PyDialog.__init__(self, parent)
        if mode is not None: self.set_mode(mode)

    @property
    def load(self): return not self.save
    @load.setter
    def load(self, load): self.save = not load

    @property
    def save(self): return self.qt_dialog.acceptMode() == QtWidgets.QFileDialog.AcceptSave
    @save.setter
    def save(self, save): self.qt_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave if save else QtWidgets.QFileDialog.AcceptOpen)

    @property
    def file(self): return self.qt_dialog.selectedFiles()[0]
    @file.setter
    def file(self, file): self.qt_dialog.selectFile(file)

    @property
    def directory(self): return os.path.split(self.qt_dialog.selectedFiles()[0])[0]
    @directory.setter
    def directory(self, directory): self.qt_dialog.setDirectory(directory)

    @property
    def filter(self):
        ls = self.qt_dialog.nameFilters()
        return ls[0] if len(ls) == 1 else ls
    @filter.setter
    def filter(self, filt):
        self.qt_dialog.setNameFilters(filt) if isinstance(filt, list) else self.qt_dialog.setNameFilter(filt)

    @property
    def value(self): return self.directory if self.qt_dialog.fileMode() == QtWidgets.QFileDialog.Directory else self.file

    _mode = {"any": QtWidgets.QFileDialog.AnyFile, "existing": QtWidgets.QFileDialog.ExistingFile, "directory": QtWidgets.QFileDialog.Directory}
    def set_mode(self, mode):
        val = self._mode.get(mode)
        if val is None: raise ValueError(f"Unknown mode '{mode}', must be one of [{','.join(self._mode.items())}]")
        self.qt_dialog.setFileMode(val)

    def _on_submit(self): self._event_handler.call_event("submit", value=self.value)

class PyColorDialog(PyDialog):
    """
     Dialog that lets the user select a color
     Submission event provides the selected color in hex format (#RRGGBB[AA])
    """
    def __init__(self, parent, color=None):
        self._qt = QtWidgets.QColorDialog(QtGui.QColor(color), parent.qt_window) if color is not None else QtWidgets.QColorDialog(parent.qt_window)
        PyDialog.__init__(self, parent)

    @property
    def color(self):
        color = self.qt_dialog.currentColor()
        return color.name() if not self.alpha else "#" + hex(color.rgba()).lstrip("0x")
    @color.setter
    def color(self, color): self.qt_dialog.setCurrentColor(QtGui.QColor(color))

    @property
    def alpha(self): return self.qt_dialog.options() & QtWidgets.QColorDialog.ShowAlphaChannel
    @alpha.setter
    def alpha(self, alpha): self.qt_dialog.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, bool(alpha))

    def _on_submit(self): self._event_handler.call_event("submit", value=self.color)