from PyQt5 import QtWidgets, QtCore, QtGui
import sys

from . import pyelement, pyevents, pylayout, pythreading, log_exception
from core import pyconfiguration


class _ScheduledTask(QtCore.QTimer):
    _schedule_signal = QtCore.pyqtSignal(int, bool, dict)
    _cancel_signal = QtCore.pyqtSignal()
    _finished_signal = QtCore.pyqtSignal()

    def __init__(self, func):
        QtCore.QTimer.__init__(self)
        self._cb = func
        self._kwargs = {}
        self._complete_event = QtCore.QEventLoop()
        self._finished_signal.connect(self._complete_event.quit)

        self._schedule_signal.connect(self._schedule)
        self._cancel_signal.connect(self._cancel)
        self.timeout.connect(self._run_task)

    def schedule(self, delay, loop, kwargs=None): self._schedule_signal.emit(delay, loop, kwargs)
    def _schedule(self, delay, loop, kwargs=None):
        self.setInterval(delay)
        self.setSingleShot(not loop)
        self._kwargs.clear()
        if kwargs: self._kwargs.update(kwargs)
        self.start()

    def cancel(self): self._cancel_signal.emit()
    def _cancel(self): self.stop()

    def wait(self):
        if self.isActive():
            self._complete_event.exec()

    def _run_task(self):
        val = None
        try: val = self._cb(**self._kwargs)
        except Exception as e: log_exception(e)
        self._finished_signal.emit()
        return val


