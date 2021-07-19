import collections
from bs4 import BeautifulSoup, element

from ui.qt import pywindow, pyelement, pyworker
from core import messagetypes, modules
module = modules.Module(__package__)

main_window_id = "lyricviewer"
LyricData = collections.namedtuple("LyricData", ["artist", "title"])

def _check_lyrics(tag):
	if tag.name == "div":
		try: return ' '.join(tag["class"]).startswith("Lyrics__Container")
		except KeyError: pass
	return False

class LyricViewer(pywindow.PyWindow):
	def __init__(self, parent, window_id):
		pywindow.PyWindow.__init__(self, parent, window_id)
		self.icon = "assets/icon"
		self.title = "LyricViewer"
		self.can_maximize = self.can_minimize = False
		self.add_task("set_lyrics", self._set_lyrics)

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		lyrics = self.add_element("lyrics_content", element_class=pyelement.PyTextField)
		lyrics.accept_input = False
		lyrics.text = "Loading..."

	def set_lyrics(self, data, lyrics): self.schedule_task(task_id="set_lyrics", data=data, lyrics=lyrics)
	def _set_lyrics(self, data, lyrics):
		self.title = f"LyricViewer: {data.artist} - {data.title}" if data is not None else "LyricViewer"
		self["lyrics_content"].text = lyrics

class TaskLyrics(pyworker.PyWorker):
	def __init__(self, artist, title):
		self._data = LyricData(artist, title)
		self._lyrics = []
		pyworker.PyWorker.__init__(self, "task_get_lyrics")

	def start(self):
		window = module.client.find_window(main_window_id)
		if window is not None: window.set_lyrics(None, "Loading...")

	def _add_element(self, item):
		if isinstance(item, element.Tag):
			if item.name == "br": self._lyrics.append("\n")
		elif isinstance(item, element.NavigableString):
			self._lyrics.append(str(item).replace("\\", ""))

	def run(self):
		print("VERBOSE", f"Looking for lyrics for artist '{self._data.artist}' and title '{self._data.title}'")
		import requests, re
		q = f"{self._data.artist} {self._data.title}"
		url = "https://genius.com/{}-lyrics".format(re.sub(r"[ =]", "-", re.sub(r"[^a-z0-9= -]", "", q, flags=re.IGNORECASE)))
		try: rq = requests.get(url)
		except Exception as e:
			print("ERROR", "Getting data from url")
			self._lyrics.append(str(e))
			return

		if rq.status_code == 200:
			html = BeautifulSoup(rq.content, features="html.parser")
			ls = html.find_all(_check_lyrics)
			try:
				for page in ls:
					page = page.contents
					for item in page:
						if isinstance(item, element.Tag) and item.name == "a":
							reference = False
							for c in item.attrs["class"]:
								if c.startswith("ReferentFragment__ClickTarget"):
									reference = True
									break

							if reference:
								for c in item.next.contents: self._add_element(c)
						else: self._add_element(item)
			except Exception as e:
				print("INFO", "Lyrics failed to parse; html might have changed:", e)
				self._lyrics.append("Error: Cannot process lyrics page")
		elif rq.status_code == "404": self._lyrics.append("Error: No lyrics found")
		else: self._lyrics.append(f"Error: HTTP code {rq.status_code}")

	def complete(self):
		window = module.client.get_window(main_window_id)
		if window is not None: window.set_lyrics(self._data, ''.join(self._lyrics))
		else: print("INFO", "Lyrics collected but no lyrics window found")

unknown_song = messagetypes.Reply("Unknown song")
def get_lyrics(song, file=None):
	artist, title = song.split(" - ", maxsplit=1)
	if artist and title:
		if not module.client.find_window(main_window_id):
			module.client.add_window(main_window_id, window_class=LyricViewer)
		TaskLyrics(artist, title)
		return messagetypes.Reply(f"Lyrics for '{song}' opened")
	else: return unknown_song

def command_lyrics(path, song):
	if path is not None and song is not None: return messagetypes.Select("Multiple songs found", get_lyrics, song)
	else: return unknown_song