from ui import pywindow, pyelement, pyimage

CLIENT_ID = "6adynlxibzw3ug8udhyzy6w3yt70pw"
emote_cache = pyimage.ImageCache("emote_cache", "http://static-cdn.jtvnw.net/emoticons/v1/{key}/1.0")
bttv_emote_cache = pyimage.ImageCache("bttv_emote_cache", "https://cdn.betterttv.net/emote/{key}/1x")

user_info_url = "https://api.twitch.tv/helix/users"

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
		self.center_window(250, 120)

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		self.content.place_element(pyelement.PyTextlabel(self.content, "header"), columnspan=2)
		self.content["header"].text = "Sign into twitch account..."
		self.content.place_element(pyelement.PyTextlabel(self.content, "status"), row=1, columnspan=2)
		self.content["status"].text = "Enter access token"
		self.content.place_element(pyelement.PyTextInput(self.content, "token"), row=2, columnspan=2)
		self.content.column(0, weight=1, minsize=30).column(1, weight=1, minsize=30).row(2, weight=1)

		bt = self.content.place_element(pyelement.PyButton(self.content, "get_url"), row=3, columnspan=2)
		bt.text = "Get token"
		bt.command = self._goto_autl_url
		bt = self.content.place_element(pyelement.PyButton(self.content, "submit_btn"), row=4)
		bt.text = "Submit"
		bt.command = self._submit_code
		bt = self.content.place_element(pyelement.PyButton(self.content, "cancel"), row=4, column=1)
		bt.text = "Cancel"
		bt.command = self.destroy

	@property
	def user_token(self): return self._token
	@user_token.setter
	def user_token(self, dt): self._token = dt

	def _goto_autl_url(self):
		self._state = generate_random_code()
		import webbrowser
		webbrowser.open(self.auth_url.format(client_id=CLIENT_ID, resp_uri=self.resp_uri, state=self._state, scope="+".join(self.scope)))
		self.content["status"].text = "State should equal '{}'".format(self._state)

	def _submit_code(self):
		txt = self.content["token"].value
		if txt:
			self.user_token = txt
			self.destroy()


user_logindata, user_meta = ".cache/userdata", ".cache/usermeta"
class TwitchPlayer(pywindow.PyWindow):
	CACHE_EXPIRY = 86400

	def __init__(self, parent):
		pywindow.PyWindow.__init__(self, parent, "twitch_overview")
		self.icon = "assets/icon_twitchviewer"
		self.title = "Twitch Overview"
		self._userlogin = None
		self.content.column(0, weight=1).row(0, minsize=20)
		self._refresh_account_status()

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		self.content.place_element(pyelement.PyTextlabel(self.content, "status_label"))
		self.content["status_label"].text = "Not signed in"

		self.content.place_element(pyelement.PyButton(self.content, "login_action"), column=1)
		self.content["login_action"].text = "Sign in"
		self.content["login_action"].command = self._do_signin

	def _refresh_account_status(self):
		if not self._userlogin:
			try:
				with open(user_logindata, "rb") as file:
					import base64, json
					self._userlogin = json.loads(base64.b85decode(file.read()))
			except FileNotFoundError: return

		if self._userlogin:
			print("INFO", "Existing user data found, updating data")
			import os, time, json

			if not os.path.isfile(user_meta) or time.time() - os.path.getmtime(user_meta) > self.CACHE_EXPIRY:
				import requests
				r = requests.get(user_info_url, headers=self._userlogin)
				try: data = json.loads(r.content.decode())
				except json.JSONDecodeError:
					print("ERROR", "Unknown data format returned, execution cannot continue")
					return self.destroy()

				if r.status_code == 200:
					print("INFO", "User data succesfully received, updating cache and elements")
					self._usermeta = data["data"][0]
					with open(user_meta, "w") as file: json.dump(self._usermeta, file)

				else:
					print("ERROR", "Unexpected status code '{}' received, caused by:".format(r.status_code), data)
					return self.destroy()

			else:
				try:
					with open(user_meta, "r") as file: self._usermeta = json.load(file)
				except json.JSONDecodeError:
					print("INFO", "Cannot parse cached user data, invalidating file")
					os.remove(user_meta)
					self._refresh_account_status()

			try:
				self.content["status_label"].text = "Signed in as {}".format(self._usermeta["display_name"])
				self.content["login_action"].text = "Sign out"
				self.content["login_action"].command = self._do_signout
			except Exception as e: print("ERROR", "Updating profile state:", e)


	def _do_signin(self):
		if not self.get_window("login_window"):
			sn = TwitchSigninWindow(self)
			self.open_window("login_window", sn)
			@sn.event_handler.WindowDestroy
			def _destroy():
				token = sn.user_token
				if token:
					login_data = {"Client-ID": CLIENT_ID, "Authorization": "Bearer {}".format(token)}
					with open(user_logindata, "wb") as file:
						import base64, json
						file.write(base64.b85encode(json.dumps(login_data).encode()))
					self._refresh_account_status()
				else: self.destroy()

	def _do_signout(self):
		import os
		try:
			os.remove(user_logindata)
			os.remove(user_meta)
		except: pass
		self.destroy()
