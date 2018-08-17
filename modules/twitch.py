from utilities import messagetypes
from modules.utilities.twitchviewer import TwitchViewer

# DEFAULT MODULE VARIABLES
priority = 5
interpreter = None
client = None

# MODULE COMMANDS
def command_twitch(arg, argc, limit=False):
	if argc == 1:
		viewer = client.add_window("twitchviewer", TwitchViewer(client, arg[0], limit))
		viewer.widgets["chat_viewer"].command_callback = interpreter.queue.put_nowait
		return messagetypes.Reply("Twitch viewer for '{}' started".format(viewer.channel))

def command_twitch_limited(arg, argc):
	if argc == 1: return command_twitch(arg, argc, limit=True)

def command_twitch_say(arg, argc):
	if argc > 0:
		viewer = client.children.get("twitchviewer")
		if viewer is not None:
			viewer.widgets["twitch_chat"].send_message(" ".join(arg))
			return messagetypes.Reply("Message sent")
		return messagetypes.Reply("No twitch viewer open")

commands = {
	"twitch": {
		"": command_twitch,
		"limited": command_twitch_limited,
		"say": command_twitch_say
	}
}