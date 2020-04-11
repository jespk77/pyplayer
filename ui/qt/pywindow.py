from PyQt5 import QtWidgets, Qt, QtCore
import sys, weakref

from . import pyelement, pyevents, pylayout, pynetwork, log_exception

class _MainWindowQt(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.resize_cb = None
        self.close_cb = self.destroy_cb = None

    def closeEvent(self, event):
        try:
            if self.close_cb and self.close_cb(): return event.ignore()

            if self.destroy_cb:
                self.destroy_cb()
                self.close_cb = self.destroy_cb = None
            QtWidgets.QWidget.closeEvent(self, event)
        except Exception as e: log_exception(e)

    def resizeEvent(self, event):
        try:
            if self.resize_cb:
                new_size = event.size()
                self.resize_cb(new_size.width(), new_size.height())
            QtWidgets.QWidget.resizeEvent(self, event)
        except Exception as e: log_exception(e)

class PyWindow:
    def __init__(self, parent, layout="grid"):
        self._parent = parent
        self._qt = _MainWindowQt()
        self._elements = {}
        self._children = weakref.WeakValueDictionary()
        self._event_handler = pyevents.PyWindowEvents()

        self._qt.destroy_cb = self._on_window_destroy
        self._qt.close_cb = lambda : self.events.call_event("window_close")
        self._qt.resize_cb = lambda width, height: self.events.call_event("window_resize", width=width, height=height)

        try: self._layout = pylayout.layouts[layout](self._qt)
        except KeyError: self._layout = None
        if not self._layout: raise ValueError(f"Unknown layout: '{layout}'")
        self._qt.setLayout(self._layout.qt_layout)

        self.title = "PyWindow"
        try:
            self.create_widgets()
            self.events.call_event("window_open")
        except Exception as e:
            print("ERROR", "Encountered error while creating widgets:")
            log_exception(e)

    def create_widgets(self):
        """ Utility method for adding initial elements to this window, ensures everything is initialized in the correct order """
        pass

    def make_borderless(self):
        """ Makes this window borderless, if set the user cannot move or resize the window via the window system """
        self._qt.setWindowFlags(QtCore.Qt.FramelessWindowHint)

    @property
    def layout(self): return self._layout
    @property
    def events(self): return self._event_handler

    @property
    def title(self): return self._qt.windowTitle()
    @title.setter
    def title(self, value): self._qt.setWindowTitle(value)

    @property
    def icon(self): return None
    @icon.setter
    def icon(self, icon): pass

    def center_window(self, size_x=None, size_y=None, fit_to_size=False):
        """
            Center this window around given resolution, leave values blank to use the current resolution
            If 'fit_to_size' is True, the window will be fixed to given resolution (only if 'size_x' or 'size_y' are not empty)
        """
        if size_x is None: size_x = self._qt.height()
        elif fit_to_size: self._qt.setFixedHeight(size_x)
        if size_y is None: size_y = self._qt.width()
        elif fit_to_size: self._qt.setFixedWidth(size_y)

        center = QtWidgets.QDesktopWidget().availableGeometry().center()
        geometry = self._qt.frameGeometry()
        geometry.moveTo(center.x() - (.5 * size_x), center.y() - (.5 * size_y))
        self._qt.setGeometry(geometry)

    def _on_window_destroy(self):
        for c in self._children.values(): c.destroy()
        self.events.call_event("window_destroy")

    def add_element(self, element_id, element=None, element_class=None, **layout_kwargs):
        """ Add new element to this window, closes previously opened element with the same id (if open) """
        element_id = element_id.lower()
        self.remove_element(element_id)

        if not element:
            if not element_class: raise ValueError("Must specify an element type")
            elif not issubclass(element_class, pyelement.PyElement): raise TypeError("'element_class' must be a PyElement class")
            element = element_class(self, id)
        elif not isinstance(element, pyelement.PyElement): raise TypeError("'element' parameter must be a PyElement instance")

        self._layout.insert_element(element, **layout_kwargs)
        self._elements[element_id] = element
        return self._elements[element_id]
    __setitem__ = add_element

    def get_element(self, element_id) -> pyelement.PyElement:
        """ Get element assigned to given id, raises KeyError if no element found
            Use 'find_element' instead if this is undesired """
        return self._elements[element_id]
    __getitem__ = get_element

    def find_element(self, element_id) -> pyelement.PyElement:
        """ Safe alternative to 'get_element', returns None instead of raising KeyError when no elements found """
        return self._elements.get(element_id)

    def remove_element(self, element_id) -> bool:
        """ Remove element with given id from this window, has no effect if no elements with that id were found
            Returns true if an element was found and destroyed """
        element_id = element_id.lower()
        element = self.find_element(element_id)
        if element:
            element._qt.close()
            del self._elements[element_id]
            return True
        return False
    __delitem__ = remove_element

    def add_window(self, window_id, window=None, window_class=None):
        """ Open new window with given id, closes previously opened window with this id if any was open
            use 'window' for attaching a previously created PyWindow instance
            'window_class' must be a subclass of PyWindow, creates an instance of PyWindow if left out
            Returns the newly created window """
        window_id = window_id.lower()
        self.close_window(window_id)

        if not window:
            if not window_class: window_class = PyWindow
            elif not issubclass(window_class, PyWindow): raise TypeError("'window_class' parameter must be a PyWindow class")
            window = window_class(self)
        elif not isinstance(window, PyWindow): raise TypeError("'window' parameter must be a PyWindow instance")

        self._children[window_id] = window
        self._children[window_id]._qt.show()
        return self._children[window_id]

    def get_window(self, window_id):
        """ Get open window with given id, raises KeyError when no window with this id is open
            Use find_window instead if this is undesired """
        return self._children[window_id]

    def find_window(self, window_id):
        """ Safe alternative to get_window, returns None when no open window exists instead """
        return self._children.get(window_id)

    def close_window(self, window_id):
        """ CLose window with given id, has no effect if no window with this is is open """
        window = self.find_window(window_id)
        if window: window.destroy()

    def destroy(self):
        """ Closes this window along with any open child windows """
        self._qt.close()

class RootPyWindow(PyWindow):
    def __init__(self, layout="grid"):
        self._app = QtWidgets.QApplication(sys.argv)
        PyWindow.__init__(self, layout)
        self.title = "RootPyWindow"

    def start(self):
        """ Run the application, this method will keep running until the root window is closed """
        self._qt.show()
        self._app.exec()