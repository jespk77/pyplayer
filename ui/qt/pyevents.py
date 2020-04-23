class EventHandler:
    block = block_action = 0xBEEF

    def __init__(self):
        self._events = {}

    def call_event(self, event_name, **kwargs):
        callback = self._events.get(event_name)
        if callback:
            args = callback.__code__.co_varnames
            try: return callback(**{key: value for key, value in kwargs.items() if key in args})
            except Exception as e:
                import traceback
                print("ERROR", f"Error processing event '{event_name}':")
                traceback.print_exception(type(e), e, e.__traceback__)

    def register_event(self, event_name, cb):
        self._events[event_name] = cb
        return cb

class PyWindowEvents(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

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

class PyElementEvents(EventHandler):
    def __init__(self, element):
        EventHandler.__init__(self)
        self._element = element

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
        self.register_event("double_left_click", cb)
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
        self.register_event("double_right_click", cb)
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
            if not key_code: raise ValueError(f"Unknown key '{key}")
        else: key_code = "*"

        def wrapped(cb):
            self._element._key_cb[key_code] = cb
            return cb
        return wrapped


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