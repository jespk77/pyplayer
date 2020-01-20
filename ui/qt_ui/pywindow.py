import PyQt5.QtWidgets as qt
import sys, weakref

from . import pyelement, block_action, log_exception

class MainWindowQt(qt.QWidget):
    def __init__(self):
        qt.QWidget.__init__(self)
        self._close_cb = None

    @property
    def _close_callback(self): return self._close_cb
    @_close_callback.setter
    def _close_callback(self, cb): self._close_cb = cb

    def closeEvent(self, event):
        try:
            if self._close_cb:
                res = self._close_cb()
                if res == block_action: return event.ignore()
                self._close_cb = None
            else: qt.QWidget.closeEvent(self, event)
        except Exception as e: log_exception(e)

class PyWindow:
    default_title = "PyWindow"

    def __init__(self):
        self._qt = MainWindowQt()
        self._qt.setWindowTitle(self.default_title)
        self._elements = {}
        self._children = weakref.WeakValueDictionary()
        self._qt._close_callback = self._on_window_close
        self._qt.setLayout(qt.QGridLayout())

    def block_action(self): return block_action

    @property
    def title(self): return self._qt.windowTitle()
    @title.setter
    def title(self, value): self._qt.setWindowTitle(value)

    @property
    def icon(self): return None
    @icon.setter
    def icon(self, icon): pass

    def _on_window_close(self):
        for c in self._children.values(): c.destroy()
        print("window close", self._qt.windowTitle())

    def add_element(self, element_id, element=None, element_class=None) -> pyelement.PyElement:
        """ Add new element to this window, closes previously opened element with the same id (if open) """
        element_id = element_id.lower()
        self.remove_element(element_id)

        if not element:
            if not element_class: raise ValueError("Must specify an element type")
            elif not issubclass(element_class, pyelement.PyElement): raise TypeError("'element_class' must be a PyElement class")
            element = element_class(self, id)
        elif not isinstance(element, pyelement.PyElement): raise TypeError("'element' parameter must be a PyElement instance")

        self._elements[element_id] = element
        return self._elements[element_id]

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
            Returns true if an element was found and closed """
        element_id = element_id.lower()
        element = self.find_element(element_id)
        if element:
            element._qt.close()
            del self._elements[element_id]
            return True
        return False

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
            window = window_class()
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
    default_title = "RootPyWindow"

    def __init__(self):
        self._app = qt.QApplication(sys.argv)
        PyWindow.__init__(self)

    def start(self):
        """ Run the application, this method will keep running until the root window is closed """
        self._qt.show()
        self._app.exec()