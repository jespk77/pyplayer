from modules.player.songbrowser import SongBrowser
from utilities import messagetypes, song_tracker

# DEFAULT MODULE VARIABLES
interpreter = client = None

# VARIABLES SPECIFIC TO THIS MODULE
default_path_key = "default_directory"
default_sort_key = "songbrowser_sorting"

# ===== HELPER OPERATIONS ===== #
def parse_path(arg, argc):
	dir = client.configuration["directory"]
	if argc > 0:
		try: return arg[0], dir[arg[0]]["path"]
		except KeyError: return f"No directory with name: '{arg[0]}'",
	else:
		path = client.configuration[default_path_key]
		if path:
			try: return path, dir[path]["path"]
			except KeyError: return f"Invalid default directory '{path}' set",
		else: return f"No default directory set, set one using key '{default_path_key}'",

def bind_events():
	browser = client["songbrowser"]
	if browser:
		@browser.events.EventDoubleClick
		def _browser_doubleclick():
			browser.selected_index = browser.current_index
			interpreter.put_command(f"player {browser.path[0]} {browser.selected_item}.")

		@browser.events.EventRightClick
		def _browser_rightclick():
			song = browser.itemlist[browser.current_index]
			interpreter.put_command(f"queue {browser.path[0]} {song}.")
		browser.select_song(client.title_song)

def title_update(data, color): client["songbrowser"].select_song(data.display_name)
def unsupported_path(): print("INFO", "Tried to open songbrowser sorted on plays with unsupported path, using name sorting instead...")

def set_songbrowser(browser):
	if browser:
		client.add_element(element=browser, row=2, columnspan=3)
		client.layout.row(2, weight=1, minsize=250).row(3, weight=0)
		bind_events()
	else:
		client.remove_element("songbrowser")
		client.layout.row(2, weight=0, minsize=0).row(3, weight=1)

# ===== MAIN COMMANDS =====
# - browser configure
def command_browser_played_month(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != client.configuration[default_path_key]:
				unsupported_path()
				return command_browser_name(arg, argc)

			browser = SongBrowser(client)
			browser.create_list_from_frequency(path, song_tracker.get_songlist(alltime=False))
			client.schedule_task(task_id="songbrowser_update", browser=browser)
			return messagetypes.Reply("Browser enabled on plays per month in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_played_all(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != client[default_path_key]:
				unsupported_path()
				return command_browser_name(arg, argc)

			browser = SongBrowser(client)
			browser.create_list_from_frequency(path, song_tracker.get_songlist(alltime=True))
			client.schedule_task(task_id="songbrowser_update", browser=browser)
			return messagetypes.Reply(f"Browser sorted on all time plays in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_recent(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client)
			browser.create_list_from_recent(path)
			client.schedule_task(task_id="songbrowser_update", browser=browser)
			return messagetypes.Reply(f"Browser sorted on recent songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_shuffle(arg, argc):
	if argc < 1:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client)
			browser.create_list_random(path)
			client.schedule_task(task_id="songbrowser_update", browser=browser)
			return messagetypes.Reply(f"Browser enabled for shuffled songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_name(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client)
			browser.create_list_from_name(path)
			client.schedule_task(task_id="songbrowser_update", browser=browser)
			return messagetypes.Reply(f"Browser enabled for songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_remove(arg, argc):
	if argc == 0:
		client.schedule_task(task_id="songbrowser_update", browser=None)
		return messagetypes.Reply("Browser closed")

def command_browser(arg, argc):
	sorting = client.configuration.get_or_create(default_sort_key, "name")
	if isinstance(sorting, str) and len(sorting) > 0:
		try: return commands["browser"][sorting](arg, argc)
		except KeyError: return messagetypes.Reply("Invalid default sorting set in configuration '{}'".format(sorting))
	return messagetypes.Reply("No default sorting set '{}' and none or invalid one specified".format(default_sort_key))

def initialize(interp, cl):
	global interpreter, client
	interpreter, client = interp, cl