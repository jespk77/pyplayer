from ui.qt import pywindow, pyelement, pyworker
from core import pyconfiguration
from . import read_logindata, read_metadata
import collections, multiprocessing, socket

client = twitch_irc = None
ChatMessage = collections.namedtuple("ChatMessage", ["channel", "meta", "content_type", "content"])

class TwitchIRC(pyworker.PyWorker):
    twitch_irc_url = "irc.chat.twitch.tv", 6667
    retry_timeout = 10
    retry_amount = -1

    def __init__(self):
        self._login_data = read_logindata()
        if not self._login_data: raise ValueError("No signin data found")
        self._usermeta = read_metadata()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self._general_queue = multiprocessing.Queue()
        self._channels = {}
        self._channel_lock = multiprocessing.Lock()
        self._retry_attempts = 0
        self._worker_state = 0
        pyworker.PyWorker.__init__(self, "twitchIRC")

    def _send(self, data): return self._socket.send(bytes(f"{data}\r\n", "UTF-8"))
    def _recv(self, size=1024): return self._socket.recv(size).decode("UTF-8")

    def _connect(self):
        print("INFO", "Connecting to twitch IRC server")
        if not self._usermeta: self._usermeta = read_metadata(True)

        self._socket.connect(self.twitch_irc_url)
        self._send(f"PASS oauth:{self._login_data['Authorization'].split(' ', maxsplit=1)[1]}")
        self._send(f"NICK {self._usermeta['login']}")
        self._send("CAP REQ :twitch.tv/tags")
        self._send("CAP REQ :twitch.tv/commands")
        self._join_connected_channels()

    def _join_connected_channels(self):
        with self._channel_lock:
            for channel in self._channels.keys(): self._send(f"JOIN #{channel}")

    def _can_close(self):
        with self._channel_lock:
            return len(self._channels) == 0

    def _try_reconnect(self):
        print("INFO", "Disconnected from server, trying to reconnect...")
        if self._can_close(): return False
        try: self._socket.close()
        except: pass

        try:
            self._retry_attempts += 1
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._connect()
            return True
        except:
            if self.retry_amount < 0 or self._retry_attempts < self.retry_amount:
                print("INFO", f"Failed to reconnect, retrying in {self.retry_timeout} seconds...")
                import time; time.sleep(self.retry_timeout)
                return self._try_reconnect()
            else:
                print("INFO", "Failed to reconnect and max number of attempts reached, shutting down...")
                return False


    def _disconnect(self):
        print("INFO", "Disconnecting from twitch IRC server")
        self._send("QUIT")
        self._socket.close()

    def join_channel(self, channel):
        channel = channel.lower()
        with self._channel_lock:
            if channel not in self._channels:
                print("INFO", "Joining channel", channel)
                if self._worker_state == 1: self._send(f"JOIN #{channel}")
                self._channels[channel] = multiprocessing.Queue()
            else: raise KeyError(f"Already joined {channel}")

    def leave_channel(self, channel):
        channel = channel.lower()
        with self._channel_lock:
            if channel in self._channels:
                print("INFO", "Leaving channel", channel)
                self._send(f"PART #{channel}")
                del self._channels[channel]
            else: raise KeyError(channel)

    def get_irc_message(self):
        if not self._general_queue.empty():
            return self._general_queue.get_nowait()

    def get_message(self, channel, limit=0):
        channel = channel.lower()
        with self._channel_lock:
            q = self._channels.get(channel)
            msg = []
            if not q:
                print("WARNING", "Tried to get message from unsubscribed channel", channel)
                return msg

            while not q.empty() and (limit <= 0 or len(msg) < limit):
                msg.append(q.get_nowait())
            return msg

    def send_message(self, channel, message):
        channel = channel.lower()
        with self._channel_lock:
            if channel not in self._channels: raise KeyError(channel)
        self._send(f"PRIVMSG #{channel} :{message}")

    def _process_message(self, message):
        if message[0].startswith("@"):
            meta = {item[0]: item[1] for item in [i.split("=", maxsplit=1) for i in message[0][1:].split(";")] if len(item) == 2}
        else: meta = None

        msg_type = message[2]
        if not message[3].startswith("#"): print("VERBOSE", "Unrecognized channel:", message[3]); return False
        channel = message[3][1:]

        content = None
        if len(message) > 4: content = message[4][1:]

        message = ChatMessage(channel=channel, meta=meta, content_type=msg_type, content=content)
        with self._channel_lock:
            message_queue = self._channels.get(channel)
            if message_queue: message_queue.put(message)
        return True

    def run(self):
        self._connect()
        self._worker_state = 1

        while True:
            try:
                data = self._recv().split("\r\n")
                self._retry_attempts = 0

                for item in data:
                    item = item.split(" ", maxsplit=4)
                    try:
                        if item[1] == "NOTICE":
                            item = " ".join(item[3:])[1:]
                            print("INFO", "Received general IRC notice:", item)
                        elif item[0] == "PING": self._send(f"PONG {item[1]}")

                        res = False
                        if len(item) >= 4: res = self._process_message(item)

                        if not res: print("VERBOSE", "Unhandled message:", item)
                    except IndexError: continue

                if self._can_close():
                    print("INFO", "No more channels connected, shutting down client...")
                    break

            except socket.timeout: pass
            except socket.error as e:
                print("ERROR", "Socket error:", e)
                self._worker_state = 2
                with self._channel_lock:
                    for channel, queue in self._channels.items():
                        queue.put_nowait(ChatMessage(channel=channel, meta=None, content_type="DISCONNECT", content="Disconnected from chat"))
                if not self._try_reconnect(): return
                else: self._worker_state = 1
            except Exception as e: print("ERROR", "While processing data:", e)
        self._disconnect()

    def complete(self):
        print("INFO", "Terminated IRC client")
        global twitch_irc
        twitch_irc = None


