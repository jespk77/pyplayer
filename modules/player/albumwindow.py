import json, os

from ui.qt import pyimage, pywindow, pyelement
from core import messagetypes, modules
module = modules.Module(__package__)

media_player = None
album_folder = "albums"
album_format = album_folder + "/{}.{}"

class AlbumWindow(pywindow.PyWindow):
	default_id = "album_window"

	def __init__(self, master, command_callback, album_data):
		self._metadata = album_data
		pywindow.PyWindow.__init__(self, master, self.default_id)
		self.icon = "assets/icon_album"
		self.title = "Album: {} - {}".format(self._metadata["artist"], self._metadata["name"])

		self._cb = command_callback
		self._path = self._metadata["song_path"]
		self.layout.row(2, weight=1).column(0, weight=5)

		img_path = self._metadata["image"]
		if len(img_path.split("/")) == 1: img_path = "images/" + img_path

		if os.path.exists(album_format.format(img_path, "png")):
			cover = pyelement.PyTextLabel(self, "cover")
			pyimage.PyImage(cover, file=album_format.format(self._metadata["image"], "png"))
			cover.set_alignment("center")
			self.add_element(element=cover, column=1, rowspan=4)
			self.layout.column(1, weight=1, minsize=100)
		else: print("ERROR", f"No image found: '{album_format.format(self._metadata['image'], 'png')}'")

	def create_widgets(self):
		lbl = self.add_element("artist", element_class=pyelement.PyTextLabel)
		lbl.display_text = f"{self._metadata['artist']}: {self._metadata['name']}"
		lbl.set_alignment("centerH")
		lbl = self.add_element("release_date", element_class=pyelement.PyTextLabel, row=1)
		lbl.display_text = "Released {}".format(self._metadata["release_date"])
		lbl.set_alignment("centerH")

		items = pyelement.PyItemlist(self, "songlist")
		items.itemlist = self._metadata["songlist"]
		@items.events.EventDoubleClick
		def _double_click(): self._cb("player", [self["songlist"].selected_item])
		self.add_element(element=items, row=2)

		bt = pyelement.PyButton(self, "action_queue")
		@bt.events.EventInteract
		def _queue_all(): self._cb("queue", self["songlist"].itemlist)
		bt.text = "Queue all"
		self.add_element(element=bt, row=3)


