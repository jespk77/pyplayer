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

# MODULE COMMANDS
def command_twitch(arg, argc):
	global twitchviewer
	if argc == 1:
		if twitchviewer is None or not twitchviewer.is_alive:
			twitchviewer = TwitchViewer(client, get_configuration(), arg[0])
			twitchviewer.chat.set_command_queue_callback(interpreter.queue.put_nowait)
			return messagetypes.Reply("Chat viewer for '"+ arg[0] + "' started")
		else: return messagetypes.Reply("Chat viewer already open, close that one first")

def command_twitch_say(arg, argc):
	global twitchviewer
	if twitchviewer is not None and twitchviewer.is_alive:
		twitchviewer.chat.send_message(" ".join(arg))
		return messagetypes.Reply("Message sent")
	else: return messagetypes.Reply("No channel open right now")

commands = {
	"twitch": {
		"": command_twitch,
		"say": command_twitch_say
	}
}