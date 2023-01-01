from core import modules, messagetypes
from . import window

module = modules.Module(__package__)

def command_close_monitor(arg, args):
    module.client.schedule_task(task_id="close_monitor")
    return messagetypes.Reply("System monitor window closed")

def command_open_monitor(arg, argc):
    module.client.schedule_task(task_id="open_monitor")
    return messagetypes.Reply("System monitor window opened")

module.commands = {
    "monitor": {
        "close": command_close_monitor,
        "open": command_open_monitor
    }
}

@module.Initialize
def initialize():
    module.client.add_task(task_id="close_monitor", func=_close_monitor)
    module.client.add_task(task_id="open_monitor", func=_open_monitor)

def _open_monitor():
    module.client.add_window(window_class=window.MonitorWindow)

def _close_monitor():
    module.client.close_window(window_id=window.MonitorWindow.window_name)