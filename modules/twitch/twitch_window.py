from ui import pywindow, pyelement, pyimage

CLIENT_ID = "6adynlxibzw3ug8udhyzy6w3yt70pw"
emote_cache = pyimage.ImageCache("emote_cache", "http://static-cdn.jtvnw.net/emoticons/v1/{key}/1.0")
bttv_emote_cache = pyimage.ImageCache("bttv_emote_cache", "https://cdn.betterttv.net/emote/{key}/1x")

def generate_random_code(n=30):
	import random
	return "".join([random.choice("aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ0123456789") for _ in range(n)])

class TwitchSigninWindow(pywindow.PyWindow):
	TIMEOUT = 30
	resp_uri = "http://localhost:6767/twitch_auth"
	scope = ["user:edit", "chat:read", "chat:edit"]
	auth_url = "https://id.twitch.tv/oauth2/authorize?response_type=token&client_id={client_id}&redirect_uri={resp_uri}&state={state}&scope={scope}&force_verify=true"

	def __init__(self, parent):
		pywindow.PyWindow.__init__(self, parent, "twitch_signin")
		self.title = "Sign In"
		self.floating = True
		self._t = None
		self._state = ""
		self.user_token = None
		self.content.column(0, weight=1, minsize=30).column(1, weight=1, minsize=30)

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		self.content.place_element(pyelement.PyTextlabel(self.content, "header"), columnspan=2)
		self.content["header"].text = "Sign into twitch account..."
		self.content.place_element(pyelement.PyTextlabel(self.content, "state", {"foreground": "gray"}), row=1, columnspan=2)
		self.content["state"].text = "Press 'continue' to sign in"

		bt = self.content.place_element(pyelement.PyButton(self.content, "initiate"), row=2)
		bt.text = "Continue"
		bt.command = self._goto_autl_url
		bt2 = self.content.place_element(pyelement.PyButton(self.content, "cancel"), row=2, column=1)
		bt2.text = "Cancel"
		bt2.command = self.destroy

	@property
	def user_token(self): return self._token
	@user_token.setter
	def user_token(self, dt): self._token = dt

	def _start_listener(self):
		if self._t is None or not self._t.is_alive():
			print("INFO", "Creating server for capturing token")
			import threading
			self._t = threading.Thread(target=self._run_listener)
			self._t.start()
			self.content["initiate"].accept_input = False

	def _run_listener(self):
		import socket
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._sock.bind(("localhost", 6767))
		self._sock.settimeout(self.TIMEOUT)
		self._sock.listen(1)

		print("INFO", "Waiting for connections on response uri")
		try:
			c = self._sock.accept()[0]
			print(c.recv(1024).decode().split("\n"))
			c.close()
		except socket.timeout:
			print("INFO", "Timed out waiting for response, shutting down server...")
			self._sock.close()
			self.schedule(func=self._on_timeout)
		else:
			self._sock.close()
			self.schedule(func=self.destroy)

	def _on_timeout(self):
		self.content["state"].text = "Request timed out"
		self.content["initiate"].text = "Try again"
		self.content["initiate"].accept_input = True

	def _goto_autl_url(self):
		self._state = generate_random_code()
		import webbrowser
		webbrowser.open(self.auth_url.format(client_id=CLIENT_ID, resp_uri=self.resp_uri, state=self._state, scope="+".join(self.scope)))
		self._start_listener()

	def destroy(self):
		if self._t and self._t.is_alive(): self._t.join()
		pywindow.PyWindow.destroy(self)


class TwitchPlayer(pywindow.PyWindow):
	def __init__(self, parent):
		pywindow.PyWindow.__init__(self, parent, "twitch_overview")
		self.icon = "assets/icon_twitchviewer"
		self.title = "Twitch Overview"
		self.content.column(0, weight=1).row(0, minsize=20)

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		self.content.place_element(pyelement.PyTextlabel(self.content, "status_label"))
		self.content["status_label"].text = "Not signed in"

		self.content.place_element(pyelement.PyButton(self.content, "login_action"), column=1)
		self.content["login_action"].text = "Sign in"
		self.content["login_action"].command = self._do_signin

	def _refresh_account_status(self):
		user_meta = self.configuration.get("userdata")
		if user_meta:
			print("INFO", "Existing user data found, signing in")


	def _do_signin(self):
		if not self.get_window("login_window"):
			sn = TwitchSigninWindow(self)
			self.open_window("login_window", sn)
			@sn.event_handler.WindowDestroy
			def _destroy():
				print("sign in window destoyed", sn.user_token)

	def _do_signout(self):
		self.destroy()
