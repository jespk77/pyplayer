from PyQt5 import QtCore, QtGui, QtWidgets

from . import pywindow, pyevents, pyimage, pylayout, pydialog

def valid_check(element):
    if not isinstance(element, PyElement) and not isinstance(element, pywindow.PyWindow): raise ValueError("Parent must be an instance of PyElement or PyWindow")


class PyElement:
    """ The base type of all elements, contains all shared logic """

    def __init__(self, container, element_id):
        valid_check(container)
        self._container = container
        self._element_id = element_id
        if not hasattr(self, "_qt"): self._qt = QtWidgets.QWidget(container)

        self.qt_element.event = self._on_event
        self.qt_element.mousePressEvent = self._on_mouse_press
        self.qt_element.mouseDoubleClickEvent = self._on_mouse_doubleclick
        self.qt_element.wheelEvent = self._on_mouse_wheel
        self.qt_element.focusInEvent = self._on_focus
        self.qt_element.focusOutEvent = self._on_focus_lose

        self._key_cb = {}
        self._double_clicked = False
        if not hasattr(self, "_event_handler"): self._event_handler = pyevents.PyElementEvents(container, self)

    def __del__(self): print("MEMORY", f"PyElement '{self.element_id}' deleted")

    @property
    def qt_element(self): return self._qt
    @property
    def qt_container(self): return self._qt
    @property
    def handle(self): return self.qt_element.winId()

    @property
    def parent(self):
        """ Reference to the parent of this element, it may be a PyWindow or another PyElement instance """
        return self._container

    @property
    def window(self):
        """ Reference to the window that contains this element, it will always be a PyWindow instance """
        return self.parent if isinstance(self.parent, pywindow.PyWindow) else self.parent.window

    @property
    def element_id(self):
        """ The id this element was registered with """
        return self._element_id
    widget_id = element_id

    @property
    def layout(self): raise TypeError(f"Layout elements not supported for '{type(self).__name__}'")
    @property
    def events(self):
        """ Reference to the event handler of this element """
        return self._event_handler
    event_handler = events

    @property
    def accept_input(self): return True

    @property
    def hidden(self): return self.qt_element.isHidden()
    @hidden.setter
    def hidden(self, hide): self.qt_element.setHidden(bool(hide))

    @property
    def tooltip(self): return self.qt_element.toolTip()
    @tooltip.setter
    def tooltip(self, tip): self.qt_element.setToolTip(str(tip))

    @property
    def tooltip_duration(self): return self.qt_element.toolTipDuration()
    @tooltip_duration.setter
    def tooltip_duration(self, duration): self.qt_element.setToolTipDuration(duration)

    @property
    def width(self): return self.qt_element.width()
    @width.setter
    def width(self, value): self.qt_element.setFixedWidth(int(value))
    def with_width(self, value):
        self.width = value
        return self

    @property
    def height(self): return self.qt_element.height()
    @height.setter
    def height(self, value): self.qt_element.setFixedHeight(int(value))
    def with_height(self, value):
        self.height = value
        return self

    def add_element(self, element_id, element=None, element_class=None, **layout_kwargs): self.get_element(element_id)
    def get_element(self, element_id): raise TypeError(f"Element hiarchy not supported for '{__name__}'")
    def find_element(self, element_id): self.get_element(element_id)
    def remove_element(self, element_id): self.get_element(element_id)

    @property
    def children(self): return self.get_element(None)

    def has_focus(self): return self.qt_element.hasFocus()
    def get_focus(self): self.qt_element.setFocus(QtCore.Qt.OtherFocusReason)
    def focus_next(self): self.qt_element.focusNextChild()
    def focus_previous(self): self.qt_element.focusPreviousChild()

    @property
    def min_height(self): return self.qt_element.minimumHeight()
    @min_height.setter
    def min_height(self, height): self.qt_element.setMinimumHeight(int(height))
    @property
    def max_height(self): return self.qt_element.maximumHeight()
    @max_height.setter
    def max_height(self, height):
        height = int(height)
        if height <= 0: height = QtWidgets.QWIDGETSIZE_MAX
        self.qt_element.setMaximumHeight(height)

    @property
    def min_width(self): return self.qt_element.minimumWidth()
    @min_width.setter
    def min_width(self, width): self.qt_element.setMinimumWidth(int(width))
    @property
    def max_width(self): return self.qt_element.maximumWidth()
    @max_width.setter
    def max_width(self, width):
        width = int(width)
        if width <= 0: width = QtWidgets.QWIDGETSIZE_MAX
        self.qt_element.setMaximumWidth(width)

    def get_key(self, key):
        """ Returns keycode associated with given description, returns None if the description was not found """
        return QtCore.Qt.__dict__.get(f"Key_{key}")

    # QWidget.event override
    def _on_event(self, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.KeyPress: return self._on_key_press(event) if self.accept_input else False
        elif event.type() == QtCore.QEvent.WinIdChange: self._on_handle_change(event)
        return type(self.qt_element).event(self.qt_element, event)

    # QWidget.keyPressEvent override
    def _on_key_press(self, event):
        if self.window._on_key_down(event) or self.events.call_keydown_event(event, element=self):
            print("VERBOSE", "Key down event blocked and won't be forwarded to the element")
            return True

        type(self.qt_element).keyPressEvent(self.qt_element, event)
        return event.isAccepted()

    # QWidget.mousePressEvent override
    def _on_mouse_press(self, event):
        if not self._double_clicked: self.events.call_event("left_click" if event.button() == QtCore.Qt.LeftButton else "right_click", x=event.x(), screen_x=event.globalX(), y=event.y(), screen_y=event.globalY())
        else: self._double_clicked = False
        type(self.qt_element).mousePressEvent(self.qt_element, event)

    # QWidget.mouseDoubleClickEvent override
    def _on_mouse_doubleclick(self, event):
        self._double_clicked = True
        self.events.call_event("double_click_left" if event.button() == QtCore.Qt.LeftButton else "double_click_right", x=event.x(), screen_x=event.globalX(), y=event.y(), screen_y=event.globalY())
        type(self.qt_element).mouseDoubleClickEvent(self.qt_element, event)

    # QWidget.wheelEvent override
    def _on_mouse_wheel(self, event):
        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()
        if not pixel_delta.isNull(): delta = pixel_delta.x(), pixel_delta.y()
        elif not angle_delta.isNull(): delta = angle_delta.x(), angle_delta.y()
        else: delta = 0,0

        self.events.call_event("scroll_wheel", x=delta[0], y=delta[1], delta=delta)
        type(self.qt_element).wheelEvent(self.qt_element, event)

    # QWidget.focusInEvent override
    def _on_focus(self, event):
        self.events.call_event("get_focus")
        type(self.qt_element).focusInEvent(self.qt_element, event)

    #QWidget.focusOutEvent override
    def _on_focus_lose(self, event):
        self.events.call_event("lose_focus")
        type(self.qt_element).focusOutEvent(self.qt_element, event)

    def _on_handle_change(self, event):
        self.events.call_event("handle_change", handle=self.handle)

    def on_destroy(self): self.events.call_event("destroy")


class PyFrame(PyElement):
    """
        General element class that can contain child widgets
        No interaction event
    """
    def __init__(self, parent, element_id, layout="grid"):
        if not hasattr(self, "_qt"): self._qt = QtWidgets.QWidget(parent._qt)
        PyElement.__init__(self, parent, element_id)
        self._children = {}
        try: self._layout = pylayout.layouts[layout](self)
        except KeyError: self._layout = None
        if not self._layout: raise ValueError("Must specify a valid layout type")
        self.qt_element.setLayout(self._layout.qt_layout)
        self.create_widgets()

    def create_widgets(self):
        """ Utility method for adding initial elements to this frame, ensures everything is initialized in the correct order """
        pass

    @property
    def children(self): return list(self._children.values())

    @property
    def layout(self): return self._layout

    def add_element(self, element_id=None, element=None, element_class=None, **layout_kwargs):
        if element is None:
            if not element_id: raise ValueError("Must specify an element id")
            elif not element_class: raise ValueError("Must specify an element class or element instance")
            else: element = element_class(self, element_id)
        else: element_id = element.element_id

        self.remove_element(element_id)
        self._layout.insert_element(element, **layout_kwargs)
        self._children[element_id] = element
        return self._children[element_id]
    __setitem__ = add_element

    def get_element(self, element_id) -> PyElement:
        return self._children[element_id]
    __getitem__ = get_element

    def find_element(self, element_id) -> PyElement:
        return self._children.get(element_id)

    def remove_element(self, element_id) -> bool:
        element_id = element_id.lower()
        element = self.find_element(element_id)
        if element:
            element.qt_element.close()
            del self._children[element_id]
            return True
        else: return False

    def on_destroy(self):
        for c in self.children: c.on_destroy()
        PyElement.on_destroy(self)


class PyScrollableFrame(PyFrame):
    """
        Similar to PyFrame but uses scrolling instead of resizing the frame
        No interaction event
    """
    def __init__(self, parent, element_id, layout="grid"):
        self._qt = QtWidgets.QScrollArea(parent.qt_element)
        self._content = QtWidgets.QWidget()
        self.qt_container.setWidgetResizable(True)
        self.qt_container.setWidget(self._content)
        PyFrame.__init__(self, parent, element_id, layout)
        self.show_scrollbar = True

    @property
    def qt_element(self): return self._content
    @property
    def qt_container(self): return self._qt

    @property
    def show_scrollbar(self):
        """ If True the vertical scrollbar will always be visible, otherwise it's only visible if its content is bigger than the visible area """
        return self.qt_container.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarAlwaysOn
    @show_scrollbar.setter
    def show_scrollbar(self, show):
        self.qt_container.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn if show else QtCore.Qt.ScrollBarAsNeeded)


