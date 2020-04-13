from PyQt5 import QtCore, QtGui, QtWidgets

from . import pywindow, pyevents, pyimage, pylayout

def valid_check(element):
    if not isinstance(element, PyElement) and not isinstance(element, pywindow.PyWindow): raise ValueError("Parent must be an instance of PyElement or PyWindow")

class PyElement:
    def __init__(self, container, element_id):
        valid_check(container)
        self._container: pywindow.PyWindow = container
        self._element_id = element_id
        if not hasattr(self, "_qt"): self._qt = None
        self._cfg = container.configuration.get_or_create(f"children::{element_id}", {})
        if not hasattr(self, "_event_handler"): self._event_handler = pyevents.PyElementEvents()

    @property
    def qt_element(self): return self._qt

    @property
    def element_id(self): return self._element_id
    widget_id = element_id

    @property
    def configuration(self): return self._cfg
    cfg = configuration

    @property
    def layout(self): raise TypeError(f"Layout elements not supported for '{__name__}'")
    @property
    def events(self): return self._event_handler

    @property
    def accept_input(self): return True

    @property
    def width(self): return self.qt_element.width()
    @width.setter
    def width(self, value): self.qt_element.setFixedWidth(value)
    def with_width(self, value):
        self.width = value
        return self

    @property
    def height(self): return self.qt_element.height()
    @height.setter
    def height(self, value): self.qt_element.setFixedHeight(value)
    def with_height(self, value):
        self.height = value
        return self

    def add_element(self, element_id, element=None, element_class=None, **layout_kwargs): self.get_element(element_id)
    def get_element(self, element_id): raise TypeError(f"Element hiarchy not supported for '{__name__}'")
    def find_element(self, element_id): self.get_element(element_id)
    def remove_element(self, element_id): self.get_element(element_id)

class PyFrame(PyElement):
    """
     General element class that can contain child widgets
     No interaction event
    """
    def __init__(self, parent, element_id, layout="grid"):
        PyElement.__init__(self, parent, element_id)
        if not hasattr(self, "_qt") or self._qt is None: self._qt = QtWidgets.QWidget(parent._qt)
        self._children = {}
        try: self._layout = pylayout.layouts[layout](self.qt_element)
        except KeyError: self._layout = None
        if not self._layout: raise ValueError("Must specify a valid layout type")
        self.qt_element.setLayout(self._layout.qt_layout)

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

class PyScrollableFrame(PyFrame):
    def __init__(self, parent, element_id, layout="grid"):
        self._qt = QtWidgets.QScrollArea(parent.qt_element)
        self._content = QtWidgets.QWidget()
        PyFrame.__init__(self, parent, element_id, layout)
        self._qt.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self._qt.setWidgetResizable(True)
        self._qt.setWidget(self._content)

    @property
    def qt_element(self): return self._content

class PyLabelFrame(PyFrame):
    def __init__(self, parent, element_id, layout="grid"):
        self._qt = QtWidgets.QGroupBox(parent.qt_element)
        PyFrame.__init__(self, parent, element_id, layout)
        pass

    @property
    def label(self): return self._qt.title()
    @label.setter
    def label(self, txt): self._qt.setTitle(txt)


class PyTextLabel(PyElement):
    """
     Element for displaying a line of text and/or an image
     No interaction event
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QLabel(parent.qt_element)
        self._img = None
        self.qt_element.setAlignment(QtCore.Qt.AlignLeft)

    @property
    def display_text(self): return self.qt_element.text()
    @display_text.setter
    def display_text(self, txt): self.qt_element.setText(txt)
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
    def wrapping(self, wrap): self.qt_element.setWordWrap(wrap)

    _alignments = {"left": QtCore.Qt.AlignLeft, "center": QtCore.Qt.AlignHCenter, "right": QtCore.Qt.AlignRight}
    def set_alignment(self, align):
        """ Set alignment for this label, must be either 'left', 'center' or 'right' """
        self.qt_element.setAlignment(self._alignments[align])


class PyTextInput(PyElement):
    """
     Element for entering a single line of data
     Interaction event fires when the enter is pressed while this element has focus, no keywords
    """
    def __init__(self, parent, element_id):
        self._event_handler = pyevents.PyElementInputEvent()
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QLineEdit(parent.qt_element)
        self.qt_element.keyPressEvent = self._on_key_press
        self.qt_element.returnPressed.connect(lambda : self.events.call_event("interact"))

    @property
    def accept_input(self): return self.qt_element.isReadOnly()
    @accept_input.setter
    def accept_input(self, value): self.qt_element.setReadOnly(not value)
    def with_accept_input(self, value):
        self.accept_input = not value
        return self

    @property
    def format_str(self): return self.qt_element.inputMask()
    @format_str.setter
    def format_str(self, rex): self.qt_element.setInputMask(rex if rex is not None else "")
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
    def max_length(self, ln): self.qt_element.setMaxLength(ln)
    def with_max_length(self, ln):
        self.max_length = ln
        return self

    # QLineEdit.keyPressEvent override
    def _on_key_press(self, key):
        key_code = key.key()
        if key_code == QtCore.Qt.Key_Up:
            res = self._event_handler.call_event("history", direction=-1)
            if res == pyevents.EventHandler.block_action: return
        elif key_code == QtCore.Qt.Key_Down:
            res = self._event_handler.call_event("history", direction=1)
            if res == pyevents.EventHandler.block_action: return
        QtWidgets.QLineEdit.keyPressEvent(self.qt_element, key)


class PyCheckbox(PyElement):
    """
     Adds a simple checkable box
     Interaction event fires when the element is toggled, no keywords
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QCheckBox(parent.qt_element)
        self.qt_element.clicked.connect(lambda :self.events.call_event("interact"))

    @property
    def display_text(self): return self.qt_element.text()
    @display_text.setter
    def display_text(self, txt): self.qt_element.setText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def checked(self): return self.qt_element.isChecked()
    @checked.setter
    def checked(self, checked): self.qt_element.setChecked(checked)

    @property
    def accept_input(self): return self.qt_element.enabled()
    @accept_input.setter
    def accept_input(self, check): self.qt_element.setEnabled(check)


