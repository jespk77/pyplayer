import os
from core import messagetypes, modules

import tinytuya
# put all tuya stuff in a separate folder
if not os.path.isdir(".cache"): os.mkdir(".cache")
tinytuya.DEVICEFILE = os.path.join(".cache", "tuya_devices.json")
tinytuya.SNAPSHOTFILE = os.path.join(".cache", "tuya_snapshot.json")
tinytuya.CONFIGFILE = os.path.join(".cache", "tuya_config.json")
tinytuya.RAWFILE = os.path.join(".cache", "tuya_raw.txt")

module = modules.Module(__package__)
devices = {}

def _load_devices():
    global devices
    devices.clear()
    for device in tinytuya.load_devicefile(tinytuya.DEVICEFILE):
        try:
            ip = device["ip"]
            if not ip: continue # ignore devices without an ip address as they won't load correctly and slow everything down

            device_obj = tinytuya.Device(dev_id=device["id"], address=ip, local_key=device["key"], version=device["version"])
            devices[device["name"]] = device_obj
        except KeyError: pass
        except Exception as ex: print("ERROR", f"Failed to create device '{device}':", ex)

    if not devices: return messagetypes.Reply("No devices found, try running 'home setup' again...")
    return None # successful operation means no need to return anything as further processing is required

def do_initial_setup(*_):
    credentials = {
        "apiKey": module.configuration.get("tuya_credentials::client_id"),
        "apiSecret": module.configuration.get("tuya_credentials::client_secret"),
        "apiRegion": module.configuration.get("tuya_credentials::client_region"),
        "apiDeviceID": "scan", # assume we have no device ids and do a local scan
    }

    for key, value in credentials.items():
        if not value: return messagetypes.Error(f"Missing required option '{key}': please enter your Tuya credentials in the options")

    from tinytuya import scanner, wizard # importing scanner is actually needed for wizard.wizard to scan for devices
    wizard.wizard(color=False, assume_yes=True, discover=True, credentials=credentials)
    _load_devices()
    return messagetypes.Reply(f"Tuya setup completed: {len(devices)} devices found and registered")

def load_devices(arg, argc):
    response = _load_devices()
    if response is not None: return response
    return messagetypes.Reply(f"Reloaded {len(devices)} from file")

def _check_input(arg, argc):
    global devices
    if not devices:
        response = _load_devices()
        if response is not None: return response
    if argc < 1: return messagetypes.Reply("Missing device or group name")

def _find_device(device_name):
    global devices
    for device in devices.keys():
        if device == device_name: return device

def _get_device_data_for_name(name):
    groups = module.configuration.get("device_groups")
    if name in groups:
        return [_find_device(device) for device in groups[name]["devices"]]
    else:
        device = _find_device(name)
        if device: return [device]
        else: return []

def turn_on_device(arg, argc):
    if (response := _check_input(arg, argc)) is not None: return response

    found_devices = _get_device_data_for_name(arg[0])
    if not found_devices: return messagetypes.Reply(f"No devices or groups found with name '{arg[0]}'")

    for device in found_devices:
        global devices
        device_obj = devices.get(device)
        if device_obj: device_obj.turn_on()
        else: print("VERBOSE", f"Ignoring device without valid object '{device}'")
    return messagetypes.Reply(f"Turned on {len(found_devices)} devices")

def turn_off_device(arg, argc):
    if (response := _check_input(arg, argc)) is not None: return response

    found_devices = _get_device_data_for_name(arg[0])
    if not found_devices: return messagetypes.Reply(f"No devices or groups found with name '{arg[0]}'")

    for device in found_devices:
        global devices
        device_obj = devices.get(device)
        if device_obj: device_obj.turn_off()
    return messagetypes.Reply(f"Turned off {len(found_devices)} devices")

def get_statistics(arg, argc):
    if (response := _check_input(arg, argc)) is not None: return response

    name = arg[0]
    global devices
    device_obj = devices.get(name)
    if not device_obj: return messagetypes.Reply(f"No devices found with name '{name}'")

module.commands = {
    "home": {
        "setup": do_initial_setup,
        "load": load_devices,
        "info": get_statistics,
        "on": turn_on_device,
        "off": turn_off_device,
    },
}

@module.Initialize
def initialize():
    module.configuration.get_or_create("tuya_credentials", {"client_id":"", "client_secret":"", "client_region": "eu"})
    device_groups = module.configuration.get_or_create_configuration("device_groups", {})
    device_groups.default_value = {"devices": []}
