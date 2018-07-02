from tkinter.font import Font
from collections import Counter
import tkinter, os

class SongBrowser(tkinter.Listbox):
	""" Can list all items (songs) from a directory in a specified order
		possible orderings: frequency(counter), creation time, name
	"""
	def __init__(self, client):
		self.listvar = tkinter.StringVar()
		super().__init__(client.master, listvariable=self.listvar, activestyle="none", border=0, selectmode="single")
		self.client = client
		self.font = Font(family="terminal", size=10)
		self.configure(font=self.font, highlightthickness=0)
		self._path = None
		self.path_valid = False
		self.bind("<Enter>", self.set_focus, True)
		self.bind("<Leave>", self.set_focus)

	@property
	def path(self):
		return self._path

	""" Path secifies the directory in which items need to be sorted
			this can be defined as a tuple where (displayname, path name)
			or a string to a path name (in this case the displayname is equal to path name)
	"""
	@path.setter
	def path(self, path):
		if isinstance(path, tuple) and len(path) > 1:
			self._path = (path[0], path[1] if path[1].endswith("/") else path[1] + "/")
		elif isinstance(path, str): self._path = (path, path if path.endswith("/") else path + "/")
		else: self._path = None

		self.path_valid = self._path is not None and os.path.isdir(self._path[1])
		if not self.path_valid:
			self.insert(0, "Invalid path selected: " + str(self._path))

	def select_song(self, song=None):
		if song is None: song = self.client.title_song

		index = -1
		for s in self.songlist:
			if s == song: index = max(0, index + 1); break
			else: index += 1

		if index >= 0:
			self.selection_clear(0, "end")
			self.selection_set(index)

	def set_configuration(self, configuration):
		if isinstance(configuration, dict):
			for (name, value) in configuration.items():
				try:
					name = name.split(".")
					if len(name) == 1:
						self.configure({name[0]: value})
					elif len(name) == 2:
						if name[0] == "font":
							self.font[name[1]] = value; self.configure(font=self.font)
				except Exception as e:
					print("[SongBrowser] error setting browser configuration:", e)
		else:
			print("[SongBrowser] got invalid configuration:", configuration)

	def create_list_from_frequency(self, path, songcounter):
		self.path = path
		if self.path_valid:
			self.is_dynamic = True
			self.songcounter = Counter()
			self.songlist = None
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self.songcounter[song] += songcounter[song]

			self.songlist = [i[0] for i in self.songcounter.most_common()]
			self.listvar.set(self.songlist)

	def create_list_from_recent(self, path):
		self.path = path
		if self.path_valid:
			self.is_dynamic = False
			self.songcounter = Counter()
			self.songlist = None
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self.songcounter[song] = entry.stat().st_ctime

			self.songlist = [i[0] for i in self.songcounter.most_common()]
			self.listvar.set(self.songlist)

	def create_list_from_name(self, path):
		self.path = path
		if self.path_valid:
			self.is_dynamic = False
			self.songcounter = None
			self.songlist = [os.path.splitext(entry.name)[0] for entry in os.scandir(self.path[1]) if entry.is_file()]
			self.listvar.set(self.songlist)

	def get_song_from_event(self, event):
		return self.songlist[self.nearest(event.y)].replace(" - ", " ") if self.path_valid else None

	def bind_event(self, event, callback):
		self.bind(event, callback)

	def set_focus(self, event, next=True):
		if next: event.widget.tk_focusNext().focus()
		else: event.widget.focus()

	def add_count(self, song, add=1):
		if self.path_valid:
			self.songcounter[song] += add
			self.songlist = [i[0] for i in self.songcounter.most_common()]
			self.listvar.set(self.songlist)
			self.select_song(song)
			return True
		else: return False

	def on_destroy(self):
		self.destroy()