class TwitchChatWindow(pywindow.PyWindow):
    configuration = pyconfiguration.ConfigurationFile("twitch_chat")
    msg_callbacks = {}

    def __init__(self, parent, channel):
        self._channel = channel
        pywindow.PyWindow.__init__(self, parent, f"twitch_{channel}")
        self.schedule_task(sec=1, task_id="process_message", func=self._add_message, loop=True)
        self.events.EventWindowDestroy(self._on_destroy)
        self.title = f"TwitchViewer: {channel}"
        self.icon = "assets/icon_twitchviewer.png"

        global twitch_irc
        if twitch_irc is None: twitch_irc = TwitchIRC()
        twitch_irc.join_channel(channel)
        self["chat_content"].style_sheet = ".chat-notice{color:gray} .chat-username{font-weight:700}"

    def _on_destroy(self):
        twitch_irc.leave_channel(self._channel)

    def create_widgets(self):
        lbl = self.add_element("channel_lbl", element_class=pyelement.PyTextLabel)
        lbl.set_alignment("center")
        lbl.text = f"Twitch Chat: {self._channel}"

        chat_content = self.add_element("chat_content", element_class=pyelement.PyTextField, row=1)
        #chat_content.append(f"<span>Joined chat: {self._channel}</span>", html=True)
        chat_content.accept_input = False

        send = self.add_element(element=pyelement.PyTextInput(self, "chat_message", True), row=2)
        @send.events.EventInteract
        def _send_message():
            if send.text:
                twitch_irc.send_message(self._channel, send.text)
                send.text = ""

        send_btn = self.add_element("chat_send", element_class=pyelement.PyButton, row=3)
        send_btn.text = "Send"
        send_btn.events.EventInteract(_send_message)

    def _insert_notice(self, notice: ChatMessage):
        chat = self["chat_content"]
        chat.append(f"\n{notice.content}", tags=("chat-notice",))
    msg_callbacks["NOTICE"] = msg_callbacks["DISCONNECT"] = _insert_notice

    def _insert_privmsg(self, msg: ChatMessage):
        chat = self["chat_content"]
        chat.append(f"<div class='chat-content'> <span class='chat-username' style='color: {msg.meta.get('color', 'orange')}'>{msg.meta.get('display-name', '')}</span> <span>", html=True)
        chat.append(msg.content)
        chat.append("</span></div>", html=True)
    msg_callbacks["PRIVMSG"] = _insert_privmsg

    def _add_message(self):
        if twitch_irc is not None:
            messages = twitch_irc.get_message(self._channel)
            for message in messages:
                cb = self.msg_callbacks.get(message.content_type)
                if cb:
                    try: cb(self, message)
                    except Exception as e: print("ERROR", "Processing chat message:", e)
        else: self.cancel_task("process_message")


def open_chat_window(channel):
    print("INFO", "Opening chat window for", channel)
    chat_window = TwitchChatWindow(client, channel)
    client.add_window(window=chat_window)