from ui import pywindow, pyelement
from PIL.ImageTk import PhotoImage

initial_cfg = { "emote_button": { "background": "gray25", "foreground": "white" } }
img_height, img_width = 30,30

class TwitchEmoteWindow(pywindow.PyWindow):
	def __init__(self, root, click_callback):
		if not callable(click_callback): raise TypeError("Button callback must be callable!")

		pywindow.PyWindow.__init__(self, root, "twitch_emotelist", initial_cfg)
		self.transient = True
		self.title = "Twitch Emotes"
		self.root.protocol("WM_DELETE_WINDOW", self.on_destroy)
		self._emote_callback = click_callback

	def add_emote_button(self, emote_name, emote_img):
		if not isinstance(emote_img, PhotoImage): raise TypeError("Emote image must be a PyImage, not " + type(emote_img).__name__)

		if emote_name not in self.widgets:
			emote_button = pyelement.PyButton(self)
			emote_button.configuration = self["emote_button"]
			emote_button.configure(width=img_width, height=img_height)
			emote_button.configure(image=emote_img, command=lambda: self._emote_callback(emote_name))
			return self.add_widget(emote_name, emote_button, disable_packing=True)

	def on_destroy(self):
		self.hidden = True
		return self.block_action