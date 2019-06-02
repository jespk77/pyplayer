from ui import pywindow, pyelement, pyimage
from modules.twitch.twitch_window import CLIENT_ID

emote_cache = pyimage.ImageCache("emote_cache", "http://static-cdn.jtvnw.net/emoticons/v1/{key}/1.0")
bttv_emote_cache = pyimage.ImageCache("bttv_emote_cache", "https://cdn.betterttv.net/emote/{key}/1x")

badge_url = "https://api.twitch.tv/kraken/chat/{channel_name}/badges?client_id=" + CLIENT_ID
channel_badge_url = "https://badges.twitch.tv/v1/badges/channels/{channel_id}/display"
# bobross: 105458682 - own id: 61667394

def _do_request(url):
	import requests
	r = requests.get(url)
	data = r.json()
	if r.status_code == 200: return data
	else: print("ERROR", "'{}': Invalid response while requesting data:".format(url), data)

class TwitchChatViewer(pyelement.PyTextfield):
	def __init__(self, container):
		pyelement.PyTextfield.__init__(self, container, "chat_viewer")
		self.accept_input = False


class TwitchChatter(pyelement.PyTextfield):
	def __init__(self, container):
		pyelement.PyTextfield.__init__(self, container, "chatter")


class TwitchChatWindow(pywindow.PyWindow):
	def __init__(self, parent, channel, irc_client):
		pywindow.PyWindow.__init__(self, parent, "twitch_chatviewer")
		# channel: twitch_window.ChannelData(name, id)
		self._channel = channel
		# irc_client: twitch_irc.IRCClient
		self._ircclient = irc_client
		self._badge_cache = {}
		self._userstate = None
		self._msg_type_callbacks = {
			"PRIVMSG": self._on_privmsg,
			"USERSTATE": self._on_userstate
		}

		self.title = "Twitch Chat Viewer"
		self.icon = "assets/icon_twitchviewer"
		self.content.row(0, weight=1).row(1, minsize=35).column(0, weight=1)
		self._load_badges()

		self._ircclient.join_channel(self._channel.name)
		@self.event_handler.WindowDestroy
		def _on_destroy():
			print("INFO", "Window destroyed, leaving channel '{}'".format(self._channel.name))
			self._ircclient.leave_channel(self._channel.name)
		self.schedule(ms=500, func=self._poll_message, loop=True)

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		self._chat = TwitchChatViewer(self.content)
		self.content.place_element(self._chat)
		self._talker = TwitchChatter(self.content)
		self.content.place_element(self._talker, row=1)

	def _load_badges(self):
		badges = _do_request(badge_url.format(channel_name=self._channel.name))
		if badges:
			self._badge_cache["global_mod"] = badges["global_mod"]["alpha"]
			self._badge_cache["admin"] = badges["admin"]["alpha"]
			self._badge_cache["broadcaster"] = badges["broadcaster"]["alpha"]
			self._badge_cache["staff"] = badges["staff"]["alpha"]
			self._badge_cache["moderator"] = badges["mod"]["alpha"]

		channel_badges = _do_request(channel_badge_url.format(channel_id=self._channel.id))
		if channel_badges:
			badge_set = channel_badges["badge_sets"]
			sbadges = badge_set.get("subscriber")
			if sbadges:
				for version, url in sbadges["versions"].items(): self._badge_cache["subscriber/" + version] = url["image_url_1x"]

			bbadges = badge_set.get("bits")
			if bbadges:
				for version, url in bbadges["versions"].items(): self._badge_cache["bits/" + version] = url["image_url_1x"]

	def _on_privmsg(self, data):
		print("PRIVMSG", data)

	def _on_userstate(self, data):
		self._userstate = data.meta

	def _poll_message(self):
		for msg in self._ircclient.get_message(self._channel.name):
			cb = self._msg_type_callbacks.get(msg.type)
			if cb: cb(msg)