class PyButton(PyElement):
    """
     Clickable button element, can be customized with text and/or an image
     Interaction event fires when the button is pressed, no keywords
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QPushButton(parent.qt_element)
        self.qt_element.clicked.connect(lambda : self.events.call_event("interact"))
        self._click_cb = self._img = None

    @property
    def accept_input(self): return self.qt_element.isEnabled()
    @accept_input.setter
    def accept_input(self, inpt): self.qt_element.setEnabled(inpt)

    @property
    def display_text(self): return self.qt_element.text()
    @display_text.setter
    def display_text(self, txt): self.qt_element.setText(txt)
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


class PyTextField(PyElement):
    """
     Element for displaying and/or entering multiple lines of text
     No interaction event
    """
    def __init__(self, parent, element_id):
        self._event_handler = pyevents.PyElementInputEvent()
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QTextEdit(parent.qt_element)
        self.qt_element.keyPressEvent = self._on_key_press
        self.undo = False

    @property
    def accept_input(self): return self.qt_element.isReadOnly()
    @accept_input.setter
    def accept_input(self, value): self.qt_element.setReadOnly(not value)
    def with_accept_input(self, value):
        self.accept_input = value
        return self

    @property
    def undo(self): return self.qt_element.isUndoRedoEnabled()
    @undo.setter
    def undo(self, do): self.qt_element.setUndoRedoEnabled(do)

    @property
    def display_text(self): return self.qt_element.toPlainText()
    @display_text.setter
    def display_text(self, txt): self.qt_element.setPlainText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def cursor(self): return self.qt_element.textCursor().position()
    @cursor.setter
    def cursor(self, value):
        cursor = self.qt_element.textCursor()
        cursor.setPosition(value)
        self.qt_element.setTextCursor(cursor)

    def insert(self, index, text):
        """ Insert text into the given position (ignores 'accept_input' property) """
        revert = not self.accept_input
        if revert: self.accept_input = True
        cursor = self.qt_element.textCursor()
        cursor.setPosition(index)
        cursor.insertText(text)
        self.qt_element.setTextCursor(cursor)
        if revert: self.accept_input = False

    # todo: insert image into text field
    def insert_image(self, index, img):
        pass
    place_image = insert_image

    def delete(self, index1, index2=None):
        """ Delete text between the given positions (ignores 'accept_input' property) """
        revert = not self.accept_input
        if revert: self.accept_input = True
        cursor = self.qt_element.textCursor()
        cursor.setPosition(index1)

        diff = index2 - index1 if index2 else 1
        for _ in range(diff): cursor.deleteChar()

        self.qt_element.setTextCursor(cursor)
        if revert: self.accept_input = False

    def position(self, search_text):
        """ Get the exact coordinates in this text field, or emtpy string if nothing found """
        return self.qt_element.find(search_text)

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

    # QTextEdit.keyPressEvent override
    def _on_key_press(self, key):
        key_code = key.key()
        if key_code == QtCore.Qt.Key_Up:
            res = self._event_handler.call_event("history", direction=-1)
            if res == self._event_handler.block_action: return
        elif key_code == QtCore.Qt.Key_Down:
            res = self._event_handler.call_event("history", direction=1)
            if res == self._event_handler.block_action: return
        QtWidgets.QTextEdit.keyPressEvent(self.qt_element, key)

class PyProgessbar(PyElement):
    """
     Display the progress of a certain action on screen
     No interaction event
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QProgressBar(parent.qt_element)
        self.qt_element.setTextVisible(False)

    @property
    def progress(self): return self.qt_element.value()
    @progress.setter
    def progress(self, value): self.qt_element.setValue(value)

    @property
    def horizontal(self): return self.qt_element.orientation() == QtCore.Qt.Horizontal
    @horizontal.setter
    def horizontal(self, value): self.qt_element.setOrientation(QtCore.Qt.Horizontal if value else QtCore.Qt.Vertical)

    @property
    def minimum(self): return self.qt_element.minimum()
    @minimum.setter
    def minimum(self, value): self.qt_element.setMinimum(value)
    def with_minimum(self, value):
        self.minimum = value
        return self

    @property
    def maximum(self): return self.qt_element.maximum()
    @maximum.setter
    def maximum(self, value): self.qt_element.setMaximum(value)
    def with_maximum(self, value):
        self.maximum = value
        return self

class PyScrollbar(PyElement):
    """
     Adds a scrollbar to an element that is larger than the window
     Generally this element does not need to be created on its own, elements that support it will create them automatically when needed
     No interaction event
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QScrollBar(parent.qt_element)

class PyItemlist(PyElement):
    """
     Show a list of items the user can select
     Interaction event fires when the item selection changes, no keywords
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QListView(parent.qt_element)
        self.qt_element.setUniformItemSizes(True)
        self.qt_element.setViewMode(QtWidgets.QListView.ListMode)
        self.qt_element.setFlow(QtWidgets.QListView.TopToBottom)