class PyLabelFrame(PyFrame):
    """
       Similar to PyFrame but adds a border with an optional label around its content
       No interaction event
    """
    def __init__(self, parent, element_id, layout="grid"):
        self._qt = QtWidgets.QGroupBox(parent.qt_element)
        PyFrame.__init__(self, parent, element_id, layout)
        self.qt_element.clicked.connect(lambda checked: self.events.call_event("interact", checked=checked))

    @property
    def qt_element(self): return self._qt

    @property
    def label(self): return self.qt_element.title()
    @label.setter
    def label(self, txt): self.qt_element.setTitle(str(txt))

    @property
    def checkbox(self): return self.qt_element.isCheckable()
    @checkbox.setter
    def checkbox(self, check):
        self.qt_element.setCheckable(bool(check))

    @property
    def checked(self): return self.checkbox and self.qt_element.isChecked()
    @checked.setter
    def checked(self, check):
        if self.checkbox: self.qt_element.setChecked(bool(check))
    value = accept_input = checked

    _alignments = {"left": QtCore.Qt.AlignLeft, "center": QtCore.Qt.AlignHCenter, "right": QtCore.Qt.AlignRight}
    def set_label_alignment(self, alignment):
        qt_alignment = self._alignments.get(alignment)
        if qt_alignment is None: raise ValueError(f"Unknown alignment '{alignment}', must be one of {','.join(self._alignments.keys())}")
        self.qt_element.setAlignment(qt_alignment)


class PyTabFrame(PyElement):
    """
       Element with a number of subframes, different frames can be selected using tabs
       Interaction event fires when the current tab is changed, keyword 'index' is the new current page index or -1 if there's no new page
    """
    def __init__(self, parent, element_id):
        self._qt = QtWidgets.QTabWidget(parent.qt_element)
        self._tabs = []
        PyElement.__init__(self, parent, element_id)
        self.qt_element.currentChanged.connect(lambda index: self.events.call_event("interact", index=index))

    @property
    def qt_element(self): return self._qt

    def add_tab(self, name, frame=None, frame_class=PyFrame, **frame_args):
        """
         Add a new tab at the end with given name and existing frame or frame class
         Returns the newly created frame
        """
        if name in self._tabs: raise ValueError(f"A tab with name '{name}' already exists")
        if frame is None:
            if not issubclass(frame_class, PyFrame): raise TypeError("Can only make tabs with subclasses of PyFrame")
            page = frame_class(self, f"tab.{name.lower().replace(' ', '_')}", **frame_args)
        else:
            if not isinstance(frame, PyFrame): raise TypeError("Can only make tabs with subclasses of PyFrame")
            page = frame

        self._tabs.append(page)
        self.qt_element.addTab(page.qt_container, name)
        return page

    def insert_tab(self, index, name, frame=None, frame_class=PyFrame, **frame_args):
        """
         Insert a new at the given position with given name and frame class
         Returns the newly created frame
        """
        if name in self._tabs: raise ValueError(f"A tab with name '{name}' already exists")
        if frame is None:
            if not issubclass(frame_class, PyFrame): raise TypeError("Can only make tabs with subclasses of PyFrame")
            page = frame_class(self, f"tab.{name.lower().replace(' ', '_')}", **frame_args)
        else:
            if not isinstance(frame, PyFrame): raise TypeError("Can only make tabs with subclasses of PyFrame")
            page = frame

        self._tabs.insert(index, page)
        self.qt_element.insertTab(index, page.qt_container, name)
        return page

    def get_tab(self, index):
        """ Returns the frame bound to the tab at given index or None if the index is out of range """
        try: return self._tabs[index]
        except IndexError: return None
    __getitem__ = get_tab

    def get_tab_name(self, index):
        """ Returns the current name of the tab at given index, returns an empty string if index out of range """
        if index < 0: index += len(self._tabs)
        return self.qt_element.tabText(index)

    def set_tab_name(self, index, name):
        """ Update the name of the tab at given index, has no effect if the index is out of range """
        if index < 0: index += len(self._tabs)
        self.qt_element.setTabText(index, name)

    def remove_tab(self, index):
        """ Remove tab at the given index, has no effect if the index is out of range """
        if index < 0: index += len(self._tabs)
        self.qt_element.removeTab(index)
        try: del self._tabs[index]
        except IndexError: pass

    @property
    def current_tab(self): return self.qt_element.indexOf(self.qt_element.currentWidget())

    def on_destroy(self):
        for tab in self._tabs: tab.on_destroy()
        PyElement.on_destroy(self)

    def __len__(self): return self.qt_element.count()
    def __iter__(self): return iter(self._tabs)
    def __contains__(self, item): return item in self._tabs


