import datetime, json, requests, socketserver, subprocess, threading, time
from ui.qt import pywindow, pyelement, pyworker, pyimage

from core import modules
module = modules.Module(__package__)

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
                print("VERBOSE", "Received account data, scheduling signin completion")
                write_logindata(data)
                write_metadata(request_metadata())
                self._window.schedule_task(task_id="signin_data", success=True)
            else:
                print("ERROR", "Ignoring sign in, received account data in invalid state")
                self._window.schedule_task(task_id="signin_data", success=False)

    def stop_server(self):
        print("VERBOSE", "Stopping server")
        self.shutdown()

    def run(self):
        print("VERBOSE", "Server started, waiting for requests")
        try: self.serve_forever()
        except Exception as e: print("ERROR", "While running server:", e)

    def complete(self):
        print("VERBOSE", "Server stopped, doing cleanup")
        self.server_close()
        self._window = None


class TwitchSigninWindow(pywindow.PyWindow):
    resp_uri = "http://localhost:6767/twitch_auth"
    scope = ["user:edit", "user:read:follows", "chat:read", "chat:edit", "channel:moderate", "whispers:read", "whispers:edit"]
    auth_url = "https://id.twitch.tv/oauth2/authorize?response_type=token&client_id={client_id}&redirect_uri={resp_uri}&scope={scope}"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, "twitch_signin")
        self.title = "Sign in"
        self.icon = "assets/blank.png"
        self.add_task(task_id="signin_data", func=self._on_sign_in)

        self._server_worker = TwitchSigninWorker(self)
        self._server_worker.activate()
        self.events.EventWindowClose(self._on_close)
        self.set_geometry(width=235, height=157)

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
        print("VERBOSE", "Started sign in process")
        self["btn_signin"].accept_input = False
        self._server_worker.create_request(self.auth_url.format(client_id=CLIENT_ID, resp_uri=self.resp_uri, scope="+".join(self.scope)))

    def _manual_sign_in(self):
        print("VERBOSE", "Used manual token submission")
        write_logindata({"access_token": self["input_token"].value})
        self._on_sign_in(True)

    def _on_sign_in(self, success):
        if success:
            print("VERBOSE", "Sign in data received, closing window")
            self.destroy()
        else:
            print("VERBOSE", "No data received")
            self["header"].text = "Error, try again..."
            self["btn_signin"].accept_input = True

    def _on_close(self):
        print("VERBOSE", "Sign in window closed, terminating server")
        self._server_worker.stop_server()
        self.parent.schedule_task(task_id="refresh_status")


class TwitchSignOutWorker(pyworker.PyWorker):
    signout_url = "https://id.twitch.tv/oauth2/revoke?client_id={client_id}&token={token}"

    def run(self):
        userdata = read_logindata()
        if userdata:
            r = requests.post(self.signout_url.format(client_id=userdata["Client-ID"], token=userdata["Authorization"].split(" ", maxsplit=1)[1]))
            if r.status_code == 200: print("VERBOSE", "Successfully logged out")
            else: print("WARNING", "Failed to deauthorize token:", f"(status={r.status_code}, message={r.content})")
            invalidate_metadata()
            invalidate_logindata()


