from PyQt5 import QtCore

class _EventCore:
    def __init__(self):
        self._events = {}

    def call_event(self, event_name, **kwargs):
        callback = self._events.get(event_name)
        if callback:
            args = callback.__code__.co_varnames
            try: return callback(**{key: value for key, value in kwargs.items() if key in args})
            except Exception as e: print("ERROR", f"Error processing event '{event_name}':", e)

    def register_event(self, event_name, cb):
        self._events[event_name] = cb
        return cb

class EventHandler(_EventCore):
    """
     Main handler for all types of events
     An event is a function that gets called whenever a certain action happened, these often support a number of keywords
     A keyword is bound to an event function when the function accepts an argument with that specific name, see description of each event for what keywords are supported
     An argument can be left out (in that case the keyword is not passed) but is an error when an argument is added that isn't a supported keyword
    """
    block = block_action = 0xBEEF

    def __init__(self, element):
        _EventCore.__init__(self)
        self._element = element

    _key_modifiers = {QtCore.Qt.NoModifier: None, QtCore.Qt.ShiftModifier: "shift", QtCore.Qt.ControlModifier: "ctrl", QtCore.Qt.AltModifier: "alt"}
    def call_keydown_event(self, event):
        cb = self._element._key_cb.get(event.key())
        if not cb: cb = self._element._key_cb.get('*')

        if cb:
            kwargs = {"key": event.key(), "modifiers": [self._key_modifiers[k] for k in self._key_modifiers.keys() if event.modifiers() & k]}
            args = cb.__code__.co_varnames
            try:
                res = cb(**{key: value for key, value in kwargs.items() if key in args})
                if res == self.block_action: return True
            except Exception as e: print("ERROR", f"Error processing event 'key_down':", e)
        return False

    def EventKeyDown(self, key):
        """
         Event that fires when a key is pressed, or 'all' to capture all keys
         Note: This event is only fired for the closest match, therefore the 'all' event is only fired if there's nothing bound to the specfic key that was pressed
            - available keywords:
                * key: the key code of the key that was pressed
                * modifier: the modifier key that was held, or None if no modifier was held
            - not cancellable
        """
        from PyQt5.QtCore import Qt
        if key != "all":
            key_code = Qt.__dict__.get("Key_"+key)
            if not key_code: raise ValueError(f"Unknown key '{key}'")
        else: key_code = "*"

        def wrapped(cb):
            self._element._key_cb[key_code] = cb
            return cb
        return wrapped

    def EventHandleChange(self, cb):
        """
         Event that fires whenever the handle to the element changes
            - available keywords:
                * handle: the new handle of the element
            - not cancellable
        """
        self.register_event("handle_change", cb)
        return cb

class PyWindowEvents(EventHandler):
    """
     Container for all window events, see EventHandler for more information
     All events support 'window' keyword, which contains a reference to the window that generated the event
     """
    def __init__(self, window):
        EventHandler.__init__(self, window)

    def call_event(self, event_name, **kwargs):
        kwargs["window"] = self._element
        return EventHandler.call_event(self, event_name, **kwargs)

    def EventWindowOpen(self, cb):
        """
         Event that fires whenever the window is shown on screen for the first time
            - no callback keywords
            - not cancellable
        """
        self.register_event("window_open", cb)
        return cb

    def EventWindowDestroy(self, cb):
        """
         Event that fires before the window gets destroyed, should be used to clean up variables and/or close open handles
         Note: this event is not equal to the 'WindowClosed' event, this one fires when the window is in the process of being destroyed and is therefore not cancellable
            - no keywords
            - not cancellable
        """
        self.register_event("window_destroy", cb)
        return cb

    def EventWindowClose(self, cb):
        """
         Event fires when the user is trying to close the window, if the event is canceled the window won't close
         Note: this event is not equal to the 'WindowDestroy' event, this one is fired if the user is trying to close it, the window might not actually get destroyed
            - no keywords
            - cancellable
        """
        self.register_event("window_close", cb)
        return cb

    def EventWindowResize(self, cb):
        """ Fired when the window has been resized
            - available keywords:
                * width: the new width of the window (in pixels)
                * height: the new height of the window (in pixels)
            - not cancellable
        """
        self.register_event("window_resize", cb)
        return cb

    def EventWindowHide(self, cb):
        """
         Fired when the window gets hidden, this can be done either with the minimize button or programatically
            - no keywords
            - not cancellable
        """
        self.register_event("window_hide", cb)
        return cb

    def EventWindowShow(self, cb):
        """
         Fired when the window becomes visible after it was hidden
            - no keywords
            - not cancellable
        """
        self.register_event("window_show", cb)
        return cb


