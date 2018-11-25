from modules.utilities.songbrowser import SongBrowser
from utilities import messagetypes, song_tracker

# DEFAULT MODULE VARIABLES
priority = 3
interpreter = None
client = None

# VARIABLES SPECIFIC TO THIS MODULE
default_path_key = "default_path"
default_sort_key = "songbrowser_sorting"

# ===== HELPER OPERATIONS ===== #
def parse_path(arg, argc):
	dir = client["directory"]
	if argc > 0:
		try: return (arg[0], dir[arg[0]]["path"])
		except KeyError: return "No directory with name: '{}'".format(arg[0]),
	else:
		path = client[default_path_key]
		if path:
			try: return path, dir[path]["path"]
			except KeyError: return "Invalid default directory '{}' set".format(path),
		else: return "No default directory set, set one using key '{}'".format(default_path_key),

def bind_events():
	try: client.widgets["songbrowser"].bind("<Button-1>", client.block_action).bind("<Double-Button-1>", on_browser_doubleclick).bind("<Button-3>", on_browser_rightclick)
	except KeyError: print("ERROR", "Cannot bind events because the browser could not be found")
	client.subscribe_event("title_update", title_update)
	client.widgets["songbrowser"].select_song()

def unbind_events():
	client.unsubscribe_event("title_update", title_update)

def title_update(widget, data):
	client.widgets["songbrowser"].select_song(data.title)

def on_browser_doubleclick(event):
	interpreter.put_command("player {path} {song}.".format(path=client.widgets["songbrowser"].path[0], song=client.widgets["songbrowser"].get_song_from_event(event)))

def on_browser_rightclick(event):
	interpreter.put_command("queue {path} {song}.".format(path=client.widgets["songbrowser"].path[0], song=client.widgets["songbrowser"].get_song_from_event(event)))

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

			browser = SongBrowser(client.frame)
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

			browser = SongBrowser(client.frame)
			browser.create_list_from_frequency(path, song_tracker.get_songlist(alltime=True))
			client.set_songbrowser(browser)
			bind_events()
			return messagetypes.Reply("Browser sorted on all time plays in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_recent(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client.frame)
			browser.create_list_from_recent(path)
			client.set_songbrowser(browser)
			bind_events()
			return messagetypes.Reply("Browser sorted on recent songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_shuffle(arg, argc):
	if argc < 1:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client.frame)
			browser.create_list_random(path)
			client.set_songbrowser(browser)
			bind_events()
			return messagetypes.Reply("Browser enabled for shuffled songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_name(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client.frame)
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
	sorting = client[default_sort_key]
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