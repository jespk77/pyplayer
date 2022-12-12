from core import messagetypes, modules
module = modules.Module(__package__)

from .keyboard_listener import KeyboardListener
from . import configurator, commands

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

def interception_device(arg, argc):
    keyboard_listener.update_device()
    return messagetypes.Reply("Press any key on the device you want to use for effects")

def _on_effect_key(code):
    command = commands.key_commands.get_command_for_code(code)
    if command: module.interpreter.put_command(command)

def _on_effect_device_change(device):
    print("VERBOSE", f"Updated effect device to {device}")
    module.configuration[effect_device_key] = device

@module.Initialize
def initialize():
    global keyboard_listener
    keyboard_listener = KeyboardListener(module.configuration.get_or_create(effect_device_key, 1))
    keyboard_listener.EventEffectKey(_on_effect_key)

@module.Destroy
def destroy():
    keyboard_listener.stop()

module.commands = {
    "interception":{
        "configure": interception_configure,
        "device-update": interception_device,
        "start": interception_start,
        "stop": interception_stop,
    }
}