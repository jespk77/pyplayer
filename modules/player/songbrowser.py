import os

from collections import Counter
from ui.qt import pyelement
from core import messagetypes, modules
from modules.player import song_tracker
module = modules.Module(__package__)

# VARIABLES SPECIFIC TO THIS MODULE
default_path_key = "default_directory"
default_sort_key = "songbrowser_sorting"

def get_songlist(path): return [os.path.splitext(entry.name)[0] for entry in os.scandir(path) if entry.is_file()]
class SongBrowser(pyelement.PyItemlist):
	""" Can list all items (songs) from a directory in a specified order
		possible orderings: frequency(counter), creation time, name
	"""
	element_id = "songbrowser"

	def __init__(self, parent):
		pyelement.PyItemlist.__init__(self, parent, self.element_id)
		self._path = self._songcounter = None
		self._path_valid = self._is_dynamic = False
		self.selection_mode = "none"
		self.auto_select = False

	@property
	def path(self): return self._path
	@path.setter
	def path(self, path):
		""" Path secifies the directory in which items need to be sorted
					this can be defined as a tuple where (displayname, path name)
					or a string to a path name (in this case the displayname is equal to path name) """
		if isinstance(path, tuple) and len(path) > 1:
			self._path = (path[0], path[1] if path[1].endswith("/") else path[1] + "/")
		elif isinstance(path, str): self._path = (path, path if path.endswith("/") else path + "/")
		else: self._path = None

		self._path_valid = self._path is not None and os.path.isdir(self._path[1])
		if not self._path_valid: self.itemlist = [(0, "Invalid path selected: " + str(self._path))]

	def select_song(self, song):
		index = -1
		found = False
		for s in self.itemlist:
			if s == song: index = max(0, index + 1); found = True; break
			else: index += 1

		if found:
			self.set_selection(index=index)
			self.move_to(index)
		else: self.clear_selection()

	def create_list_from_frequency(self, path, songcounter):
		self.path = path
		if self._path_valid:
			self._is_dynamic = True
			self._songcounter = Counter()
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self._songcounter[song] += songcounter[song]
			self.itemlist = [i[0] for i in self._songcounter.most_common()]

	def create_list_from_recent(self, path):
		self.path = path
		if self._path_valid:
			self._songcounter = Counter()
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self._songcounter[song] = entry.stat().st_ctime
			self.itemlist = [i[0] for i in self._songcounter.most_common()]

	def create_list_from_name(self, path):
		self.path = path
		if self._path_valid: self.itemlist = get_songlist(path[1])

	def create_list_random(self, path):
		self.path = path
		if self._path_valid:
			sl = get_songlist(path[1])
			import random; random.shuffle(sl)
			self.itemlist = sl

	def add_count(self, song, add=1):
		if self._path_valid:
			if self._is_dynamic:
				self._songcounter[song] += add
				self.itemlist = [i[0] for i in self._songcounter.most_common()]
				self.select_song(song)
			return True
		else: return False


# ===== HELPER OPERATIONS ===== #
def parse_path(arg, argc):
	dir = module.configuration["directory"]
	if argc > 0:
		try: return arg[0], dir[arg[0]]["$path"]
		except KeyError: return f"No directory with name: '{arg[0]}'",
	else:
		path = module.configuration[default_path_key]
		if path:
			try: return path, dir[path]["$path"]
			except KeyError: return f"Invalid default directory '{path}' set",
		else: return "No default directory set"

def bind_events():
	browser = module.client["player"]["songbrowser"]
	if browser:
		@browser.events.EventDoubleClick
		def _browser_doubleclick():
			browser.selected_index = browser.clicked_index
			module.interpreter.put_command(f"player {browser.path[0]} {browser.selected_item.replace(' - ', ' ')}.")

		@browser.events.EventDoubleClickRight
		def _browser_rightclick():
			module.interpreter.put_command(f"queue {browser.path[0]} {browser.itemlist[browser.clicked_index].replace(' - ', ' ')}.")
		browser.select_song(module.client.title_song)

def title_update(data, color):
	try: module.client["player"]["songbrowser"].select_song(data.display_name)
	except KeyError: print("VERBOSE", "Failed to select the song in the browser, it's probably not currently open")
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
		module.client.layout.item(module.client.layout.index_of("console"), weight=0)
		player = module.client["player"]
		player.add_element("browser_separator", element_class=pyelement.PySeparator, row=8, columnspan=2)
		player.add_element(element=browser, row=9, columnspan=2)
		player.layout.row(9, weight=1)
		module.client["console"].max_height = 150
		module.client.layout.item(module.client.layout.index_of("player"), weight=1)
		bind_events()
	else:
		module.client.layout.item(module.client.layout.index_of("console"), weight=1)
		module.client["player"].remove_element("browser_separator")
		module.client["player"].remove_element(SongBrowser.element_id)
		module.client["console"].max_height = 0
		module.client.layout.item(module.client.layout.index_of("player"), weight=0)

def create_songbrowser(type, args=None):
	if type < 0: return set_songbrowser(None)

	try:
		browser_cb = _browser_types[type]
		browser = SongBrowser(module.client["player"])
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
			if path[0] != module.configuration[default_path_key]:
				unsupported_path()
				return command_browser_name(arg, argc)

			module.client.schedule_task(task_id="songbrowser_create", type=3, args=(path, song_tracker.get_songlist(alltime=False)))
			return messagetypes.Reply("Browser enabled on plays per month in '{}'".format(path[0]))
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_played_all(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			if path[0] != module.configuration[default_path_key]:
				unsupported_path()
				return command_browser_name(arg, argc)

			module.client.schedule_task(task_id="songbrowser_create", type=3, args=(path, song_tracker.get_songlist(alltime=True)))
			return messagetypes.Reply(f"Browser sorted on all time plays in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_recent(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			module.client.schedule_task(task_id="songbrowser_create", type=2, args=(path,))
			return messagetypes.Reply(f"Browser sorted on recent songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_shuffle(arg, argc):
	if argc < 1:
		path = parse_path(arg, argc)
		if len(path) == 2:
			module.client.schedule_task(task_id="songbrowser_create", type=1, args=(path,))
			return messagetypes.Reply(f"Browser enabled for shuffled songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_name(arg, argc):
	if argc <= 2:
		path = parse_path(arg, argc)
		if len(path) == 2:
			module.client.schedule_task(task_id="songbrowser_create", type=0, args=(path,))
			return messagetypes.Reply(f"Browser enabled for songs in '{path[0]}'")
		elif len(path) == 1: return messagetypes.Reply(path[0])

def command_browser_remove(arg, argc):
	if argc == 0:
		module.client.schedule_task(task_id="songbrowser_create", type=-1)
		return messagetypes.Reply("Browser closed")

def initialize():
	module.client.add_task(task_id="songbrowser_create", func=create_songbrowser)
	module.configuration.get_or_create(default_sort_key, "name")