class PyFrameList(PyElement):
    """
     Supports multiple frames inside itself, only one is visible at a time
     No interaction event
    """
    def __init__(self, parent, element_id):
        self._qt = QtWidgets.QStackedWidget(parent.qt_element)
        self._pages = []
        PyElement.__init__(self, parent, element_id)

    @property
    def qt_element(self): return self._qt

    def add_frame(self, frame=None, frame_class=None, **frame_args):
        """
         Adds a new frame at the end with given frame instance or class
         Returns the newly added frame
        """
        if frame is None:
            if not issubclass(frame_class, PyFrame): raise TypeError("Can only add pages with subclasses of PyFrame")
            frame = frame_class(self, f"frame_{len(self._pages)}", **frame_args)
        elif not isinstance(frame, PyFrame): raise TypeError("Can only add pages with subclasses of PyFrame")

        self._pages.append(frame)
        self.qt_element.addWidget(frame.qt_container)
        return frame

    def insert_frame(self, index, frame=None, frame_class=None, **frame_args):
        """
         Inserts a new frame at given index with the frame instance or class
         Returns the newly added frame
        """
        if frame is None:
            if not issubclass(frame_class, PyFrame): raise TypeError("Can only add pages with subclasses of PyFrame")
            frame = frame_class(self, f"frame_{len(self._pages)}", **frame_args)
        elif not isinstance(frame, PyFrame): raise TypeError("Can only add pages with subclasses of PyFrame")

        self._pages.insert(index, frame)
        self.qt_element.insertWidget(index, frame.qt_container)
        return frame

    def get_frame(self, index):
        """ Gets the frame at the given index or None if out of range """
        try: return self._pages[index]
        except ValueError: return None
    __getitem__ = get_frame

    def remove_frame(self, index):
        """ Removes the frame at given index, has no effect if the index is out of range """
        try:
            frame = self._pages[index]
            self.qt_element.removeWidget(frame.qt_container)
            del self._pages[index]
        except IndexError: pass

    @property
    def current_index(self):
        """ The index of the currently visible frame or -1 if no frames are available """
        return self.qt_element.currentIndex()
    @current_index.setter
    def current_index(self, index): self.qt_element.setCurrentIndex(int(index))

    @property
    def current_frame(self):
        """ The currently visible frame or None if no frames available """
        try: return self._pages[self.current_index]
        except IndexError: return None

    def on_destroy(self):
        for frame in self._pages: frame.on_destroy()
        PyElement.on_destroy(self)

    def __len__(self): return self.qt_element.count()
    def __iter__(self): return iter(self._pages)
    def __contains__(self, item): return item in self._pages


class PyTextLabel(PyElement):
    """
        Element for displaying a line of text and/or an image
        No interaction event
    """
    def __init__(self, parent, element_id):
        self._qt = QtWidgets.QLabel(parent.qt_element)
        PyElement.__init__(self, parent, element_id)
        self._img = None
        self.qt_element.setAlignment(QtCore.Qt.AlignLeft)

    @property
    def qt_element(self): return self._qt

    @property
    def display_text(self): return self.qt_element.text()
    @display_text.setter
    def display_text(self, txt): self.qt_element.setText(str(txt))
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def display_image(self): return self.qt_element.pixmap() is not None or self.qt_element.movie() is not None
    @display_image.setter
    def display_image(self, image): pyimage.PyImage(self, file=image)
    def with_image(self, *args):
        pyimage.PyImage(self, *args)
        return self

    def set_image(self, img):
        self._img = img
        if img.animated:
            self.qt_element.setMovie(img.data)
            img.start()
        else: self.qt_element.setPixmap(img.data)

    @property
    def wrapping(self): return self.qt_element.wordWrap()
    @wrapping.setter
    def wrapping(self, wrap): self.qt_element.setWordWrap(bool(wrap))

    _alignments = {"left": QtCore.Qt.AlignLeft, "centerH": QtCore.Qt.AlignHCenter, "right": QtCore.Qt.AlignRight,
                   "center": QtCore.Qt.AlignCenter, "centerV": QtCore.Qt.AlignVCenter, "justify": QtCore.Qt.AlignJustify}
    def set_alignment(self, align):
        """ Set alignment for this label, must be one of ['left', 'centerH', 'right', 'center', 'centerV', 'justify'] """
        try:
            self.qt_element.setAlignment(self._alignments[align])
            return
        except KeyError: pass
        raise ValueError(f"Unknown alignment '{align}' specified")

    _font_style = {"none": "", "bold": "font-weight:bold", "italic": "font-style:italic", "underline": "text-decoration:underline",
                   "strike": "text-decoration:line-through"}
    def set_font_style(self, style):
        try:
            if isinstance(style, tuple):
                self.qt_element.setStyleSheet(f"QLabel {{ {'; '.join([self._font_style[s] for s in style])} }}")
            else: self.qt_element.setStyleSheet(f"QLabel {{ {self._font_style[style]} }}")
            return
        except KeyError: pass
        raise ValueError(f"Unknown font style '{style}' specified")


