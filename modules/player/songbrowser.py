from collections import Counter
from ui.qt import pyelement
import os

def get_songlist(path): return [os.path.splitext(entry.name)[0] for entry in os.scandir(path) if entry.is_file()]

class SongBrowser(pyelement.PyItemlist):
	""" Can list all items (songs) from a directory in a specified order
		possible orderings: frequency(counter), creation time, name
	"""
	def __init__(self, client):
		pyelement.PyItemlist.__init__(self, client, "songbrowser")
		self._path = self._songcounter = None
		self._path_valid = self._is_dynamic = False

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
			self.set_selection(index)
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