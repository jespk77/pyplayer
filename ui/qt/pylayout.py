from PyQt5 import QtCore, QtGui, QtWidgets

class PyLayout:
    layout_name = "undefined"

    def __init__(self): self._qt = None
    def insert_element(self, element): raise TypeError("Cannot insert items in an undefined layout")

class PyGridLayout(PyLayout):
    layout_name = "grid"

    def __init__(self, owner):
        PyLayout.__init__(self)
        self._qt = QtWidgets.QGridLayout(owner)

    @property
    def qt_layout(self): return self._qt

    @property
    def rows(self): return self._qt.rowCount()
    @property
    def columns(self): return self._qt.columnCount()

    def row(self, index, minsize=None, weight=None):
        if minsize: self._qt.setRowMinimumHeight(index, minsize)
        if weight: self._qt.setRowStretch(index, weight)
        return self

    def column(self, index, minsize=None, weight=None):
        if minsize: self._qt.setColumnMinimumWidth(index, minsize)
        if weight: self._qt.setColumnStretch(index, weight)
        return self

    def insert_element(self, element, row=0, column=0, rowspan=1, columnspan=1):
        self._qt.addWidget(element, row, column, rowSpan=rowspan, columnSpan=columnspan)
        return self

layouts = {
    PyGridLayout.layout_name: PyGridLayout
}