class PyTextInput(PyElement):
    """
        Element for entering a single line of data
        Interaction event fires when the enter key is pressed or if this element loses focus, no keywords
        If 'return_only' is set to true, interaction event only fires if the enter key is pressed
    """
    def __init__(self, parent, element_id, return_only=False):
        self._qt = QtWidgets.QLineEdit(parent.qt_element)
        self._event_handler = pyevents.PyElementInputEvent(parent, self)
        PyElement.__init__(self, parent, element_id)
        (self.qt_element.returnPressed if return_only else self.qt_element.editingFinished).connect(lambda : self.events.call_event("interact"))

    @property
    def qt_element(self): return self._qt

    @property
    def accept_input(self): return not self.qt_element.isReadOnly()
    @accept_input.setter
    def accept_input(self, value): self.qt_element.setReadOnly(not value)
    def with_accept_input(self, value):
        self.accept_input = value
        return self

    @property
    def format_str(self): return self.qt_element.inputMask()
    @format_str.setter
    def format_str(self, rex): self.qt_element.setInputMask(str(rex) if rex is not None else "")
    def with_format_str(self, rex):
        self.format_str = rex
        return self

    @property
    def value(self): return self.qt_element.text()
    @value.setter
    def value(self, val): self.qt_element.setText(str(val))
    def with_value(self, val):
        self.value = val
        return self
    display_text = text = value

    @property
    def max_length(self): return self.qt_element.maxLength()
    @max_length.setter
    def max_length(self, ln): self.qt_element.setMaxLength(int(ln))
    def with_max_length(self, ln):
        self.max_length = ln
        return self

    # QLineEdit.keyPressEvent override
    def _on_key_press(self, key):
        key_code = key.key()
        if key_code == QtCore.Qt.Key_Up:
            res = self._event_handler.call_event("history", direction=-1)
            if res == pyevents.EventHandler.block_action: return True
        elif key_code == QtCore.Qt.Key_Down:
            res = self._event_handler.call_event("history", direction=1)
            if res == pyevents.EventHandler.block_action: return True
        return PyElement._on_key_press(self, key)


class PyNumberInput(PyElement):
    """
     Variant of PyTextInput that only accepts numbers
     Precision can be adjusted during creation
     Interaction event fires when the enter key is pressed or if this element loses focus, no keywords
     If 'return_only' is set to true, interaction event only fires if the enter key is pressed
     If 'all_updates' is set to true, interaction event updates every time the value changes
    """
    def __init__(self, parent, element_id, double=False, return_only=False, all_updates=False):
        self._double = double
        self._qt = (QtWidgets.QSpinBox if not double else QtWidgets.QDoubleSpinBox)(parent.qt_element)
        PyElement.__init__(self, parent, element_id)
        if return_only: event = self.qt_element.returnPressed
        elif all_updates: event = self.qt_element.valueChanged
        else: event = self.qt_element.editingFinished
        event.connect(lambda : self.events.call_event("interact"))
        self.min, self.max = -2147483647, 2147483647

    @property
    def qt_element(self): return self._qt

    @property
    def accept_input(self): return not self.qt_element.isReadOnly()
    @accept_input.setter
    def accept_input(self, inpt): self.qt_element.setReadOnly(not inpt)
    def with_accept_input(self, inpt):
        self.accept_input = inpt
        return self

    @property
    def value(self):
        """ The current value, does not include the prefix and/or suffix if set """
        return self.qt_element.value()
    @value.setter
    def value(self, val): self.qt_element.setValue(val)
    def with_value(self, val):
        self.value = val
        return self

    @property
    def min(self):
        """ The minimum allowed value that can be entered """
        return self.qt_element.minimum()
    minimum = min
    @min.setter
    def min(self, value): self.qt_element.setMinimum(int(value) if not self._double else float(value))

    @property
    def max(self):
        """ The maximum allowed value that can be entered """
        return self.qt_element.maximum()
    maximum = max
    @max.setter
    def max(self, value): self.qt_element.setMaximum(int(value) if not self._double else float(value))

    def range(self, min_value, max_value): self.qt_element.setRange(min_value, max_value)

    @property
    def step(self):
        """ How much the value should increase/decrease in one step """
        return self.qt_element.singleStep()
    @step.setter
    def step(self, amount): self.qt_element.setSingleStep(int(amount) if not self._double else float(amount))

    @property
    def value_base(self):
        """ The number base that should be used for display """
        return self.qt_element.displayIntegerBase()
    @value_base.setter
    def value_base(self, base): self.qt_element.setDisplayIntegerBase(int(base))

    @property
    def prefix(self):
        """ Text that should be displayed in front of the actual value """
        return self.qt_element.prefix()
    @prefix.setter
    def prefix(self, txt): self.qt_element.setPrefix(txt)

    @property
    def suffix(self):
        """ Text that should be displayed after the actual value """
        return self.qt_element.suffix()
    @suffix.setter
    def suffix(self, txt): self.qt_element.setSuffix(txt)


class PyCheckbox(PyElement):
    """
        Adds a simple checkable box
        Interaction event fires when the element is toggled, no keywords
    """
    def __init__(self, parent, element_id):
        self._qt = QtWidgets.QCheckBox(parent.qt_element)
        PyElement.__init__(self, parent, element_id)
        self.qt_element.clicked.connect(lambda :self.events.call_event("interact"))

    @property
    def qt_element(self): return self._qt

    @property
    def display_text(self): return self.qt_element.text()
    @display_text.setter
    def display_text(self, txt): self.qt_element.setText(str(txt))
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def checked(self): return self.qt_element.isChecked()
    @checked.setter
    def checked(self, checked): self.qt_element.setChecked(bool(checked))
    value = checked

    @property
    def accept_input(self): return self.qt_element.isEnabled()
    @accept_input.setter
    def accept_input(self, check): self.qt_element.setEnabled(bool(check))


class PyButton(PyElement):
    """
        Clickable button element, can be customized with text and/or an image
        Interaction event fires when the button is pressed, no keywords
    """
    def __init__(self, parent, element_id):
        self._qt = QtWidgets.QPushButton(parent.qt_element)
        PyElement.__init__(self, parent, element_id)
        self.qt_element.clicked.connect(lambda : self.events.call_event("interact"))
        self._click_cb = self._img = None

    @property
    def qt_element(self): return self._qt

    @property
    def accept_input(self): return self.qt_element.isEnabled()
    @accept_input.setter
    def accept_input(self, inpt): self.qt_element.setEnabled(bool(inpt))
    def with_accept_input(self, inpt):
        self.accept_input = inpt
        return self

    @property
    def checkable(self): return self.qt_element.isCheckable()
    @checkable.setter
    def checkable(self, checkable): self.qt_element.setCheckable(bool(checkable))

    @property
    def checked(self): return self.qt_element.isChecked()
    @checked.setter
    def checked(self, checked): self.qt_element.setChecked(checked)

    @property
    def display_text(self): return self.qt_element.text()
    @display_text.setter
    def display_text(self, txt): self.qt_element.setText(str(txt))
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def display_image(self): return self.qt_element.icon() is not None
    @display_image.setter
    def display_image(self, image): pyimage.PyImage(self, file=image)
    def with_image(self, *args):
        pyimage.PyImage(self, *args)
        return self

    def set_image(self, img):
        self._img = QtGui.QIcon(img.data)
        self.qt_element.setIcon(self._img)


def random_url():
    import random
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyz1234567890") for _ in range(20))

