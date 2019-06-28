from modules.twitch.twitch_window import CLIENT_ID
from ui import pyelement, pyimage, pywindow

badge_url = "https://api.twitch.tv/kraken/chat/{channel_name}/badges?client_id=" + CLIENT_ID
channel_badge_url = "https://badges.twitch.tv/v1/badges/channels/{channel_id}/display"
emote_cache = pyimage.ImageCache("emote_cache", "http://static-cdn.jtvnw.net/emoticons/v1/{key}/1.0")
cheermote_list_url = "https://api.twitch.tv/v5/bits/actions?channel_id={channel_id}&client_id=" + CLIENT_ID

bttv_emote_list_url = "https://api.betterttv.net/2/emotes"
bttv_emote_cache = pyimage.ImageCache("bttv_emote_cache", "https://cdn.betterttv.net/emote/{key}/1x")
# bobross: 105458682 - own id: 61667394

# --- DEBUG OPTIONS ---
log_unknown_badges = False
# =====================

def _do_request(url):
	import requests
	r = requests.get(url)
	data = r.json()
	if r.status_code == 200: return data
	else: print("ERROR", "'{}': Invalid response while requesting data:".format(url), data)
bttv_emote_map = {entry["code"]: entry["id"] for entry in _do_request(bttv_emote_list_url)["emotes"]}

def _split_bits(text):
	# todo: requires optimization
	t = list(text)
	t.reverse()
	dg = []
	for t1 in t:
		if not t1.isdigit(): break
		else: dg.append(t1)
	t = t[len(dg):]
	t.reverse()
	dg.reverse()
	return "".join(t), int("".join(dg))


