from PyQt5 import QtCore, QtGui, QtWidgets

from . import pywindow, log_exception

def valid_check(element):
    if not isinstance(element, PyElement) and not isinstance(element, pywindow.PyWindow): raise ValueError("Parent must be an instance of PyElement or PyWindow")

class PyElement:
    def __init__(self, container, element_id):
        valid_check(container)
        self._container: pywindow.PyWindow = container
        self._element_id = element_id
        self._qt = None

    @property
    def element_id(self): return self._element_id
    widget_id = element_id

    # todo: element configuration
    @property
    def configuration(self): return None
    def load_configuration(self):
        pass

    # todo: element event handler
    @property
    def event_handler(self): return None

    @property
    def accept_input(self): return True

    @property
    def width(self): return self._qt.width()
    @width.setter
    def width(self, value): self._qt.setFixedWidth(value)
    def with_width(self, value):
        self.width = value
        return self

    @property
    def height(self): return self._qt.height()
    @height.setter
    def height(self, value): self._qt.setFixedHeight(value)
    def with_height(self, value):
        self.height = value
        return self

    def add_element(self, element_id, element=None, element_class=None): raise TypeError(f"Adding child elements not supported for '{__name__}'")
    def get_element(self, element_id): raise TypeError(f"Child elements not supported for '{__name__}")
    def find_element(self, element_id): self.get_element(element_id)
    def remove_element(self, element_id): self.get_element(element_id)

    def grid(self, row=0, column=1, rowspan=1, columnspan=1):
        layout = self._container._qt.layout()
        if not isinstance(layout, QtWidgets.QGridLayout): raise ValueError("Cannot grid element in a non grid layout")
        layout.addWidget(self._qt, row, column, rowspan, columnspan)
        return self

class PyFrame(PyElement):
    def __init__(self, parent, id):
        PyElement.__init__(self, parent, id)
        self._qt = QtWidgets.QWidget(parent._qt)

class PyTextLabel(PyElement):
    """ Element for displaying a line of text """
    def __init__(self, parent, id):
        PyElement.__init__(self, parent, id)
        self._qt = QtWidgets.QLabel(parent._qt)

    @property
    def display_text(self): return self._qt.text()
    @display_text.setter
    def display_text(self, txt): self._qt.setText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def display_image(self): return None
    @display_image.setter
    def display_image(self, img): pass
    def with_image(self, img):
        self.display_image = img
        return self
    image = display_image

    @property
    def wrapping(self): return self._qt.wordWrap()
    @wrapping.setter
    def wrapping(self, wrap): self._qt.setWordWrap(wrap)

class PyTextInput(PyElement):
    """ Element for entering one line data """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QLineEdit(parent._qt)
        self._input_cb = None
        self._qt.textEdited.connect(self._on_edit)

    def _on_edit(self):
        if self._input_cb: self._input_cb()

    @property
    def accept_input(self): return self._qt.isReadOnly()
    @accept_input.setter
    def accept_input(self, value): self._qt.setReadOnly(value)
    def with_accept_input(self, value):
        self.accept_input = value
        return self

    @property
    def format_str(self): return self._qt.inputMask()
    @format_str.setter
    def format_str(self, rex): self._qt.setInputMask(rex if rex is not None else "")
    def with_format_str(self, rex):
        self.format_str = rex
        return self

    @property
    def command(self): return self._input_cb is not None
    @command.setter
    def command(self, cb): self._input_cb = cb
    def with_command(self, cb):
        self.command = cb
        return self

    @property
    def value(self): return self._qt.text()
    @value.setter
    def value(self, val): self._qt.setText(val)
    def with_value(self, val):
        self.value = val
        return self
    display_text = text = value

    @property
    def max_length(self): return self._qt.maxLength()
    @max_length.setter
    def max_length(self, ln): self._qt.setMaxLength(ln)
    def with_max_length(self, ln):
        self.max_length = ln
        return self

class PyCheckbox(PyElement):
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QCheckBox(parent._qt)
        self._input_cb = None
        self._qt.clicked.connect(self._on_press)

    def _on_press(self):
        if self._input_cb: self._input_cb()

    @property
    def display_text(self): return self._qt.text()
    @display_text.setter
    def display_text(self, txt): self._qt.setText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def display_image(self): return None
    @display_image.setter
    def display_image(self, img): pass
    def with_image(self, img):
        self.display_image = img
        return self
    image = display_image

    @property
    def checked(self): return self._qt.isChecked()
    @checked.setter
    def checked(self, checked): self._qt.setChecked(checked)

    @property
    def accept_input(self): return self._qt.isCheckable()
    @accept_input.setter
    def accept_input(self, check): self._qt.setCheckable(check)

    @property
    def command(self): return self._input_cb is not None
    @command.setter
    def command(self, cb): self._input_cb = cb
    def with_command(self, cb):
        self.command = cb
        return self

