from utilities import messagetypes
from modules.twitch import twitch_window

# DEFAULT MODULE VARIABLES
interpreter = client = None

window_id = "twitch_viewer"
# MODULE COMMANDS
def command_twitch(arg, argc):
	if argc == 0:
		viewer = client.open_window(window_id, twitch_window.TwitchPlayer(client))
		return messagetypes.Reply("Twitch overview window opened")

def command_twitch_resetcache(arg, argc):
	if argc == 0:
		client.close_window(window_id)

		import shutil, os
		try: shutil.rmtree(twitchviewer.twitchchat.emote_cache_folder)
		except FileNotFoundError: pass
		try: os.remove(twitchviewer.twitchchat.emotemap_cache_file)
		except FileNotFoundError: pass
		return messagetypes.Reply("Twitch cache cleared")

def command_twitch_say(arg, argc):
	if argc > 1:
		viewer = client.children.get(window_id)
		if viewer is not None and viewer.channel.lower() == arg[0].lower():
			viewer["chat_viewer"].send_message(" ".join(arg[1:]))
			return messagetypes.Reply("Message sent")
		return messagetypes.Reply("No twitch viewer for channel '{}' open".format(arg[0]))
	elif argc == 1: return messagetypes.Reply("Name of channel to send to is required now")

commands = {
	"twitch": {
		"": command_twitch,
		"reset": command_twitch_resetcache,
		"say": command_twitch_say
	}
}