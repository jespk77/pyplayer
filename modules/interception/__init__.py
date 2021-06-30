import os, json
from interception import ffi, lib as interception

from ui.qt import pyworker
from core import messagetypes, modules
module = modules.Module(__package__)

from . import keyconfigurationwindow

# MODULE SPECIFIC VARIABLES
trigger_file = "keytriggers"
loop_effect_command = "effect loop {}"
hook_running = False
key_cache = {}
key_cache_date = -1
interception_worker = None

def verify_key_cache():
    global trigger_file, key_cache, key_cache_date
    if os.path.isfile(trigger_file):
        mtm = os.stat(trigger_file).st_mtime
        if mtm > key_cache_date:
            key_cache_date = mtm
            try:
                file = open(trigger_file, "r")
                key_cache = json.load(file)
                file.close()
            except Exception as e:
                key_cache.clear()
                print("ERROR", "Updating keyfile:", e)
    else: key_cache.clear()

def on_key_down(key):
    global key_cache
    verify_key_cache()
    key = str(key)
    item = key_cache.get(key)
    if item is not None:
        cmd = item.get("command")
        if cmd is not None: module.interpreter.put_command(cmd)
    else: print("WARNING", "no entry found for keycode", key)

class InterceptionWorker(pyworker.PyWorker):
    def __init__(self):
        pyworker.PyWorker.__init__(self, "interception_worker", True)
        self._lock = pyworker.PyLock()
        self._run = True
        self._ctrl = self._shift = False

    def _on_key_event(self, device, key):
        if device == 1:
            if key.state == 0 or key.state == 2: on_key_down(key.state * 100 + key.code)
            return True
        else:
            if key.state == 0:
                self._ctrl = key.code == 29
                self._shift = key.code == 42
            elif key.state == 1:
                self._ctrl = self._ctrl and key.code == 29
                self._shift = self._shift and key.code == 42
            elif key.state == 2:
                if self._ctrl and self._shift and key.code < 100: on_key_down(100 + key.code)

    def run(self):
        print("INFO", "Initializing interception...")
        context = interception.interception_create_context()
        interception.interception_set_filter(context, interception.interception_is_keyboard, interception.INTERCEPTION_FILTER_KEY_ALL)
        stroke = ffi.new("InterceptionStroke*")

        print("INFO", "Interception worker started")
        while True:
            device = interception.interception_wait(context)
            with self._lock:
                if not self._run: break
            if not interception.interception_receive(context, device, stroke, 1): break

            block = False
            if interception.interception_is_keyboard(device):
                key = ffi.cast("InterceptionKeyStroke*", stroke)
                if key.state > 3 and key.code == 29: break
                block = self._on_key_event(device, key)

            if not block: interception.interception_send(context, device, stroke, 1)

        print("INFO", "Stopping interception...")
        interception.interception_destroy_context(context)

    def stop(self):
        with self._lock: self._run = False

def _is_interception_running():
    return interception_worker is not None and interception_worker.running

def interception_start(arg=None, argc=None):
    if interception is not None:
        if not _is_interception_running():
            global interception_worker
            interception_worker = InterceptionWorker()
            return messagetypes.Reply("Interception started")
        else: return messagetypes.Reply("Interception already running")

def interception_stop(arg=None, argc=None):
    global interception_worker
    if _is_interception_running():
        interception_worker.stop()
        return messagetypes.Reply("Interception stopped")
    else: return messagetypes.Reply("Interception not started")

def interception_toggle(arg=None, argc=None):
    if _is_interception_running(): return interception_stop()
    else: return interception_start()

def interception_configure(arg, argc):
    if not os.path.isfile(trigger_file): return messagetypes.Reply("Cannot configure keys without a file")
    keyconfigurationwindow.trigger_file = trigger_file
    if module.client.find_window(keyconfigurationwindow.KeyConfigurationWindow.window_id) is None:
        module.client.add_window(window_class=keyconfigurationwindow.KeyConfigurationWindow)
    return messagetypes.Reply("Interception key configuration window opened")

module.commands = {
    "interception": {
        "configure": interception_configure,
        "start": interception_start,
        "stop": interception_stop,
        "toggle": interception_toggle,
    }
}