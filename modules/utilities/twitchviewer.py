import requests

from ui import pywindow, pyelement
from modules.utilities import twitchchat, twitchemotelist

initial_cfg = { "autosave_delay": 5, "chat_input": {"background": "gray3", "foreground": "white", "font":{"family": "segoeui", "size": 10, "slant": "italics"}},
				"chat_limit": 300, "message_blacklist": [], "chat_viewer": {"background": "gray3", "foreground": "white", "font":{"family": "segoeui", "size": 10},
																			"notice.foreground": "gray50", "deleted.foreground": "gray75"}}

class TwitchViewer(pywindow.PyWindow):
	channel_meta_url = "https://api.twitch.tv/kraken/channels/{channel}?client_id={client_id}"
	chat = twitchchat.TwitchChat

	def __init__(self, parent, channel, command_callback, limited_mode=False):
		if not callable(command_callback): raise TypeError("Command callback must be callable")
		pywindow.PyWindow.__init__(self, parent, id="Twitch", initial_cfg=initial_cfg)
		self.title = "TwitchViewer"
		self.channel = channel
		self.always_on_top = True
		self.icon = "assets/icon_twitchviewer"

		login = self["account_data"]
		if login is not None:
			print("INFO", "Getting metadata for channel", channel)
			self._channel_meta = requests.get(self.channel_meta_url.format(channel=channel, client_id=login["client-id"])).json()
			self.error = self._channel_meta["error"] if "error" in self._channel_meta else None
		else: self.error = "No login information specified"

		if self.error is None:
			print("INFO", "no errors, starting chat...")
			self.bind("<Destroy>", self.disconnect)
			chat = TwitchViewer.chat(self, limited_mode)
			chat.command_callback = command_callback
			self.add_widget("chat_viewer", chat, disable_packing=True, fill="both", expand=True)

			chatter = twitchchat.TwitchChatTalker(self, self.widgets["chat_viewer"].send_message)
			chatter.pack_propagate(0)
			self.add_widget("chat_input", chatter, disable_packing=True, fill="x")

			emotelist_toggle = pyelement.PyButton(self)
			emotelist_toggle.pack_propagate(0)
			emotelist_toggle.configure(text="Emote List [COMING SOON]", command=self.on_emotelist_toggle)
			emotelist_toggle.configure(state="disabled")
			self.add_widget("emote_toggle", emotelist_toggle, fill="x", side="bottom")

			chatter.pack(fill="x", side="bottom")
			chat.pack(fill="both", expand=True)
			self.set_title()
			self.start()
		else:
			self.label = pyelement.PyTextlabel(self)
			self.label.display_text = "Error getting metadata for '{}': {}".format(channel, self.error)

	def on_emotelist_toggle(self):
		if not "emotelist" in self.children:
			chat = self.widgets["chat_viewer"]
			emotes = twitchemotelist.TwitchEmoteWindow(self, self.on_emoteclick)
			cont = 0
			for emote_name, emote_id in chat.emotemap_cache.items():
				if cont == 30: break
				else: cont += 1

				try:
					button = emotes.add_emote_button(emote_name, chat.get_emoteimage_from_cache(emote_id))
					button.grid(row=1, column=cont, sticky="nwes")
				except Exception as e: print("ERROR", "Couldn't create image from emote name", emote_name, "and id", emote_id, "->", e)
			self.add_window("emotelist", emotes)
		else: self.children["emotelist"].toggle_hidden()

	def on_emoteclick(self, emote_name):
		self.widgets["chat_input"].add_emote(emote_name)

	def set_title(self):
		title = self._channel_meta["display_name"]
		if self._channel_meta["status"] is not None:
			title += " - " + self._channel_meta["status"]
			if self._channel_meta["game"] is not None: title += " [" + self._channel_meta["game"] + "]"
		else: title = "TwitchViewer - " + title
		self.title = title

	def start(self):
		chat = self.widgets["chat_viewer"]
		chat.connect(self._channel_meta, login=self["account_data"])
		self.after(.5, chat.run)

	def disconnect(self, event):
		self.widgets["chat_viewer"].disconnect()
		self.write_configuration()