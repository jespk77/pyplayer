from ui.qt import pywindow, pyelement, pyworker, pyimage
import json, requests, socketserver, threading, os

relative_path = "modules/twitch/"
from . import CLIENT_ID, read_logindata, write_logindata, invalidate_logindata
from . import read_metadata, request_metadata, write_metadata, invalidate_metadata, metadata_expired

STATE_LENGTH = 25
def generate_state():
    import random
    return "".join([random.choice("aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ0123456789") for _ in range(STATE_LENGTH)])

class SignInRequestHandler(socketserver.BaseRequestHandler):
    ok_message = b'HTTP/1.1 200 OK\r\n'
    reply_message = ok_message + b'Content-Type:text/html\r\n\r\n'
    empty_message = b'HTTP/1.1 404 NOT FOUND\r\n\r\n'
    error_message = b'HTTP/1.1 400 ERROR'

    def __init__(self, request, client_address, server):
        socketserver.BaseRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        header = self.request.recv(1024).decode().split("\r\n")
        try:
            http_header = header[0].split(" ")

            url, method = http_header[1], http_header[0]
            if method == "GET":
                html = self.server.get_page(url)
                self.request.send(self.reply_message)
                self.request.send(html)
            elif method == "POST" and url == "/token":
                try:
                    data = json.loads(header[-1])
                    self.request.send(self.ok_message)
                    self.server.set_account_data(data)
                except json.JSONDecodeError: self.request.send(self.error_message)
        except IndexError: pass


class TwitchSigninWorker(pyworker.PyWorker, socketserver.TCPServer):
    def __init__(self, window):
        pyworker.PyWorker.__init__(self, "twitch_signin", False)
        self._window = window
        self._state_event = threading.Lock()
        self._state = None
        socketserver.TCPServer.__init__(self, ("localhost", 6767), SignInRequestHandler)

        self._content = {
            "/twitch_auth": "server/token_get.html",
            "/complete": "server/token_complete.html",
        }

    def get_page(self, url):
        page = self._content.get(url)
        if page is not None:
            if isinstance(page, str):
                with open(relative_path + page, "r") as file: self._content[url] = file.read().encode()
                return self._content[url]
            return page
        return b''

    def create_request(self, url):
        with self._state_event:
            self._state = generate_state()
            import webbrowser
            webbrowser.open(url + f"&state={self._state}")

    def set_account_data(self, data):
        with self._state_event:
            if data.get("state") == self._state:
                print("INFO", "Received account data, scheduling signin completion")
                write_logindata(data)
                write_metadata(request_metadata())
                self._window.schedule_task(task_id="signin_data", success=True)
            else:
                print("ERROR", "Ignoring sign in, received account data in invalid state")
                self._window.schedule_task(task_id="signin_data", success=False)

    def stop_server(self):
        print("INFO", "Stopping server")
        self.shutdown()

    def run(self):
        print("INFO", "Server started, waiting for requests")
        try: self.serve_forever()
        except Exception as e: print("ERROR", "While running server:", e)

    def complete(self):
        print("INFO", "Server stopped, doing cleanup")
        self.server_close()
        self._window = None


