from PyQt5 import QtCore, QtGui, QtWidgets

from . import pywindow, pyevents, pyimage

def valid_check(element):
    if not isinstance(element, PyElement) and not isinstance(element, pywindow.PyWindow): raise ValueError("Parent must be an instance of PyElement or PyWindow")

class PyElement:
    def __init__(self, container, element_id):
        valid_check(container)
        self._container: pywindow.PyWindow = container
        self._element_id = element_id
        self._qt = None
        self._event_handler = pyevents.PyElementEvents()

    @property
    def element_id(self): return self._element_id
    widget_id = element_id

    # todo: element configuration
    @property
    def configuration(self): return None
    def load_configuration(self):
        pass

    @property
    def layout(self): raise TypeError(f"Layout elements not supported for '{__name__}'")
    @property
    def events(self): return self._event_handler

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

    def add_element(self, element_id, element=None, element_class=None, **layout_kwargs): self.get_element(element_id)
    def get_element(self, element_id): raise TypeError(f"Element hiarchy not supported for '{__name__}'")
    def find_element(self, element_id): self.get_element(element_id)
    def remove_element(self, element_id): self.get_element(element_id)

class PyFrame(PyElement):
    """
     General element class that can contain child widgets
     No interaction event
    """
    def __init__(self, parent, id):
        PyElement.__init__(self, parent, id)
        self._qt = QtWidgets.QWidget(parent._qt)


class PyTextLabel(PyElement):
    """
     Element for displaying a line of text and/or an image
     No interaction event
    """
    def __init__(self, parent, id):
        PyElement.__init__(self, parent, id)
        self._qt = QtWidgets.QLabel(parent._qt)
        self._img = None
        self._qt.setAlignment(QtCore.Qt.AlignLeft)

    @property
    def display_text(self): return self._qt.text()
    @display_text.setter
    def display_text(self, txt): self._qt.setText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def display_image(self): return self._qt.pixmap() is not None or self._qt.movie() is not None
    @display_image.setter
    def display_image(self, image): pyimage.PyImage(self, file=image)
    def with_image(self, *args):
        pyimage.PyImage(self, *args)
        return self

    def set_image(self, img):
        self._img = img
        if img.animated:
            self._qt.setMovie(img.data)
            img.start()
        else: self._qt.setPixmap(img.data)

    @property
    def wrapping(self): return self._qt.wordWrap()
    @wrapping.setter
    def wrapping(self, wrap): self._qt.setWordWrap(wrap)

    _alignments = {"left": QtCore.Qt.AlignLeft, "center": QtCore.Qt.AlignHCenter, "right": QtCore.Qt.AlignRight}
    def set_alignment(self, align):
        """ Set alignment for this label, must be either 'left', 'center' or 'right' """
        self._qt.setAlignment(self._alignments[align])


class PyTextInput(PyElement):
    """
     Element for entering a single line of data
     Interaction event fires when the enter is pressed while this element has focus, no keywords
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QLineEdit(parent._qt)
        self._qt.returnPressed.connect(lambda : self.events.call_event("interact"))

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
    """
     Adds a simple checkable box
     Interaction event fires when the element is toggled, no keywords
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QCheckBox(parent._qt)
        self._qt.clicked().connect(lambda :self.events.call_event("interact"))

    @property
    def display_text(self): return self._qt.text()
    @display_text.setter
    def display_text(self, txt): self._qt.setText(txt)
    def with_text(self, txt):
        self.display_text = txt
        return self
    text = display_text

    @property
    def checked(self): return self._qt.isChecked()
    @checked.setter
    def checked(self, checked): self._qt.setChecked(checked)

    @property
    def accept_input(self): return self._qt.isCheckable()
    @accept_input.setter
    def accept_input(self, check): self._qt.setCheckable(check)


class PyButton(PyElement):
    """
     Clickable button element, can be customized with text and/or an image
     Interaction event fires when the button is pressed, no keywords
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QPushButton(parent._qt)
        self._qt.clicked.connect(lambda : self.events.call_event("interact"))
        self._click_cb = self._img = None

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
    def display_image(self): return self._qt.icon() is not None
    @display_image.setter
    def display_image(self, image): pyimage.PyImage(self, file=image)
    def with_image(self, *args):
        pyimage.PyImage(self, *args)
        return self

    def set_image(self, img):
        self._img = QtGui.QIcon(img.data)
        self._qt.setIcon(self._img)


class PyTextField(PyElement):
    """
     Element for displaying and/or entering multiple lines of text
     No interaction event
    """
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
    """
     Display the progress of a certain action on screen
     No interaction event
    """
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
    """
     Adds a scrollbar to an element that is larger than the window
     Generally this element does not need to be created on its own, elements that support it will create them automatically when needed
     No interaction event
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QScrollBar(parent._qt)

class PyItemlist(PyElement):
    """
     Show a list of items the user can select
     Interaction event fires when the item selection changes, no keywords
    """
    def __init__(self, parent, element_id):
        PyElement.__init__(self, parent, element_id)
        self._qt = QtWidgets.QListView(parent._qt)
        self._qt.setUniformItemSizes(True)
        self._qt.setViewMode(QtWidgets.QListView.ListMode)
        self._qt.setFlow(QtWidgets.QListView.TopToBottom)