class PyTextField(PyElement):
    """
        Element for displaying and/or entering multiple lines of text
        No interaction event
    """
    def __init__(self, parent, element_id):
        self._qt = QtWidgets.QTextEdit(parent.qt_element)
        self._event_handler = pyevents.PyElementInputEvent(parent, self)
        PyElement.__init__(self, parent, element_id)
        self.qt_element.keyPressEvent = self._on_key_press
        self.undo = False
        self.tabChangesFocus = True

    @property
    def qt_element(self): return self._qt

    @property
    def accept_input(self): return not self.qt_element.isReadOnly()
    @accept_input.setter
    def accept_input(self, value): self.qt_element.setReadOnly(not value)
    def with_accept_input(self, value):
        self.accept_input = value
        return self

    @property
    def undo(self): return self.qt_element.isUndoRedoEnabled()
    @undo.setter
    def undo(self, do): self.qt_element.setUndoRedoEnabled(bool(do))

    @property
    def display_text(self): return self.qt_element.toPlainText()
    @display_text.setter
    def display_text(self, txt): self.qt_element.setPlainText(str(txt))
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = value = display_text

    start = 0
    @property
    def end(self): return len(self.text)

    @property
    def cursor(self): return self.qt_element.textCursor().position()
    @cursor.setter
    def cursor(self, value):
        cursor = self.qt_element.textCursor()
        cursor.setPosition(value)
        self.qt_element.setTextCursor(cursor)

    @property
    def style_sheet(self): return self.qt_element.document().defaultStyleSheet()
    @style_sheet.setter
    def style_sheet(self, value): self.qt_element.document().setDefaultStyleSheet(str(value))

    @property
    def font_size(self): return self.qt_element.font().pointSize()
    @font_size.setter
    def font_size(self, size):
        font = self.qt_element.font()
        font.setPointSize(size)
        self.qt_element.setFont(font)

    @property
    def tabChangesFocus(self): return self.qt_element.tabChangesFocus()
    @tabChangesFocus.setter
    def tabChangesFocus(self, val): self.qt_element.setTabChangesFocus(bool(val))

    @staticmethod
    def _insert(cursor, text, tags, html):
        span = tags is not None
        if span: cursor.insertHtml(f"<span class='{' '.join(tags)}'>")

        if html: cursor.insertHtml(text.replace("\n", "<br/>"))
        else: cursor.insertText(text)
        if span: cursor.insertHtml("</span>")

    def append(self, text, tags=None, html=False, move_cursor=False):
        """
         Shorthand for inserting text at the end of this field, supports same set of keywords
         Equivalent to chat.insert(chat.end, ...)
        """
        prev_pos = self.cursor if not move_cursor else None
        cursor: QtGui.QTextCursor = self.qt_element.textCursor()
        cursor.movePosition(cursor.End)
        PyTextField._insert(cursor, str(text), tags, html)
        if prev_pos is not None: cursor.setPosition(prev_pos)
        self.qt_element.setTextCursor(cursor)

    def get(self, index1=None, index2=None, line=None, selection=None):
        """
            Utility method for getting specific text from the textfield
            If 'index1' and 'index2' are specified, returns the characters between both positions. If only 'index1' specified returns the character at that index.
            If 'line' is specified, returns the text at given line number. If 'line' is 0 or negative, returns the text on the line of the cursor
            If 'selection' is True, returns the currently selected text
        """
        if index1 is not None or index2 is not None:
            if index1 is None: raise ValueError("Missing starting index")
            if index2 is None: return self.qt_element.document().toPlainText()[index1]
            return self.qt_element.document().toPlainText()[index1:index2]

        if line is not None:
            if line > 0: return self.qt_element.document().findBlockByLineNumber(line).text()
            else: return self.qt_element.textCursor().block().text()

        if selection is True: return self.qt_element.textCursor().selectedText()

    def insert(self, index, text, tags=None, html=False, move_cursor=False):
        """
         Insert given text into the given position (ignores 'accept_input' property)
         If tags is defined, the inserted text will have attached style classes that can be configured in the style sheet
         If html is set to true, inserted text will be treated as html, otherwise it is treated as plain text
         If move_cursor is set to false, inserting text will not affect the position of the cursor
        """
        prev_pos = self.cursor if not move_cursor else None
        cursor: QtGui.QTextCursor = self.qt_element.textCursor()
        cursor.setPosition(index)

        PyTextField._insert(cursor, str(text), tags, html)
        if prev_pos is not None: cursor.setPosition(prev_pos)
        self.qt_element.setTextCursor(cursor)

    def insert_image(self, index, img_file):
        prev_pos = self.cursor
        cursor: QtGui.QTextCursor = self.qt_element.textCursor()
        cursor.setPosition(index)

        img = random_url()
        self.qt_element.document().addResource(QtGui.QTextDocument.ImageResource, img, QtGui.QPixmap(img_file))
        cursor.insertHtml(f"<img src='{img}'/>")
        cursor.setPosition(prev_pos)
        self.qt_element.setTextCursor(cursor)

    def delete(self, index1, index2=None):
        """ Delete text between the given positions (ignores 'accept_input' property) """
        cursor: QtGui.QTextCursor = self.qt_element.textCursor()
        cursor.setPosition(index1)

        diff = index2 - index1 if index2 else 1
        for _ in range(diff): cursor.deleteChar()
        self.qt_element.setTextCursor(cursor)

    def position(self, index):
        """ Get the exact coordinates in this text field, or emtpy string if nothing found """
        if index == "start": return 0
        if index == "end": return self.end
        if index == "insert": return self.cursor

    def show(self, position):
        """ Make sure that the given line is visible on screen """
        cursor = self.qt_element.textCursor()
        cursor.setPosition(position)
        self.qt_element.setTextCursor(cursor)

    def clear_selection(self):
        """ Remove selection in this text field (has no effect if nothing was selected) """
        cursor = self.qt_element.textCursor()
        cursor.clearSelection()
        self.qt_element.setTextCursor(cursor)

    def _on_key_press(self, event):
        key_code = event.key()
        if key_code == QtCore.Qt.Key_Up:
            res = self._event_handler.call_event("history", direction=-1)
            if res == self._event_handler.block_action: return
        elif key_code == QtCore.Qt.Key_Down:
            res = self._event_handler.call_event("history", direction=1)
            if res == self._event_handler.block_action: return
        return PyElement._on_key_press(self, event)


