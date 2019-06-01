from ui import pywindow, pyelement, pyimage, pycontainer

CLIENT_ID = "6adynlxibzw3ug8udhyzy6w3yt70pw"
# all requests done using new twitch API: https://dev.twitch.tv/docs/api/reference/
user_info_url = "https://api.twitch.tv/helix/users"
user_follows_url = "https://api.twitch.tv/helix/users/follows?from_id={user_id}"
user_stream_url = "https://api.twitch.tv/helix/streams?user_id={ids}"
user_game_url = "https://api.twitch.tv/helix/games?id={ids}"

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


class StreamEntry(pycontainer.PyLabelFrame):
	def __init__(self, parent, meta, go_cb):
		pycontainer.PyLabelFrame.__init__(self, parent)
		self._meta = meta

		lbl = self.place_element(pyelement.PyTextlabel(self, "header"))
		lbl.text = self._meta.get("user_name", "?")
		lbl = self.place_element(pyelement.PyTextlabel(self, "stream_title"), row=1)
		lbl.text = self._meta.get("title", "No stream title")
		lbl = self.place_element(pyelement.PyTextlabel(self, "stream_game"), row=2)
		lbl.text = self._meta.get("game_id", "undefined")
		self.row(0, weight=1).row(1, weight=1).column(0, weight=1)

		btn = self.place_element(pyelement.PyButton(self, "goto"), rowspan=4, column=1)
		btn.text = "Open"
		btn.command = lambda : go_cb(self._meta.get("user_name"))
		self.column(2, minsize=50)


user_logindata, user_meta = ".cache/userdata", ".cache/usermeta"
class TwitchPlayer(pywindow.PyWindow):
	CACHE_EXPIRY = 86400

	def __init__(self, parent):
		pywindow.PyWindow.__init__(self, parent, "twitch_overview")
		self.icon = "assets/icon_twitchviewer"
		self.title = "Twitch Overview"
		self._userlogin = None
		self._irc = None
		self._chatwindows = {}
		self.content.column(0, weight=1).row(0, minsize=20)
		self.schedule(func=self._refresh_account_status)

		@self.event_handler.WindowClose
		def _on_window_close():
			if len(self._chatwindows.keys()) > 0: self.hidden = True
			else: self.destroy()

	def create_widgets(self):
		pywindow.PyWindow.create_widgets(self)
		self.content.place_element(pyelement.PyTextlabel(self.content, "status_label"), columnspan=2)
		self.content["status_label"].text = "Not signed in"
		self.content.place_element(pyelement.PyButton(self.content, "login_action"), column=2)
		self.content["login_action"].text = "Sign in"
		self.content["login_action"].command = self._do_signin
		self.content.place_element(pyelement.PySeparator(self.content, "separator1"), row=1, columnspan=3)

		lbl = self.content.place_element(pyelement.PyTextlabel(self.content, "live_channels"), row=2, columnspan=3)
		lbl.text = "Followed live channels"
		self.content.place_element(pyelement.PyTextlabel(self.content, "live_update", {"foreground": "gray"}), row=3)
		bt = self.content.place_element(pyelement.PyButton(self.content, "refresh_btn"), row=3, column=1, columnspan=2)
		bt.text = "Refresh"
		bt.command = self.update_livestreams

		self._live_content = pycontainer.PyScrollableFrame(self.content)
		self.content.place_frame(self._live_content, row=4, columnspan=3)
		self.content.row(4, weight=1).column(1, minsize=50)
		self._live_content.content.column(0, weight=1)
		self._live_content.scrollbar_y = True

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
				data = self._process_request(user_info_url)
				if not data: return
				print("INFO", "User data succesfully received, updating cache and elements")
				self._usermeta = data["data"][0]

				fls = self._process_request(user_follows_url.format(user_id=self._usermeta["id"]))
				self._usermeta["followed"] = fls["data"] if fls else []
				with open(user_meta, "w") as file: json.dump(self._usermeta, file)

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
				self.content["refresh_btn"].accept_input = False
				self.schedule(sec=1, func=self.update_livestreams)
			except Exception as e: print("ERROR", "Updating profile state:", e)

	def _process_request(self, get_url):
		import requests, json
		r = requests.get(get_url, headers=self._userlogin)
		body = r.content.decode()
		try: data = json.loads(body)
		except json.JSONDecodeError: return self._invalid_data()
		if r.status_code != 200: return self._invalid_response(r.status_code, body)
		else: return data

	def _invalid_data(self):
		print("ERROR", "Unknown data format returned, execution cannot continue")
		self.destroy()

	def _invalid_response(self, code, data):
		print("ERROR", "Unexpected status code '{}' received, error body:".format(code), data)
		self.destroy()

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
		try: os.remove(user_logindata)
		except: pass
		try: os.remove(user_meta)
		except: pass

		#todo: unauthorize stored token
		self.destroy()

	def clear_userdata_cache(self, refresh=True):
		""" Remove all cached user metadata, updated data will be requested automatically (unless refresh is set to False) """
		import os
		try:
			os.remove(user_meta)
			if refresh: self._refresh_account_status()
			return True
		except Exception as e: print("ERROR", e); return False

	def update_livestreams(self):
		""" Update the live followed channel list, can be requested several times and each time an updated list will be fetched """
		print("INFO", "Refreshing live channels list")
		self.content["refresh_btn"].accept_input = False
		self.content["live_update"].text = "Fetching..."
		self.schedule(min=1, func=self._enable_refresh)
		follow_data = self._usermeta.get("followed", [])
		follow_channels = "&user_id=".join([c["to_id"] for c in follow_data])
		live_follows = self._process_request(user_stream_url.format(ids=follow_channels))
		if not live_follows:
			self.content["live_update"].text = "Error occured while fetching, try again later"
			return

		live_follows = live_follows["data"]
		self._live_content.clear_content()
		if len(live_follows) == 0: return

		game_set = set([l["game_id"] for l in live_follows])
		game_data = self._process_request(user_game_url.format(ids="&id=".join(game_set)))
		if not game_data: game_data = {}
		else: game_data = {et["id"]: et["name"] for et in game_data["data"]}

		i = 0
		for live_data in live_follows:
			live_data["game_id"] = game_data.get(live_data["game_id"], live_data["game_id"])
			self._live_content.place_frame(StreamEntry(self._live_content.content, live_data, self._open_stream), row=i)
			self._live_content.row(i, weight=1)
			i += 1

		import datetime
		self.content["live_update"].text = datetime.datetime.today().strftime("Last update: %b %d, %Y - %I:%M %p")

	def _enable_refresh(self):
		self.content["refresh_btn"].accept_input = True

	def open_channel(self, channel):
		self._open_stream(channel)
		self.hidden = True

	def destroy(self):
		if self._irc:
			try:
				self._irc.disconnect()
				self._irc.join()
			except Exception as e: print("ERROR", "while stopping IRC client:", e)
		pywindow.PyWindow.destroy(self)

	def _open_stream(self, channel):
		print("INFO", "Opening", channel, "stream")
		if self._irc is None:
			from modules.twitch import twitch_irc
			self._irc = twitch_irc.IRCClient()
			self._irc.connect(self._usermeta["display_name"].lower(), "oauth:" + self._userlogin["Authorization"][7:])

		if not channel in self._chatwindows:
			from modules.twitch import twitch_chatviewer
			vw = twitch_chatviewer.TwitchChatWindow(self)
			self.open_window("twitch_" + channel, vw)
			self._chatwindows[channel] = vw

			@vw.event_handler.WindowDestroy
			def _viewer_destroy(): del self._chatwindows[channel]