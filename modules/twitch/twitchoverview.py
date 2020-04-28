from ui.qt import pywindow, pyelement, pyworker, pyimage
import json, requests, socketserver, threading, os

client = None
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
    def __init__(self, window):
        pyworker.PyWorker.__init__(self, "twitch_refresh_follows")
        self._window = window
        self._data = self._error = None
        self._logindata = read_logindata()

    def run(self):
        print("INFO", "Fetching currently live channels...")
        res = self.fetch_data()

        print("INFO", "Fetching complete, refreshing data")
        if res: self._window.schedule_task(task_id="twitch_channel_data", data=self._data)
        else: self._window.schedule_task(task_id="twitch_channel_data", error=self._error)

    def fetch_data(self):
        if metadata_expired():
            print("INFO", "User meta cache expired, requesting")
            metadata = request_metadata()
            write_metadata(metadata)
        else: metadata = read_metadata()

        followed_channels = [c["to_id"] for c in metadata["followed"]]
        req = requests.get(self.followed_stream_url.format(ids="&user_id=".join(followed_channels)), headers=self._logindata)
        if req.status_code != 200:
            print("ERROR", "Got status code", req.status_code, "while requesting followed channels")
            self._error = req.content
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
            self._error = req.content
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

        btn = self.add_element("btn_visit", element_class=pyelement.PyButton, rowspan=3, column=2)
        btn.text = "Open"
        btn.events.EventInteract(self._open_stream)
        self.layout.column(1, weight=1, minsize=100)
        self.height = 100

    def _open_stream(self):
        print("INFO", "Opening stream to", self._data['user_name'])


class TwichOverview(pywindow.PyWindow):
    follow_channel_text = "Followed live channels\n"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, "twitch_overview")
        self.title = "TwitchViewer: Overview"
        self.icon = "assets/icon_twitchviewer.png"
        self._userlogin = self._usermeta = None

        self.layout.row(3, weight=1, minsize=200).column(0, weight=1)
        self.schedule_task(func=self._refresh_status, task_id="refresh_status")
        self.add_task(task_id="twitch_channel_data", func=self._fill_channel_data)

    def create_widgets(self):
        pywindow.PyWindow.create_widgets(self)
        lbl = self.add_element("status", element_class=pyelement.PyTextLabel)
        lbl.text = "Not signed in"
        lbl.set_alignment("center")
        self.add_element("button_signinout", element_class=pyelement.PyButton, column=1)
        self.add_element("sep1", element_class=pyelement.PySeparator, row=1, columnspan=2)

        lbl = self.add_element("followed_label", element_class=pyelement.PyTextLabel, row=2)
        lbl.text = self.follow_channel_text
        lbl.set_alignment("center")
        btn = self.add_element("followed_refresh", element_class=pyelement.PyButton, row=2, column=1)
        btn.text = "Refresh"
        btn.accept_input = False
        @btn.events.EventInteract
        def _on_refresh():
            TwitchRefeshLiveChannelsWorker(self)
            lbl.text = self.follow_channel_text + "Updating..."
            btn.accept_input = False

        self.add_element("followed_content", element_class=pyelement.PyScrollableFrame, row=3, columnspan=2)
        self.add_element("sep2", element_class=pyelement.PySeparator, row=4, columnspan=2)

        lbl2 = self.add_element("custom_label", element_class=pyelement.PyTextLabel, row=5)
        lbl2.text = "Join another channel"
        custom_inpt = self.add_element("custom_channel", element_class=pyelement.PyTextInput, row=5, column=1)
        custom_inpt.accept_input = False

    def _refresh_status(self):
        self._userlogin = read_logindata()
        self._usermeta = read_metadata()
        if self._userlogin:
            print("INFO", "Currently signed in")
            self["status"].text = f"Signed in as {self._usermeta['display_name']}" if self._usermeta else "Signed in"
            btn_signinout = self["button_signinout"]
            btn_signinout.text = "Sign out"
            btn_signinout.events.EventInteract(self.sign_out)
            self["followed_refresh"].accept_input = True

        else:
            print("INFO", "Not currently signed in")
            self["status"].text = "Not signed in"
            btn_signinout = self["button_signinout"]
            btn_signinout.text = "Sign in"
            btn_signinout.events.EventInteract(self.sign_in)
            self["followed_refresh"].accept_input = False

    def sign_in(self):
        print("INFO", "Opening sign in window")
        sign_in = self.add_window(window=TwitchSigninWindow(self))
        @sign_in.events.EventWindowDestroy
        def _on_signed_in(): self.schedule_task(task_id="refresh_status")

    def sign_out(self):
        print("INFO", "Signing out of account")
        TwitchSignOutWorker("twitch_signout")
        self.destroy()

    def _fill_channel_data(self, data=None, error=None):
        if data:
            print("INFO", "Got updated live channel data")
            import datetime
            self["followed_label"].text = self.follow_channel_text + datetime.datetime.today().strftime("Last update: %b %d, %Y - %I:%M %p")
            content = self["followed_content"]
            for c in list(content.children): content.remove_element(c.element_id)

            index = 0
            for channel in data:
                content.add_element(element=StreamEntryFrame(content, channel), row=index)
                index += 1
            self.schedule_task(min=1, func=self._enable_refresh)

        elif error:
            print("INFO", "Failed to get updated live channel data")
            self["followed_label"].text = self.follow_channel_text + "An error occured"
            self._enable_refresh()

        else: raise ValueError("Missing 'data' or 'error' keyword")

    def _enable_refresh(self): self["followed_refresh"].accept_input = True

def create_window():
    if not read_metadata(): write_metadata(request_metadata())
    client.schedule_task(task_id="show_twitch_overview", create=True)

def destroy_window(): client.schedule_task(task_id="show_twitch_overview")

def initialize(clt):
    global client
    client = clt
    client.add_task(task_id="show_twitch_overview", func=_set_twitch_overview)

def _set_twitch_overview(create=False):
    if create:
        if client.find_window("twitch_overview") is None: client.add_window(window=TwichOverview(client))
    else: client.close_window("twitch_overview")