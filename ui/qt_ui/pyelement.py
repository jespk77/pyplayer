import PyQt5.QtWidgets as qt, PyQt5.QtCore as qtcore

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

    @property
    def accept_input(self): return True

    def add_element(self, element_id, element=None, element_class=None): raise TypeError(f"Adding child elements not supported for '{__name__}'")
    def get_element(self, element_id): raise TypeError(f"Child elements not supported for '{__name__}")
    def find_element(self, element_id): self.get_element(element_id)
    def remove_element(self, element_id): self.get_element(element_id)

    def grid(self, row=0, column=1, rowspan=1, columnspan=1):
        layout = self._container._qt.layout()
        if not isinstance(layout, qt.QGridLayout): raise ValueError("Cannot grid element in a non grid layout")
        layout.addWidget(self._qt, row, column, rowspan, columnspan)
        return self

class PyFrame(PyElement):
    def __init__(self, parent, id):
        PyElement.__init__(self, parent, id)
        self._qt = qt.QWidget(parent._qt)

class PyTextLabel(PyElement):
    """ Element for displaying a line of text """
    def __init__(self, parent, id):
        PyElement.__init__(self, parent, id)
        self._qt = qt.QLabel(parent._qt)

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
        self._qt = qt.QLineEdit(parent._qt)
        self._input_cb = None
        self._qt.textEdited.connect(self._on_edit)

    def _on_edit(self):
        if self._input_cb: self._input_cb()

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
        self._qt = qt.QCheckBox(parent._qt)
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
    def command(self, cb):
        self._input_cb = cb
    def with_command(self, cb):
        self.command = cb
        return self

class PyButton(PyElement):
    """ Clickable button element """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = qt.QPushButton(parent._qt)
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
        self._qt = qt.QTextEdit(parent._qt)
        self.undo = False

    @property
    def accept_input(self): return self._qt.isEnabled()
    @accept_input.setter
    def accept_input(self, inpt): self._qt.setEnabled(inpt)

    @property
    def undo(self): return self._qt.isUndoRedoEnabled()
    @undo.setter
    def undo(self, do): self._qt.setUndoRedoEnabled(do)

    @property
    def current_pos(self): return self._qt.textCursor()
    @current_pos.setter
    def current_pos(self, pos): self._qt.cursorForPosition(pos)

    @property
    def display_text(self): return self._qt.toPlainText()
    @display_text.setter
    def display_text(self, txt): self._qt.setText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

class PyProgessbar(PyElement):
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = qt.QProgressBar(parent._qt)

class PyScrollbar(PyElement):
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = qt.QScrollBar(parent._qt)

class PyItemlist(PyElement):
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = qt.QListView(parent._qt)