class PyTable(PyElement):
    """
        Element that displays content in table form
        Interaction event fires when the value in a cell gets updated
            - Keywords: row: int, column: int, new_value: str
    """
    def __init__(self, parent, element_id, rows=1, columns=1):
        self._qt = QtWidgets.QTableWidget(rows, columns, parent.qt_element)
        PyElement.__init__(self, parent, element_id)
        self._dynamic_column, self._dynamic_row = False, False
        self._horizontal_header, self._vertical_header = False, False
        self.qt_element.cellChanged.connect(self._on_cell_changed)
        self.qt_element.setCornerButtonEnabled(True)
        self._read_only = False

    @property
    def qt_element(self): return self._qt

    def _update_header_visibility(self):
        self.qt_element.horizontalHeader().setVisible(self.columns > 1 or self._horizontal_header)
        self.qt_element.verticalHeader().setVisible(self.rows > 1 or self._vertical_header)
    def _table_update(self):
        if self._dynamic_column and self.columns > 0:
            col = self.columns - 1
            for row in range(self.rows):
                item = self.qt_element.item(row, col)
                if item is not None and item.text():
                    self.insert_column()
                    break

            empty = True
            while empty:
                col = self.columns - 2
                if col < 1: break
                for row in range(self.rows):
                    item = self.qt_element.item(row, col)
                    if item is not None and item.text():
                        empty = False
                        break
                if empty: self.remove_column()

        if self._dynamic_row and self.rows > 0:
            row = self.rows - 1
            for col in range(self.columns):
                item = self.qt_element.item(row, col)
                if item is not None and item.text():
                    self.insert_row()
                    break

            empty = True
            while empty:
                row = self.rows - 2
                if row < 1: break
                for col in range(self.columns):
                    item = self.qt_element.item(row, col)
                    if item is not None and item.text():
                        empty = False
                        break
                if empty: self.remove_row()
        self._update_header_visibility()

    @property
    def accept_input(self): return self.qt_element.isEnabled()
    @accept_input.setter
    def accept_input(self, inpt): self.qt_element.setEnabled(inpt)

    @property
    def read_only(self): return self._read_only
    @read_only.setter
    def read_only(self, read_only):
        self._read_only = read_only
        for row in range(self.rows):
            for column in range(self.columns):
                item = self._qt.item(row, column)
                if item is not None:
                    edit_flag = QtCore.Qt.ItemIsEditable
                    item.setFlags(item.flags() | edit_flag if read_only else item.flags() & ~edit_flag)
                    self._qt.setItem(row, column, item)

    @property
    def columns(self):
        """ The number of columns in this table """
        return self.qt_element.columnCount()
    @columns.setter
    def columns(self, count):
        """ Set a fixed number of columns for this table (disables dynamic column count) """
        count = int(count)
        self.dynamic_columns = False
        self.qt_element.setColumnCount(count)
        self._update_header_visibility()

    @property
    def column_width(self): return self.qt_element.horizontalHeader().sectionSize(0)
    @column_width.setter
    def column_width(self, width):
        width = int(width)
        if width <= 0: raise ValueError("column width must be greater than 0")

        header = self.qt_element.horizontalHeader()
        for i in range(self.columns): header.resizeSection(i, width)
        header.setDefaultSectionSize(width)

    @property
    def column_header(self):
        """ Whether the column header is currently visible """
        return self.qt_element.horizontalHeader().isVisible()
    @column_header.setter
    def column_header(self, visible):
        self._horizontal_header = bool(visible)
        self._update_header_visibility()

    @property
    def column_labels(self): return
    @column_labels.setter
    def column_labels(self, labels): self._qt.setHorizontalHeaderLabels(labels)

    @property
    def dynamic_columns(self):
        """ Whether the column count should automatically grow with the content """
        return self._dynamic_column
    @dynamic_columns.setter
    def dynamic_columns(self, dynamic):
        self._dynamic_column = bool(dynamic)
        self._table_update()

    def insert_column(self, index=None):
        """
            Insert new column at specified index
            Inserts the column at the end if nothing specified
        """
        if index is None: index = self.columns
        elif index < 0: index += self.columns
        self.qt_element.insertColumn(index)

    def remove_column(self, index=None):
        """
            Removes column at the specified index
            Removes the column at the end if nothing specified
        """
        if index is None: index = self.columns - 1
        elif index < 0: index += self.columns
        self.qt_element.removeColumn(index)

    @property
    def rows(self):
        """ The number of rows in this table """
        return self.qt_element.rowCount()
    @rows.setter
    def rows(self, count):
        """ Set a fixed number of rows for this table (disables dynamic row count) """
        self.dynamic_rows = False
        self.qt_element.setRowCount(count)
        self._update_header_visibility()

    @property
    def row_header(self):
        """ Whether the row header is currently visible """
        return self.qt_element.verticalHeader().isVisible()
    @row_header.setter
    def row_header(self, visible):
        self._vertical_header = bool(visible)
        self._update_header_visibility()

    @property
    def row_labels(self): return
    @row_labels.setter
    def row_labels(self, labels): self._qt.setVerticalHeaderLabels(labels)

    @property
    def row_height(self): return self.qt_element.verticalHeader().sectionSize(0)
    @row_height.setter
    def row_height(self, height):
        height = int(height)
        if height <= 0: raise ValueError("Height must be greater than 0")

        header = self.qt_element.verticalHeader()
        for i in range(self.rows): header.resizeSection(i, height)
        header.setDefaultSectionSize(height)

    @property
    def dynamic_rows(self):
        """ Whether the row count should automatically grow with the content """
        return self._dynamic_row
    @dynamic_rows.setter
    def dynamic_rows(self, dynamic):
        self._dynamic_row = bool(dynamic)
        self._table_update()

    def insert_row(self, index=None):
        """
            Insert new row at specified index
            Inserts the row at the end if nothing specified
        """
        if index is None: index = self.rows
        elif index < 0: index += self.rows
        self.qt_element.insertRow(index)

    def remove_row(self, index=None):
        """
            Removes row at the specified index
            Removes the row at the end if nothing specified
        """
        if index is None: index = self.rows - 1
        elif index < 0: index += self.rows
        self.qt_element.removeRow(index)

    def resize_fit(self, row=False, column=False):
        """
            Resize cells to make the current content fit
            If 'row' is True, all rows are resized based on their contents
            If 'column' is True, all columns are resized based on their contents
        """
        if row: self._qt.resizeRowsToContents()
        if column: self._qt.resizeColumnsToContents()

    def resize_row(self, row):
        """ Resizes a specific row to fit its content """
        self._qt.resizeRowToContents(row)

    def resize_column(self, column):
        """ Resizes a specific column to fit its content """
        self._qt.resizeColumnToContents(column)

    def get(self, row=None, column=None):
        """
            Get value(s) from the table
            If only 'row' is specified, returns values in all columns from that row
            If only 'column' is specified, returns values in all rows from that columns
            If both 'row' and 'column' specified, returns value from that position
            Supports negative indices (with the same behavior as builtin types)
            Returns None when a value out of range specified
        """
        if row is not None:
            if row < 0: row += self.rows

            if column is not None:
                if column < 0: column += self.columns
                item = self.qt_element.item(row, column)
                return item.text() if item is not None else ""
            items = [self.qt_element.item(row, i) for i in range(self.columns)] if 0 <= row < self.rows else None
            return [i.text() if i is not None else "" for i in items] if items is not None else None

        if column is not None:
            if column < 0: column += self.columns
            items = [self.qt_element.item(i, column) for i in range(self.rows)] if 0 <= column < self.columns else None
            return [i.text() if i is not None else "" for i in items] if items is not None else None

        return ValueError("Must specify at least one of 'row' or 'column'")

    def set(self, row, column, value):
        """
            Update the cell at the specified position in the table
            Supports negative indices (with the same behavior as builtin types)
            It is an error if the position is out of range
        """
        if row < 0: row += self.rows
        if column < 0: column += self.columns

        if 0 <= row < self.rows and 0 <= column < self.columns:
            item = self.qt_element.item(row, column)
            if item is None:
                item = QtWidgets.QTableWidgetItem(value)
                self.qt_element.setItem(row, column, item)
            else: item.setText(value)
        else: raise IndexError(f"table index out of range ({row},{column})")

    def _on_cell_changed(self, row, column):
        self._table_update()
        self.event_handler.call_event("interact", row=row, column=column, new_value=self.get(row, column))


