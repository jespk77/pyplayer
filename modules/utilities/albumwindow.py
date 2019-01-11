from ui import pywindow, pyelement
import json

album_format = "albums/{}.{}"
class AlbumWindow(pywindow.PyWindow):
	def __init__(self, master, command_callback, album_file):
		pywindow.PyWindow.__init__(self, master, "album_window")
		with open(album_format.format(album_file, "json"), "r") as file: self._metadata = json.load(file)

		self.icon = "assets/blank"
		self.transient = True
		self.title = "Album: {}".format(self._metadata["name"])
		self.set_widget("artist", pyelement.PyTextlabel(self.window)).display_text = "{}: {}".format(self._metadata["artist"], self._metadata["name"])
		self.set_widget("release_date", pyelement.PyTextlabel(self.window), row=1).display_text = "Released {}".format(self._metadata["release_date"])
		items = pyelement.PyItemlist(self.window)
		items.itemlist = self._metadata["songlist"]
		items.bind("<Double-Button-1>", self._callback)
		items.bind("<Button-1>", lambda e: self.block_action())
		self.set_widget("songlist", items, row=2)
		bt = pyelement.PyButton(self.window)
		bt.command = self._callback
		bt.text = "Queue all"
		self.set_widget("action_queue", bt, row=3)

		self._cb = command_callback
		self._path = self._metadata["song_path"]
		self.row_options(2, weight=1)
		self.column_options(0, weight=5, minsize=200)

		import os
		img_path = album_format.format(self._metadata["image"], "png")
		if os.path.exists(img_path):
			img = pyelement.PyImage(file=img_path)
			cover = pyelement.PyTextlabel(self.window)
			cover.image = img
			self.set_widget("cover", cover, column=1, rowspan=4)
			self.column_options(1, weight=1, minsize=100)
		else: print("ERROR", "No image found: '{}'".format(album_format.format(self._metadata["image"], "png")))

	def _callback(self, event=None):
		if callable(self._cb):
			if event: self._cb("player", [self.widgets["songlist"].get_item_from_event(event)])
			else: self._cb("queue", self.widgets["songlist"].itemlist)
		else: print("WARNING", "No (valid) callback was bound to the album window")


class AlbumWindowInput(pywindow.PyWindow):
	def __init__(self, master):
		pywindow.PyWindow.__init__(self, master, "album_input")
		self.set_widget("input_artist", pyelement.PyTextInput(self.window))
		self.set_widget("input_name", pyelement.PyTextInput(self.window), row=1)
		self.set_widget("input_release_date", pyelement.PyTextInput(self.window), row=2)
		self.set_widget("input_songlist", pyelement.PyTextfield(self.window), row=3)
		self.set_widget("input_image", pyelement.PyTextInput(self.window), row=4)

		self.icon = "assets/blank"
		self.title = "Create new album..."
		self.row_options(3, weight=1)