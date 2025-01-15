import threading

from collections import namedtuple
from multiprocessing import Event, RLock

from pyftdi import ftdi

Device = namedtuple("Device", ["vendor_id", "product_id"])
Connection = namedtuple("Connection", ["baud", "data_bits", "stop_bit", "parity"])
NumericalLimit = namedtuple("NumericalLimit", ["min", "max"])

class DMXController:
    channel_limit = NumericalLimit(0, 512)
    value_limit = NumericalLimit(0, 255)

    def __init__(self, device: Device, connection: Connection, fps: float):
        if fps <= 0: raise ValueError("fps cannot be negative")
        self._device, self._connection = device, connection
        self._fps = fps

        self._ftdi: ftdi.Ftdi|None = None
        self._thread : threading.Thread|None = None
        self._thread_lock = RLock()
        self._thread_event = Event()

        self._events = {}
        self._frame = [0] * 512
        self._dirty = False

    @property
    def running(self): return self._thread is not None and self._thread.is_alive()
    @property
    def connected(self): return self.running and self._ftdi is not None and self._ftdi.is_connected
    @property
    def frame(self):
        with self._thread_lock: return iter(self._frame)

    @property
    def device(self):
        with self._thread_lock: return self._device
    @device.setter
    def device(self, value : Device):
        with self._thread_lock: self._device = value
    @property
    def connection(self):
        with self._thread_lock: return self._connection
    @connection.setter
    def connection(self, value : Connection):
        with self._thread_lock: self._connection = value

    @property
    def fps(self):
        with self._thread_lock: return self._fps
    @fps.setter
    def fps(self, fps: float):
        if fps <= 0: raise ValueError("fps cannot be negative")
        with self._thread_lock: self._fps = fps

    def EventConnected(self, cb):
        if not callable(cb): raise TypeError("Event callback must be callable")
        with self._thread_lock: self._events["connect"] = cb
        return cb
    def EventDisconnected(self, cb):
        if not callable(cb): raise TypeError("Event callback must be callable")
        with self._thread_lock: self._events["disconnect"] = cb
        return cb
    def EventDataTransmit(self, cb):
        if not callable(cb): raise TypeError("Event callback must be callable")
        with self._thread_lock: self._events["transmit"] = cb
        return cb
    def EventError(self, cb):
        if not callable(cb): raise TypeError("Event callback must be callable")
        with self._thread_lock: self._events["error"] = cb
        return cb

    def clear_events(self):
        with self._thread_lock: self._events.clear()

    def start(self):
        if self.running: return
        self._thread_event.clear()
        self._thread = threading.Thread(target=self._main, name="DMXControllerThread")
        self._thread.start()

    def stop(self, blocking=False):
        if not self.running: return
        self._thread_event.set()
        if blocking: self._thread.join()

    def get_channel_value(self, channel):
        if channel <= self.channel_limit.min or channel >= self.channel_limit.max: raise ValueError(f"Channel #{channel} out of range")
        return self._frame[channel - 1]

    def set_channel_value(self, channel, value):
        if channel <= self.channel_limit.min or channel >= self.channel_limit.max: raise ValueError(f"Channel #{channel} out of range")
        print(f"set #{channel} to {value}")
        with self._thread_lock:
            self._frame[channel - 1] = max(self.value_limit.min, min(int(value), self.value_limit.max))
            self._dirty = True

    def _call_event(self, event_id: str, *args, **kwargs):
        if cb := self._events.get(event_id):
            try: cb(*args, **kwargs)
            except Exception as e: print("ERROR", f"Calling event '{event_id}':", e)

    def _connect(self):
        if self.connected: return True
        print("VERBOSE", f"Connecting to DMX device vendor_id={hex(self._device.vendor_id)}({self._device.vendor_id}), product_id={hex(self._device.product_id)}({self._device.product_id})")

        # if device not detected: use zadig to install libusbK driver for device
        with self._thread_lock:
            try:
                self._ftdi = ftdi.Ftdi()
                self._ftdi.open(self._device.vendor_id, self._device.product_id)
                self._ftdi.reset()
                self._ftdi.set_baudrate(baudrate=self._connection.baud)
                self._ftdi.set_line_property(bits=self._connection.data_bits, stopbit=self._connection.stop_bit, parity=self._connection.parity)
            except OSError as e:
                # device not found errors don't need error logging and can exit normally
                if str(e) == "Device not found":
                    self._call_event("error", e)
                    return False
                else: raise
        self._call_event("connect")
        return True

    def _disconnect(self):
        if not self.connected: return
        print("VERBOSE", "Disconnecting from DMX device")
        self._ftdi.close()
        self._call_event("disconnect")

    def _transmit(self):
        with self._thread_lock:
            if not self._dirty: return
            print("transmitting data to DMX device")
            data = bytearray(self._frame)
            data.insert(0, 0)

            self._ftdi.set_break(True)
            self._ftdi.set_break(False)
            self._ftdi.write_data(data)
            self._dirty = False
            self._call_event("transmit", self.frame)

    def _main(self):
        print("VERBOSE", "DMX Controller started")
        try:
            if not self._connect(): return
            while True:
                if self._thread_event.wait(self._fps): break
                self._transmit()
        except Exception as e:
            print("ERROR", "Running DMX controller", e)
            self._call_event("error", e)
        finally: self._disconnect()
        print("VERBOSE", "DMX Controller stopped")