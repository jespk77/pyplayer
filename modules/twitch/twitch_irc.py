import socket, threading, multiprocessing
from collections import namedtuple

twitch_irc = "irc.chat.twitch.tv", 6667

Message = namedtuple("Message", ["meta", "type", "data"])
class IRCClient(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self, name="IRCClient")
		self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._channel_queue = {}

	def start(self): raise TypeError("Please call 'connect' instead to start this thread")

	def connect(self, name, auth):
		""" Start this thread, provide corrent credentials to be connected to the server """
		self._s.connect(twitch_irc)
		self._send("PASS {}".format(auth))
		self._send("NICK {}".format(name))
		self._send("CAP REQ :twitch.tv/tags")
		self._send("CAP REQ :twitch.tv/commands")
		threading.Thread.start(self)

	def disconnect(self):
		""" Leave all previously joined channels, disconnect from server and close this socket """
		if self._s:
			self._send("QUIT")
			self._s.close()

	def join_channel(self, channel):
		""" Join requested channel, once joined all messages received on this channel can be polled
		 	It is fine to call this more than once, when already joined the channel this call is ignored """
		if channel not in self._channel_queue:
			self._channel_queue[channel] = multiprocessing.Queue()
			self._send("JOIN #{}".format(channel))

	def leave_channel(self, channel):
		""" Leave requested channel, previously received messages still in queue will be dropped """
		q = self._channel_queue.get(channel)
		if q is not None:
			self._send("PART #{}".format(channel))
			del self._channel_queue[channel]

	def get_message(self, channel, message_limit=0):
		""" Get all messages that were sent to the channel since the last time this was called
		 	Use 'message_limit' to only request a certain number of items
		 		(will return fewer messages if there aren't not enough messages available)
		 	Returns a list of strings with all received messages """
		if channel in self._channel_queue:
			res = []
			q = self._channel_queue[channel]
			while not q.empty() and (not message_limit or len(res) < message_limit):
				res.append(q.get_nowait())
			return res

	def run(self):
		while True:
			try:
				data = self._receive().split("\r\n", maxsplit=4)
				for msg in data:
					msg = msg.split(" ")
					if not msg: continue
					if msg[0] == "PING": self._send("PONG {}".format(msg[1:]))
					else: self._process_data(msg)

			except socket.timeout: pass
			except ConnectionAbortedError: break
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
		if len(data) > 4:
			meta, type, channel, msg = data[0], data[2], data[3][1:], data[4][1:]
			q = self._channel_queue.get(channel)
			if q:
				try: meta = self._convert_meta(meta)
				except ValueError: return
				else: q.put(Message(meta=meta, type=type, data=msg))

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