from utilities import messagetypes
from modules.utilities import twitchviewer

# DEFAULT MODULE VARIABLES
priority = 5
interpreter = None
client = None

# MODULE COMMANDS
def command_twitch(arg, argc, limit=False):
	if argc == 1:
		viewer = client.add_window("twitchviewer", twitchviewer.TwitchViewer(client, arg[0], interpreter.put_command, limit))
		return messagetypes.Reply("Twitch viewer for '{}' started".format(viewer.channel))

def command_twitch_limited(arg, argc):
	return command_twitch(arg, argc, limit=True)

def command_twitch_resetcache(arg, argc):
	if argc == 0:
		twitchviewer.reset_twitch_cache()
		return messagetypes.Reply("Twitch cache will be regenerated")

def command_twitch_say(arg, argc):
	if argc > 0:
		viewer = client.children.get("twitchviewer")
		if viewer is not None:
			viewer.widgets["chat_viewer"].send_message(" ".join(arg))
			return messagetypes.Reply("Message sent")
		return messagetypes.Reply("No twitch viewer open")

commands = {
	"twitch": {
		"": command_twitch,
		"reset_cache": command_twitch_resetcache,
		"limited": command_twitch_limited,
		"say": command_twitch_say
	}
}