class TwitchSigninWindow(pywindow.PyWindow):
    resp_uri = "http://localhost:6767/twitch_auth"
    scope = ["user:edit", "chat:read", "chat:edit", "channel:moderate", "whispers:read", "whispers:edit"]
    auth_url = "https://id.twitch.tv/oauth2/authorize?response_type=token&client_id={client_id}&redirect_uri={resp_uri}&scope={scope}&force_verify=true"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, "twitch_signin")
        self.title = "Sign in"
        self.icon = "assets/blank.png"
        self.add_task(task_id="signin_data", func=self._on_sign_in)

        self._server_worker = TwitchSigninWorker(self)
        self._server_worker.activate()
        self.events.EventWindowClose(self._on_close)

    def create_widgets(self):
        pywindow.PyWindow.create_widgets(self)
        lbl = self.add_element("header", element_class=pyelement.PyTextLabel)
        lbl.text = "Sign into twitch account, either through a browser or by manually submitting a token."
        lbl.wrapping = True

        btn = self.add_element("btn_signin", element_class=pyelement.PyButton, row=1)
        btn.text = "Sign in with browser"
        btn.events.EventInteract(self._start_sign_in)

        inpt = self.add_element(element=pyelement.PyTextInput(self, "input_token", True), row=2)
        inpt.events.EventInteract(self._manual_sign_in)
        btn2 = self.add_element("btn_manual_signin", element_class=pyelement.PyButton, row=3)
        btn2.text = "Sign in with token"
        btn2.events.EventInteract(self._manual_sign_in)

        btn3 = self.add_element("btn_cancel", element_class=pyelement.PyButton, row=4)
        btn3.text = "Cancel"
        btn3.events.EventInteract(self.destroy)

    def _start_sign_in(self):
        print("INFO", "Started sign in process")
        self["btn_signin"].accept_input = False
        self._server_worker.create_request(self.auth_url.format(client_id=CLIENT_ID, resp_uri=self.resp_uri, scope="+".join(self.scope)))

    def _manual_sign_in(self):
        print("INFO", "Used manual token submission")
        write_logindata({"access_token": self["input_token"].value})
        self._on_sign_in(True)

    def _on_sign_in(self, success):
        if success:
            print("INFO", "Sign in data received, closing window")
            self.destroy()
        else:
            print("INFO", "No data received")
            self["header"].text = "Error, try again..."
            self["btn_signin"].accept_input = True

    def _on_close(self):
        print("INFO", "Sign in window closed, terminating server")
        self._server_worker.stop_server()


class TwitchSignOutWorker(pyworker.PyWorker):
    signout_url = "https://id.twitch.tv/oauth2/revoke?client_id={client_id}&token={token}"

    def run(self):
        userdata = read_logindata()
        if userdata:
            r = requests.post(self.signout_url.format(client_id=userdata["Client-ID"], token=userdata["Authorization"].split(" ", maxsplit=1)[1]))
            if r.status_code == 200: print("INFO", "Successfully logged out")
            else: print("WARNING", "Failed to deauthorize token:", f"(status={r.status_code}, message={r.content})")
            invalidate_metadata()
            invalidate_logindata()


THUMBNAIL_SIZE = 128, 64
class TwitchRefeshLiveChannelsWorker(pyworker.PyWorker):
    followed_stream_url = "https://api.twitch.tv/helix/streams?user_id={ids}"
    followed_game_url = "https://api.twitch.tv/helix/games?id={ids}"
    def __init__(self, window, auto_active=True):
        pyworker.PyWorker.__init__(self, "twitch_refresh_follows", auto_active)
        self._window = window
        self._data = self._error = self._logindata = None

        self.wait = pyworker.PyWaitCondition()
        self.active = True
        self.repeated = False
        self.wait_time = 15

    def run(self):
        with self.wait:
            while self.active:
                print("VERBOSE", "Fetching currently live channels...")
                self._window.schedule_task(task_id="twitch_start_refresh")
                res = self._fetch_data()

                print("VERBOSE", "Fetching complete, refreshing data...")
                if res: self._window.schedule_task(task_id="twitch_channel_data", data=self._data)
                else: self._window.schedule_task(task_id="twitch_channel_data", error=self._error)

                if not self.repeated: break
                # regular fetch takes about 3 seconds, so try to incorporate that in the wait time
                self.wait.wait(min=self.wait_time, sec=-3)

    def complete(self):
        print("INFO", "Auto refresh worker completed")

    def error(self, error):
        self._window.schedule_task(task_id="twitch_channel_data", error=str(error))

    def _fetch_data(self):
        self._logindata = read_logindata()
        if metadata_expired():
            print("VERBOSE", "User meta cache expired, requesting...")
            metadata = request_metadata()
            write_metadata(metadata)
        else: metadata = read_metadata()

        followed_channels = [c["to_id"] for c in metadata["followed"]]
        if len(followed_channels) == 0:
            self._data = []
            return True

        req = requests.get(self.followed_stream_url.format(ids="&user_id=".join(followed_channels)), headers=self._logindata)
        if req.status_code != 200:
            print("ERROR", "Got status code", req.status_code, "while requesting followed channels")
            self._error = req.text
            print("ERROR", "->", req.content)
            return False

        try: followed_channels = json.loads(req.content)["data"]
        except (json.JSONDecodeError, KeyError) as e:
            print("ERROR", "Processing reply:", e)
            self._error = e.msg
            return False

        followed_games = set([channel["game_id"] for channel in followed_channels])
        req = requests.get(self.followed_game_url.format(ids="&id=".join(followed_games)), headers=self._logindata)
        if req.status_code != 200:
            print("ERROR", "Got status code", req.status_code, "while requesting followed games")
            self._error = req.text
            print("ERROR", "->", req.content)
            return False

        try: followed_games = {game["id"]: game["name"] for game in json.loads(req.content)["data"]}
        except (json.JSONDecodeError, KeyError) as e:
            print("ERROR", "Processing followed games respone:", e)
            self._error = e.msg
            return False

        for channel in followed_channels:
            game_name = followed_games.get(channel["game_id"])
            if game_name: channel["game_id"] = game_name
            else: del channel["game_id"]

            thumbnail_url = channel["thumbnail_url"]
            req = requests.get(thumbnail_url.format(width=THUMBNAIL_SIZE[0], height=THUMBNAIL_SIZE[1]))
            if req.status_code == 200: channel["thumbnail"] = req.content
            else: print("INFO", "Failed to get thumbnail:", f"(status={req.status_code}, message={req.content}")

        self._data = followed_channels
        return True


