import requests

from ui import pywindow, pyelement
import modules.utilities.twitchchat as twitchchat

class TwitchViewer(pywindow.PyWindow):
	channel_meta_url = "https://api.twitch.tv/kraken/channels/{channel}?client_id={client_id}"

	def __init__(self, parent, channel, limited_mode=False):
		pywindow.PyWindow.__init__(self, parent, id="Twitch")
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
			self.add_widget("chat_viewer", twitchchat.TwitchChat(self, limited_mode), fill="both", expand=True)
			self.add_widget("chat_input", twitchchat.TwitchChatTalker(self, self.widgets["chat_viewer"].send_message), fill="x")
			self.set_title()
			self.start()
		else:
			self.label = pyelement.PyTextlabel(self)
			self.label.display_text = "Error getting metadata for '{}': {}".format(channel, self.error)

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