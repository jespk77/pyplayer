from core import messagetypes, modules
module = modules.Module(__package__)

from .setup_window import DMXSetupWindow

def open_dmx_setup(args, argc):
    module.client.schedule_task(func=lambda : module.client.add_window(window_class=DMXSetupWindow))
    return messagetypes.Reply("Opened DMX setup window")

module.commands = {
    "dmx":{
        "setup": open_dmx_setup
    }
}