class PyProgessbar(PyElement):
    """
        Display the progress of a certain action on screen
        Interaction event called when the mouse is clicked over the widget
        Available keywords:
            * x: the x coordinate of the element the mouse clicked on
            * y: the y coordinate of the element the mouse clicked on
            * position: the progress value it was clicked on, relative to the element's width
    """
    def __init__(self, parent, element_id):
        self._qt = QtWidgets.QProgressBar(parent.qt_element)
        PyElement.__init__(self, parent, element_id)
        self.qt_element.setTextVisible(False)

    @property
    def qt_element(self): return self._qt

    @property
    def progress(self): return self.qt_element.value()
    @progress.setter
    def progress(self, value): self.qt_element.setValue(int(value))
    value = progress

    @property
    def horizontal(self): return self.qt_element.orientation() == QtCore.Qt.Horizontal
    @horizontal.setter
    def horizontal(self, value): self.qt_element.setOrientation(QtCore.Qt.Horizontal if value else QtCore.Qt.Vertical)

    @property
    def minimum(self): return self.qt_element.minimum()
    @minimum.setter
    def minimum(self, value): self.qt_element.setMinimum(int(value))
    def with_minimum(self, value):
        self.minimum = value
        return self

    @property
    def maximum(self): return self.qt_element.maximum()
    @maximum.setter
    def maximum(self, value): self.qt_element.setMaximum(int(value))
    def with_maximum(self, value):
        self.maximum = value
        return self

    @property
    def color(self): return self.qt_element.palette().color(QtGui.QPalette.Active, QtGui.QPalette.Highlight).name()
    @color.setter
    def color(self, color):
        pal, col = self.qt_element.palette(), QtGui.QColor(color)
        pal.setColor(QtGui.QPalette.Active, QtGui.QPalette.Highlight, col)
        pal.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight, col)
        self.qt_element.setPalette(pal)

    def _on_mouse_press(self, event):
        x, y = event.x(), event.y()
        self.events.call_event("interact", x=x, y=y, position=x/self.qt_element.width())
        PyElement._on_mouse_press(self, event)


class PyItemlist(PyElement):
    """
     Show a list of items the user can select
     Interaction event fires when an item is left clicked, updating the selection
        Keywords: current: int -> the newly selected index, previous: int -> the previously selected index
    """
    def __init__(self, parent, element_id):
        self._qt = QtWidgets.QListView(parent.qt_element)
        PyElement.__init__(self, parent, element_id)
        self.qt_element.setUniformItemSizes(True)
        self.qt_element.setSelectionMode(QtWidgets.QListView.SingleSelection)
        self.qt_element.setViewMode(QtWidgets.QListView.ListMode)
        self.qt_element.setFlow(QtWidgets.QListView.TopToBottom)
        self.qt_element.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.qt_element.setEditTriggers(QtWidgets.QListView.NoEditTriggers)
        self.qt_element.currentChanged = self._on_selection_change
        self.qt_element.setStyleSheet(f"""
            QListView {{ 
             selection-background-color: #101010; selection-color: {self.qt_element.palette().highlight().color().name()}
            }} """)
        self._items = QtCore.QStringListModel()

    @property
    def qt_element(self) -> QtWidgets.QListView: return self._qt

    @property
    def itemlist(self): return self._items.stringList()
    @itemlist.setter
    def itemlist(self, items):
        self._items.setStringList(items)
        self.qt_element.setModel(self._items)
    value = itemlist

    _selection_modes = {
        "none": QtWidgets.QListView.NoSelection,
        "single": QtWidgets.QListView.SingleSelection,
        "multi": QtWidgets.QListView.MultiSelection
    }
    @property
    def selection_mode(self):
        for mode_name, mode in self._selection_modes.items():
            if mode == self.qt_element.selectionMode(): return mode_name
    @selection_mode.setter
    def selection_mode(self, mode):
        mode = mode.lower()
        if mode not in self._selection_modes: raise ValueError(f"Unknown selection mode '{mode}', must be one of [{','.join(self._selection_modes.keys())}]")
        self.qt_element.setSelectionMode(self._selection_modes[mode])

    _edit_modes = {
        "none": QtWidgets.QListView.NoEditTriggers,
        "current_change": QtWidgets.QListView.CurrentChanged,
        "double_click": QtWidgets.QListView.DoubleClicked,
        "selected_click": QtWidgets.QListView.SelectedClicked,
        "edit_keypress": QtWidgets.QListView.EditKeyPressed,
        "keypress": QtWidgets.QListView.AnyKeyPressed,
        "all": QtWidgets.QListView.AllEditTriggers
    }
    @property
    def edit_mode(self):
        for mode_name, mode in self._selection_modes.items():
            if mode == self.qt_element.editTriggers(): return mode_name
    @edit_mode.setter
    def edit_mode(self, mode):
        mode = mode.lower()
        if mode not in self._edit_modes: raise ValueError(f"Unknown edit mode '{mode}', must be one of [{','.join(self._edit_modes.keys())}]")
        self.qt_element.setEditTriggers(self._edit_modes[mode])

    @property
    def selected_index(self):
        """ Returns the index of the currently selected item, or -1 if nothing was selected """
        try: return self.qt_element.selectedIndexes()[0].row()
        except IndexError: return -1
    @selected_index.setter
    def selected_index(self, index):
        """ Set the current selection to given index, clears the selection if the given index is less than 0 """
        self.clear_selection()
        if index >= 0: self.qt_element.setSelection(self.qt_element.visualRect(self._items.index(index)), QtCore.QItemSelectionModel.Select)

    def clear_selection(self):
        """ Removes any selected item """
        self.qt_element.clearSelection()

    def select_all(self):
        self.qt_element.selectAll()

    def set_selection(self, index=None, item=None):
        """ Set the selection to given index or given item, returns the selected item """
        if index is not None:
            self.selected_index = index
            return self.selected_item
        if item is not None:
            self.selected_item = item
            return self.selected_item
        raise ValueError("Must specify either an index or an item")

    @property
    def selected_item(self):
        """ Returns the string of the currently selected item, or None if nothing was selected """
        index = self.selected_index
        try: return self.itemlist[index]
        except IndexError: return None
    @selected_item.setter
    def selected_item(self, item):
        """ Set the selection to given string, clears the selection if the given string wasn't found """
        items = self.itemlist
        try: self.selected_index = items.index(item)
        except ValueError: self.selected_index = -1

    @property
    def clicked_index(self):
        """ Returns the index of the item that was last clicked on """
        return self.qt_element.currentIndex().row()
    @clicked_index.setter
    def clicked_index(self, index): self.qt_element.setCurrentIndex(index)

    def move_to(self, index):
        """ Make sure given index is visible """
        self.qt_element.scrollTo(self._items.index(index))

    # QListView.currentChanged override
    def _on_selection_change(self, current, previous):
        self.events.call_event("interact", current=current.row(), previous=previous.row())
        return type(self.qt_element).currentChanged(self.qt_element, current, previous)

