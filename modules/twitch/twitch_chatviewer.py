from ui import pywindow, pyelement, pyimage
from modules.twitch.twitch_window import CLIENT_ID

badge_url = "https://api.twitch.tv/kraken/chat/{channel_name}/badges?client_id=" + CLIENT_ID
channel_badge_url = "https://badges.twitch.tv/v1/badges/channels/{channel_id}/display"
emote_cache = pyimage.ImageCache("emote_cache", "http://static-cdn.jtvnw.net/emoticons/v1/{key}/1.0")

bttv_emote_list_url = "https://api.betterttv.net/2/emotes"
bttv_emote_cache = pyimage.ImageCache("bttv_emote_cache", "https://cdn.betterttv.net/emote/{key}/1x")
# bobross: 105458682 - own id: 61667394

def _do_request(url):
	import requests
	r = requests.get(url)
	data = r.json()
	if r.status_code == 200: return data
	else: print("ERROR", "'{}': Invalid response while requesting data:".format(url), data)
bttv_emote_map = {entry["code"]: entry["id"] for entry in _do_request(bttv_emote_list_url)["emotes"]}


chat_cfg = {"subnotice.background": "gray15", "subnotice.foreground": "white", "notice.foreground": "gray", "deleted.foreground": "gray15", "timestamp.foreground": "gray"}
class TwitchChatViewer(pyelement.PyTextfield):
	def __init__(self, container, window):
		pyelement.PyTextfield.__init__(self, container, "chat_viewer", initial_cfg=chat_cfg)
		self._window = window
		self.accept_input = False
		self._badge_cache = {}
		self._timestamp = None
		self._scroll_enabled = True
		@self.event_handler.MouseEnter
		def _enable_scroll(): self._scroll_enabled = False
		@self.event_handler.MouseLeave
		def _disable_scroll(): self._scroll_enabled = True
		self._load_badges()
		self.with_option(cursor="left_ptr", wrap="word", spacing1=3, padx=5)

	def _load_badges(self):
		badges = _do_request(badge_url.format(channel_name=self._window.channel_name))
		if badges:
			self._badge_cache["global_mod/1"] = badges["global_mod"]["alpha"]
			self._badge_cache["admin/1"] = badges["admin"]["alpha"]
			self._badge_cache["broadcaster/1"] = badges["broadcaster"]["alpha"]
			self._badge_cache["staff/1"] = badges["staff"]["alpha"]
			self._badge_cache["moderator/1"] = badges["mod"]["alpha"]

		channel_badges = _do_request(channel_badge_url.format(channel_id=self._window.channel_id))
		if channel_badges:
			badge_set = channel_badges["badge_sets"]
			sbadges = badge_set.get("subscriber")
			if sbadges:
				for version, url in sbadges["versions"].items(): self._badge_cache["subscriber/" + version] = url["image_url_1x"]

			bbadges = badge_set.get("bits")
			if bbadges:
				for version, url in bbadges["versions"].items(): self._badge_cache["bits/" + version] = url["image_url_1x"]

	def _get_badge(self, key):
		bg = self._badge_cache.get(key)
		if isinstance(bg, str):
			self._badge_cache[key] = pyimage.ImageData(url=bg)
			return self._badge_cache.get(key)
		elif isinstance(bg, pyimage.ImageData): return bg
		else: raise KeyError(key)

	def on_privmsg(self, meta, msg):
		if not meta or not msg: return
		#print("//", meta, "\n//", msg)

		if self.configuration.get("enable_timestamp") and self._timestamp: self.insert("end", self._timestamp.strftime("%I:%M "), ("timestamp",))
		self._insert_badges(meta.get("badges", "").split(","))
		self._insert_username(meta.get("display-name"), color=meta.get("color"))
		self._insert_message(meta, msg)
		self.see_bottom()
		self.insert("end", "\n")

	def _insert_badges(self, badges):
		for b in badges:
			if not b: continue

			try:
				self.place_image("end", self._get_badge(b))
				self.insert("end", " ")
			except KeyError as e: print("INFO", "Unknown badge:", e)
			except Exception as e: print("ERROR", "While fetching badge '{}':".format(b), e)

	def _insert_username(self, user, color=None):
		tagname = user.lower()
		if color is None:
			try: color = self.get_tag_option(tagname, "foreground")
			except KeyError:
				import random
				color = "#" + "".join("{:02x}".format(n) for n in [random.randrange(75, 255), random.randrange(75, 255), random.randrange(75, 255)])

		self.set_tag_option(tagname, foreground=color, font=self.bold_font)
		self.insert("end", user + " ", (tagname,))

	def _insert_message(self, meta, text):
		emotes = meta.get("emotes", "").split("/")
		emote_list = {}
		for emote in emotes:
			emote = emote.split(":")
			if len(emote) == 2:
				ids = emote[1].split(",")
				for i in ids:
					i = i.split("-")
					if len(i) == 2:
						index_from, index_to = int(i[0]), int(i[1])+1
						emote_list[text[index_from:index_to]] = emote[0]

		for word in text.split(" "):
			if 1+1 == 5: #word in chat_triggers
				pass

			if word in emote_list:
				img = emote_cache.get_image(emote_list[word])
				if img: self.place_image("end", img)

			elif word in bttv_emote_map:
				img = bttv_emote_cache.get_image(bttv_emote_map[word])
				if img:
					if img.animated:
						img = pyimage.PyImage(self._window.content, word, img=img)
						img.start()
					self.place_image("end", img)


			else: self.insert("end", word + " ")

	def see_bottom(self):
		if self._scroll_enabled:
			self.show("end")


