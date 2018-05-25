from tkinter.font import Font
from collections import Counter
import tkinter, os

class SongBrowser(tkinter.Listbox):
	prefix = "  "

	def __init__(self, root):
		self.root = root
		self.listvar = tkinter.StringVar()
		super().__init__(root, listvariable=self.listvar, activestyle="none", border=0, selectmode="single")
		self.font = Font(family="terminal", size=10)
		self.configure(font=self.font, highlightthickness=0)
		self.current_options = {}
		self.queue_options = {}
		self.path = None
		self.bind("<Enter>", self.set_focus, True)
		self.bind("<Leave>", self.set_focus)

	def set_path(self, path):
		try:
			if not path[1].endswith("/"):
				self.path = (path[0], path[1] + "/")
			else:
				self.path = path
		except Exception as e:
			print("got invalid path:", e)

	def check_path(self):
		if self.path is None or not os.path.isdir(self.path[1]):
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

	def create_list_from_frequency(self, path, songcounter):
		self.set_path(path)
		if self.check_path():
			self.is_dynamic = True
			self.songcounter = Counter()
			self.songlist = None
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self.songcounter[song] += songcounter[song]

			self.listvar.set([el[0] for el in self.songcounter.most_common()])

	def create_list_from_recent(self, path):
		self.set_path(path)
		if self.check_path():
			self.is_dynamic = False
			self.songcounter = Counter()
			self.songlist = None
			for entry in os.scandir(self.path[1]):
				if entry.is_file():
					song = os.path.splitext(entry.name)[0]
					self.songcounter[song] = entry.stat().st_ctime
			self.listvar.set([el[0] for el in self.songcounter.most_common()])

	def create_list_from_name(self, path):
		self.set_path(path)
		if self.check_path():
			self.is_dynamic = False
			self.songcounter = None
			self.songlist = [os.path.splitext(entry.name)[0] for entry in os.scandir(self.path[1]) if entry.is_file()]
			self.listvar.set(self.songlist)

	def get_song_from_event(self, event):
		index = self.nearest(event.y)
		if self.songlist is not None: return self.songlist[index].replace(" - ", " ")
		elif self.songcounter is not None: return self.get(index).replace(" - ", " ")

	def bind_event(self, event, callback):
		self.bind(event, callback)

	def set_focus(self, event, next=True):
		if next: event.widget.tk_focusNext().focus()
		else: event.widget.focus()

	def add_count(self, song, add=1):
		if self.is_dynamic:
			self.songcounter[song] += add
			self.listvar.set([el[0] for el in self.songcounter.most_common()])
			return True
		else: return False

	def on_destroy(self):
		self.destroy()