THUMBNAIL_SIZE = 128, 64
class TwitchRefreshLiveChannelsWorker(pyworker.PyWorker):
    followed_stream_url = "https://api.twitch.tv/helix/streams/followed?user_id={user_id}"
    def __init__(self, window, auto_active=True):
        pyworker.PyWorker.__init__(self, "twitch_refresh_follows", auto_active)
        self._window = window
        self._data = self._error = self._logindata = None

        self.wait = pyworker.PyWaitCondition()
        self.active = True
        self.repeated = False
        self.wait_time = 15
        if auto_active: self.refresh()

    def refresh(self):
        self._window.refresh_worker_refresh_time = 0
        self.wait.notify_one()

    def run(self):
        with self.wait:
            while self.active:
                current = time.time()
                try: refresh_time = self._window.refresh_worker_refresh_time
                except AttributeError: refresh_time = 0
                wtime = round(current - refresh_time)

                if wtime >= (self.wait_time * 60):
                    print("VERBOSE", "Fetching currently live channels...")
                    self._window.schedule_task(task_id="twitch_start_refresh")
                    res = self._fetch_data()

                    print("VERBOSE", "Fetching complete, refreshing data...")
                    if res: self._window.schedule_task(task_id="twitch_channel_data", data=self._data)
                    else: self._window.schedule_task(task_id="twitch_channel_data", error=self._error)

                    self._window.refresh_worker_refresh_time = time.time()
                    if not self.repeated: break
                    self.wait.wait(min=self.wait_time, sec=round(current-time.time()))
                else: self.wait.wait(sec=(self.wait_time * 60) - wtime)

    def complete(self):
        print("VERBOSE", "Auto refresh worker completed")

    def error(self, error):
        self._window.schedule_task(task_id="twitch_channel_data", error=str(error))

    def _fetch_data(self):
        self._logindata = read_logindata()
        if metadata_expired():
            print("VERBOSE", "User meta cache expired, requesting...")
            metadata = request_metadata()
            if metadata == "Unauthorized":
                self._error = metadata
                return False
            else: write_metadata(metadata)
        else: metadata = read_metadata()

        if metadata is None:
            print("VERBOSE", "No metadata avaiable, cannot fetch data")
            self._error = "Cannot get user metadata"
            return False

        try: req = requests.get(self.followed_stream_url.format(user_id=metadata["id"]), headers=self._logindata)
        except requests.ConnectionError as e:
            print("ERROR", "Failed to get updated channels:", str(e))
            self._error = "Connection failed"
            return False
        else:
            if req.status_code == 401:
                err = req.json().get("error")
                if err == "Unauthorized":
                    print("VERBOSE", "Invalid credentials, signing out")
                    invalidate_logindata()
                    self._error = err
                    return False

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

        for channel in followed_channels:
            thumbnail_url = channel["thumbnail_url"]
            req = requests.get(thumbnail_url.format(width=THUMBNAIL_SIZE[0], height=THUMBNAIL_SIZE[1]))
            if req.status_code == 200: channel["thumbnail"] = req.content
            else: print("ERROR", "Failed to get thumbnail:", f"(status={req.status_code}, message={req.content}")

        self._data = followed_channels
        return True


class StreamEntryFrame(pyelement.PyLabelFrame):
    def __init__(self, parent, data):
        self._data = data
        pyelement.PyLabelFrame.__init__(self, parent, f"entry_{self._data['id']}")
        self.layout.column(1, weight=1, minsize=150).margins(2)

    def create_widgets(self):
        thumbnail = self.add_element("thumbnail", element_class=pyelement.PyTextLabel, rowspan=3)
        thumbnail_img = self._data.get("thumbnail")
        if thumbnail_img:
            pyimage.PyImage(thumbnail, data=thumbnail_img)
            thumbnail.width, thumbnail.height = THUMBNAIL_SIZE

        self.set_label_alignment("center")
        self.label = self._data.get('user_name', "(No username set)")
        lbl2 = self.add_element("title_lbl", element_class=pyelement.PyTextLabel, rowspan=2, column=1)
        lbl2.text = self._data.get('title', "(No title set)")
        lbl2.set_alignment("center")
        lbl2.wrapping = True
        lbl3 = self.add_element("game_lbl", element_class=pyelement.PyTextLabel, row=2, column=1)
        lbl3.text = self._data.get("game_name", "(No game set)")
        lbl3.set_alignment("center")
        lbl3.wrapping = True

        btn = self.add_element("btn_visit", element_class=pyelement.PyButton, row=0, column=2)
        btn.text = "Twitch player \u25b6"
        btn.events.EventInteract(lambda : self.window.open_stream_twitch(self._data["user_name"]))
        browser_available = browser_path_key in module.configuration
        if not browser_available:
            btn.accept_input = False
            btn.text = "No browser set"

        btn2 = self.add_element("btn_visit_alt", element_class=pyelement.PyButton, row=1, column=2)
        btn2.text = "Alternate player \u25b6"
        btn2.events.EventInteract(lambda : self.window.open_stream_alt(self._data["user_name"]))
        if not browser_available or alternate_player_key not in module.configuration:
            btn2.accept_input = False
            btn2.text = "No alternate player"

        start_time = self._data.get("started_at")
        if start_time is not None:
            start_time = datetime.datetime.fromisoformat(start_time.rstrip('Z'))
            uptime = str(datetime.datetime.utcnow() - start_time).split(".", maxsplit=1)[0]
            uptime_lbl = self.add_element("uptime_lbl", element_class=pyelement.PyTextLabel, row=2, column=2)
            uptime_lbl.text = f"\u23f0 {uptime}"
            uptime_lbl.set_alignment("center")

