from ui import pywindow, pyelement
import json

album_format = "albums/{}.{}"

class AlbumWindow(pywindow.PyWindow):
	def __init__(self, master, command_callback, album_file):
		with open(album_format.format(album_file, "json"), "r") as file:
			self._metadata = json.load(file)
		pywindow.PyWindow.__init__(self, master, "album_window")

		self.icon = "assets/blank"
		self.title = "Album: {}".format(self._metadata["name"])
		self.set_widget("artist", pyelement.PyTextlabel(self.window)).display_text = "{}: {}".format(self._metadata["artist"], self._metadata["name"])
		self.set_widget("release_date", pyelement.PyTextlabel(self.window), row=1).display_text = "Released {}".format(self._metadata["release_date"])

		items = pyelement.PyItemlist(self.window)
		items.itemlist = self._metadata["songlist"]
		items.bind("<Double-Button-1>", self._callback)
		self.set_widget("songlist", items, row=2)

		bt = pyelement.PyButton(self.window)
		bt.command = self._callback
		bt.text = "Queue all"
		self.set_widget("action_queue", bt, row=3)

		self._cb = command_callback
		self._path = self._metadata["song_path"]
		self.row_options(2, weight=1)
		self.column_options(0, weight=5)

		import os
		img_path = self._metadata["image"]
		if len(img_path.split("/")) == 1: img_path = "images/" + img_path

		if os.path.exists(album_format.format(img_path, "png")):
			img = pyelement.PyImage(file=album_format.format(self._metadata["image"], "png"))
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
	def __init__(self, master, file=None):
		if file:
			with open(album_format.format(file, "json")) as file:
				self._dt = json.load(file)
		else: self._dt = {}

		pywindow.PyWindow.__init__(self, master, "album_input")
		inpt = pyelement.PyTextInput(self.window)
		inpt.value = self._dt.get("artist", "")
		inpt.command = self._reset_button
		self.set_widget("artist_label", pyelement.PyTextlabel(self.window)).display_text = "Artist:"
		self.set_widget("input_artist", inpt, column=1)

		inpt = pyelement.PyTextInput(self.window)
		inpt.value = self._dt.get("name", "")
		inpt.command = self._reset_button
		self.set_widget("name_label", pyelement.PyTextlabel(self.window), row=1).display_text = "Album:"
		self.set_widget("input_name", inpt, row=1, column=1)

		inpt = pyelement.PyTextInput(self.window)
		inpt.value = self._dt.get("release_date", "")
		inpt.command = self._reset_button
		self.set_widget("release_label", pyelement.PyTextlabel(self.window), row=2).display_text = "Release date:"
		self.set_widget("input_release_date", inpt, row=2, column=1)

		inpt = pyelement.PyTextInput(self.window)
		inpt.value = self._dt.get("song_path", "")
		inpt.command = self._reset_button
		self.set_widget("song_path", pyelement.PyTextlabel(self.window), row=3).display_text = "Song path:"
		self.set_widget("input_song_path", inpt, row=3, column=1)

		inpt = pyelement.PyTextfield(self.window)
		inpt.text = self._dt.get("songlist", [])
		inpt.command = self._reset_button
		inpt.bind("<Tab>", inpt.focus_next)
		self.set_widget("songlist_label", pyelement.PyTextlabel(self.window), row=4).display_text = "Song list:"
		self.set_widget("input_songlist", inpt, row=4, column=1)

		inpt = pyelement.PyTextInput(self.window)
		inpt.value = self._dt.get("image", "")
		inpt.command = self._reset_button
		self.set_widget("image_label", pyelement.PyTextlabel(self.window), row=5).display_text = "Cover image:"
		self.set_widget("input_image", pyelement.PyTextInput(self.window), row=5, column=1)

		self.column_options(0, minsize=30)
		self.column_options(1, weight=1)
		self.row_options(4, weight=1)
		for i in range(5): self.row_options(i, minsize=30)

		bt = pyelement.PyButton(self.window)
		bt.command = self.write_file
		self.set_widget("confirm_write", bt, row=5, columnspan=2)
		self._reset_button()

		self.icon = "assets/blank"
		self.title = "Create new album..."
		self.transient = True
		self.row_options(3, weight=1)

	@property
	def status_display(self): return self.widgets["confirm_write"].text
	@status_display.setter
	def status_display(self, vl): self.widgets["confirm_write"].text = str(vl)

	def _reset_button(self):
		self.status_display = "Save & Close"
		self.widgets["confirm_write"].accept_input = True

	def write_file(self):
		import os
		if not os.path.isdir("albums"): os.mkdir("albums")
		filename = album_format.format(self.widgets["input_name"].value.lower().replace(' ', '_'), "json")
		print("INFO", "Writing album info to '{}'".format(filename))

		wd = self.widgets["confirm_write"]
		try:
			with open(filename, "w") as file:
				self._dt["artist"] = self.widgets["input_artist"].value
				if not self._dt["artist"]: raise LookupError
				self._dt["name"] = self.widgets["input_name"].value
				if not self._dt["name"]: raise LookupError
				self._dt["release_date"] = self.widgets["input_release_date"].value
				self._dt["song_path"] = self.widgets["input_song_path"].value
				self._dt["songlist"] = self.widgets["input_songlist"].text.split("\n")
				if not self._dt["songlist"]: raise LookupError
				self._dt["image"] = self.widgets["input_image"].value

				import json
				json.dump(self._dt, file)
				self.destroy()
		except LookupError:
			print("INFO", "Tried to save information but failed to fill required fields")
			wd.text = "Missing fields"
			wd.accept_input = False

		except Exception as e:
			print("ERROR", "Writing album data {} to file:".format(self._dt), e)
			wd.text = "Error writing to file"
			wd.accept_input = False