import threading
class PyWindow:
    def __init__(self, parent, window_id, layout="grid"):
        if threading.current_thread() != threading.main_thread(): raise RuntimeError("Window must be created in main thread")
        if window_id is None: raise ValueError("Must specify a window id")
        if parent is not None and not isinstance(parent, PyWindow): raise ValueError(f"Parent must be a PyWindow instance, not '{type(parent).__name__}'")

        self._parent = parent
        self._window_id = window_id.lower()
        if not hasattr(self, "_qt"):
            self._qt = QtWidgets.QWidget()
            self._qt.setObjectName("PyWindow")
        self._window_lock = pythreading.PyLock()

        self.qt_window.resizeEvent = self._on_window_resize
        self.qt_window.closeEvent = self._on_window_close
        self.qt_window.hideEvent = self._on_window_hide
        self.qt_window.showEvent = self._on_window_show
        self.qt_window.hide()

        self._elements = {}
        self._scheduled_tasks = {}
        self._children = {}
        self._key_cb = {}
        self._event_handler = pyevents.PyWindowEvents(self)
        self._cfg = pyconfiguration.ConfigurationFile(window_id)
        self._closed = False

        try: self._layout = pylayout.layouts[layout](self)
        except KeyError: self._layout = None
        if not self.layout: raise ValueError(f"Unknown layout: '{layout}'")
        self.qt_element.setLayout(self.layout.qt_layout)

        self.title = "PyWindow"
        try: self.create_widgets()
        except Exception as e:
            print("ERROR", "Encountered error while creating widgets:")
            log_exception(e)

        geo = self._cfg.get("geometry")
        if isinstance(geo, list):
            self.set_geometry(*geo[:4])
            if len(geo) > 4:
                if geo[4] == 2: self.maximized = True
                elif geo[4] == 1: self.minimized = True
        self.add_task("_add_window", func=self._add_window)
        self.add_task("_close_window", func=self._close_window)

    def __del__(self): print("MEMORY", f"PyWindow '{self.window_id}' deleted")

    def create_widgets(self):
        """ Utility method for adding initial elements to this window, ensures everything is initialized in the correct order """
        pass

    def make_borderless(self):
        """ Makes this window borderless, if set the user cannot move or resize the window via the window system """
        self.qt_element.setWindowFlags(QtCore.Qt.FramelessWindowHint)

    @property
    def parent(self):
        """ Reference to the parent of this window, will always be a PyWindow """
        return self._parent
    @property
    def window(self):
        """ Reference to self (used for keeping attribute consistency with PyElement) """
        return self

    @property
    def children(self):
        """ Returns an iterator with all contained child element """
        return list(self._elements.values())

    @property
    def windows(self):
        """ Returns an iterator with all open child windows """
        return list(self._children.values())

    @property
    def is_closed(self): return self._closed

    @property
    def qt_element(self): return self._qt
    @property
    def qt_window(self): return self._qt
    @property
    def handle(self): return self.qt_window.winId()

    @property
    def window_id(self):
        """ The id this windows was registered with """
        try: return self._window_id
        except AttributeError: return "[Undefined]"

    @property
    def layout(self):
        """ Reference to the layout manager of this window """
        return self._layout

    @property
    def events(self):
        """ Reference to the event handler of this window """
        return self._event_handler

    @property
    def configuration(self):
        """ Reference to the configuration of this window """
        return self._cfg
    cfg = configuration

    @property
    def title(self): return self.qt_window.windowTitle()
    @title.setter
    def title(self, value): self.qt_window.setWindowTitle(str(value))

    @property
    def icon(self): return self.qt_window.windowIcon() is not None
    @icon.setter
    def icon(self, icon): self.qt_window.setWindowIcon(QtGui.QIcon(icon))

    @property
    def hidden(self): return self.qt_window.isHidden()
    @hidden.setter
    def hidden(self, hide): self.qt_window.setHidden(bool(hide))

    @property
    def maximized(self): return self.qt_window.isMaximized()
    @maximized.setter
    def maximized(self, maximized): self.qt_window.showMaximized() if maximized else self.qt_window.showNormal()
    @property
    def can_maximize(self): return int(self.qt_window.windowFlags()) & QtCore.Qt.WindowMaximizeButtonHint != 0
    @can_maximize.setter
    def can_maximize(self, maximize): self.qt_window.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, maximize)

    @property
    def minimized(self): return self.qt_window.isMinimized()
    @minimized.setter
    def minimized(self, minimized): self.qt_window.showMinimized() if minimized else self.qt_window.showNormal()
    @property
    def can_minimize(self): return int(self.qt_window.windowFlags()) & QtCore.Qt.WindowMinimizeButtonHint != 0
    @can_minimize.setter
    def can_minimize(self, minimize): self.qt_window.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint, minimize)

    @property
    def always_on_top(self): return int(self.qt_window.windowFlags()) & QtCore.Qt.WindowStaysOnTopHint
    @always_on_top.setter
    def always_on_top(self, top): self.qt_window.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, top)
    topmost = always_on_top

    def activate(self):
        """ Sets this window to be visible and have keyboard focus """
        self.qt_window.activateWindow()

    @property
    def geometry_string(self):
        """
         Returns the geometry of this window using the legacy string format
         Note: Don't use this if not familiar with the format
        """
        geo = self.qt_window.geometry()
        return f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"

    def set_geometry(self, x=None, y=None, width=None, height=None, geometry=None):
        """ Update the geometry of this window using properties or with a legacy style geometry string """
        if geometry is not None:
            if not isinstance(geometry, str): raise ValueError("Geometry string must be string")
            import re
            res = re.findall("\d+", geometry)
            if len(res) == 4: width, height, x, y = res
            else: raise ValueError("Invalid geometry string")

        if x is None: x = self.qt_window.x()
        if y is None: y = self.qt_window.y()
        if width is None: width = self.qt_window.width()
        if height is None: height = self.qt_window.height()
        self.qt_window.setGeometry(x,y,width,height)
        self.qt_window.move(x, y)
        self.qt_window.frameGeometry().setSize(QtCore.QSize(width, height))

    def center_window(self, size_x=None, size_y=None, fit_to_size=False):
        """
            Center this window around given resolution, leave values blank to use the current resolution
            If 'fit_to_size' is True, the window will be fixed to given resolution (only if 'size_x' or 'size_y' are not empty)
        """
        if size_x is None: size_x = self.qt_window.height()
        elif fit_to_size: self.qt_window.setFixedHeight(size_x)
        if size_y is None: size_y = self.qt_window.width()
        elif fit_to_size: self.qt_window.setFixedWidth(size_y)

        center = QtWidgets.QDesktopWidget().availableGeometry().center()
        geometry = self.qt_window.frameGeometry()
        geometry.moveTo(round(center.x() - (.5 * size_x)), round(center.y() - (.5 * size_y)))
        self.qt_window.setGeometry(geometry)

    def fill_window(self):
        """ Show this window full screen """
        self.qt_window.setGeometry(QtWidgets.QDesktopWidget().availableGeometry())

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
        self.layout.insert_element(element, **layout_kwargs)
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

    def add_window(self, window_id=None, window=None, window_class=None, **window_args):
        """ Open new window with given id, closes previously opened window with this id if any was open
            use 'window' for attaching a previously created PyWindow instance
            'window_class' must be a subclass of PyWindow, creates an instance of PyWindow if left out
            Supports custom keywords that are passed to the constructor of the window (ignored if window is specified) """
        self.schedule_task(task_id="_add_window", window_id=window_id, window=window, window_class=window_class, wait=True, window_args=window_args)

    def _add_window(self, window_id, window, window_class, window_args):
        if not window:
            if not window_class: window_class = PyWindow
            elif not issubclass(window_class, PyWindow): raise TypeError("'window_class' parameter must be a PyWindow class")

            if window_id:
                window_id = window_id.lower()
                window = window_class(self, window_id, **window_args)
            else:
                # when no window_id specified, try to construct a window anyway
                # can still work if a subclass constructor specifies a window id, otherwise the error is raised in the PyWindow constructor
                window = window_class(self, **window_args)
                window_id = window.window_id
        elif isinstance(window, PyWindow): window_id = window.window_id
        else: raise TypeError("'window' parameter must be a PyWindow instance")

        self._close_window(window_id)
        with self._window_lock:
            self._children[window_id] = window
            self._children[window_id].qt_window.show()
            self._children[window_id].events.call_event("window_open")

    def get_window(self, window_id):
        """
            Get open window with given id, raises KeyError when no window with this id is open
            Use 'find_window' instead if this is undesired
        """
        with self._window_lock:
            window = self._children[window_id]
            if window.is_closed:
                del self._children[window_id]
                raise KeyError(window_id)
            return window

    def find_window(self, window_id):
        """ Safe alternative to get_window, returns None when no open window exists instead """
        try: return self.get_window(window_id)
        except KeyError: return None

    def close_window(self, window_id):
        """ CLose window with given id, has no effect if no window with the id is open """
        self.schedule_task(task_id="_close_window", window_id=window_id)

    def _close_window(self, window_id):
        with self._window_lock:
            try: self.get_window(window_id).destroy()
            except KeyError: return

    def destroy(self):
        """
            Tries to close this window along with any open child windows
            After calling this function, the window can stay open if (for instance) the window close event was canceled
            Returns True if the window was closed, False otherwise
        """
        return self.qt_element.close()

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
    def schedule_task(self, min=0, sec=0, ms=0, func=None, loop=False, wait=False, task_id=None, **kwargs):
        """
            Schedule an operation to be executed at least after the given time, all registered callbacks will stop when the window is closed
        	 - Amount of time to wait can be specified with minutes (keyword 'min'), seconds (keyword 'sec') and/or milliseconds (keyword 'ms')
        	 - The argument passed to func must be callable and accept all extra keywords passed to this function
        	 - The function can be executed repeatedly by setting 'loop' to True:
        	     it will be executed repeatedly after the given time either until the window is destroyed, an error occurs, or the callback returns False
        	     Note: If looping is set, the delay must be at least 100 milliseconds
             - If 'wait' argument is True the function will wait for any previously scheduled tasks to finish before scheduling, otherwise the function that was scheduled is aborted
             - The 'task_id' argument (if provided) must be a string is used to later cancel, postpone or change the previously scheduled function
               Note: scheduled tasks without a task_id cannot be looping and cannot be changed once scheduled
        """
        delay = min * 60000 + sec * 1000 + ms
        if delay < 0: raise ValueError("Delay must be positive")
        elif delay < 100 and loop: raise ValueError("Looping task must have some delay")

        task: _ScheduledTask = self._scheduled_tasks.get(task_id)
        if task and not func:
            if wait: task.wait()
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
        self.cfg['geometry'] = self.qt_window.x(), self.qt_window.y(), self.qt_window.width(), self.qt_window.height(), 2 if self.maximized else 1 if self.minimized else 0
        self.configuration.save()

    def _on_key_down(self, event):
        if self.events.call_keydown_event(event):
            print("VERBOSE", "Key event was blocked and won't be forwarded to the window")
            return True

    # QWidget.resizeEvent override
    def _on_window_resize(self, event):
        try:
            new_size = event.size()
            self.events.call_event("window_resize", width=new_size.width(), height=new_size.height())
        except Exception as e: log_exception(e)
        QtWidgets.QWidget.resizeEvent(self.qt_window, event)

    # QWidget.closeEvent override
    def _on_window_close(self, event):
        print("VERBOSE", f"Window {self.window_id} closed")
        try:
            if self.events.call_event("window_close") == self.events.block: return event.ignore()
            for window in self.windows:
                if not window.destroy():
                    window.activate()
                    return event.ignore()

            if self._parent:
                try: del self._parent._children[self.window_id]
                except KeyError: pass
            for element in self.children: element.on_destroy()

            self.events.call_event("window_destroy")
            self.save_configuration()
            self._closed = True
        except Exception as e: log_exception(e)
        self._scheduled_tasks = None
        QtWidgets.QWidget.closeEvent(self.qt_window, event)

    # QWidget.hideEvent override
    def _on_window_hide(self, event):
        if not self._closed:
            self.events.call_event("window_hide")
            QtWidgets.QWidget.hideEvent(self.qt_window, event)

    # QWidget.showEvent override
    def _on_window_show(self, event):
        if not self._closed:
            self.events.call_event("window_show")
            QtWidgets.QWidget.showEvent(self.qt_window, event)

