from utilities import messagetypes
from modules.utilities import twitchviewer

# DEFAULT MODULE VARIABLES
priority = 5
interpreter = None
client = None

# MODULE COMMANDS
def command_twitch(arg, argc, limit=False):
	if argc == 1:
		window_id = "twitch_" + arg[0]
		rmv = client.close_window(window_id)
		if not rmv: return messagetypes.Reply("Cannot open another window for this channel because the current open window cannot be closed")

		viewer = client.open_window(window_id, twitchviewer.TwitchViewer(client.window, arg[0], interpreter.put_command, limit))
		return messagetypes.Reply("Twitch viewer for '{}' started".format(viewer.channel))

def command_twitch_limited(arg, argc):
	return command_twitch(arg, argc, limit=True)

def command_twitch_resetcache(arg, argc):
	if argc == 0:
		twitchviewer.reset_twitch_cache()
		return messagetypes.Reply("Twitch cache cleared")

def command_twitch_say(arg, argc):
	if argc > 1:
		viewer = client.children.get("twitch_" + arg[0])
		if viewer is not None:
			viewer.widgets["chat_viewer"].send_message(" ".join(arg[1:]))
			return messagetypes.Reply("Message sent")
		return messagetypes.Reply("No twitch viewer for channel '{}' open".format(arg[0]))
	elif argc == 1: return messagetypes.Reply("Name of channel to send to is required now")

commands = {
	"twitch": {
		"": command_twitch,
		"reset_cache": command_twitch_resetcache,
		"limited": command_twitch_limited,
		"say": command_twitch_say
	}
}