chat_cfg = {"subnotice.background": "gray15", "subnotice.foreground": "white", "notice.foreground": "gray", "deleted.foreground": "gray15", "timestamp.foreground": "gray"}
class TwitchChatViewer(pyelement.PyTextfield):
	def __init__(self, container, window, initial_cfg=None):
		global chat_cfg
		if initial_cfg:
			chat_cfg = chat_cfg.copy()
			chat_cfg.update(initial_cfg)

		pyelement.PyTextfield.__init__(self, container, "chat_viewer", initial_cfg=chat_cfg)
		self._window = window
		self.accept_input = False
		self._badge_cache = {}
		self._timestamp = None
		self._scroll_enabled = True
		self._cheermote_map = {}
		self._cmd_cb = None
		@self.event_handler.MouseEnter
		def _enable_scroll(): self._scroll_enabled = False
		@self.event_handler.MouseLeave
		def _disable_scroll():
			self._scroll_enabled = True
			self.see_bottom()

		self._load_badges()
		self._load_cheermotes()
		self.with_option(cursor="left_ptr", wrap="word", spacing1=3, padx=5)

	@property
	def command_callback(self): return self._cmd_cb
	@command_callback.setter
	def command_callback(self, cb):
		if not callable(cb): raise ValueError("Callback must be callable!")
		else: self._cmd_cb = cb

	def _load_badges(self):
		badges = _do_request(badge_url.format(channel_name=self._window.channel_name))
		if badges:
			self._badge_cache["global_mod/1"] = badges["global_mod"]["alpha"]
			self._badge_cache["admin/1"] = badges["admin"]["alpha"]
			self._badge_cache["broadcaster/1"] = badges["broadcaster"]["alpha"]
			self._badge_cache["staff/1"] = badges["staff"]["alpha"]
			self._badge_cache["moderator/1"] = badges["mod"]["alpha"]
		else: print("WARNING", "Badge data fetch failed, badges not visible")

		channel_badges = _do_request(channel_badge_url.format(channel_id=self._window.channel_id))
		if channel_badges:
			badge_set = channel_badges["badge_sets"]
			sbadges = badge_set.get("subscriber")
			if sbadges:
				for version, url in sbadges["versions"].items(): self._badge_cache["subscriber/" + version] = url["image_url_1x"]

			bbadges = badge_set.get("bits")
			if bbadges:
				for version, url in bbadges["versions"].items(): self._badge_cache["bits/" + version] = url["image_url_1x"]
		else: print("WARNING", "Tiered badges data fetch failed, tiered badges not visible")

	def _load_cheermotes(self):
		cheers = _do_request(cheermote_list_url.format(channel_id=self._window.channel_id))
		if cheers:
			from collections import namedtuple
			CheermoteData = namedtuple("CheermoteData", ["min_bits", "color", "image"])
			for emote in cheers["actions"]:
				try:
					tierlist = [CheermoteData(min_bits=int(entry["min_bits"]), color=entry["color"], image=entry["images"]["dark"]["animated"]["1"]) for entry in emote["tiers"]]
					tierlist.reverse()
					self._cheermote_map[emote["prefix"]] = tierlist
				except Exception as e:
					print("ERROR", "Processing cheermote data:", emote)
					import traceback; traceback.print_exception(type(e), e, e.__traceback__)
		else: print("WARNING", "Cheermote data fetch failed, cheermotes not visible")

	def _get_badge(self, key):
		bg = self._badge_cache.get(key)
		if isinstance(bg, str):
			self._badge_cache[key] = pyimage.ImageData(url=bg)
			return self._badge_cache.get(key)
		elif isinstance(bg, pyimage.ImageData): return bg
		else: raise KeyError(key)

	def _get_cheermote(self, key):
		try: name, value = _split_bits(key)
		except ValueError: return

		print("INFO", "Getting cheermote '{}' with value:".format(name), value)
		data = self._cheermote_map.get(name)
		if data:
			bit_index, bit_data = 0, None
			for b_index, b_data in enumerate(data):
				if b_data.min_bits < value:
					bit_index = b_index
					bit_data = b_data
					break

			if bit_data:
				print("INFO", "Found data for image on index:", bit_index)
				if isinstance(bit_data.image, str):
					print("INFO", "Image not yet cached, collecting image from url")
					try: img = pyimage.PyImage(self._window.content, "cheer_{}_{}".format(name, bit_data.min_bits), url=bit_data.image)
					except Exception as e: return print("ERROR", "Getting image:", e)
					bit_data = bit_data._replace(image=img)
					self._cheermote_map[name][bit_index] = bit_data
				return bit_data.image, value, bit_data.color
			else: print("WARNING", "No valid bit emote found for '{}', it is either a false positive or something went wrong during bit info collection".format(key))

	def _insert_badges(self, badges):
		for b in badges:
			if not b: continue

			try:
				self.place_image("end", self._get_badge(b))
				self.insert("end", " ")
			except KeyError as e:
				if log_unknown_badges: print("INFO", "Unknown badge:", e)
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
		if text.startswith("\x01ACTION"):
			text = text.lstrip("\x01ACTION ").rstrip("\x01")
			tags = (meta.get("display-name", "").lower(),)
		else: tags = None

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
			if word in self._window.configuration["chat_triggers"]:
				if self._cmd_cb:
					try: self._cmd_cb(word)
					except Exception as e: print("ERROR", "While calling chat trigger callback:", e)

			if word in emote_list:
				img = emote_cache.get_image(emote_list[word])
				if img: self.place_image("end", img)
				continue

			if word in bttv_emote_map:
				img = bttv_emote_cache.get_image(bttv_emote_map[word])
				if img:
					if img.animated:
						img = pyimage.PyImage(self._window.content, word, img=img)
						img.start()
					self.place_image("end", img)
				continue

			if "bits" in meta:
				img = self._get_cheermote(word)
				if img:
					img, amount, color = img
					self.place_image("end", img)
					tag_amount = "cheer_{}".format(amount)
					self.set_tag_option(tag_amount, foreground=color)
					self.insert("end", "{} ".format(amount), (tag_amount,))
					continue

			self.insert("end", word + " ", tags)

	def on_privmsg(self, meta, msg):
		if not meta or not msg: return
		if self.configuration.get("enable_timestamp") and self._timestamp: self.insert("end", self._timestamp.strftime("%I:%M "), ("timestamp",))
		self._insert_badges(meta.get("badges", "").split(","))
		self._insert_username(meta.get("display-name"), color=meta.get("color"))
		self._insert_message(meta, msg)
		self.see_bottom()
		self.insert("end", "\n")

	def on_usernotice(self, meta, data):
		if meta is None: return
		type = meta.get("msg-id")

		if type == "resub":
			text = "{} resubscribed for {} months".format(meta["display-name"], meta["msg-param-cumulative-months"])
			if meta["msg-param-should-share-streak"] == '1': text += " and is on a {} month streak".format(meta["msg-param-streak-months"])
		elif type == "sub": text = meta["display-name"] + " subscribed"

		elif type == "subgift":
			text = "{} gifted a subscription to {}".format(meta["display-name"], meta["msg-param-recipient-display-name"])
			amt = meta.get("msg-param-sender-count", "0")
			if amt > "0": text += " for {} total gifts".format(meta["msg-param-sender-count"])
		elif type == "submysterygift":
			text = "{} is gifting {} random subscriptions".format(meta["display-name"], meta["msg-param-mass-gift-count"])
			amt = meta.get("msg-param-sender-count", "0")
			if amt > "0": text += " for {} total gifts".format(meta["msg-param-sender-count"])
		elif type == "charity": return self.on_charity(meta, data)
		else: return

		if meta["msg-param-sub-plan"] == "Prime": level = " with Prime"
		elif meta["msg-param-sub-plan"] == "1000": level = ""
		elif meta["msg-param-sub-plan"] == "2000": level = " at tier 2"
		else: level = " at tier 3"

		start_index = self.position("end-1l")
		self.insert("end", text + level + '\n')
		if len(data) > 0:
			start_index = self.position("end-2l")
			self.on_privmsg(meta, data)
		self.place_tag("subnotice", start_index, "end-1c")
		self.tag_lower("subnotice")
		self.see_bottom()

	def on_notice(self, meta, data):
		self.insert("end", data + "\n", ("notice",))
		self.see_bottom()

	def on_charity(self, meta, data):
		self.insert("end", "${:,} raised for {} so far! {} days left\n".format(int(meta["msg-param-total"]), meta["msg-param-charity-name"].replace("\s", " "), meta["msg-param-charity-days-remaining"]), ("notice",))
		self.see_bottom()

	def on_whisper(self, meta, data):
		self.insert("end", " ***** Received Whisper ***** \n", ("notice",))
		self.on_privmsg(meta, data)
		self.insert("end", "-----------------------------------------\n", ("notice",))

	def on_clearchat(self, meta, data=None):
		tag = meta.get("display-name", "") + ".last"
		try: self.place_tag("deleted", tag, tag + " lineend")
		except: pass

	def see_bottom(self):
		if self._scroll_enabled:
			self.show("end")