def default_palette():
    Palette, Color = QtGui.QPalette, QtGui.QColor
    foreground, background = Color(255,255,255), Color(35,35,35)

    palette = Palette()
    palette.setColor(Palette.Window, background)
    palette.setColor(Palette.WindowText, foreground)
    palette.setColor(Palette.Base, background)
    palette.setColor(Palette.AlternateBase, Color(45,45,45))
    palette.setColor(Palette.Highlight, Color(0,185,185))

    palette.setColor(Palette.Text, foreground)
    palette.setColor(Palette.Button, background)
    palette.setColor(Palette.ButtonText, foreground)
    palette.setColor(Palette.Disabled, Palette.ButtonText, Color(128,128,128))
    return palette

class RootPyWindow(PyWindow):
    def __init__(self, window_id, layout="grid"):
        self._app = QtWidgets.QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._app.setPalette(default_palette())
        PyWindow.__init__(self, None, window_id=window_id, layout=layout)
        self.title = "RootPyWindow"

    def start(self):
        """ Run the application, this method will keep running until the root window is closed """
        self.qt_element.show()
        self._app.exec()

class PyWindowDocked(PyWindow):
    def __init__(self, parent, window_id, layout="grid"):
        self._qt = QtWidgets.QDockWidget(parent.qt_element)
        self._content = QtWidgets.QWidget(self.qt_window)
        self.qt_window.setWidget(self._content)
        PyWindow.__init__(self, parent, window_id, layout)
        self.floating = True

    @property
    def qt_element(self): return self._content

    @property
    def floating(self):
        """ Whether the window is currently floating """
        return self.qt_window.isFloating()
    @floating.setter
    def floating(self, floating): self.qt_window.setFloating(bool(floating))