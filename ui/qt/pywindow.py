from PyQt5 import QtWidgets, QtCore, QtGui
import sys, weakref

from . import pyelement, pyevents, pylayout, log_exception
from .. import pyconfiguration

class _ScheduledTask(QtCore.QTimer):
    _schedule_signal = QtCore.pyqtSignal(int, bool, dict)

    def __init__(self, func):
        QtCore.QTimer.__init__(self)
        self._cb = func
        self._kwargs = {}
        self._schedule_signal.connect(self._schedule)
        self.timeout.connect(self._run_task)

    def schedule(self, delay, loop, kwargs=None): self._schedule_signal.emit(delay, loop, kwargs)

    def _schedule(self, delay, loop, kwargs=None):
        self.setInterval(delay)
        self.setSingleShot(not loop)
        if kwargs: self._kwargs.update(kwargs)
        self.start()

    def _run_task(self):
        try: return self._cb(**self._kwargs)
        except Exception as e: log_exception(e)


class PyWindow:
    def __init__(self, parent, window_id, layout="grid"):
        self._parent = parent
        self._window_id = window_id.lower()
        self._qt = QtWidgets.QWidget()
        self._qt.resizeEvent = self._on_window_resize
        self._qt.closeEvent = self._on_window_close

        self._elements = {}
        self._scheduled_tasks = {}
        self._children = weakref.WeakValueDictionary()
        self._event_handler = pyevents.PyWindowEvents()
        self._cfg = pyconfiguration.ConfigurationFile(f".cfg/{window_id}")
        self._closed = False

        try: self._layout = pylayout.layouts[layout](self.qt_element)
        except KeyError: self._layout = None
        if not self._layout: raise ValueError(f"Unknown layout: '{layout}'")
        self.qt_element.setLayout(self._layout.qt_layout)

        self.title = "PyWindow"
        try:
            self.create_widgets()
            self.events.call_event("window_open")
        except Exception as e:
            print("ERROR", "Encountered error while creating widgets:")
            log_exception(e)
        self.hidden = True

    def create_widgets(self):
        """ Utility method for adding initial elements to this window, ensures everything is initialized in the correct order """
        pass

    def make_borderless(self):
        """ Makes this window borderless, if set the user cannot move or resize the window via the window system """
        self.qt_element.setWindowFlags(QtCore.Qt.FramelessWindowHint)

    @property
    def children(self):
        """ Returns an iterator with all contained child element """
        return self._elements.values()

    @property
    def windows(self):
        """ Returns an iterator with all open child windows """
        return self._children.values()

    @property
    def is_closed(self): return self._closed

    @property
    def qt_element(self): return self._qt
    @property
    def window_id(self): return self._window_id
    @property
    def layout(self): return self._layout
    @property
    def events(self): return self._event_handler
    @property
    def configuration(self): return self._cfg
    cfg = configuration

    @property
    def title(self): return self.qt_element.windowTitle()
    @title.setter
    def title(self, value): self.qt_element.setWindowTitle(value)

    @property
    def icon(self): return self.qt_element.windowIcon() is not None
    @icon.setter
    def icon(self, icon): self.qt_element.setWindowIcon(QtGui.QIcon(icon))

    @property
    def hidden(self): return self.qt_element.isHidden()
    @hidden.setter
    def hidden(self, hide): self.qt_element.setHidden(hide)

    @property
    def geometry_string(self):
        """
         Returns the geometry of this window using the legacy string format
         Note: Don't use this if not familiar with the format
        """
        geo = self.qt_element.geometry()
        return f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"

    def set_geometry(self, x=None, y=None, width=None, height=None, geometry=None):
        """ Update the geometry of this window using properties or with a legacy style geometry string """
        if geometry is not None:
            if not isinstance(geometry, str): raise ValueError("Geometry string must be string")
            import re
            res = re.findall("\d+", geometry)
            if len(res) == 4: self.qt_element.setGeometry(res[2], res[3], res[0], res[1])
            else: raise ValueError("Invalid geometry string")
            return

        if x is None or y is None or width is None or height is None: raise ValueError("Missing arguments")
        self.qt_element.setGeometry(x, y, width, height)

    def center_window(self, size_x=None, size_y=None, fit_to_size=False):
        """
            Center this window around given resolution, leave values blank to use the current resolution
            If 'fit_to_size' is True, the window will be fixed to given resolution (only if 'size_x' or 'size_y' are not empty)
        """
        if size_x is None: size_x = self.qt_element.height()
        elif fit_to_size: self.qt_element.setFixedHeight(size_x)
        if size_y is None: size_y = self.qt_element.width()
        elif fit_to_size: self.qt_element.setFixedWidth(size_y)

        center = QtWidgets.QDesktopWidget().availableGeometry().center()
        geometry = self.qt_element.frameGeometry()
        geometry.moveTo(center.x() - (.5 * size_x), center.y() - (.5 * size_y))
        self.qt_element.setGeometry(geometry)

    def add_element(self, element_id=None, element=None, element_class=None, **layout_kwargs):
        """ Add new element to this window, closes previously opened element with the same id (if open) """
        if not element:
            if not element_class: raise ValueError("Must specify an element type")
            elif not element_id: raise ValueError("Must specify an element id")
            elif not issubclass(element_class, pyelement.PyElement): raise TypeError("'element_class' must be a PyElement class")
            element = element_class(self, element_id)
        elif isinstance(element, pyelement.PyElement): element_id = element.element_id
        else: raise TypeError("'element' parameter must be a PyElement instance")

        self.remove_element(element_id)
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
            element.qt_element.close()
            del self._elements[element_id]
            return True
        return False
    __delitem__ = remove_element

    def add_window(self, window_id=None, window=None, window_class=None):
        """ Open new window with given id, closes previously opened window with this id if any was open
            use 'window' for attaching a previously created PyWindow instance
            'window_class' must be a subclass of PyWindow, creates an instance of PyWindow if left out
            Returns the newly created window """
        if not window:
            if not window_id: raise ValueError("Must specify a window_id")
            window_id = window_id.lower()
            if not window_class: window_class = PyWindow
            elif not issubclass(window_class, PyWindow): raise TypeError("'window_class' parameter must be a PyWindow class")
            window = window_class(self, window_id)
        elif isinstance(window, PyWindow): window_id = window.window_id
        else: raise TypeError("'window' parameter must be a PyWindow instance")

        self.close_window(window_id)
        self._children[window_id] = window
        self._children[window_id].qt_element.show()
        return self._children[window_id]

    def get_window(self, window_id):
        """ Get open window with given id, raises KeyError when no window with this id is open
            Use find_window instead if this is undesired """
        window = self._children[window_id]
        if window.is_closed: raise KeyError(window_id)
        return window

    def find_window(self, window_id):
        """ Safe alternative to get_window, returns None when no open window exists instead """
        window = self._children.get(window_id)
        return window if window is not None and not window.is_closed else None

    def close_window(self, window_id):
        """ CLose window with given id, has no effect if no window with this is is open """
        window = self.find_window(window_id)
        if window: window.destroy()

    def destroy(self):
        """ Closes this window along with any open child windows """
        self.qt_element.close()

    def add_task(self, task_id, func):
        """ Bind a function to a task id without scheduling it """
        if not self.has_task(task_id):
            self._scheduled_tasks[task_id] = _ScheduledTask(func)

    def has_task(self, task_id, running=False):
        """
         Returns whether current task id is known, that is, it can be changed or canceled using just this id
         If running is true, this call will only return true if the task is also running, otherwise it returns true if it exists
        """
        task = self._scheduled_tasks.get(task_id)
        if task: return running == task.isActive() if running else True
        return False

    # todo: scheduling tasks from another thread only work if the task was added previously
    def schedule_task(self, min=0, sec=0, ms=0, func=None, loop=False, task_id=None, **kwargs):
        """
        Schedule an operation to be executed at least after the given time, all registered callbacks will stop when the window is closed
        	- Amount of time to wait can be specified with minutes (keyword 'min'), seconds (keyword 'sec') and/or milliseconds (keyword 'ms')
        	- The argument passed to func must be callable and accept all extra keywords passed to this function
        	- The function can be executed repeatedly by setting 'loop' to True;
        	     in this case it will be executed repeatedly after the given time either until the window is destroyed, an error occurs, or the callback returns False
        	  Note: If looping is set, the delay must be at least 100 milliseconds
            - The 'task_id' argument (if proviced) must be a string is used to later cancel, postpone or change the previously scheduled function
               Note: scheduled tasks without a task_id cannot be looping and cannot be changed once scheduled
        """
        delay = min * 60000 + sec * 1000 + ms
        if delay < 0: raise ValueError("Delay must be positive")
        elif delay < 100 and loop: raise ValueError("Looping task must have some delay")

        task: _ScheduledTask = self._scheduled_tasks.get(task_id)
        if task and not func:
            task.schedule(delay, loop, kwargs)
            return

        if not callable(func): raise ValueError("Newly scheduled tasks must have a valid callback")

        if task_id:
            task = _ScheduledTask(func)
            task.schedule(delay, loop, kwargs)
            self._scheduled_tasks[task_id] = task
        else:
            def _execute_task():
                try: func(**kwargs)
                except Exception as e: log_exception(e)
            QtCore.QTimer.singleShot(delay, _execute_task)

    def cancel_task(self, task_id):
        """
         Cancel previously scheduled task with given id, the id must have previously been added with 'add_task' or 'schedule_task'
         Has no effect if the task is not currently scheduled
        """
        self._scheduled_tasks[task_id].cancel()

    def delete_task(self, task_id):
        """
         Cancel and remove scheduled task with given id, the id must have previously been added with 'add_task' or 'schedule_task'
         Once this call completes the given id is cleared and cannot be used without readding it as a new task
        """
        task = self._scheduled_tasks[task_id]
        task.cancel()
        del self._scheduled_tasks[task_id]

    def save_configuration(self):
        """
         Save current configuration options to file (if changed)
         Note: configuration is automatically saved when the window closes, this only needs to be called if changes need to be written beforehand
        """
        self._cfg.save()

    # QWidget.resizeEvent override
    def _on_window_resize(self, event):
        try:
            new_size = event.size()
            self.events.call_event("window_resize", width=new_size.width(), height=new_size.height())
        except Exception as e: log_exception(e)
        QtWidgets.QWidget.resizeEvent(self.qt_element, event)

    # QWidget.closeEvent override
    def _on_window_close(self, event):
        try:
            if self.events.call_event("window_close") == self.events.block: return event.ignore()

            self.save_configuration()
            for c in self._children.values(): c.destroy()
            self.events.call_event("window_destroy")
            self._closed = True
        except Exception as e: log_exception(e)
        QtWidgets.QWidget.closeEvent(self.qt_element, event)

class RootPyWindow(PyWindow):
    def __init__(self, window_id, layout="grid"):
        self._app = QtWidgets.QApplication(sys.argv)
        PyWindow.__init__(self, None, window_id=window_id, layout=layout)
        self.title = "RootPyWindow"

    def start(self):
        """ Run the application, this method will keep running until the root window is closed """
        self.qt_element.show()
        self._app.exec()