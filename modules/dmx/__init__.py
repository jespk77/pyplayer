import json, os.path

from core import messagetypes, modules
module = modules.Module(__package__)

configuration_keys = {
    "directory": "$fixture_directory",
    "refresh_rate": "refresh_rate",
    "hardware": {
        "vendor_id": "#vendor_id",
        "product_id": "#product_id",
    },
    "advanced": {
        "baud": "baud_rate",
        "data": "data_bits",
        "stop": "stop_bit",
        "parity": "parity",
    }
}

from .dmx_controller import Connection, Device, DMXController
from .fixture import Fixture
from .fixture_data import FixtureData

module.dmx = None
module.fixtures = set()
module.fixture_types = set()
module.loaded = False

def load_fixture_type(filename):
    try:
        with open(filename, "r") as file:
            data = json.load(file)
        return FixtureData(**data)
    except Exception as e: print("ERROR", f"Loading fixture file '{filename}':", e)
module.load_fixture_type = load_fixture_type

def load_fixtures():
    device = Device(*[module.configuration[item] for item in configuration_keys['hardware'].values()])
    connection = Connection(*[module.configuration['advanced'][item] for item in configuration_keys['advanced'].values()])
    module.dmx = DMXController(device, connection, module.configuration[configuration_keys['refresh_rate']])

    module.fixture_types.clear()
    directory = module.configuration.get(configuration_keys['directory'])
    try:
        for item in os.scandir(os.path.join(directory, "types")):
            if item.is_file() and item.name.endswith(".fxt"):
                if fxt := load_fixture_type(item.path): module.fixture_types.add(fxt)
    except FileNotFoundError: pass
    print("VERBOSE", f"Loaded {len(module.fixture_types)} fixture types")

    try:
        with open(os.path.join(directory, "dmx.json"), "r") as file:
            data = json.load(file)
        module.fixtures = [Fixture(**item) for item in data.get("fixtures", [])]
    except FileNotFoundError:
        module.fixtures.clear()
    print("VERBOSE", f"Loaded {len(module.fixtures)} fixtures")
    module.loaded = True
module.load_fixtures = load_fixtures

def get_fixture_type_by_name(name):
    if not name: return None

    for item in module.fixture_types:
        if item.name == name: return item
    return None
module.get_fixture_type_by_name = get_fixture_type_by_name

def save_fixture_type(item):
    directory = os.path.join(module.configuration.get(configuration_keys['directory']), "types")
    if not os.path.isdir(directory):
        mk_path = ""
        for path in directory.split(os.sep):
            mk_path += f"{path}{os.path.sep}"
            if not os.path.isdir(mk_path): os.mkdir(mk_path)
    module.fixture_types.add(item)

    data = item.to_json()
    if len(data) > 1:
        print("VERBOSE", f"Saving fixture '{item.name}' to file...")
        with open(os.path.join(directory, f"{item.name}.fxt"), "w") as file:
            json.dump(item.to_json(), file, indent=5)
    else: print("VERBOSE", f"Skip saving fixture '{item.name}' as it has no data")
module.save_fixture_type = save_fixture_type

def save_fixtures():
    directory = module.configuration.get(configuration_keys['directory'])
    data = {
        "fixtures": [item.to_json() for item in module.fixtures]
    }

    print("VERBOSE", "Saving DMX data to file...")
    with open(os.path.join(directory, "dmx.json"), "w") as file:
        json.dump(data, file, indent=5)
module.save_fixtures = save_fixtures

def delete_fixture_type(name):
    directory = module.configuration.get(configuration_keys['directory'])
    found_fixture = None
    for item_index, data in enumerate(module.fixture_types):
        if data.name == name:
            found_fixture = data
            break

    try: module.fixture_types.remove(found_fixture)
    except KeyError: pass
    try: os.remove(os.path.join(directory, "types", f"{name}.fxt"))
    except FileNotFoundError: pass
module.delete_fixture_type = delete_fixture_type

from .control_window import DMXControlWindow

def open_dmx_control(*_):
    if not module.loaded: load_fixtures()
    module.client.schedule_task(func=lambda : module.client.add_window(window_class=DMXControlWindow))
    return messagetypes.Reply("Opened DMX control window")

from .output_window import DMXOutputWindow

def open_output_window(*_):
    if not module.loaded: load_fixtures()
    module.client.schedule_task(func=lambda : module.client.add_window(window_class=DMXOutputWindow))
    return messagetypes.Reply("Opened DMX output window")

from .setup_window import DMXSetupWindow

def open_dmx_setup(*_):
    if not module.loaded: load_fixtures()
    module.client.schedule_task(func=lambda : module.client.add_window(window_class=DMXSetupWindow))
    return messagetypes.Reply("Opened DMX setup window")

def start_dmx(*_):
    if not module.loaded: load_fixtures()
    module.dmx.start()
    return messagetypes.Reply("DMX Controller started")

def stop_dmx(*_):
    if module.dmx and module.dmx.running:
        module.dmx.stop()
        return messagetypes.Reply("DMX Controller stopped")
    else: return messagetypes.Reply("DMX Controller not running")

module.commands = {
    "dmx": {
        "control": open_dmx_control,
        "output": open_output_window,
        "setup": open_dmx_setup,
        "start": start_dmx,
        "stop": stop_dmx,
    }
}

@module.Initialize
def initialize():
    module.configuration.get_or_create(configuration_keys['directory'], "fixtures")
    module.configuration.get_or_create(configuration_keys['refresh_rate'], 1.0)
    # default settings based on Enttec OpenDMX USB
    module.configuration.get_or_create(configuration_keys['hardware']['vendor_id'], 0x0403)
    module.configuration.get_or_create(configuration_keys['hardware']['product_id'], 0x6001)
    module.configuration.get_or_create("advanced", {
        configuration_keys['advanced']['baud']: 250000,
        configuration_keys['advanced']['data']: 8,
        configuration_keys['advanced']['stop']: 2,
        configuration_keys['advanced']['parity']: "N",
    })

@module.Destroy
def destroy():
    # ensure device is closed properly when exiting
    module.dmx.stop(blocking=True)