class PyElementEvents(EventHandler):
    """
     Container for all element events, see EventHandler for more information
     All events support 'element' and 'container' keywords for references to the element that generated the event and its parent, respectively
    """
    def __init__(self, container, element):
        EventHandler.__init__(self, element)
        self._container = container

    def call_event(self, event_name, **kwargs):
        kwargs["container"] = self._container
        kwargs["element"] = self._element
        EventHandler.call_event(self, event_name, **kwargs)

    def EventDestroy(self, cb):
        """
         Event that fires when an element is about to be destroyed
            - not cancellable
        """
        self.register_event("destroy", cb)
        return cb

    def EventLeftClick(self, cb):
        """
         Event that fires when an element is left clicked
            - available keywords:
                * x: the x position of the cursor, relative to the element's size
                * screen_x: the x position of the cursor on the screen
                * y: the y position of the cursor, relative to the element's size
                * screen_y: the y postition of the cursor on the screen
            - not cancellable
        """
        self.register_event("left_click", cb)
        return cb

    def EventDoubleClick(self, cb):
        """
         Event that fires when an element is double clicked
            - available keywords:
                * x: the x position of the cursor, relative to the element's size
                * screen_x: the x position of the cursor on the screen
                * y: the y position of the cursor, relative to the element's size
                * screen_y: the y postition of the cursor on the screen
            - not cancellable
        """
        self.register_event("double_click_left", cb)
        return cb

    def EventRightClick(self, cb):
        """
         Event that fires when an element is right clicked
            - available keywords:
                * x: the x position of the cursor, relative to the element's size
                * screen_x: the x position of the cursor on the screen
                * y: the y position of the cursor, relative to the element's size
                * screen_y: the y postition of the cursor on the screen
            - not cancellable
        """
        self.register_event("right_click", cb)
        return cb

    def EventDoubleClickRight(self, cb):
        """
         Event that fires when an element is double clicked with the right mouse button
            - available keywords:
                * x: the x position of the cursor, relative to the element's size
                * screen_x: the x position of the cursor on the screen
                * y: the y position of the cursor, relative to the element's size
                * screen_y: the y postition of the cursor on the screen
            - not cancellable
        """
        self.register_event("double_click_right", cb)
        return cb

    def EventScroll(self, cb):
        """
         Event that fires when the mouse wheel is scrolled while hovering over the element
            - available keywords:
                * x: the amount of scroll in the x direction
                * y: the amount of scroll in the y direction
                * delta: the amount of scroll packed in a tuple (x,y)
            - not cancellable
        """
        self.register_event("scroll_wheel", cb)
        return cb

    def EventInteract(self, cb):
        """
         Event that fires when an element is interacted with
         Details on this interaction vary per element
            - available keywords: varied, see documentation for each element
            - not cancellable
        """
        self.register_event("interact", cb)
        return cb

    def EventFocusGet(self, cb):
        """
         Event that fires when this element receives focus
            - no keywords
            - not cancellable
        """
        self.register_event("get_focus", cb)
        return cb

    def EventFocusLost(self, cb):
        """
         Event that fires when this element loses focus
            - no keywords
            - not cancellable
        """
        self.register_event("lose_focus", cb)
        return cb


class PyElementInputEvent(PyElementEvents):
    def EventHistory(self, cb):
        """
         Event that fires when the user presses the up or down key
         Can be used to go back and forth between previous entered lines
            - available keywords:
                * direction: which direction to go (-1 for backward, 1 for forward)
            - cancellable: if cancelled the key press will not be forwarded to the element
        """
        self.register_event("history", cb)
        return cb


class PyDialogEvent(_EventCore):
    """
     Container for all dialog events, see EventHandler for more information
     All events support 'dialog' keyword for a reference to the dialog that generated the event
    """
    def __init__(self, dialog):
        self._dialog = dialog
        _EventCore.__init__(self)

    def call_event(self, event_name, **kwargs):
        kwargs["dialog"] = self._dialog
        _EventCore.call_event(self, event_name, **kwargs)

    def EventSubmit(self, cb):
        """
         Event that fires when the user submits their choice in the dialog
            - available keywords:
                * value: the submitted value, possible options depend on the type of dialog
            - not cancellable
        """
        self.register_event("submit", cb)
        return cb

    def EventCancel(self, cb):
        """
         Event that fires when the user closes the dialog without submitting anything
            - no keywords
            - not cancellable
        """
        self.register_event("cancel", cb)
        return cb