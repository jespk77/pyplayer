import json

from ui import pywindow, pyelement, pyimage

album_folder = "albums"
album_format = album_folder + "/{}.{}"

class AlbumWindow(pywindow.PyWindow):
	def __init__(self, master, command_callback, album_file):
		with open(album_format.format(album_file, "json"), "r") as file:
			self._metadata = json.load(file)
		pywindow.PyWindow.__init__(self, master, "album_window")

		self.icon = "assets/blank"
		self.title = "Album: {} - {}".format(self._metadata["artist"], self._metadata["name"])
		self.content.place_element(pyelement.PyTextlabel(self.content, "artist")).display_text = "{}: {}".format(self._metadata["artist"], self._metadata["name"])
		self.content.place_element(pyelement.PyTextlabel(self.content, "release_date"), row=1).display_text = "Released {}".format(self._metadata["release_date"])

		items = pyelement.PyItemlist(self.content, "songlist")
		items.itemlist = self._metadata["songlist"]
		@items.event_handler.MouseClickEvent("left", doubleclick=True)
		def _double_click(y):
			self._cb("player", [self.content["songlist"].get_nearest_item(y)])
		self.content.place_element(items, row=2)

		bt = pyelement.PyButton(self.content, "action_queue")
		bt.command = lambda : self._cb("queue", self.content["songlist"].itemlist)
		bt.text = "Queue all"
		self.content.place_element(bt, row=3)

		self._cb = command_callback
		self._path = self._metadata["song_path"]
		self.content.row(2, weight=1).column(0, weight=5)

		img_path = self._metadata["image"]
		if len(img_path.split("/")) == 1: img_path = "images/" + img_path

		import os
		if os.path.exists(album_format.format(img_path, "png")):
			img = pyimage.PyImage(file=album_format.format(self._metadata["image"], "png"))
			cover = pyelement.PyTextlabel(self.content, "cover")
			cover.image = img
			self.content.place_element(cover, column=1, rowspan=4)
			self.content.column(1, weight=1, minsize=100)
		else: print("ERROR", "No image found: '{}'".format(album_format.format(self._metadata["image"], "png")))


class AlbumWindowInput(pywindow.PyWindow):
	def __init__(self, master, file=None, autocomplete_callback=None):
		self._autocomplete = autocomplete_callback
		if file:
			with open(album_folder + "/" + file) as file:
				self._dt = json.load(file)
		else: self._dt = {}

		pywindow.PyWindow.__init__(self, master, "album_input")
		inpt = pyelement.PyTextInput(self.content, "input_artist")
		inpt.value = self._dt.get("artist", "")
		inpt.command = self._reset_button
		self.content.place_element(pyelement.PyTextlabel(self.content, "artist_label")).display_text = "Artist:"
		self.content.place_element(inpt, column=1)

		inpt = pyelement.PyTextInput(self.content, "input_name")
		inpt.value = self._dt.get("name", "")
		inpt.command = self._reset_button
		self.content.place_element(pyelement.PyTextlabel(self.content, "name_label"), row=1).display_text = "Album:"
		self.content.place_element(inpt, row=1, column=1)

		inpt = pyelement.PyTextInput(self.content, "input_release_date")
		inpt.value = self._dt.get("release_date", "")
		inpt.command = self._reset_button
		self.content.place_element(pyelement.PyTextlabel(self.content, "release_label"), row=2).display_text = "Release date:"
		self.content.place_element(inpt, row=2, column=1)

		inpt = pyelement.PyTextInput(self.content, "input_song_path")
		inpt.value = self._dt.get("song_path", "")
		inpt.command = self._reset_button
		self.content.place_element(pyelement.PyTextlabel(self.content, "song_path"), row=3).display_text = "Song path:"
		self.content.place_element(inpt, row=3, column=1)

		inpt = pyelement.PyTextfield(self.content, "input_songlist")
		inpt.text = "\n".join(self._dt.get("songlist", []))
		inpt.command = self._reset_button

		@inpt.event_handler.KeyEvent("Tab")
		def _move_focus_down(): inpt.move_focus_down()
		@inpt.event_handler.KeyEvent("Enter")
		def _try_autocomplete(): self._autocomplete_line()

		self.content.place_element(pyelement.PyTextlabel(self.content, "songlist_label"), row=4).display_text = "Song list:"
		self.content.place_element(inpt, row=4, column=1)

		inpt = pyelement.PyTextInput(self.content, "input_image")
		inpt.value = self._dt.get("image", "")
		inpt.command = self._reset_button
		self.content.place_element(pyelement.PyTextlabel(self.content, "image_label"), row=5).display_text = "Cover image:"
		self.content.place_element(pyelement.PyTextInput(self.content), row=5, column=1)

		self.content.column(0, minsize=30).column(1, weight=1).row(4, weight=1)
		for i in range(5): self.content.row(i, minsize=30)

		bt = pyelement.PyButton(self.content, "confirm_write")
		bt.command = self.write_file
		self.content.place_element(bt, row=5, columnspan=2)
		self._reset_button()

		self.icon = "assets/blank"
		self.title = "Create new album..."
		self.transient = True
		self.content.row(3, weight=1)

	@property
	def status_display(self): return self.content["confirm_write"].text
	@status_display.setter
	def status_display(self, vl): self.content["confirm_write"].text = str(vl)

	def _reset_button(self):
		self.status_display = "Save & Close"
		self.content["confirm_write"].accept_input = True

	def _autocomplete_line(self):
		textfield = self.content["input_songlist"]
		line = textfield.get("insert linestart", "insert lineend")
		if line and self._autocomplete:
			try:
				sg = self._autocomplete(self.content["input_song_path"].value, line)
				if sg:
					textfield.delete("insert linestart", "insert lineend")
					textfield.insert("insert", sg[0])
			except Exception as e: print("ERROR", "Trying to autocomplete '{}':".format(line), e); raise

	def write_file(self):
		import os
		if not os.path.isdir("albums"): os.mkdir("albums")
		filename = album_format.format(self.content["input_name"].value.lower().replace(' ', '_'), "json")

		print("INFO", "Processing album information")
		wd = self.content["confirm_write"]
		try:
			self._dt["artist"] = self.content["input_artist"].value
			if not self._dt["artist"]: raise LookupError("Missing required 'Artist' field")
			self._dt["name"] = self.content["input_name"].value
			if not self._dt["name"]: raise LookupError("Missing required 'Album' field")
			self._dt["release_date"] = self.content["input_release_date"].value
			self._dt["song_path"] = self.content["input_song_path"].value
			self._dt["songlist"] = self.content["input_songlist"].text.split("\n")
			if not self._dt["songlist"] or not self._dt["songlist"][0]: raise LookupError("Missing required 'Song list' field")
			self._dt["image"] = self.content["input_image"].value
			if not self._dt["image"].startswith("/"): self._dt["image"] = "images/" + self._dt["image"]

			with open(filename, "w") as file:
				print("INFO", "Writing album info to '{}'".format(filename))
				import json
				json.dump(self._dt, file)
				self.destroy()

		except LookupError as e:
			print("INFO", "Tried to save information but failed to fill required fields")
			wd.text = "".join(e.args) if e.args else "Missing fields"
			wd.accept_input = False

		except Exception as e:
			print("ERROR", "Writing album data {} to file:".format(self._dt), e)
			wd.text = "Error writing to file"
			wd.accept_input = False