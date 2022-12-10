from core import messagetypes, modules
module = modules.Module(__package__)

from .keyboard_listener import KeyboardListener
from . import configurator

effect_device_key = "effect_device"
keyboard_listener : KeyboardListener = None

def interception_start(arg, argc):
    result = keyboard_listener.start()
    return messagetypes.Reply("Input listener started" if result else "Input listener couldn't be started")

def interception_stop(arg, argc):
    result = keyboard_listener.stop()
    return messagetypes.Reply("Input listener stopped" if result else "Input listener not running")

def interception_configure(arg, argc):
    module.client.add_window(window_class=configurator.ConfiguratorWindow)
    return messagetypes.Reply("Interception configurator window opened")

@module.Initialize
def initialize():
    global keyboard_listener
    keyboard_listener = KeyboardListener(module.configuration.get_or_create(effect_device_key, 1))

@module.Destroy
def destroy():
    keyboard_listener.stop()

module.commands = {
    "interception":{
        "configure": interception_configure,
        "start": interception_start,
        "stop": interception_stop,
    }
}