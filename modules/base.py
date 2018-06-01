import json
from utilities import values, messagetypes

# DEFAULT MODULE VARIABLES
priority = 0
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
cfg_file = "cfg"
last_drink = 0
drink_delay = 0

def initialize():
	interpreter.configuration = load_configuration()

def load_configuration():
	try:
		print("reading configuration file:", cfg_file)
		file = open(cfg_file, "r")
		configuration = json.load(file)
		file.close()
		print("configuration file loaded as:", configuration)
		return configuration
	except Exception as e:
		print(messagetypes.Error(e).get_contents()[0])
		return {}

def save_configuration():
	print("writing configuration:", interpreter.configuration)
	file = open(cfg_file, "w")
	json.dump(interpreter.configuration, file, indent=5, sort_keys=True)
	file.close()
	print("written to file:", cfg_file)

def update_configuration(key, value=0):
	cfg = interpreter.configuration
	print("update")
	while isinstance(key, dict):
		try:
			k = next(iter(key.keys()))
			cfg = cfg.get(k, cfg)
			key = key[k]
		except: break

	if value != 0:
		if value is None:
			try: del cfg[key]
			except: pass
		elif isinstance(cfg.get(key), dict): raise TypeError("Cannot directly update dictionary to string")
		else: cfg[key] = value
	return cfg.get(key)

# ===== MAIN COMMANDS =====
# - cfg commmand
def command_cfg_get(arg, argc):
	if argc == 1:
		arg = values.parse(arg[0])
		s = update_configuration(arg.get_value())
		if s is not None: return messagetypes.Reply(str(arg) + " is set to " + str(s))

def command_cfg_reload(arg, argc):
	if argc == 0:
		interpreter.configuration = load_configuration()
		return messagetypes.Reply("Configuration file reloaded")

def command_cfg_remove(arg, argc):
	if argc == 1:
		arg = values.parse(arg[0])
		update_configuration(arg.get_value, None)
		save_configuration()
		return messagetypes.Reply("Entry " + str(arg) + " has been deleted")

def command_cfg_set(arg, argc, save=True):
	if argc == 2:
		try:
			id = values.parse(arg[0])
			s = update_configuration(id.get_value(), values.parse(arg[1]).get_value())
			interpreter.set_configuration(interpreter.configuration)
			save_configuration()
			return messagetypes.Reply(str(id) + " has been updated to '" + str(s) + "'")
		except TypeError as e: return messagetypes.Reply(str(e))

def command_timer(arg, size):
	return messagetypes.Pass()

commands = {
	"cfg": {
		"": command_cfg_get,
		"reload": command_cfg_reload,
		"remove": command_cfg_remove,
		"set": command_cfg_set
	}, "timer": command_timer
}