class PySeparator(PyElement):
    def __init__(self, parent, element_id, horizontal=True):
        self._qt = QtWidgets.QFrame(parent.qt_element)
        PyElement.__init__(self, parent, element_id)
        self.qt_element.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.horizontal, self.thickness = horizontal, 2

    @property
    def qt_element(self): return self._qt

    @property
    def horizontal(self): return self.qt_element.frameShape() == QtWidgets.QFrame.HLine
    @horizontal.setter
    def horizontal(self, horizontal): self.qt_element.setFrameShape(QtWidgets.QFrame.HLine if horizontal else QtWidgets.QFrame.VLine)

    @property
    def vertical(self): return not self.horizontal
    @vertical.setter
    def vertical(self, vertical): self.horizontal = not vertical

    @property
    def thickness(self): return self.max_height if self.horizontal else self.max_width
    @thickness.setter
    def thickness(self, thickness):
        if self.horizontal: self.max_height = thickness
        else: self.max_width = thickness

    @property
    def color(self): return self.qt_element.palette().color(QtGui.QPalette.Active, QtGui.QPalette.Highlight).name()
    @color.setter
    def color(self, color): self.qt_element.setStyleSheet(f"QFrame{{ border: {self.thickness}px inset {color} }} """)


class PyColorInput(PyFrame):
    """
     Custom element for entering a color value, can either be updated with text or a dialog
     Interaction event fires when the color is updated either through text or the dialog
     Keyword: 'color': str, the newly selected color
    """
    def __init__(self, parent, element_id, color=None):
        PyFrame.__init__(self, parent, element_id)
        self.layout.row(0, weight=1).column(0, weight=1).margins(0)
        self._color = pydialog.PyColorDialog(self.window)
        self._color.events.EventSubmit(self._on_select_color)
        if color is not None: self.color = color

    @property
    def qt_element(self): return self._qt

    def create_widgets(self):
        txt = self.add_element("txt", element_class=PyTextInput)
        txt.events.EventInteract(lambda : self._on_select_color(txt.value))

        btn = self.add_element("select", element_class=PyButton, column=1)
        btn.text, btn.max_width = "...", 25
        btn.events.EventInteract(lambda : self._color.open())

    @property
    def accept_input(self): return self["txt"].accept_input
    @accept_input.setter
    def accept_input(self, inpt):
        self["txt"].accept_input = inpt
        self["select"].hidden = not inpt

    @property
    def dialog(self): return self._color

    @property
    def color(self): return self["txt"].text
    @color.setter
    def color(self, color):
        self["txt"].text = color
        self.dialog.color = color
    value = color

    def _on_select_color(self, value):
        self.color = value
        self.events.call_event("interact", color=value)


class PyPathInput(PyFrame):
    """
     Custom element for entering a path or directory, can either be updated with text or a dialog
     Interaction event fires when the path is updated either through text or with the dialog
     Keywords: 'path': str, the newly selected path
    """
    def __init__(self, parent, element_id, path=None):
        PyFrame.__init__(self, parent, element_id)
        self.layout.row(0, weight=1).column(0, weight=1).margins(0)
        self._path = pydialog.PyFileDialog(self.window)
        self._path.events.EventSubmit(self._on_path_select)
        if path is not None: self.path = path

    @property
    def qt_element(self): return self._qt

    def create_widgets(self):
        txt = self.add_element("txt", element_class=PyTextInput)
        txt.events.EventInteract(lambda : self._on_path_select(txt.value))

        btn = self.add_element("select", element_class=PyButton, column=1)
        btn.text, btn.max_width = "...", 25
        btn.events.EventInteract(lambda : self._path.open())

    @property
    def accept_input(self): return self["txt"].accept_input
    @accept_input.setter
    def accept_input(self, inpt):
        self["txt"].accept_input = inpt
        self["select"].hidden = not inpt

    @property
    def dialog(self): return self._path

    @property
    def path(self): return self["txt"].text
    @path.setter
    def path(self, path):
        self["txt"].text = path
        self.dialog.value = path
    value = path

    def _on_path_select(self, value):
        self.path = value
        self.events.call_event("interact", path=value)


try:
    from PyQt5 import QtWebEngineWidgets
    class PyWebpage(PyElement):
        insert_html_script = "document.body.innerHTML += {html}"
        insert_css_script = "const s = document.createElement('style'); s.textContent = {css}; document.head.style = s"

        def __init__(self, parent, element_id):
            self._qt = QtWebEngineWidgets.QWebEngineView()
            PyElement.__init__(self, parent, element_id)
            self.html_page = "<html><head></head><body>body</body></html>"

        @property
        def qt_element(self): return self._qt

        @property
        def html_page(self): return ""
        @html_page.setter
        def html_page(self, html): self.qt_element.setHtml(html)

        @property
        def style_sheet(self): return ""
        @style_sheet.setter
        def style_sheet(self, css): self.qt_element.page().runJavaScript(self.insert_css_script.format(css=css))

        def append(self, html):
            self.qt_element.page().runJavaScript(self.insert_html_script.format(html=html.replace("\n", "<br/>")))

except ImportError:
    print("WARNING", "Missing dependency: 'PyQtWebEngine', PyWebpage element will not be available")