class AlbumWindowInput(pywindow.PyWindow):
	default_id = "album_input"
	def __init__(self, master, album_file=None, autocomplete_callback=None):
		self._autocomplete_cb = autocomplete_callback
		self._dt = None
		if album_file:
			try:
				with open(album_folder + "/" + album_file) as file: self._dt = json.load(file)
			except FileNotFoundError: pass
		if self._dt is None: self._dt = {}

		pywindow.PyWindow.__init__(self, master, self.default_id)
		self.icon = "assets/icon_album"
		self.title = "Album Creator"
		self.layout.row(3, weight=1)

	def create_widgets(self):
		inpt = pyelement.PyTextInput(self, "input_artist")
		inpt.value = self._dt.get("artist", "")
		inpt.events.EventInteract(self._reset_button)
		self.add_element("artist_label", element_class=pyelement.PyTextLabel).display_text = "Artist:"
		self.add_element(element=inpt, column=1)

		inpt = pyelement.PyTextInput(self, "input_name")
		inpt.value = self._dt.get("name", "")
		inpt.events.EventInteract(self._reset_button)
		self.add_element("name_label", element_class=pyelement.PyTextLabel, row=1).display_text = "Album:"
		self.add_element(element=inpt, row=1, column=1)

		inpt = pyelement.PyTextInput(self, "input_release_date")
		inpt.value = self._dt.get("release_date", "")
		inpt.events.EventInteract(self._reset_button)
		self.add_element("release_label", element_class=pyelement.PyTextLabel, row=2).display_text = "Release date:"
		self.add_element(element=inpt, row=2, column=1)

		inpt = pyelement.PyTextInput(self, "input_song_path")
		inpt.value = self._dt.get("song_path", self.parent.configuration.get("default_directory", ""))
		inpt.events.EventInteract(self._reset_button)
		self.add_element("song_path", element_class=pyelement.PyTextLabel, row=3).display_text = "Song path:"
		self.add_element(element=inpt, row=3, column=1)

		inpt = pyelement.PyTable(self, "input_songlist")
		inpt.dynamic_rows = inpt.row_header = True
		inpt.column_width = 500
		songlist = self._dt.get("songlist", [])
		for i in range(len(songlist)): inpt.set(i, 0, songlist[i])
		inpt.events.EventInteract(self._autocomplete_line)

		self.add_element("songlist_label", element_class=pyelement.PyTextLabel, row=4).display_text = "Song list:"
		self.add_element(element=inpt, row=4, column=1)

		inpt = pyelement.PyTextInput(self, "input_image")
		inpt.value = self._dt.get("image", "")
		inpt.events.EventInteract(self._reset_button)
		self.add_element("image_label", element_class=pyelement.PyTextLabel, row=5).display_text = "Cover image:"
		self.add_element(element=inpt, row=5, column=1)

		self.layout.column(0, minsize=30).column(1, weight=1).row(4, weight=1)
		for i in range(5): self.layout.row(i, minsize=30)

		bt = pyelement.PyButton(self, "confirm_write")
		bt.events.EventInteract(self.write_file)
		self.add_element(element=bt, row=6, columnspan=2)
		self._reset_button()

	@property
	def status_display(self): return self["confirm_write"].text
	@status_display.setter
	def status_display(self, vl): self["confirm_write"].text = str(vl)

	def _reset_button(self):
		self.status_display = "Save & Close"
		self["confirm_write"].accept_input = True

	def _autocomplete_line(self, row, column, new_value):
		self._reset_button()
		if new_value and self._autocomplete_cb:
			try:
				sg = self._autocomplete_cb(self["input_song_path"].value, new_value)
				if sg: self["input_songlist"].set(row, column, sg[0])
			except Exception as e: print("ERROR", f"Trying to autocomplete '{new_value}':", e)

	def _warn_missing_fields(self, text):
		print("INFO", "Tried to save information but failed to fill required fields")
		wd = self["confirm_write"]
		wd.text = text
		wd.accept_input = False

	def write_file(self):
		import os
		if not os.path.isdir("albums"): os.mkdir("albums")
		filename = album_format.format(self["input_name"].value.lower().replace(' ', '_'), "json")

		print("INFO", "Processing album information")
		wd = self["confirm_write"]
		try:
			self._dt["artist"] = self["input_artist"].value
			if not self._dt["artist"]: return self._warn_missing_fields("Missing artist name")
			self._dt["name"] = self["input_name"].value
			if not self._dt["name"]: return self._warn_missing_fields("Missing album name")
			self._dt["release_date"] = self["input_release_date"].value
			self._dt["song_path"] = self["input_song_path"].value
			if not self._dt["song_path"]: return self._warn_missing_fields("Missing song path")
			self._dt["songlist"] = self["input_songlist"].get(column=0)
			if not self._dt["songlist"] or not self._dt["songlist"][0]: return self._warn_missing_fields("Album must contain at least one song")
			self._dt["image"] = os.path.join("images", self["input_image"].value)

			with open(filename, "w") as file:
				print("VERBOSE", f"Writing album info to '{filename}'")
				import json
				json.dump(self._dt, file, indent=5)
				self.destroy()

		except Exception as e:
			print("ERROR", f"Writing album data {self._dt} to file:", e)
			wd.text = "An error occured"
			wd.accept_input = False


