class EventHandler:
    def __init__(self):
        self._events = {}

    def call_event(self, event_name, context, **kwargs):
        callback = self._events.get(event_name)
        if callback:
            args = callback.__code__.co_varnames
            try: return callback(context, **{key: value for key, value in kwargs.items() if key in args})
            except Exception as e:
                import traceback
                print("ERROR", f"Error processing event '{event_name}':")
                traceback.print_exception(type(e), e, e.__traceback__)

    def register_event(self, event_name, cb):
        self._events[event_name] = cb
        return cb