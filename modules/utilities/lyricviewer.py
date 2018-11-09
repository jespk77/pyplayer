from ui import pywindow, pyelement

initial_cfg = { "foreground": "white", "background": "gray5" }

class LyricViewer(pywindow.PyWindow):
	def __init__(self, parent):
		pywindow.PyWindow.__init__(self, parent, id="LyricViewer")
		self.transient = True
		self.icon = "assets/blank"

		lyric = pyelement.PyTextfield(self.frame)
		lyric.accept_input = False
		lyric.bind("<Button-1>&&<B1-Motion>", self.block_action)
		lyric.configure(cursor="arrow")
		self.set_widget("lyrics", lyric, initial_cfg=initial_cfg)
		self.row_options(0, weight=1)
		self.column_options(0, weight=1)

	def load_lyrics(self, artist, title):
		import requests
		print("INFO", "Looking for lyrics for artist:'{}' and title:'{}'".format(artist, title))
		rq = requests.get("https://api.lyrics.ovh/v1/{artist}/{title}".format(artist=artist.replace(' ', '-'), title=title.replace(' ', '-')))

		try:
			result = rq.json()
			print("INFO", "Received json data: ", result.keys())
			err = result.get("error")
			if err is not None: return self.update_lyrics(err)
			else: return self.update_lyrics(result["lyrics"])
		except Exception as e:
			print("ERROR", "Decoding received data into json:", e)
			return self.update_lyrics(str(e))

	def update_lyrics(self, lyrics):
		import itertools
		self.widgets["lyrics"].text = "\n\n".join(["".join([t for t,_ in itertools.groupby(g)]) for g in lyrics.split("\n\n\n\n")])