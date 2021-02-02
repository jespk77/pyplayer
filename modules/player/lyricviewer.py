from ui.qt import pywindow, pyelement, pyworker
from core import messagetypes
import collections

client = None
main_window_id = "lyricviewer"

LyricData = collections.namedtuple("LyricData", ["artist", "title"])

def _check_lyrics(tag):
	if tag.name == "div":
		try: return ' '.join(tag["class"]) == "lyrics"
		except KeyError: pass
	return False

class LyricViewer(pywindow.PyWindowDocked):
	def __init__(self, parent, window_id):
		pywindow.PyWindowDocked.__init__(self, parent, window_id)
		self.icon = "assets/blank.png"
		self.title = "LyricViewer"
		self.add_task("set_lyrics", self._set_lyrics)

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		lyrics = self.add_element("lyrics_content", element_class=pyelement.PyTextField)
		lyrics.accept_input = False
		lyrics.text = "Loading..."

	def set_lyrics(self, data, lyrics): self.schedule_task(task_id="set_lyrics", data=data, lyrics=lyrics)
	def _set_lyrics(self, data, lyrics):
		self.title = f"LyricViewer: {data.artist} - {data.title}"
		self["lyrics_content"].text = lyrics

class TaskLyrics(pyworker.PyWorker):
	def __init__(self, artist, title):
		self._data = LyricData(artist, title)
		self._lyrics = None
		pyworker.PyWorker.__init__(self, "task_get_lyrics")

	def run(self):
		print("INFO", f"Looking for lyrics for artist:'{self._data.artist}' and title:'{self._data.title}'")
		import requests, re
		q = f"{self._data.artist} {self._data.title}"
		url = "https://genius.com/{}-lyrics".format(re.sub(r"[ =]", "-", re.sub(r"[^a-z0-9= -]", "", q, flags=re.IGNORECASE)))
		try: rq = requests.get(url)
		except Exception as e:
			print("ERROR", "Getting data from url")
			self._lyrics = str(e)
			return

		if rq.status_code == 200:
			from bs4 import BeautifulSoup
			html = BeautifulSoup(rq.content, features="html.parser")
			ls = html.find_all(_check_lyrics)
			try:
				self._lyrics = re.sub(r"<.+?>", "", str(ls[0].contents[3]), flags=re.DOTALL)
			except IndexError:
				print("INFO", "Lyrics cannot be parsed; html might have changed!")
				self._lyrics = "Lyrics not found"
		else: self._lyrics = f"Error: HTTP code {rq.status_code}"

	def complete(self):
		window = client.get_window(main_window_id)
		if window is not None: window.set_lyrics(self._data, self._lyrics)
		else: print("INFO", "Lyrics collected but no lyrics window found")

unknown_song = messagetypes.Reply("Unknown song")
def get_lyrics(song, file=None):
	artist, title = song.split(" - ", maxsplit=1)
	if artist and title:
		client.add_window(main_window_id, window_class=LyricViewer)
		TaskLyrics(artist, title)
		return messagetypes.Reply(f"Lyrics for {song} opened")
	else: return unknown_song

def command_lyrics(path, song):
	if path is not None and song is not None: return messagetypes.Select("Multiple songs found", get_lyrics, song)
	else: return unknown_song

def initialize(interp, clt):
	global client
	client = clt