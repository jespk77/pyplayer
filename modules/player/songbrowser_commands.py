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
			browser.selected_index = browser.clicked_index
			interpreter.put_command(f"player {browser.path[0]} {browser.selected_item.replace(' - ', ' ')}.")

		@browser.events.EventRightClick
		def _browser_rightclick():
			interpreter.put_command(f"queue {browser.path[0]} {browser.itemlist[browser.clicked_index].replace(' - ', ' ')}.")
		browser.select_song(client.title_song)

def title_update(data, color): client["songbrowser"].select_song(data.display_name)
def unsupported_path(): print("INFO", "Tried to open songbrowser sorted on plays with unsupported path, using name sorting instead...")

# ===== Songbrowser configuration =====
_browser_types = [
	lambda browser, *args: browser.create_list_from_name(*args),
	lambda browser, *args: browser.create_list_random(*args),
	lambda browser, *args: browser.create_list_from_recent(*args),
	lambda browser, *args: browser.create_list_from_frequency(*args)
]

def set_songbrowser(browser):
	if browser:
		client.add_element(element=browser, row=2, columnspan=3)
		client.layout.row(2, weight=1, minsize=250).row(3, weight=0)
		bind_events()
	else:
		client.remove_element("songbrowser")
		client.layout.row(2, weight=0, minsize=0).row(3, weight=1)

def create_songbrowser(type, args=None):
	if type < 0: return set_songbrowser(None)

	try:
		browser_cb = _browser_types[type]
		browser = SongBrowser(client)
		browser_cb(browser, *args)

		set_songbrowser(browser)
		bind_events()
	except IndexError: pass
	except Exception as e:
		print("ERROR", "Creating songbrowser:", e)
		set_songbrowser(None)


# ===== MAIN COMMANDS =====
# - browser configure
def command_browser_played_month(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != client.configuration[default_path_key]:
				unsupported_path()
				return command_browser_name(arg, argc)

			client.schedule_task(task_id="songbrowser_create", type=3, args=(path, song_tracker.get_songlist(alltime=False)))
			return messagetypes.Reply("Browser enabled on plays per month in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_played_all(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != client[default_path_key]:
				unsupported_path()
				return command_browser_name(arg, argc)

			client.schedule_task(task_id="songbrowser_create", type=3, args=(path, song_tracker.get_songlist(alltime=True)))
			return messagetypes.Reply(f"Browser sorted on all time plays in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_recent(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			client.schedule_task(task_id="songbrowser_create", type=2, args=(path,))
			return messagetypes.Reply(f"Browser sorted on recent songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_shuffle(arg, argc):
	if argc < 1:
		path = parse_path(arg, argc)
		if len(path) == 2:
			client.schedule_task(task_id="songbrowser_create", type=1, args=(path,))
			return messagetypes.Reply(f"Browser enabled for shuffled songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_name(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			client.schedule_task(task_id="songbrowser_create", type=0, args=(path,))
			return messagetypes.Reply(f"Browser enabled for songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_remove(arg, argc):
	if argc == 0:
		client.schedule_task(task_id="songbrowser_create", type=-1)
		return messagetypes.Reply("Browser closed")

def initialize(interp, cl):
	global interpreter, client
	interpreter, client = interp, cl
	client.add_task(task_id="songbrowser_create", func=create_songbrowser)