element_cfg = {"foreground": "white", "background": "black"}
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
			"NOTICE": self._chat.on_notice,
			"USERSTATE": self._on_userstate,
			"USERNOTICE": self._chat.on_usernotice,
			"CLEARCHAT": self._chat.on_clearchat,
			"WHISPER": self._chat.on_whisper
		}

		self.title = "Twitch Chat Viewer"
		self.icon = "assets/icon_twitchviewer"
		self.content.row(0, minsize=20).row(1, weight=1).column(0, weight=1)
		self._window = parent
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
		self._header = pyelement.PyTextlabel(self.content, "chat_header", initial_cfg=element_cfg)
		self.content.place_element(self._header)
		self._header.wrapping = True

		self._chat = TwitchChatViewer(self.content, self, initial_cfg=element_cfg)
		self.content.place_element(self._chat, row=1)
		self._talker = pyelement.PyTextfield(self.content, "chatter", initial_cfg=element_cfg).with_undo(True)
		self._talker.with_option(wrap="word", spacing1=3, padx=5)
		self.content.place_element(self._talker, row=2)
		self._talker.height = 5

		@self._talker.event_handler.KeyEvent("enter")
		def _send_message():
			self._ircclient.send_message(self._channel.name, self._talker.text)
			self._talker.text = ""
			return self._talker.event_handler.block

	def window_tick(self, date):
		self._chat._timestamp = date
		pywindow.PyWindow.window_tick(self, date)

	def _on_userstate(self, meta, data=None):
		self._userstate = meta
		self._window.update_emoteset(meta.get("emote-sets", "").split(","))

	def _poll_message(self):
		for msg in self._ircclient.get_message(self._channel.name):
			cb = self._msg_type_callbacks.get(msg.type)
			if cb:
				try: cb(msg.meta, msg.data)
				except Exception as e:
					import traceback
					print("ERROR", "During message callback:")
					traceback.print_exception(type(e), e, e.__traceback__)