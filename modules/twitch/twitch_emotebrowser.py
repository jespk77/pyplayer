from ui import pywindow, pycontainer, pyelement

from modules.twitch.twitch_window import CLIENT_ID
emoteset_url = "https://api.twitch.tv/kraken/chat/emoticon_images?emotesets={}"
request_header = {"Client-ID": CLIENT_ID, "Accept": "application/vnd.twitchtv.v5+json"}

from collections import namedtuple
SetData = namedtuple("SetData", ["code", "id"])

from threading import Thread
class _EmotesetFetch(Thread):
	def __init__(self, emote_cache, sets):
		self._cache = emote_cache
		self._sets = sets
		Thread.__init__(self, name="EmotesetFetchThread")

	def start(self, done_cb=None):
		self._donecb = done_cb
		Thread.start(self)

	def run(self):
		print("INFO", "Started fetching task for sets:", self._sets)
		import requests
		r = requests.get(emoteset_url.format(",".join([s for s in self._sets])), headers=request_header)
		data = None
		if r.status_code == 200:
			try:
				data = {}
				for set_id, set_data in r.json()["emoticon_sets"].items():
					l = []
					for dt in set_data:
						sd = SetData(dt["code"], dt["id"])
						self._cache.load_image(str(sd.id))
						l.append(sd)
					data[set_id] = l
			except Exception as e: print("ERROR", "While fetching emote sets:", e)
		else: print("WARNING", "Unexpected response while fetching emote sets:", r.content)

		try: self._donecb(r.status_code, data)
		except Exception as e: print("ERROR", "While calling result callback:", e)


class TwitchEmoteBrowser(pywindow.PyWindow):
	def __init__(self, parent, emote_cache):
		pywindow.PyWindow.__init__(self, parent, "twitch_emotebrowser")
		self.title = "Twitch Emotebrowser"
		self.icon = "assets/icon_twitchviewer"

		self._emoteset = set()
		self._t = None
		self._window = parent
		self._emote_cache = emote_cache

		self._content_frame = pycontainer.PyScrollableFrame(self.content)
		self._content_frame.scrollbar_y = True
		self._content_frame.column(0, weight=1)
		self.content.place_frame(self._content_frame)
		self.content.row(0, weight=1).column(0, weight=1)


	def update_emoteset(self, emotesets):
		""" Make sure all emotes from given list are loaded, if not these are loaded asyncronously """
		emotesets = set(emotesets)
		self._load_emotesets(emotesets - self._emoteset)
		self._remove_emotesets(self._emoteset - emotesets)

	def _load_emotesets(self, sets):
		if self._t is None and sets:
			print("INFO", "New emote sets found, starting fetch task...")
			self._t = _EmotesetFetch(self._emote_cache, sets)
			self._t.start(self._done_loading)

	def _done_loading(self, status, data):
		if status == 200 and data: self.schedule(func=self._append_emotesets, data=data)
		else: print("INFO", "Skipping invalid status:", status)

	def _append_emotesets(self, data):
		self._t.join()
		self._t = None

		print("INFO", "Emote set fetching done, updating interface...")
		for row, (set_id, set_data) in enumerate(data.items()):
			browser = pycontainer.PyItemBrowser(self._content_frame.content)
			browser.min_width = browser.min_height = 40
			for sd in set_data:
				btn = pyelement.PyButton(browser, "emote_{}".format(sd.code))
				def _click(): self._on_button_click(sd)
				btn.command = _click
				btn.image = self._emote_cache.get_image(sd.id)
				browser.append_element(btn)

			self._content_frame.place_frame(browser, row=row)
			self._content_frame.row(row, weight=1)
			self._emoteset.add(set_id)

		print("INFO", "Interface updating complete, window can now be shown")
		#todo: update emote button on chat window

	def _on_button_click(self, emote_data):
		print("Clicked!", emote_data)

	def _remove_emotesets(self, sets):
		if self._t is None and sets: pass

	def destroy(self):
		if self._t: self._t.join()
		pywindow.PyWindow.destroy(self)