from urllib.request import urlopen
from collections import OrderedDict
from multiprocessing import Queue

import tkinter
from tkinter.font import Font
from PIL import Image
from PIL.ImageTk import PhotoImage

import re, threading, time, datetime
import io, socket, requests, random

class IRCClient(threading.Thread):
	def __init__(self, message_queue, extra_info=False):
		super().__init__()
		self.socket = None
		self.message_queue = message_queue
		self.extra_info = extra_info

	def start_client(self, server, port, username, auth, channel):
		self.server = server
		self.port = port
		self.username = username
		self.auth = auth
		self.channel_name = channel
		super().start()

	def connect(self):
		print("[IRCClient] connecting to", self.server, ":", self.port)
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.connect((self.server, self.port))
		self.send("PASS {!s}".format(self.auth))
		self.send("NICK {!s}".format(self.username))
		if self.extra_info:
			self.send("CAP REQ :twitch.tv/tags")
			self.send("CAP REQ :twitch.tv/commands")
		self.send("JOIN #{}".format(self.channel_name))

	def disconnect(self):
		print("[IRCClient] disconnecting from", self.server)
		if self.socket is not None:
			try:
				self.socket.shutdown(socket.SHUT_RDWR)
				self.socket.close()
			except Exception as e: print("[IRCClient] exception closing socket:", e)
			print("[IRCClient] disconnected")
		self.socket = None

	def send(self, message):
		self.socket.send(bytes("{!s}\r\n".format(message), "UTF-8"))

	def run(self):
		self.connect()
		while self.socket is not None:
			try:
				rec = self.socket.recv(1024).decode("UTF-8").split("\r\n")
				if rec == 0:
					print("[IRCClient] Whoops, the connections seems to have broken, reconnecting...")
					self.connect()
					time.sleep(2)
					continue

				for data in rec: self.message_queue.put_nowait(data.split(" ", maxsplit=4))
			except UnicodeDecodeError: pass
			except socket.error: pass

