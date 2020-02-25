from modules.songbrowser.songbrowser_element import SongBrowser
from utilities import messagetypes, song_tracker

# DEFAULT MODULE VARIABLES
interpreter = client = None

# VARIABLES SPECIFIC TO THIS MODULE
default_path_key = "default_path"
default_sort_key = "songbrowser_sorting"
element_id = "songbrowser"

# ===== HELPER OPERATIONS ===== #
def parse_path(arg, argc):
	dir = client.configuration["directory"]
	if argc > 0:
		try: return (arg[0], dir[arg[0]]["path"])
		except KeyError: return "No directory with name: '{}'".format(arg[0]),
	else:
		path = client.configuration[default_path_key]
		if path:
			try: return path, dir[path]["path"]
			except KeyError: return "Invalid default directory '{}' set".format(path),
		else: return "No default directory set, set one using key '{}'".format(default_path_key),

def bind_events():
	browser = client.content[element_id]
	if browser:
		@browser.event_handler.MouseClickEvent("left", doubleclick=True)
		def _browser_doubleclick(y): interpreter.put_command("player {path} {song}.".format(path=client.content["songbrowser"].path[0], song=client.content["songbrowser"].get_nearest_song(y)))

		@browser.event_handler.MouseClickEvent("right")
		def _browser_rightclick(y): interpreter.put_command("queue {path} {song}.".format(path=client.widgets["songbrowser"].path[0], song=client.widgets["songbrowser"].get_nearest_song(y)))

		interpreter.register_event("media_update", title_update)
		browser.select_song(client.title_song)

def unbind_events(): interpreter.unregister_event("media_update", title_update)
def title_update(data, color): client.content[element_id].select_song(data.display_name)
def unsupported_path(): print("INFO", "Tried to open songbrowser sorted on plays with unsupported path, using name sorting instead...")

# ===== MAIN COMMANDS =====
# - browser configure
def command_browser_played_month(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != client[default_path_key]:
				unsupported_path()
				return command_browser_name(arg, argc)

			browser = SongBrowser(client.content, element_id)
			browser.create_list_from_frequency(path, song_tracker.get_songlist(alltime=False))
			client.set_songbrowser(browser)
			bind_events()
			return messagetypes.Reply("Browser enabled on plays per month in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_played_all(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != client[default_path_key]:
				unsupported_path()
				return command_browser_name(arg, argc)

			browser = SongBrowser(client.content, element_id)
			browser.create_list_from_frequency(path, song_tracker.get_songlist(alltime=True))
			client.set_songbrowser(browser)
			bind_events()
			return messagetypes.Reply("Browser sorted on all time plays in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_recent(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client.content, element_id)
			browser.create_list_from_recent(path)
			client.set_songbrowser(browser)
			bind_events()
			return messagetypes.Reply("Browser sorted on recent songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_shuffle(arg, argc):
	if argc < 1:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client.content, element_id)
			browser.create_list_random(path)
			client.set_songbrowser(browser)
			bind_events()
			return messagetypes.Reply("Browser enabled for shuffled songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_name(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client.content, element_id)
			browser.create_list_from_name(path)
			client.set_songbrowser(browser)
			bind_events()
			return messagetypes.Reply("Browser enabled for songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_remove(arg, argc):
	if argc == 0:
		client.set_songbrowser(None)
		return messagetypes.Reply("Browser closed")

def command_browser(arg, argc):
	sorting = client.configuration.get_or_create(default_sort_key, "name")
	if isinstance(sorting, str) and len(sorting) > 0:
		try: return commands["browser"][sorting](arg, argc)
		except KeyError: return messagetypes.Reply("Invalid default sorting set in configuration '{}'".format(sorting))
	return messagetypes.Reply("No default sorting set '{}' and none or invalid one specified".format(default_sort_key))

commands = {
	"browser": {
		"": command_browser,
		"none": command_browser_remove,
		"name": command_browser_name,
		"played-month": command_browser_played_month,
		"played": command_browser_played_all,
		"recent": command_browser_recent,
		"shuffle": command_browser_shuffle
	}
}