class AlbumBrowser(pywindow.PyWindow):
	default_id = "album_browser"
	def __init__(self, parent):
		self._albums = {}
		for album in album_list():
			with open(os.path.join(album_folder, album[1]), "r") as file:
				data = json.load(file)
				data["command_name"] = album[0]
				data["file"] = album[1]
				self._albums[AlbumBrowser._display_from_data(data)] = data

		pywindow.PyWindow.__init__(self, parent, self.default_id)
		self.title = "Album Browser"
		self.icon = "assets/icon_album"
		self.layout.row(1, weight=1, minsize=100).column(0, weight=1)

	@staticmethod
	def _display_from_data(album_data): return f"{album_data['artist']} - {album_data['name']}"

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		lbl = self.add_element("header", element_class=pyelement.PyTextLabel, columnspan=3)
		lbl.text = "Saved albums:"
		lbl.set_alignment("center")

		album_items = self.add_element("album_items", element_class=pyelement.PyItemlist, row=1, columnspan=3)
		album_items.itemlist = [item for item in self._albums.keys()]
		album_items.events.EventDoubleClick(self._select_album)

		new_album = self.add_element("new_album", element_class=pyelement.PyButton, row=2)
		new_album.text = "Add new..."
		new_album.events.EventInteract(self._add_album)

		edit_album = self.add_element("edit_album", element_class=pyelement.PyButton, row=2, column=1)
		edit_album.text = "Edit selected"
		edit_album.events.EventInteract(self._edit_album)

		remove_album = self.add_element("remove_album", element_class=pyelement.PyButton, row=2, column=2)
		remove_album.text = "Remove selected"
		remove_album.events.EventInteract(self._remove_album)

	def _select_album(self, element=None):
		if element is None: element = self["album_items"]
		item = element.selected_item
		if item:
			print("VERBOSE", f"Loading album '{item}'...")
			data = self._albums[item]
			command_album([data['command_name']], 1)
			self.destroy()

	def _add_album(self):
		command_album_add(None, 0)
		self.destroy()

	def _edit_album(self):
		item = self["album_items"].selected_item
		if item:
			print("VERBOSE", f"Editing album '{item}'...")
			data = self._albums[item]
			self.parent.add_window(window_class=AlbumWindowInput, album_file=data['file'], autocomplete_callback=get_songmatches)
			self.destroy()

	def _remove_album(self):
		album_items = self["album_items"]
		item = album_items.selected_item
		if item:
			print("VERBOSE", f"Removing album '{item}'...")
			data = self._albums[item]
			try: os.remove(os.path.join(album_folder, data['file']))
			except FileNotFoundError: pass
			except Exception as e: print("ERROR", f"Removing album '{item}':", e)

			try:
				del self._albums[item]
				album_items.itemlist = [item for item in self._albums.keys()]
			except KeyError: pass


# === Utilities ===
def initialize(player):
	global media_player
	media_player = player
	if not os.path.isdir(album_folder): os.mkdir(album_folder)

def get_songmatches(path, keyword):
	if not path: return None
	ls = media_player.find_song(path=module.configuration["directory"].get(path)["$path"], keyword=keyword.split(" "))
	if len(ls) == 1: return ls[0]
	else: return None

def load_album_data(album_file):
	with open(album_format.format(album_file, "json"), "r") as file:
		return json.load(file)

def album_list(keyword=""):
	try:
		with os.scandir(album_folder) as album_dir:
			return [(os.path.splitext(f.name)[0], f.name) for f in album_dir if f.is_file() and keyword in f.name]
	except FileNotFoundError: return []

def album_process(type, songs):
	for s in songs: module.interpreter.put_command("{} {} {}.".format(type, "music", s.replace(" - ", " ")))

# === Album commands ===
def command_album(arg, argc):
	if argc > 0:
		try: meta = load_album_data("_".join(arg))
		except FileNotFoundError: return messagetypes.Reply("Unknown album")

		module.client.add_window(window_class=AlbumWindow, command_callback=album_process, album_data=meta)
		return messagetypes.Reply("Album opened")
	else:
		module.client.add_window(window_class=AlbumBrowser)
		return messagetypes.Reply("Album browser opened")

def command_album_add(arg, argc, display=None, album=None):
	if argc > 0 and display is album is None:
		albums = album_list(" ".join(arg))
		if albums: return messagetypes.Select("Multiple albums found", lambda d, a: command_album_add(arg, argc, display=d, album=a), albums)
		else: return messagetypes.Reply("No albums found")

	module.client.add_window(window_class=AlbumWindowInput, album_file=album, autocomplete_callback=get_songmatches)
	return messagetypes.Reply(f"Album editor for '{display}' opened" if display else "Album creator opened")

def command_album_remove(arg, argc):
	if argc > 0:
		import os
		filename = album_format.format("_".join(arg), "json")
		try: os.remove(filename)
		except FileNotFoundError: return messagetypes.Reply("Unknown album")
		return messagetypes.Reply("Album deleted")

def command_album_list(arg, argc):
	albumlist = album_list(" ".join(arg))
	if albumlist: return messagetypes.Reply("Found albums:\n  - " + "\n  - ".join([a[1] for a in albumlist]))
	else: return messagetypes.Reply("No albums found")