class TwitchChat(tkinter.Text):
	chat_server = "irc.chat.twitch.tv"
	chat_port = 6667
	twitch_badge_url = "https://api.twitch.tv/kraken/chat/{channel}/badges?client_id={client_id}"
	channel_badge_url = "https://badges.twitch.tv/v1/badges/channels/{channel_id}/display"
	twitch_emote_url = "http://static-cdn.jtvnw.net/emoticons/v1/{emote_id}/1.0"
	bit_url = "https://api.twitch.tv/kraken/bits/actions?api_version=5&client_id={client_id}&channel_id={channel_id}"
	bit_format = re.compile(r"(.+?)([0-9]+)")
	bttv_emote_list = "https://api.betterttv.net/2/emotes"
	bttv_emote_url = "https://cdn.betterttv.net/emote/{id}/1x"

	def __init__(self, master):
		super().__init__(master, state="disabled")
		self.configuration = dict()
		self.queue_callback = None
		self.client = None
		self.user_meta = None
		self.chat_size = 0
		self.enable_scroll = True
		self.enable_triggers = True
		self.enable_timestamp = True
		self.update_time()
		self.emote_cache = dict()
		self.bttv_emotes = dict()
		self.versioned_badges = []
		self.limited = False

		self.configure(highlightbackground="gray50", highlightcolor="white", cursor="left_ptr", wrap="word", spacing1=3, padx=5)
		self.message_queue = Queue()
		self.bind("<End>", self.adjust_scroll)
		self.bind("<Enter>", self.set_scroll)
		self.bind("<Leave>", self.set_scroll)
		self.pack(fill="both", expand=True)
		self.chat_text = TwitchChatTalker(self.master, self.send_message)
		self.chat_text.configure(highlightbackground="gray50", highlightcolor="white", insertbackground="white", wrap="word", spacing1=3, padx=5)
		self.chat_text.pack(fill="x")

	def set_configuration(self, configuration):
		print("[TwitchChat] updating configuration", configuration.keys())
		self.configuration = configuration
		style = self.configuration.get("style", {}).get("global", {})
		self.configure(**style)
		self.chat_text.configure(**style)

		fonts = self.configuration.get("font", {})
		self.normal_font = Font(**fonts)
		self.bold_font = Font(**fonts)
		self.bold_font.config(weight="bold")
		self.configure(font=self.normal_font)
		self.chat_text.configure(font=self.normal_font, height=5)

		self.max_size = self.configuration.get("max-size", 150)
		self.enable_triggers = self.configuration.get("enable-triggers", self.enable_triggers)
		self.enable_timestamp = self.configuration.get("enable-timestamp", self.enable_timestamp)
		self.blacklist = self.configuration.get("blacklist", [])

		for key, value in self.configuration.get("style", {}).items():
			if key.startswith("tag_"): self.tag_configure(key[4:], **value)

	def set_command_queue_callback(self, callback):
		if callable(callback): self.queue_callback = callback
		else: print("[TwitchChat] tried to set queue callback to non-callable type", callback)

	def set_limited_mode(self, limited_mode):
		self.limited = limited_mode

	def update_time(self):
		self.timestamp = datetime.datetime.today()
		self.after(60000, self.update_time)

	def adjust_scroll(self, event):
		self.see("end")

	def set_scroll(self, event):
		self.enable_scroll = (event.x < 0 or event.x > event.widget.winfo_width()) or (event.y < 0 or event.y > event.widget.winfo_height())
		if self.enable_scroll: self.adjust_scroll(event)

	def connect(self, channel_meta, login):
		if self.client is None and login is not None:
			self.channel_meta = channel_meta
			self.client = IRCClient(self.message_queue, extra_info=True)
			self.client.start_client(self.chat_server, self.chat_port, login["username"], login["oauth"], self.channel_meta["name"])

			self.load_badges(login)
			self.load_local_emote()
			self.load_bttv()
			self.load_bits(login)
			self.add_text(text=" - Joined channel: {} -".format(self.channel_meta["display_name"]), tags=("notice",))

	def disconnect(self):
		if self.client is not None:
			self.client.send("PART #{}".format(self.channel_meta["name"]))
			self.client.send("QUIT")
			self.client.disconnect()
			self.client.join()
			self.client = None

	def load_bttv(self):
		u = requests.get(self.bttv_emote_list).json()
		self.bttv_emotes = {}
		for emote in u["emotes"]:
			if emote["imageType"] != "gif": self.bttv_emotes[emote["code"]] = emote["id"]

	def get_bttv_emote(self, name):
		if name in self.bttv_emotes:
			img = self.bttv_emotes[name]
			if isinstance(img, str):
				try:
					u = urlopen(self.bttv_emote_url.format(id=img))
					self.bttv_emotes[name] = PhotoImage(Image.open(io.BytesIO(u.read())))
					u.close()

				except Exception as e:
					print("[TwitchChat] error loading bttv emote '{}':".format(name), e)
					del self.bttv_emotes[name]
					return
			return self.bttv_emotes[name]

	def load_bits(self, login):
		self.bit_cache = {}
		bit_motes = requests.get(self.bit_url.format(client_id=login["client-id"],channel_id=self.channel_meta["_id"])).json()
		self.tag_configure("cheer1", font=self.bold_font, foreground="gray")
		self.tag_configure("cheer100", font=self.bold_font, foreground="purple")
		self.tag_configure("cheer1000", font=self.bold_font, foreground="cyan")
		self.tag_configure("cheer5000", font=self.bold_font, foreground="blue")
		self.tag_configure("cheer10000", font=self.bold_font, foreground="red")
		for emote in bit_motes["actions"]:
			list = []
			for tier in emote["tiers"]:
				list.append((int(tier["min_bits"]), tier["images"]["dark"]["static"]["1"]))
			self.bit_cache[emote["prefix"].lower()] = OrderedDict(list)

	def get_bit_emote(self, name, amount):
		if not name in self.bit_cache: return None

		try: amount = int(amount)
		except Exception: return None

		emote = None
		for (min_amount, img) in self.bit_cache[name].items():
			if min_amount > amount: break
			emote = (min_amount, img)

		if emote is None: return None
		if isinstance(emote[1], str):
			try:
				url = urlopen(emote[1])
				self.bit_cache[name][emote[0]] = PhotoImage(Image.open(io.BytesIO(url.read())))
				url.close()

			except Exception:
				del self.bit_cache[name]
				return None
		return (emote[0], self.bit_cache[name][emote[0]])

	def load_badges(self, login):
		badges = requests.get(self.twitch_badge_url.format(channel=self.channel_meta["name"], client_id=login["client-id"])).json()
		self.badge_cache = dict()
		self.badge_cache["global_mod"] = badges["global_mod"]["alpha"]
		self.badge_cache["admin"] = badges["admin"]["alpha"]
		self.badge_cache["broadcaster"] = badges["broadcaster"]["alpha"]
		self.badge_cache["staff"] = badges["staff"]["alpha"]
		self.badge_cache["moderator"] = badges["mod"]["alpha"]

		if self.channel_meta["partner"]:
			badges = requests.get(self.channel_badge_url.format(channel_id=self.channel_meta["_id"])).json()
			badge_set = badges["badge_sets"]
			if "subscriber" in badge_set:
				self.versioned_badges.append("subscriber")
				for version, url in badge_set["subscriber"]["versions"].items():
					self.badge_cache["subscriber/" + version] = url["image_url_1x"]

			if "bits" in badge_set:
				self.versioned_badges.append("bits")
				for version, url in badge_set["bits"]["versions"].items():
					self.badge_cache["bits/" + version] = url["image_url_1x"]

		for badge_id, badge_url in self.badge_cache.items():
			try:
				url = urlopen(badge_url)
				self.badge_cache[badge_id] = PhotoImage(Image.open(io.BytesIO(url.read())))
				url.close()
			except Exception: del self.badge_cache[badge_id]

	def send_message(self, msg):
		if self.client is not None:
			self.client.send("PRIVMSG #" + self.channel_meta["name"] + " :" + msg)
			if self.user_meta is None:
				self.configure(state="normal")
				self.insert("end", "\n You: ", ("notice",))
				self.insert("end", msg.rstrip("\n"))
				self.see("end")
				self.configure(state="disabled")
			else: self.on_privmsg(self.user_meta, msg.rstrip("\n"))

	def on_privmsg(self, meta, data):
		if meta is None: return

		for line in self.blacklist:
			if line in data: return

		user = meta["display-name"]
		if len(meta["color"]) == 0:
			try: color = self.tag_cget(user.lower(), "foreground")
			except: color = "#" + "".join("{:02x}".format(n) for n in [random.randrange(75,255), random.randrange(75,255), random.randrange(75,255)])
		else: color = meta["color"]
		self.tag_configure(user.lower(), foreground=color, font=self.bold_font)

		emotes = meta.get("emotes", "").split("/")
		emote_list = {}
		for emote in emotes:
			emote = emote.split(":")
			if len(emote) == 2: emote_list[emote[0]] = emote[1]

		badges = meta["badges"].split(",")
		self.configure(state="normal")
		self.insert("end", "\n")
		if self.enable_timestamp: self.insert("end", self.timestamp.strftime("%I:%M "), ("notice",))
		for badge in badges:
			is_versioned = False
			for b in self.versioned_badges:
				if badge.startswith(b): is_versioned = True; break

			if not is_versioned: badge = badge.split("/")[0]

			if badge in self.badge_cache:
				self.image_create(index="end", image=self.badge_cache[badge])
				self.insert("end", " ")

		self.add_text(user=user, text=data, emotes=emote_list, bits="bits" in meta)

	def add_text(self, text, user="", emotes=None, bits=False, tags=()):
		text = "".join([c for c in text if ord(c) <= 65536])
		if text.startswith("\x01ACTION"):
			text = text.lstrip("\x01ACTION ").rstrip("\x01")
			tags = (user.lower())
		elif text == "": return

		self.configure(state="normal")
		if self.chat_size >= self.max_size:
			self.delete("2.0", "3.0")
		else: self.chat_size += 1

		if user != "": self.insert("end", user + " ", (user.lower(),))

		emote_map = {}
		if emotes is not None:
			for emote_id, emote_index in emotes.items():
				if not emote_id in self.emote_cache: self.load_emote(emote_id)
				if self.emote_cache[emote_id] is None:
					del self.emote_cache[emote_id]
					continue

				emote_index = emote_index.split(",")[0].split("-")
				emote_begin = int(emote_index[0])
				emote_end = int(emote_index[1]) + 1
				emote_map[text[emote_begin:emote_end]] = emote_id

		text = text.split(" ")
		for word in text:
			if not self.limited and self.enable_triggers and word in self.configuration.get("triggers", {}):
				if self.queue_callback is not None: self.queue_callback(self.configuration["triggers"][word])

			if word in emote_map:
				try: self.image_create(index="end", image=self.emote_cache[emote_map[word]])
				except Exception: pass
				continue
			elif bits:
				bit = self.bit_format.findall(word)
				if len(bit) > 0:
					try:
						im = self.get_bit_emote(name=bit[0][0], amount=bit[0][1])
						self.image_create("end", image=im[1])
						self.insert("end", str(bit[0][1]), "cheer"+str(im[0]))
					except Exception: pass
					continue
			elif word in self.bttv_emotes:
				try: self.image_create("end", image=self.get_bttv_emote(word))
				except Exception as e: print("[TwitchChat] error creating image for bttv emote '{}':".format(word), e)
				continue

			self.insert("end", word + " ", tags)

		if self.enable_scroll: self.see("end")
		self.configure(state="disabled")

	def load_local_emote(self):
		self.emote_cache["25"] = PhotoImage(Image.open("twitch/kappa.png"))
		self.emote_cache["36"] = PhotoImage(Image.open("twitch/pjsalt.png"))
		self.emote_cache["66"] = PhotoImage(Image.open("twitch/onehand.png"))

	def load_emote(self, emote_id):
		u = self.twitch_emote_url.format(emote_id=emote_id)
		try:
			url = urlopen(u)
			self.emote_cache[emote_id] = PhotoImage(Image.open(io.BytesIO(url.read())))
			url.close()

		except Exception: self.emote_cache[emote_id] = None

	def get_meta(self, data):
		if not data.startswith("@"): return None
		else: data = data.lstrip("@")

		data = data.split(";")
		res = {}
		for line in data:
			line = line.split("=")
			if len(line) == 2: res[line[0]] = line[1]
		return res

	def on_usernotice(self, meta, data):
		if meta is None or self.limited: return
		type = meta["msg-id"]
		if type == "resub": text = meta["display-name"] + " resubscribed for " + meta["msg-param-months"] + " months"
		elif type == "sub": text = meta["display-name"] + " subscribed"
		elif type == "subgift": text = meta["display-name"] + " gifted a subscription to " + meta["msg-param-recipient-display-name"]
		else: return

		if meta["msg-param-sub-plan"] == "Prime": level = " with Prime"
		elif meta["msg-param-sub-plan"] == "1000": level = ""
		elif meta["msg-param-sub-plan"] == "2000": level = " at tier 2"
		else: level = " at tier 3"
		self.configure(state="normal")
		self.insert("end", "\n")
		self.insert("end", text + level, ("notice",))
		self.configure(state="disabled")
		if len(data) > 0: self.on_privmsg(meta, data)

	def on_clearchat(self, user):
		tag = user.lower() + ".last"
		try: self.tag_add("deleted", tag, tag + " lineend")
		except: pass

	def on_userstate(self, meta):
		if meta is not None: self.user_meta = meta

	def run(self):
		if self.client is not None:
			if not self.message_queue.empty(): self.process_data(self.message_queue.get_nowait())
			self.master.after(100, self.run)

	def process_data(self, data):
		try:
			if data[0] == "PING": self.client.send("PONG " + "".join(data[1:]))
			elif data[2] == "PRIVMSG": self.on_privmsg(meta=self.get_meta(data[0]), data=data[4][1:])
			elif data[2] == "USERNOTICE": self.on_usernotice(meta=self.get_meta(data[0]), data="".join(data[4:])[1:])
			elif data[2] == "CLEARCHAT": self.on_clearchat(data[4][1:])
			elif data[2] == "USERSTATE": self.on_userstate(self.get_meta(data[0]))
		except IndexError: pass

class TwitchChatTalker(tkinter.Text):
	def __init__(self, root, send_message_callback):
		super().__init__(root, height=250)
		self.bind("<Escape>", self.clear_text)
		self.bind("<Return>", self.on_send_message)
		self.message_callback = send_message_callback

	def on_send_message(self, event):
		if callable(self.message_callback):
			message = self.get("0.0", "end")
			if len(message) > 1: self.message_callback(message)
			self.clear_text(event)
		return "break"

	def clear_text(self, event):
		self.delete("0.0", "end")
		self.mark_set("insert", "0.0")