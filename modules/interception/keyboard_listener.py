import threading

from interception import ffi, lib as interception

from .codes import KeyCode

class KeyboardListener:
    """ Background thread for listening and handling interception key events """
    def __init__(self, effect_device_id):
        self._effect_device = effect_device_id
        self._interception_context = self._interception_thread = None

        self._key_down_cb = self._effect_key_cb = None

        self._lock = threading.RLock()
        self._run = False
        self._block_next = False

    @property
    def effect_device_id(self):
        """ The device id used for generating keypress event, set to < 0 to disable """
        with self._lock: return self._effect_device

    @effect_device_id.setter
    def effect_device_id(self, device_id):
        device_id = int(device_id)
        with self._lock: self._effect_device = device_id

    @property
    def active(self):
        """ True if the listener is currently active, False otherwise """
        return self._interception_thread is not None

    def EventKeyDown(self, cb):
        self._key_down_cb = cb
        return cb

    def EventEffectKey(self, cb):
        self._effect_key_cb = cb
        return cb

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

                    if self._on_key_down(device, key) is True: continue

                    if self.effect_device_id == device:
                        self._on_effect_key_down(device, key)
                        continue

                interception.interception_send(context, device, stroke, 1)

        interception.interception_destroy_context(context)
        print("VERBOSE", "Interception thread finished")
        return True

    def _on_key_down(self, device, key):
        code = key.code
        print("VERBOSE", f"Key {hex(code)} down on device {device}")
        if self._key_down_cb:
            try: return self._key_down_cb(device, code)
            except Exception as e: print("ERROR", f"Processing callback for key {hex(code)}", e)

    def _on_effect_key_down(self, device, key):
        code = key.code
        print("VERBOSE", f"Key {hex(code)} down on effect device ({device})")
        if self._effect_key_cb:
            try: self._effect_key_cb(code)
            except Exception as e: print("ERROR", f"Processing effect callback for key {hex(code)}", e)