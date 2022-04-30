import threading

from interception import ffi, lib as interception

from .codes import KeyCode

class KeyboardListener:
    """ Background thread for listening and handling interception key events """
    def __init__(self, device_id=-1):
        self._intercept_device = device_id
        self._interception_context = self._interception_thread = None

        self._lock = threading.RLock()
        self._run = False
        self._event_callback = None
        self._block_next = False

    @property
    def has_device(self):
        """ True if this listener has a device to listen to bound, False otherwise """
        with self._lock: return self._intercept_device >= 0

    @property
    def device_id(self):
        """ The device id used for generating keypress event, set to -1 to disable """
        with self._lock: return self._intercept_device
    @device_id.setter
    def device_id(self, device_id):
        with self._lock: self._intercept_device = int(device_id)

    @property
    def event_callback(self):
        """
            The callback to call when key events are received.
            If this callback is set, it must be a function that takes the device id and key data as arguments
            If this callback returns True, the event is not processed any further.
            If the callback returns any other value or if it's set to None, the normal behavior remains
        """
        return self._event_callback
    @event_callback.setter
    def event_callback(self, cb):
        with self._lock: self._event_callback = cb

    @property
    def active(self):
        """ True if the listener is currently active, False otherwise """
        return self._interception_thread is not None

    def start(self):
        """ Start the interception listener, returns True if the listener is running """
        if not self.active:
            self._interception_context = interception.interception_create_context()
            if not self._interception_context:
                print("WARNING", "Failed to create interception context, key events cannot be generated")
                self._interception_context = None
                return False

            self._run = True
            self._interception_thread = threading.Thread(name="InterceptionThread", target=self.run)
            self._interception_thread.start()
        return True

    def stop(self):
        """ Stops the interception listener, returns True if the listener was stopped """
        if self.active:
            with self._lock:
                self._run = False
                interception.interception_send(self._interception_context, 1, ffi.new("InterceptionKeyStroke*"), 1)
                interception.interception_destroy_context(self._interception_context)
                self._interception_context = None

            self._interception_thread.join()
            self._interception_thread = None
            return True
        return False

    def run(self):
        print("VERBOSE", "Interception thread started")
        context = interception.interception_create_context()
        interception.interception_set_filter(context, interception.interception_is_keyboard, interception.INTERCEPTION_FILTER_KEY_ALL)
        stroke = ffi.new("InterceptionStroke*")

        while True:
            device = interception.interception_wait(context)
            with self._lock:
                if not self._run or not interception.interception_receive(context, device, stroke, 1): break
                if self._block_next:
                    self._block_next = False
                    continue

                if interception.interception_is_keyboard(device):
                    key = ffi.cast("InterceptionKeyStroke*", stroke)
                    # key down events have an even state so only listen to those
                    if key.state % 2 != 0: continue

                    print("VERBOSE", f"Key event received on device {device} with code {hex(key.code)} and state {key.state}")
                    if key.state > 1: key.code *= key.state + 2

                    # pressing PAUSE key also generates NumLock event which needs to be ignored
                    if key.code == KeyCode.Key_Pause: self._block_next = True

                    if self._event_callback is not None:
                        print("VERBOSE", "Key callback set, calling this first")
                        try:
                            result = self._event_callback(device, key)
                            if result is True: continue
                        except Exception as e: print("ERROR", "Failed to call keylister callback:", e)

                    if self.device_id == device:
                        self._on_key_down(device, key)
                        continue

                interception.interception_send(context, device, stroke, 1)

        interception.interception_destroy_context(context)
        print("VERBOSE", "Interception thread finished")
        return True

    def _on_key_down(self, device, key):
        print("VERBOSE", f"Key {hex(key.code)} pressed on device {device}")