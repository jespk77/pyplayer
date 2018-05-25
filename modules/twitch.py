import json

from utilities import messagetypes
from modules.utilities.twitchviewer import TwitchViewer

# DEFAULT MODULE VARIABLES
priority = 5
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
twitchviewer = None
twitch_cfg = "twitch_data"

# HELPER FUNCTIONS
def get_configuration():
	try:
		file = open(twitch_cfg, "r")
		cfg = json.load(file)
		file.close()
		return cfg
	except FileNotFoundError: return {}

def check_active_viewer():
	global twitchviewer
	if twitchviewer is not None and twitchviewer.is_alive: return True
	twitchviewer = None
	return False

# MODULE COMMANDS
def command_twitch(arg, argc):
	global twitchviewer
	if argc == 1:
		if not check_active_viewer():
			twitchviewer = TwitchViewer(client, get_configuration(), arg[0])
			twitchviewer.chat.set_command_queue_callback(interpreter.queue.put_nowait)
			return messagetypes.Reply("Twitch viewer for '"+ arg[0] + "' started")
		else: return messagetypes.Reply("Twitch viewer already open, close that one first")

def command_twitch_reload(arg, argc):
	if argc == 0:
		if check_active_viewer():
			twitchviewer.set_configuration(get_configuration())
			return messagetypes.Reply("Twitch configuration reloaded")
		return messagetypes.Reply("No twitch viewer open")

def command_twitch_trigger_enable(arg, argc):
	if argc == 1:
		if check_active_viewer():
			twitchviewer.chat.enable_triggers = True
			return messagetypes.Reply("Command triggers enabled")

def command_twitch_trigger_disable(arg, argc):
	if argc == 1:
		if check_active_viewer():
			twitchviewer.chat.enable_triggers = False
			return messagetypes.Reply("Command triggers disabled")

def command_twitch_say(arg, argc):
	if argc > 0:
		if check_active_viewer():
			twitchviewer.chat.send_message(" ".join(arg))
			return messagetypes.Reply("Message sent")
		return messagetypes.Reply("No twitch viewer open")

commands = {
	"twitch": {
		"": command_twitch,
		"reload": command_twitch_reload,
		"trigger": {
			"disable": command_twitch_trigger_disable,
			"enable": command_twitch_trigger_enable
		}, "say": command_twitch_say
	}
}