class AutoRefreshFrame(pyelement.PyFrame):
    main_id, check_id, input_id, btn_id = "auto_refresh", "refresh_check", "refresh_delay", "manual_refresh"

    def __init__(self, parent):
        pyelement.PyFrame.__init__(self, parent, AutoRefreshFrame.main_id)
        self.events.EventDestroy(self._on_close)
        self.layout.column(2, weight=1)

    def _on_close(self):
        self.window.configuration["refresh_time"] = self[AutoRefreshFrame.input_id].value

    def create_widgets(self):
        check = self.add_element(AutoRefreshFrame.check_id, element_class=pyelement.PyCheckbox)
        check.text = "Auto refresh every"
        inpt = self.add_element(AutoRefreshFrame.input_id, element_class=pyelement.PyNumberInput, column=1)
        inpt.min = inpt.step = 5
        inpt.max = 900
        inpt.with_value(self.window.configuration.get("refresh_time", 20))
        lbl = self.add_element("min_lbl", element_class=pyelement.PyTextLabel, column=2)
        lbl.text = "minutes"
        lbl.set_alignment("centerV")

        btn = self.add_element(AutoRefreshFrame.btn_id, element_class=pyelement.PyButton, column=3)
        btn.text = "Refresh \u21bb"
        btn.accept_input = False

    @property
    def enabled(self): return self["refresh_check"].checked
    @property
    def delay(self): return int(self["refresh_delay"].value)


TwitchOverviewID = "twitch_overview"
browser_path_key = "&browser_path"
alternate_player_key = "alternate_player_url"
channel_live_command_key = "new_channel_live_command"