class TwitchChatWindow(pywindow.PyWindow):
	def __init__(self, parent, channel, irc_client):
		# channel: twitch_window.ChannelData(name, id)
		self._channel = channel
		# irc_client: twitch_irc.IRCClient
		self._ircclient = irc_client
		pywindow.PyWindow.__init__(self, parent, "twitch_chatviewer")

		self._userstate = None
		self._msg_type_callbacks = {
			"PRIVMSG": self._chat.on_privmsg,
			"USERSTATE": self._on_userstate
		}

		self.title = "Twitch Chat Viewer"
		self.icon = "assets/icon_twitchviewer"
		self.content.row(0, minsize=20).row(1, weight=1).column(0, weight=1)
		self._header.text = self._channel.name

		self._ircclient.join_channel(self._channel.name)
		@self.event_handler.WindowDestroy
		def _on_destroy():
			print("INFO", "Chat window closed, leaving channel '{}'".format(self._channel.name))
			self._ircclient.leave_channel(self._channel.name)
		self.schedule(ms=500, func=self._poll_message, loop=True)

	@property
	def channel_name(self): return self._channel.name
	@property
	def channel_id(self): return self._channel.id

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		self._header = pyelement.PyTextlabel(self.content, "chat_header")
		self.content.place_element(self._header)
		self._header.wrapping = True

		self._chat = TwitchChatViewer(self.content, self)
		self.content.place_element(self._chat, row=1)
		self._talker = pyelement.PyTextfield(self.content, "chatter").with_undo(True).with_option(wrap="word", spacing1=3, padx=5)
		self.content.place_element(self._talker, row=2)
		self._talker.height = 5

	def window_tick(self, date):
		self._chat._timestamp = date
		pywindow.PyWindow.window_tick(self, date)

	def _on_userstate(self, meta, data=None):
		self._userstate = meta

	def _poll_message(self):
		for msg in self._ircclient.get_message(self._channel.name):
			cb = self._msg_type_callbacks.get(msg.type)
			if cb:
				try: cb(msg.meta, msg.data)
				except Exception as e:
					import traceback
					print("ERROR", "During message callback:")
					traceback.print_exception(type(e), e, e.__traceback__)