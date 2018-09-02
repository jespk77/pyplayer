from modules.utilities.songbrowser import SongBrowser
from utilities import messagetypes, song_tracker

# DEFAULT MODULE VARIABLES
priority = 3
interpreter = None
client = None

# ===== HELPER OPERATIONS ===== #
def close_browser(arg=None, argc=0):
	if argc == 0:
		client.remove_widget("songbrowser")
		return messagetypes.Reply("Songbrowser closed")

def parse_path(arg, argc):
	dir = client["directory"]
	if argc > 0:
		if arg[0] in dir: return (arg[0], dir[arg[0]])
		else: return ("No directory with name: '{}'".format(arg[0]),)
	else:
		path = dir.get("default")
		if isinstance(path, str): return (path, dir[path])
		else: return ("No default directory set",)

def bind_events():
	try: client.widgets["songbrowser"].bind("<Button-1>", block_event).bind("<Double-Button-1>", on_browser_doubleclick).bind("<Button-3>", on_browser_rightclick)
	except KeyError: print("[module.songbrowser.ERROR] Cannot bind events because the browser could not be found")
	client.subscribe_event("title_update", title_update)

def unbind_events():
	client.unsubscribe_event("title_update", title_update)

def title_update(widget, data):
	client.widgets["songbrowser"].select_song(data.title)

def on_browser_doubleclick(event):
	interpreter.put_command("player {path} {song}.".format(path=client.widgets["songbrowser"].path[0], song=client.widgets["songbrowser"].get_song_from_event(event)))

def on_browser_rightclick(event):
	interpreter.put_command("queue {path} {song}.".format(path=client.widgets["songbrowser"].path[0], song=client.widgets["songbrowser"].get_song_from_event(event)))

def block_event(event):
	return "break"

# ===== MAIN COMMANDS =====
# - browser configure
def command_browser_played_month(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != client["directory"].get("default"): return command_browser_name(arg, argc)

			browser = SongBrowser(client.root)
			browser.create_list_from_frequency(path, song_tracker.get_songlist(alltime=False))
			# TODO: fix dirty console unpack/pack
			client.widgets["console"].pack_forget()
			client.add_widget("songbrowser", browser, fill="both", expand=True)
			client.widgets["console"].pack(fill="x")
			bind_events()
			return messagetypes.Reply("Browser enabled on plays per month in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_played_all(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != client["directory"].get("default"): return command_browser_name(arg, argc)

			browser = SongBrowser(client.root)
			browser.create_list_from_frequency(path, song_tracker.get_songlist(alltime=True))
			# TODO: fix dirty console unpack/pack
			client.widgets["console"].pack_forget()
			client.add_widget("songbrowser", browser, fill="both", expand=True)
			client.widgets["console"].pack(fill="x")
			bind_events()
			return messagetypes.Reply("Browser enabled on all time plays in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_recent(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client)
			browser.create_list_from_recent(path)
			# TODO: fix dirty console unpack/pack
			client.widgets["console"].pack_forget()
			client.add_widget("songbrowser", browser, fill="both", expand=True)
			client.widgets["console"].pack(fill="x")
			bind_events()
			return messagetypes.Reply("Browser enabled on recent songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_name(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			browser = SongBrowser(client)
			# TODO: fix dirty console unpack/pack
			client.widgets["console"].pack_forget()
			client.add_widget("songbrowser", browser, fill="both", expand=True)
			client.widgets["console"].pack(fill="x")
			browser.create_list_from_name(path)
			bind_events()
			return messagetypes.Reply("Browser enabled for songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_remove(arg, argc):
	if argc == 0:
		if client.remove_widget("songbrowser"):
			# TODO: fix dirty console unpack/pack
			client.widgets["console"].pack_forget()
			client.widgets["console"].pack(fill="both", expand=True)
		return messagetypes.Reply("Browser closed")

def command_browser(arg, argc):
	sorting = client["songbrowser_sorting"]
	if isinstance(sorting, str) and len(sorting) > 0:
		if sorting in commands["browser"]: return commands["browser"][sorting](arg, argc)
		else: return messagetypes.Reply("Invalid default sorting set in configuration '{}'".format(sorting))
	return messagetypes.Reply("No default sorting set {songbrowser::default-sort} and none or invalid one specified")

commands = {
	"browser": {
		"": command_browser,
		"none": command_browser_remove,
		"name": command_browser_name,
		"played-month": command_browser_played_month,
		"played": command_browser_played_all,
		"recent": command_browser_recent
	}
}