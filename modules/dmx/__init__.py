import json, os.path

from core import messagetypes, modules
module = modules.Module(__package__)

fixture_folder_key = "$fixture_directory"

from .fixture_data import FixtureData

module.fixture_types = set()

def load_fixture_type(filename):
    try:
        with open(filename, "r") as file:
            data = json.load(file)
        return FixtureData(**data)
    except Exception as e: print("ERROR", f"Loading fixture file '{filename}':", e)
module.load_fixture_type = load_fixture_type

def load_fixtures():
    module.fixture_types.clear()
    directory = module.configuration.get(fixture_folder_key)
    try:
        for item in os.scandir(os.path.join(directory, "types")):
            if item.is_file() and item.name.endswith(".fxt"):
                if fxt := load_fixture_type(item.path): module.fixture_types.add(fxt)
    except FileNotFoundError: pass
    print("VERBOSE", f"Loaded {len(module.fixture_types)} fixture types")
module.load_fixtures = load_fixtures

def get_fixture_type_by_name(name):
    if not name: return None

    for item in module.fixture_types:
        if item.name == name: return item
    return None
module.get_fixture_type_by_name = get_fixture_type_by_name

def save_fixture_type(item):
    directory = os.path.join(module.configuration.get(fixture_folder_key), "types")
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
    directory = module.configuration.get(fixture_folder_key)
    for item in module.fixtures:
        save_fixture_type(item)
module.save_fixtures = save_fixtures

def delete_fixture_type(name):
    directory = module.configuration.get(fixture_folder_key)
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

from .setup_window import DMXSetupWindow

def open_dmx_setup(*_):
    load_fixtures()
    module.client.schedule_task(func=lambda : module.client.add_window(window_class=DMXSetupWindow))
    return messagetypes.Reply("Opened DMX setup window")

module.commands = {
    "dmx": {
        "setup": open_dmx_setup
    }
}

@module.Initialize
def initialize():
    module.configuration.get_or_create(fixture_folder_key, "fixtures")