class StreamEntryFrame(pyelement.PyLabelFrame):
    def __init__(self, parent, data):
        pyelement.PyLabelFrame.__init__(self, parent, f"entry_{data['id']}")
        self._data = data

        thumbnail = self.add_element("thumbnail", element_class=pyelement.PyTextLabel, rowspan=3)
        thumbnail_img = data.get("thumbnail")
        if thumbnail_img:
            pyimage.PyImage(thumbnail, data=thumbnail_img)
            thumbnail.width, thumbnail.height = THUMBNAIL_SIZE

        lbl1 = self.add_element("user_lbl", element_class=pyelement.PyTextLabel, row=0, column=1)
        lbl1.text = data.get('user_name', "(No username set)")
        lbl1.set_alignment("center")
        lbl1.wrapping = True
        lbl2 = self.add_element("title_lbl", element_class=pyelement.PyTextLabel, row=1, column=1)
        lbl2.text = data.get('title', "(No title set)")
        lbl2.set_alignment("center")
        lbl2.wrapping = True
        lbl3 = self.add_element("game_lbl", element_class=pyelement.PyTextLabel, row=2, column=1)
        lbl3.text = data.get("game_id", "(No game set)")
        lbl3.set_alignment("center")
        lbl3.wrapping = True

        btn = self.add_element("btn_visit", element_class=pyelement.PyButton, row=0, column=2)
        btn.text = "Open (Twitch)"
        btn.events.EventInteract(lambda : self.window.open_stream_twitch(self._data["user_name"]))
        browser_available = self.window.configuration.get("browser_path") is not None
        if not browser_available:
            btn.accept_input = False
            btn.text = "No 'browser_path'"

        btn2 = self.add_element("btn_visit_alt", element_class=pyelement.PyButton, row=1, column=2)
        btn2.text = "Open (Alternate twitch)"
        btn2.events.EventInteract(lambda : self.window.open_stream_alt(self._data["user_name"]))
        if not browser_available:
            btn2.accept_input = False
            btn2.text = "No 'browser_path'"
        if self.window.configuration.get("alternate_player_url") is None:
            btn2.accept_input = False
            btn2.text = "No 'alternate_player_url'"
        self.layout.column(1, weight=1, minsize=150)


