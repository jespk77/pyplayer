from modules.utilities import twitchviewer
from utilities import messagetypes

# DEFAULT MODULE VARIABLES
interpreter = client = None

window_id = "twitch_viewer"
# MODULE COMMANDS
def command_twitch(arg, argc, limit=False):
	if argc == 1:
		client.close_window(window_id)
		viewer = client.open_window(window_id, twitchviewer.TwitchViewer(client.window, arg[0], interpreter.put_command, limit))
		return messagetypes.Reply("Twitch viewer for '{}' started".format(viewer.channel))

def command_twitch_limited(arg, argc):
	return command_twitch(arg, argc, limit=True)

def command_twitch_resetcache(arg, argc):
	if argc == 0:
		client.close_window(window_id)

		import shutil, os
		try: shutil.rmtree(twitchviewer.twitchchat.emote_cache_folder)
		except FileNotFoundError: pass
		try: os.remove(twitchviewer.twitchchat.emotemap_cache_file)
		except FileNotFoundError: pass
		return messagetypes.Reply("Twitch cache cleared")

def command_twitch_token(arg, argc):
	if argc == 0:
		file = open(".cfg/twitch", "r")
		import json
		js = json.load(file)
		file.close()
		js = js.get("account_data")
		return messagetypes.URL(twitchviewer.twitchchat.token_url.format(client_id=js.get("client-id")), message="Login to receive new token")

def command_twitch_say(arg, argc):
	if argc > 1:
		viewer = client.children.get(window_id)
		if viewer is not None and viewer.channel.lower() == arg[0].lower():
			viewer.widgets["chat_viewer"].send_message(" ".join(arg[1:]))
			return messagetypes.Reply("Message sent")
		return messagetypes.Reply("No twitch viewer for channel '{}' open".format(arg[0]))
	elif argc == 1: return messagetypes.Reply("Name of channel to send to is required now")

commands = {
	"twitch": {
		"": command_twitch,
		"reset": command_twitch_resetcache,
		"token": command_twitch_token,
		"limited": command_twitch_limited,
		"say": command_twitch_say
	}
}