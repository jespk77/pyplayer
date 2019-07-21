import socket, threading, multiprocessing
from collections import namedtuple

twitch_irc = "irc.chat.twitch.tv", 6667

Message = namedtuple("Message", ["meta", "type", "data"])
class IRCClient:
	def __init__(self, name, auth):
		""" Create a new client, provided credentials will be used to log onto the server """
		self._auth = name, auth
		self._th = threading.Thread(name="IRCClient", target=self.run)
		self._s = None
		self._general_queue = multiprocessing.Queue()
		self._channel_queue = {}
		self.connect()
		self._th.start()

	def connect(self):
		""" Start the client if it hasn't been started yet """
		if self._s is not None: raise RuntimeError("Client already started!")
		self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._s.connect(twitch_irc)
		self._send("PASS {}".format(self._auth[1]))
		self._send("NICK {}".format(self._auth[0]))
		self._send("CAP REQ :twitch.tv/tags")
		self._send("CAP REQ :twitch.tv/commands")

	def disconnect(self):
		""" Leave all previously joined channels, disconnect from server and close this socket """
		if self._s:
			self._send("QUIT")
			self._s.close()
			self._s = None

	def join_channel(self, channel):
		""" Join requested channel, once joined all messages received on this channel can be polled
		 	It is fine to call this more than once, when already joined the channel this call is ignored """
		channel = channel.lower()
		if channel not in self._channel_queue:
			self._channel_queue[channel] = multiprocessing.Queue()
			self._send("JOIN #{}".format(channel))

	def leave_channel(self, channel):
		""" Leave requested channel, previously received messages still in queue will be dropped """
		channel = channel.lower()
		q = self._channel_queue.get(channel)
		if q is not None:
			self._send("PART #{}".format(channel))
			del self._channel_queue[channel]

	def get_message(self, channel, message_limit=0):
		""" Get all messages that were sent to the channel since the last time this was called
		 	Use 'message_limit' to only request a certain number of items
		 		(will return fewer messages if there aren't not enough messages available)
		 	Returns a list of strings with all received messages """
		channel = channel.lower()
		if channel in self._channel_queue:
			res = []
			q = self._channel_queue[channel]
			while not q.empty() and (not message_limit or len(res) < message_limit):
				res.append(q.get_nowait())
			return res
		else: raise NameError("Not subscribed to messages from '{}'".format(channel))

	def send_message(self, channel, message):
		""" Send a message to given channel, must have joined that channel in order to have an effect """
		channel = channel.lower()
		if channel not in self._channel_queue: raise KeyError(channel)
		self._send("PRIVMSG #{} : {}".format(channel, message))

	def run(self):
		while True:
			try:
				data = self._receive().split("\r\n")
				if not data or len(data) == 1 and not data[0]: break
				for msg in data:
					msg = msg.split(" ", maxsplit=4)
					if not msg: continue
					if msg[0] == "PING": self._send("PONG {}".format(msg[1:]))
					else: self._process_data(msg)

			except socket.timeout: pass
			except socket.error as e:
				print("ERROR", "Socket error!")
				import traceback
				traceback.print_exception(type(e), e, e.__traceback__)
				break
			except Exception as e:
				print("ERROR", "Processing error!")
				import traceback
				traceback.print_exception(type(e), e, e.__traceback__)

	def _process_data(self, data):
		if len(data) > 3:
			meta, type, channel = data[0], data[2], data[3][1:]
			msg = data[4][1:] if len(data) > 4 else ""
			q = self._channel_queue.get(channel)
			if q:
				try: meta = self._convert_meta(meta)
				except ValueError: meta = {}
				q.put(Message(meta=meta, type=type, data=msg))

	def _convert_meta(self, meta):
		if not isinstance(meta, str): raise TypeError("'meta' must be a string!")
		if not meta.startswith('@'): raise ValueError("Invalid metadata, first character should be '@'")
		meta = meta[1:]

		data = {}
		for entry in meta.split(';'):
			entry = entry.split("=", maxsplit=1)
			if len(entry) == 2: data[entry[0]] = entry[1]
		return data

	def _send(self, data): self._s.send(bytes("{}\r\n".format(data), "UTF-8"))
	def _receive(self, bufsize=1024): return self._s.recv(bufsize).decode()