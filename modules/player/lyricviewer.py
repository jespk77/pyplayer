from ui.tk_legacy import pywindow, pyelement

initial_cfg = { "foreground": "white", "background": "gray5" }

def _check_lyrics(tag):
	if tag.name == "div":
		try: return ' '.join(tag["class"]) == "lyrics"
		except KeyError: pass
	return False

class LyricViewer(pywindow.PyWindow):
	def __init__(self, parent):
		pywindow.PyWindow.__init__(self, parent, id="LyricViewer")
		self.transient = True
		self.icon = "assets/blank"

		lyric = pyelement.PyTextfield(self.content, "lyrics", initial_cfg=initial_cfg)
		lyric.accept_input = False
		self.content.place_element(lyric)
		self.content.row(0, weight=1).column(0, weight=1)

	def load_lyrics(self, artist, title):
		import requests, re
		print("INFO", "Looking for lyrics for artist:'{}' and title:'{}'".format(artist, title))
		q = artist + ' ' + title
		url = "https://genius.com/{}-lyrics".format(re.sub(r"[ =]", "-", re.sub(r"[^a-z0-9= -]", "", q, flags=re.IGNORECASE)))
		try: rq = requests.get(url)
		except Exception as e:
			print("ERROR", "Getting data from url")
			return self.update_lyrics(str(e))

		if rq.status_code == 200:
			from bs4 import BeautifulSoup
			html = BeautifulSoup(rq.content, features="html.parser")
			ls = html.find_all(_check_lyrics)
			try:
				ly = re.sub(r"<.+?>", "", str(ls[0].contents[3]), flags=re.DOTALL)
				self.title = "Lyrics: {} - {}".format(artist, title)
				return self.update_lyrics(ly)
			except IndexError:
				print("INFO", "Lyrics cannot be parsed; html might have changed!")
				return self.update_lyrics("Lyrics not found")
		else: return self.update_lyrics("Error: HTTP request code {}".format(rq.status_code))

	def update_lyrics(self, lyrics):
		self.content["lyrics"].text = lyrics