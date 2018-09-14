import os

from utilities import messagetypes
from modules.utilities.twitchviewer import TwitchViewer

# DEFAULT MODULE VARIABLES
priority = 5
interpreter = None
client = None

# MODULE COMMANDS
def command_twitch(arg, argc, limit=False):
	if argc == 1:
		viewer = client.add_window("twitchviewer", TwitchViewer(client, arg[0], interpreter.put_command, limit))
		return messagetypes.Reply("Twitch viewer for '{}' started".format(viewer.channel))

def command_twitch_limited(arg, argc):
	return command_twitch(arg, argc, limit=True)

def command_twitch_clearcache(arg, argc):
	if argc == 0:
		if "twitchviewer" in client.children: return messagetypes.Reply("I wouldn't do that while the viewer is open")

		try: os.remove(TwitchViewer.chat.emotemap_cache_file)
		except FileNotFoundError: pass
		except Exception as e: return messagetypes.Error(e, "Cannot remove cache")
		return messagetypes.Reply("Cache file deleted")

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
		"clear_cache": command_twitch_clearcache,
		"limited": command_twitch_limited,
		"say": command_twitch_say
	}
}