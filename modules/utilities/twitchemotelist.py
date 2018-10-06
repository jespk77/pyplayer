from ui import pywindow, pyelement

initial_cfg = { "root": {"background": "black"}, "emote_button": { "background": "gray3", "foreground": "white" }, "emote_height": 30, "emote_width": 35, "column_size": 15 }

class TwitchEmoteWindow(pywindow.PyWindow):
	def __init__(self, root, click_callback, emote_cache, emote_callback):
		if not callable(click_callback): raise TypeError("Button callback must be callable!")
		if not callable(emote_callback): raise TypeError("Emote callback must be callable!")

		pywindow.PyWindow.__init__(self, root, "twitch_emotelist", initial_cfg)
		self.transient = True
		self.hidden = True
		self.title = "Twitch Emotes"
		self.icon = None

		self.bind("<Button-3>", self.hide_window)
		self.root.protocol("WM_DELETE_WINDOW", self.on_destroy)
		self.root.resizable(width=False, height=True)

		self._emote_count = 0
		self._click_callback = click_callback
		self._emote_callback = emote_callback

	def load_emotes(self, emote_iterator, done_callback):
		print("INFO", "Loading emotelist")
		for emote_name, emote_img in emote_iterator.items():
			self.add_emote_button(emote_name, self._emote_callback(emote_img))
			self._emote_count += 1

		print("INFO", "Finished loading emotelist")
		try: done_callback()
		except Exception as e: print("ERROR", "Cannot call emote done callback:", e)

	def add_emote_button(self, emote_name, emote_img):
		if emote_name not in self.widgets:
			emote_button = pyelement.PyButton(self)
			emote_button.has_master_configuration = False
			emote_button.configuration = self["emote_button"]
			emote_button.configure(width=self["emote_width"], height=self["emote_height"])
			emote_button.configure(image=emote_img, command=lambda: self._click_callback(emote_name))
			emote_button.grid(row=int(self._emote_count / self["column_size"]), column=(self._emote_count % self["column_size"]), sticky="news")
			return self.add_widget(emote_name, emote_button, disable_packing=True)

	def hide_window(self, event):
		self.hidden = True

	def on_destroy(self):
		self.hidden = True
		return self.block_action