class TwichOverview(pywindow.PyWindow):
    follow_channel_text = "Followed live channels\n"

    def __init__(self, parent):
        self._userlogin = self._usermeta = None
        self._refresh_task = self._last_update = None
        self._live_channels = None

        pywindow.PyWindow.__init__(self, parent, TwitchOverviewID)
        self.title = "TwitchViewer: Overview"
        self.icon = "assets/icon_twitchviewer.png"

        self.layout.row(4, weight=1, minsize=200).column(0, weight=1).margins(5)
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

        lbl = self.add_element("followed_label", element_class=pyelement.PyTextLabel, row=2, columnspan=2)
        lbl.text = self.follow_channel_text
        lbl.set_alignment("center")
        refresh_frame = self.add_element(element=AutoRefreshFrame(self), row=3, columnspan=2)
        refresh_frame[AutoRefreshFrame.check_id].events.EventInteract(self._set_repeated_refresh)
        refresh_frame[AutoRefreshFrame.input_id].events.EventInteract(self._delay_repeated_refresh)
        refresh_frame[AutoRefreshFrame.btn_id].events.EventInteract(self.activate_refresh)

        self.add_element("followed_content", element_class=pyelement.PyScrollableFrame, row=4, columnspan=2)

    @property
    def last_updated_time(self):
        if self._last_update is not None: return self._last_update.strftime("Last update: %b %d, %Y - %I:%M %p")
        else: return "Press the refresh button to update"

    def _set_repeated_refresh(self):
        frame = self[AutoRefreshFrame.main_id]
        check, inpt = frame[AutoRefreshFrame.check_id], frame[AutoRefreshFrame.input_id]
        if check.checked:
            print("VERBOSE", "Enabling auto refresh worker")
            if self._refresh_task is not None:
                print("ERROR", "Refresh task already running, aborting...")
                return

            self._refresh_task = TwitchRefreshLiveChannelsWorker(self, False)
            self._delay_repeated_refresh()
            self._refresh_task.repeated = True
            self._refresh_task.activate()
        else:
            print("VERBOSE", "Disabling auto refresh worker")
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
            self._refresh_task.wait.notify_one()

    def _on_refresh_active(self):
        self._set_refresh_status(False)
        self["followed_label"].text = self.follow_channel_text + "Updating..."

    def activate_refresh(self):
        if self._refresh_task: self._refresh_task.refresh()
        else: TwitchRefreshLiveChannelsWorker(self)

    def _set_refresh_status(self, enabled):
        self[AutoRefreshFrame.main_id][AutoRefreshFrame.btn_id].accept_input = enabled

    def _refresh_status(self):
        self._userlogin = read_logindata()
        self._usermeta = read_metadata()
        if self._userlogin:
            print("VERBOSE", "Currently signed in")
            self["status"].text = f"Signed in as {self._usermeta['display_name']}" if self._usermeta else "Signed in"
            btn_signinout = self["button_signinout"]
            btn_signinout.text = "Sign out"
            btn_signinout.events.EventInteract(self.sign_out)

            self["followed_label"].text = self.follow_channel_text + self.last_updated_time
            self._set_refresh_status(True)

        else:
            print("VERBOSE", "Not currently signed in")
            self["status"].text = "Not signed in"
            btn_signinout = self["button_signinout"]
            btn_signinout.text = "Sign in"
            btn_signinout.events.EventInteract(self.sign_in)

            self["followed_label"].text = self.follow_channel_text + "Sign in to get started"
            self._set_refresh_status(False)

    def sign_in(self):
        print("VERBOSE", "Opening sign in window")
        self.add_window(window=TwitchSigninWindow(self))

    def sign_out(self):
        print("VERBOSE", "Signing out of account")
        TwitchSignOutWorker("twitch_signout")
        self.destroy()

    def _fill_channel_data(self, data=None, error=None):
        if error is not None:
            print("VERBOSE", "Failed to get updated live channel data")
            if data is not None: print("WARNING", "Received data even though an error occured")
            if error == "Unauthorized":
                self["followed_label"].text = self.follow_channel_text + "Login information no longer valid, please sign in again"
                self._refresh_status()
                return

            self["followed_label"].text = self.follow_channel_text + self.last_updated_time + "\nAn error occured, try again later"
            self._set_refresh_status(True)

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
                cmd = module.configuration.get(channel_live_command_key)
                if cmd: module.interpreter.put_command(cmd)
            self._live_channels = {channel['user_id']: channel for channel in data}

            if len(data) == 0:
                end_label.text = "No channels live"
                end_label.set_alignment("centerH")
            self._set_refresh_status(True)

        else: raise ValueError("Missing 'data' or 'error' keyword")

    def open_stream_twitch(self, channel):
        print("VERBOSE", "Opening stream for", channel)
        browser_path = module.configuration.get(browser_path_key)
        if browser_path: subprocess.run(f'"{browser_path}" https://twitch.tv/{channel}', shell=True)

    def open_stream_alt(self, channel):
        print("VERBOSE", "Opening stream to", channel, "with alternate player")
        browser_path = module.configuration.get(browser_path_key)
        alt_url = module.configuration.get(alternate_player_key)
        if browser_path and alt_url: subprocess.run(f'"{browser_path}" {alt_url.format(channel=channel)}', shell=True)

def initialize():
    module.configuration.get_or_create(browser_path_key, "")
    module.configuration.get_or_create(alternate_player_key, "")
    module.configuration.get_or_create(channel_live_command_key, "")

def create_window(client):
    if not read_metadata(): write_metadata(request_metadata())
    if client.find_window(TwitchOverviewID) is None: client.add_window(window_class=TwichOverview)

def refresh_overview(client):
    window = client.find_window(TwitchOverviewID)
    if window is not None:
        window.activate_refresh()
        return True
    return False