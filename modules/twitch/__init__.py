from utilities import messagetypes

# DEFAULT MODULE VARIABLES
interpreter = client = None

window_id = "twitch_viewer"
# MODULE COMMANDS
def command_twitch(arg, argc):
	viewer = client.get_window(window_id)
	if not viewer:
		hidden = True
		from modules.twitch import twitch_window
		viewer = twitch_window.TwitchPlayer(client)
		client.open_window(window_id, viewer)
	else: hidden = viewer.hidden

	if argc == 1:
		viewer.hidden = hidden
		viewer.open_channel(arg[0])
		return messagetypes.Reply("Twitch viewer for '{}' opened".format(arg[0]))

	elif argc == 0:
		viewer.hidden = False
		viewer.schedule(func=viewer.update_livestreams)
		return messagetypes.Reply("Twitch overview window opened")

def command_twitch_resetcache(arg, argc):
	pass

def command_twitch_say(arg, argc):
	pass

commands = {
	"twitch": {
		"": command_twitch,
		"reset": command_twitch_resetcache,
		"say": command_twitch_say
	}
}