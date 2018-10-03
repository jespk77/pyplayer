import requests

from ui import pywindow, pyelement
from modules.utilities import twitchchat, twitchemotelist

initial_cfg = { "account_data": {"username": "user", "access-token": "y20nzhiwuss8fmw1j2t8wh6ya3wv1x", "client-id": "6adynlxibzw3ug8udhyzy6w3yt70pw", "oauth": "noauth"},
				"autosave_delay": 5, "chat_input": {"background": "gray3", "foreground": "white", "font":{"family": "segoeui", "size": 10, "slant": "italic"}},
				"chat_limit": 300, "message_blacklist": [], "emote_toggle": {"background": "gray3", "foreground": "white"}, "enable_timestamp": "true", "enable_triggers": "false",
				"chat_viewer": {"background": "gray3", "foreground": "white", "font":{"family": "segoeui", "size": 10}, "notice.foreground": "gray50", "deleted.foreground": "gray75"}}

#TODO: make sure we're not currently loading cache
def reset_twitch_cache():
	import os
	os.remove(twitchchat.TwitchChat.emote_cache_folder)
	os.remove(twitchchat.TwitchChat.emotemap_cache_file)

class TwitchViewer(pywindow.PyWindow):
	channel_meta_url = "https://api.twitch.tv/kraken/channels/{channel}?client_id={client_id}"
	chat = twitchchat.TwitchChat

	def __init__(self, parent, channel, command_callback, limited_mode=False):
		if not callable(command_callback): raise TypeError("Command callback must be callable")
		pywindow.PyWindow.__init__(self, parent, id="Twitch_"+channel, initial_cfg=initial_cfg, cfg_file="twitch")
		self.title = "TwitchViewer"
		self.channel = channel
		self.always_on_top = True
		self.icon = "assets/icon_twitchviewer"

		login = self["account_data"]
		if login is not None:
			print("INFO", "Getting metadata for channel", channel)
			self._channel_meta = requests.get(self.channel_meta_url.format(channel=channel, client_id=login["client-id"])).json()
			error = self._channel_meta["error"] if "error" in self._channel_meta else None
		else: error = "No login information specified"

		if error is None:
			print("INFO", "no errors, starting chat...")
			self.bind("<Destroy>", self.disconnect)
			chat = TwitchViewer.chat(self, limited_mode)
			chat.command_callback = command_callback
			self.add_widget("chat_viewer", chat, disable_packing=True, fill="both", expand=True)

			chatter = twitchchat.TwitchChatTalker(self, self.widgets["chat_viewer"].send_message)
			chatter.pack_propagate(0)
			self.add_widget("chat_input", chatter, disable_packing=True, fill="x")
			emotelist_window = twitchemotelist.TwitchEmoteWindow(self, self.on_emoteclick, chat.emotemap_cache, chat.get_emoteimage_from_cache)

			emotelist_toggle = pyelement.PyButton(self)
			emotelist_toggle.text = "Emote list loading..."
			emotelist_toggle.accept_input = False
			emotelist_toggle.configure(command=self.on_emotetoggle)
			self.add_widget("emote_toggle", emotelist_toggle, fill="x", side="bottom")

			chatter.pack(fill="x", side="bottom")
			chat.pack(fill="both", expand=True)

			self.add_window("emotelist", emotelist_window)
			self.set_title()
			self.start()
		else: self.add_widget("error_message", pyelement.PyTextlabel(self)).display_text = "Error getting metadata for '{}': {}".format(channel, error)

	def on_emotetoggle(self): self.children["emotelist"].toggle_hidden()
	def on_emoteclick(self, emote_name): self.widgets["chat_input"].add_emote(emote_name)
	def on_emoteready(self):
		toggle = self.widgets["emote_toggle"]
		toggle.text = "Emote list"
		toggle.accept_input = True

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
		self.children["emotelist"].load_emotes(chat.emotemap_cache, self.on_emoteready)
		self.after(.5, chat.run)

	def disconnect(self, event=None):
		self.widgets["chat_viewer"].disconnect()
		self._channel_meta = None

	def on_destroy(self, event=None):
		self.disconnect(event)
		self.write_configuration()
		self.root.destroy()