class AutoRefreshFrame(pyelement.PyFrame):
    main_id, check_id, input_id = "auto_refresh", "refresh_check", "refresh_delay"

    def __init__(self, parent):
        pyelement.PyFrame.__init__(self, parent, AutoRefreshFrame.main_id)
        check = self.add_element(AutoRefreshFrame.check_id, element_class=pyelement.PyCheckbox)
        check.text = "Auto refresh every"
        inpt = self.add_element(AutoRefreshFrame.input_id, element_class=pyelement.PyTextInput, column=1)
        inpt.width = 25
        inpt.with_format_str("00").with_value(20)
        lbl = self.add_element("min_lbl", element_class=pyelement.PyTextLabel, column=2)
        lbl.text = "minutes"
        lbl.set_alignment("centerV")
        self.layout.column(2, weight=1)

    @property
    def enabled(self): return self["refresh_check"].checked
    @property
    def delay(self): return max(10, int(self["refresh_delay"].value))


TwitchOverviewID = "twitch_overview"
class TwichOverview(pywindow.PyWindow):
    follow_channel_text = "Followed live channels\n"

    def __init__(self, parent):
        self._userlogin = self._usermeta = None
        self._refresh_task = self._last_update = None
        self._live_channels = None

        pywindow.PyWindow.__init__(self, parent, TwitchOverviewID)
        self.title = "TwitchViewer: Overview"
        self.icon = "assets/icon_twitchviewer.png"

        self.layout.row(4, weight=1, minsize=200).column(0, weight=1)
        self.schedule_task(func=self._refresh_status, task_id="refresh_status")
        self.add_task(task_id="twitch_channel_data", func=self._fill_channel_data)
        self.add_task(task_id="twitch_start_refresh", func=self._on_refresh_active)

    def create_widgets(self):
        pywindow.PyWindow.create_widgets(self)
        lbl = self.add_element("status", element_class=pyelement.PyTextLabel)
        lbl.text = "Not signed in"
        lbl.set_alignment("center")
        self.add_element("button_signinout", element_class=pyelement.PyButton, column=1)
        self.add_element("sep1", element_class=pyelement.PySeparator, row=1, columnspan=2)

        lbl = self.add_element("followed_label", element_class=pyelement.PyTextLabel, row=2)
        lbl.text = self.follow_channel_text + self.last_updated_time
        lbl.set_alignment("center")
        refresh_frame = self.add_element(element=AutoRefreshFrame(self), row=3)
        refresh_frame["refresh_check"].events.EventInteract(self._set_repeated_refresh)
        refresh_frame["refresh_delay"].events.EventInteract(self._delay_repeated_refresh)

        btn = self.add_element("followed_refresh", element_class=pyelement.PyButton, row=2, column=1, rowspan=2)
        btn.text = "Refresh"
        btn.accept_input = False
        btn.events.EventInteract(self.activate_refresh)
        self.add_element("followed_content", element_class=pyelement.PyScrollableFrame, row=4, columnspan=2)

    @property
    def last_updated_time(self):
        if self._last_update is not None: return self._last_update.strftime("Last update: %b %d, %Y - %I:%M %p")
        else: return "Press the refresh button to update"

    def _set_repeated_refresh(self):
        frame = self[AutoRefreshFrame.main_id]
        check, inpt = frame[AutoRefreshFrame.check_id], frame[AutoRefreshFrame.input_id]
        if check.checked:
            print("INFO", "Enabling auto refresh worker")
            if self._refresh_task is not None:
                print("ERROR", "Refresh task already running, aborting...")
                return

            self._refresh_task = TwitchRefeshLiveChannelsWorker(self, False)
            self._delay_repeated_refresh()
            self._refresh_task.repeated = True
            self._refresh_task.activate()
        else:
            print("INFO", "Disabling auto refresh worker")
            if self._refresh_task is not None:
                with self._refresh_task.wait: self._refresh_task.active = False
                self._refresh_task.wait.notify_one()
                self._refresh_task = None

    def _delay_repeated_refresh(self):
        frame = self[AutoRefreshFrame.main_id]
        if self._refresh_task is None:
            print("ERROR", "Refresh delay updated while no refresh task was set, aborting...")
            return

        if frame.delay != self._refresh_task.wait_time:
            print("VERBOSE", "Updating refresh delay from", self._refresh_task.wait_time, "to", frame.delay)
            with self._refresh_task.wait: self._refresh_task.wait_time = frame.delay
            frame[AutoRefreshFrame.input_id].value = self._refresh_task.wait_time

    def _on_refresh_active(self):
        self["followed_refresh"].accept_input = False
        self["followed_label"].text = self.follow_channel_text + "Updating..."

    def activate_refresh(self):
        if self._refresh_task: self._refresh_task.wait.notify_one()
        else: TwitchRefeshLiveChannelsWorker(self)

    def _refresh_status(self):
        self._userlogin = read_logindata()
        self._usermeta = read_metadata()
        if self._userlogin:
            print("VERBOSE", "Currently signed in")
            self["status"].text = f"Signed in as {self._usermeta['display_name']}" if self._usermeta else "Signed in"
            btn_signinout = self["button_signinout"]
            btn_signinout.text = "Sign out"
            btn_signinout.events.EventInteract(self.sign_out)
            self["followed_refresh"].accept_input = True

        else:
            print("VERBOSE", "Not currently signed in")
            self["status"].text = "Not signed in"
            btn_signinout = self["button_signinout"]
            btn_signinout.text = "Sign in"
            btn_signinout.events.EventInteract(self.sign_in)
            self["followed_refresh"].accept_input = False

    def sign_in(self):
        print("VERBOSE", "Opening sign in window")
        sign_in = self.add_window(window=TwitchSigninWindow(self))
        @sign_in.events.EventWindowDestroy
        def _on_signed_in(): self.schedule_task(task_id="refresh_status")

    def sign_out(self):
        print("VERBOSE", "Signing out of account")
        TwitchSignOutWorker("twitch_signout")
        self.destroy()

    def _fill_channel_data(self, data=None, error=None):
        if error is not None:
            print("VERBOSE", "Failed to get updated live channel data")
            if data is not None: print("WARNING", "Received data even though an error occured")
            self["followed_label"].text = self.follow_channel_text + self.last_updated_time + "\nAn error occured, try again later"
            self._enable_refresh()

        elif data is not None:
            print("VERBOSE", "Got updated live channel data")
            import datetime
            self._last_update = datetime.datetime.today()
            self["followed_label"].text = self.follow_channel_text + self.last_updated_time
            content = self["followed_content"]
            for c in content.children: content.remove_element(c.element_id)

            index, new_channel = 0, False
            for channel in data:
                if not new_channel and self._live_channels is not None: new_channel = channel['user_id'] not in self._live_channels
                content.add_element(element=StreamEntryFrame(content, channel), row=index)
                content.layout.row(index, weight=0)
                index += 1
            end_label = content.add_element("filler", element_class=pyelement.PyTextLabel,row=index)
            content.layout.row(index, weight=1)

            if new_channel:
                print("VERBOSE", "Found new channel in the live list")
                cmd = self.cfg.get_or_create("event-new_channel_live", "")
                if cmd:
                    from . import interpreter
                    interpreter.put_command(cmd)
            self._live_channels = {channel['user_id']: channel for channel in data}

            if len(data) == 0:
                end_label.text = "No channels live"
                end_label.set_alignment("centerH")
            self._enable_refresh()

        else: raise ValueError("Missing 'data' or 'error' keyword")

    def _enable_refresh(self): self["followed_refresh"].accept_input = True

    def open_stream_twitch(self, channel):
        print("INFO", "Opening stream for", channel)
        browser_path = self.window.configuration.get("browser_path")
        if browser_path: os.system(f'"{browser_path}" https://twitch.tv/{channel}')

    def open_stream_alt(self, channel):
        print("INFO", "Opening stream to", channel, "with alternate player")
        browser_path = self.window.configuration.get("browser_path")
        alt_url = self.window.configuration.get("alternate_player_url")
        if browser_path and alt_url: os.system(f'"{browser_path}" {alt_url.format(channel=channel)}')

def create_window(client):
    if not read_metadata(): write_metadata(request_metadata())
    if client.find_window(TwitchOverviewID) is None: client.add_window(window_class=TwichOverview)

def refresh_overview(client):
    window = client.find_window(TwitchOverviewID)
    if window is not None:
        window.activate_refresh()
        return True
    return False