class PyButton(PyElement):
    """ Clickable button element """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QPushButton(parent._qt)
        self._qt.clicked.connect(self._on_press)
        self._click_cb = None

    def _on_press(self):
        try:
            if self._click_cb: self._click_cb()
        except Exception as e: log_exception(e)

    @property
    def accept_input(self): return self._qt.isEnabled()
    @accept_input.setter
    def accept_input(self, inpt): self._qt.setEnabled(inpt)

    @property
    def display_text(self): return self._qt.text()
    @display_text.setter
    def display_text(self, txt): self._qt.setText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def display_image(self): return None
    @display_image.setter
    def display_image(self, img): pass
    def with_image(self, img):
        self.display_image = img
        return self
    image = display_image

    @property
    def command(self): return self._click_cb is not None
    @command.setter
    def command(self, cb): self._click_cb = cb
    def with_command(self, cb):
        self.command = cb
        return self

class PyTextField(PyElement):
    """ Element for entering multi line text """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QTextEdit(parent._qt)
        self.undo = False

    @property
    def accept_input(self): return self._qt.isReadOnly()
    @accept_input.setter
    def accept_input(self, value): self._qt.setReadOnly(not value)
    def with_accept_input(self, value):
        self.accept_input = value
        return self

    @property
    def undo(self): return self._qt.isUndoRedoEnabled()
    @undo.setter
    def undo(self, do): self._qt.setUndoRedoEnabled(do)

    @property
    def display_text(self): return self._qt.toPlainText()
    @display_text.setter
    def display_text(self, txt): self._qt.setPlainText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def cursor(self): return self._qt.textCursor().position()
    @cursor.setter
    def cursor(self, value):
        cursor = self._qt.textCursor()
        cursor.setPosition(value)
        self._qt.setTextCursor(cursor)

    def insert(self, index, text):
        """ Insert text into the given position (ignores 'accept_input' property) """
        revert = not self.accept_input
        if revert: self.accept_input = True
        cursor = self._qt.textCursor()
        cursor.setPosition(index)
        cursor.insertText(text)
        self._qt.setTextCursor(cursor)
        if revert: self.accept_input = False

    # todo: insert image into text field
    def insert_image(self, index, img):
        pass
    place_image = insert_image

    def delete(self, index1, index2=None):
        """ Delete text between the given positions (ignores 'accept_input' property) """
        revert = not self.accept_input
        if revert: self.accept_input = True
        cursor = self._qt.textCursor()
        cursor.setPosition(index1)

        diff = index2 - index1 if index2 else 1
        for _ in range(diff): cursor.deleteChar()

        self._qt.setTextCursor(cursor)
        if revert: self.accept_input = False

    def position(self, search_text):
        """ Get the exact coordinates in this text field, or emtpy string if nothing found """
        return self._qt.find(search_text)

    def show(self, position):
        """ Make sure that the given line is visible on screen """
        cursor = self._qt.textCursor()
        cursor.setPosition(position)
        self._qt.setTextCursor(cursor)

    def clear_selection(self):
        """ Remove selection in this text field (has no effect if nothing was selected) """
        cursor = self._qt.textCursor()
        cursor.clearSelection()
        self._qt.setTextCursor(cursor)

class PyProgessbar(PyElement):
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QProgressBar(parent._qt)
        self._qt.setTextVisible(False)

    @property
    def progress(self): return self._qt.value()
    @progress.setter
    def progress(self, value): self._qt.setValue(value)

    @property
    def horizontal(self): return self._qt.orientation() == QtCore.Qt.Horizontal
    @horizontal.setter
    def horizontal(self, value): self._qt.setOrientation(QtCore.Qt.Horizontal if value else QtCore.Qt.Vertical)

    @property
    def minimum(self): return self._qt.minimum()
    @minimum.setter
    def minimum(self, value): self._qt.setMinimum(value)
    def with_minimum(self, value):
        self.minimum = value
        return self

    @property
    def maximum(self): return self._qt.maximum()
    @maximum.setter
    def maximum(self, value): self._qt.setMaximum(value)
    def with_maximum(self, value):
        self.maximum = value
        return self

class PyScrollbar(PyElement):
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QScrollBar(parent._qt)

class PyItemlist(PyElement):
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QListView(parent._qt)
        self._qt.setUniformItemSizes(True)
        self._qt.setViewMode(QtWidgets.QListView.ListMode)
        self._qt.setFlow(QtWidgets.QListView.TopToBottom)