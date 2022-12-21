from core import messagetypes, modules
module = modules.Module(__package__)

from . import fixture_control

def open_dmx_window(arg, argc):
    if module.client.find_window(fixture_control.FixtureControlWindow.fixture_window_id) is None:
        module.client.add_window(window_class=fixture_control.FixtureControlWindow)
    return messagetypes.Reply("Opening DMX control")

module.commands = {
    "dmx": {
        "control": open_dmx_window
    }
}