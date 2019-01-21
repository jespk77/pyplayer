import os
import requests

from modules.utilities import twitchchat, twitchemotelist
from ui import pywindow, pyelement

initial_cfg = { "account_data": {"username": "user", "client-id": "6adynlxibzw3ug8udhyzy6w3yt70pw", "oauth": "noauth"}, "autosave_delay": 5, "chat_input": {"background": "gray3", "foreground": "white", "font":{"family": "segoeui", "size": 10, "slant": "italic"}},
				"chat_limit": 300, "message_blacklist": [], "emote_toggle": {"background": "gray3", "foreground": "white"}, "enable_timestamp": "true", "enable_triggers": "false",
				"chat_viewer": {"background": "gray3", "foreground": "white", "font":{"family": "segoeui", "size": 10}, "notice.foreground": "gray50", "deleted.foreground": "gray75"}}

channel_meta_url = "https://api.twitch.tv/kraken/channels/{channel}?client_id={client_id}"
def get_meta(channel):
	return requests.get(channel_meta_url.format(channel=channel, client_id=initial_cfg["account_data"]["client-id"])).json()

class TwitchViewer(pywindow.PyWindow):
	def __init__(self, parent, channel, command_callback, limited_mode=False):
		if not callable(command_callback): raise TypeError("Command callback must be callable")
		pywindow.PyWindow.__init__(self, parent, id="Twitch_"+channel, initial_cfg=initial_cfg, cfg_file="twitch")
		self.title = "TwitchViewer"
		self.channel = channel
		self.always_on_top = True
		self.icon = "assets/icon_twitchviewer"

		if self["account_data"] is not None:
			print("INFO", "Getting metadata for channel", channel)
			self._channel_meta = get_meta(self.channel)
			error = self._channel_meta["error"] if "error" in self._channel_meta else None
		else: error = "No login information specified"

		if error is None:
			print("INFO", "no errors, starting chat...")
			if not os.path.isdir("twitch"): os.mkdir("twitch")
			self.bind("<Destroy>", self.on_destroy)

			chat = twitchchat.TwitchChat(self.frame, limited_mode)
			chat.command_callback = command_callback
			self.set_widget("chat_viewer", chat)

			chatter = twitchchat.TwitchChatTalker(self.frame, self.widgets["chat_viewer"].send_message)
			self.set_widget("chat_input", chatter, row=1)
			emotelist_window = twitchemotelist.TwitchEmoteWindow(self.frame, self.on_emoteclick, chat.emotemap_cache, chat.get_emoteimage_from_cache)

			emotelist_toggle = pyelement.PyButton(self.frame)
			emotelist_toggle.text = "Emote list loading..."
			emotelist_toggle.accept_input = False
			emotelist_toggle.callback = self.on_emotetoggle
			self.set_widget("emote_toggle", emotelist_toggle, row=2)

			self.row_options(0, weight=1)
			self.column_options(0, weight=1)
			self.open_window("emotelist", emotelist_window)
			self.set_title()
			self.start()
		else: self.set_widget("error_message", pyelement.PyTextlabel(self.frame)).display_text = "Error getting metadata for '{}': {}".format(channel, error)

	def on_emotetoggle(self): self.children["emotelist"].toggle_hidden()
	def on_emoteclick(self, emote_name): self.widgets["chat_input"].add_emote(emote_name)
	def on_emoteready(self):
		toggle = self.widgets["emote_toggle"]
		toggle.text = "Emote list"
		toggle.accept_input = True

	def set_title(self, refresh=False):
		if refresh: self._channel_meta = get_meta(self.channel)

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
		self.schedule(min=15, func=self.set_title, loop=True, refresh=True)
		self.after(.5, chat.run)

	def disconnect(self, event=None):
		self.widgets["chat_viewer"].disconnect()
		self._channel_meta = None

	def on_destroy(self, event=None):
		self.disconnect(event)
		self.write_configuration()
		self.window.destroy()