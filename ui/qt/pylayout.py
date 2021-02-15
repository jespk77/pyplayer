from collections import namedtuple
from PyQt5 import QtWidgets

class PyLayout:
    layout_name = "undefined"

    def __init__(self, owner):
        self._owner = owner
        self._qt = None

    @property
    def owner(self): return self._owner

    @property
    def qt_layout(self): return self._qt

    def insert_element(self, element): raise TypeError("Cannot insert items in an undefined layout")
    def index_of(self, element_id): self.index_of(None)

    def margins(self, w=None, h=None, left=None, right=None, up=None, down=None):
        if w is None: w = h
        if h is None: h = w

        margin = self.qt_layout.getContentsMargins()
        if left is None: left = w if w is not None else margin[0]
        if right is None: right = w if w is not None else margin[2]
        if up is None: up = h if h is not None else margin[1]
        if down is None: down = h if h is not None else margin[3]
        self.qt_layout.setContentsMargins(left, up, right, down)
        return self

class PyGridLayout(PyLayout):
    layout_name = "grid"
    GridPosition = namedtuple("GridPosition", ["row", "column", "rowspan", "columnspan"])

    def __init__(self, owner):
        PyLayout.__init__(self, owner)
        self._qt = QtWidgets.QGridLayout(owner.qt_element)

    @property
    def rows(self): return self.qt_layout.rowCount()
    @property
    def columns(self): return self.qt_layout.columnCount()

    def row(self, index, minsize=None, weight=None):
        if minsize is not None: self.qt_layout.setRowMinimumHeight(index, minsize)
        if weight is not None: self.qt_layout.setRowStretch(index, weight)
        return self

    def column(self, index, minsize=None, weight=None):
        if minsize is not None: self.qt_layout.setColumnMinimumWidth(index, minsize)
        if weight is not None: self.qt_layout.setColumnStretch(index, weight)
        return self

    def insert_element(self, element, row=0, column=0, rowspan=1, columnspan=1):
        self.qt_layout.addWidget(element._qt, row, column, rowspan, columnspan)
        return self

    def index_of(self, item_id):
        element = self.owner.find_element(item_id)
        if element is not None:
            return self.GridPosition(*self.qt_layout.getItemPosition(self.qt_layout.indexOf(element.qt_element)))
        else: return None

class PyVerticalLayout(PyLayout):
    layout_name = "vertical"

    def __init__(self, owner):
        PyLayout.__init__(self, owner)
        self._qt = QtWidgets.QVBoxLayout(owner.qt_element)

    @property
    def count(self): return self.qt_layout.count()

    def item(self, index, weight=None):
        if weight is not None: self.qt_layout.setStretch(index, weight)

    def insert_element(self, element, index=None, weight=0):
        if index is None: self.qt_layout.addWidget(element._qt, weight)
        else: self.qt_layout.insertWidget(index, element._qt, weight)
        return self

    def insert_spacing(self, index=None, spacing=0):
        if index is None: self.qt_layout.addSpacing(spacing)
        else: self.qt_layout.insertSpacing(index, spacing)

    def index_of(self, element_id):
        element = self.owner.find_element(element_id)
        if element is not None: return self.qt_layout.indexOf(element.qt_element)
        else: return None

class PyHorizontalLayout(PyVerticalLayout):
    layout_name = "horizontal"

    def __init__(self, owner):
        PyLayout.__init__(self, owner)
        self._qt = QtWidgets.QHBoxLayout(owner.qt_element)

layouts = {
    PyGridLayout.layout_name: PyGridLayout,
    PyVerticalLayout.layout_name: PyVerticalLayout,
    PyHorizontalLayout.layout_name: PyHorizontalLayout
}