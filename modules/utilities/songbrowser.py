from tkinter.font import Font
from collections import Counter
import tkinter, os

class SongBrowser(tkinter.Listbox):
	prefix = "  "

	def __init__(self, root):
		self.root = root
		super().__init__(root, activestyle="none", border=0, selectmode="single")
		self.font = Font(family="terminal", size=10)
		self.configure(font=self.font)
		self.current_options = {}
		self.queue_options = {}
		self.path = None

	def set_path(self, path):
		try:
			if not path[1].endswith("/"):
				self.path = (path[0], path[1] + "/")
			else:
				self.path = path
		except Exception as e:
			print("got invalid path:", e)

	def check_path(self):
		if self.path == None or not os.path.isdir(self.path[1]):
			self.insert("end", "Invalid path selected")
			return False
		else:
			return True

	def set_configuration(self, configuration):
		if isinstance(configuration, dict):
			for (name, value) in configuration.items():
				try:
					name = name.split(".")
					if len(name) == 1:
						self.configure({name[0]: value})
					elif len(name) == 2:
						if name[0] == "current":
							self.current_options[name[1]] = value
						elif name[0] == "queue":
							self.queue_options[name[1]] = value
						elif name[0] == "font":
							self.font[name[1]] = value; self.configure(font=self.font)
				except Exception as e:
					print("[SongBrowser] error setting browser configuration:", e)
		else:
			print("[SongBrowser] got invalid configuration:", configuration)

	def create_list_from_frequency(self, path, songlist):
		self.set_path(path)
		if self.check_path():
			self.songlist = Counter()
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self.songlist[song] = 0
			self.songlist.update(self.songlist | songlist)

			for (song, count) in self.songlist.most_common():
				self.insert("end", self.prefix + song)

	def create_list_from_recent(self, path):
		self.set_path(path)
		if self.check_path():
			self.songlist = Counter()
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self.songlist[song] = entry.stat().st_ctime

			for (song, count) in self.songlist.most_common():
				self.insert("end", self.prefix + song)

	def create_list_from_name(self, path):
		self.set_path(path)
		if self.check_path():
			self.songlist = []
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self.songlist.append(song)
					self.insert("end", self.prefix + song)

	def get_song_from_event(self, event):
		index = self.nearest(event.y)
		try: song = self.songlist.most_common()[index][0]
		except AttributeError: song = self.songlist[index]
		return song.replace(" - ", " ")

	def bind_event(self, event, callback):
		self.bind(event, callback)

	def on_destroy(self):
		self.destroy()