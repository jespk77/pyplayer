from modules.utilities.songbrowser import SongBrowser
from utilities import messagetypes, song_tracker

# DEFAULT MODULE VARIABLES
priority = 3
interpreter = None
client = None

# ===== HELPER OPERATIONS ===== #
def set_configuration(cfg):
	client.songbrowser.set_configuration(cfg.get("window", {}).get("songbrowser"))

def on_destroy(arg=None, argc=0):
	if argc == 0:
		client.songbrowser.on_destroy()
		client.console.pack_forget()
		client.console.pack(fill="both", expand=True)
		return messagetypes.Reply("Songbrowser closed")

def parse_path(arg, argc):
	dir = interpreter.configuration.get("directory", {})
	if argc > 0:
		if arg[0] in dir: return (arg[0], dir[arg[0]])
		else: return ("No directory with name: '{}'".format(arg[0]),)
	else:
		path = dir.get("default")
		if isinstance(path, str): return (path, dir[path])
		else: return ("No default directory set",)

def bind_events():
	client.songbrowser.bind_event("<Double-Button-1>", on_browser_doubleclick)
	client.songbrowser.bind_event("<Button-3>", on_browser_rightclick)

def on_browser_doubleclick(event):
	interpreter.queue.put_nowait("player {path} {song}.".format(path=client.songbrowser.path[0], song=client.songbrowser.get_song_from_event(event)))

def on_browser_rightclick(event):
	interpreter.queue.put_nowait("player queue {path} {song}.".format(path=client.songbrowser.path[0], song=client.songbrowser.get_song_from_event(event)))


# ===== MAIN COMMANDS =====
# - browser configure
def command_browser_played_month(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != interpreter.configuration.get("directory", {}).get("default"): return command_browser_name(arg, argc)

			client.console.pack_forget()
			try: client.songbrowser.on_destroy()
			except: pass
			client.console.pack(fill="both", expand=True)
			client.songbrowser = SongBrowser(client.root)
			client.songbrowser.create_list_from_frequency(path, song_tracker.get_songlist())
			client.songbrowser.set_configuration(interpreter.configuration.get("window", {}).get("songbrowser"))
			client.console.pack_forget()
			client.songbrowser.pack(fill="both", expand=True)
			client.console.pack(fill="x")
			bind_events()
			return messagetypes.Reply("Browser enabled on plays per month in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_played_all(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != interpreter.configuration.get("directory", {}).get("default"): return command_browser_name(arg, argc)

			client.console.pack_forget()
			try: client.songbrowser.on_destroy()
			except: pass
			client.console.pack(fill="both", expand=True)
			client.songbrowser = SongBrowser(client.root)
			client.songbrowser.create_list_from_frequency(path, song_tracker.get_songlist(alltime=True))
			client.songbrowser.set_configuration(interpreter.configuration.get("window", {}).get("songbrowser"))
			client.console.pack_forget()
			client.songbrowser.pack(fill="both", expand=True)
			client.console.pack(fill="x")
			bind_events()
			return messagetypes.Reply("Browser enabled on all time plays in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_recent(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			client.console.pack_forget()
			try: client.songbrowser.on_destroy()
			except: pass
			client.console.pack(fill="both", expand=True)
			client.songbrowser = SongBrowser(client.root)
			client.songbrowser.create_list_from_recent(path)
			client.songbrowser.set_configuration(interpreter.configuration.get("window", {}).get("songbrowser"))
			client.console.pack_forget()
			client.songbrowser.pack(fill="both", expand=True)
			client.console.pack(fill="x")
			bind_events()
			return messagetypes.Reply("Browser enabled on recent songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_name(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			client.console.pack_forget()
			try: client.songbrowser.on_destroy()
			except: pass
			client.console.pack(fill="both", expand=True)
			client.songbrowser = SongBrowser(client.root)
			client.songbrowser.create_list_from_name(path)
			client.songbrowser.set_configuration(interpreter.configuration.get("window", {}).get("songbrowser"))
			client.console.pack_forget()
			client.songbrowser.pack(fill="both", expand=True)
			client.console.pack(fill="x")
			bind_events()
			return messagetypes.Reply("Browser enabled for songs in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser(arg, argc):
	sorting = interpreter.configuration.get("songbrowser", {}).get("default-sort")
	if isinstance(sorting, str):
		if sorting in commands["browser"]: return commands["browser"][sorting](arg, argc)
		else: return messagetypes.Reply("Invalid default sorting set in configuration '{}'".format(sorting))
	return messagetypes.Reply("No default sorting set {songbrowser::default-sort} and none or invalid one specified")

commands = {
	"browser": {
		"": command_browser,
		"none": on_destroy,
		"name": command_browser_name,
		"played-month": command_browser_played_month,
		"played": command_browser_played_all,
		"recent": command_browser_recent
	}
}