from ui.qt import pywindow, pyelement, pyworker
import socketserver, threading, os

client = CLIENT_ID = None
relative_path = "modules/twitch/"

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
                import json
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


user_logindata = ".cache/userdata"
def read_logindata():
    try:
        with open(user_logindata, "r") as file:
            import base64, json
            return json.loads(base64.b85decode(file.read()))
    except FileNotFoundError: return None
    except Exception as e: print("ERROR", "While reading login data:", e)

def write_logindata(data):
    if not data: return

    login_data = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {data['access_token']}"}
    try:
        with open(user_logindata, "wb") as file:
            import base64, json
            file.write(base64.b85encode(json.dumps(login_data).encode()))
    except Exception as e: print("ERROR", "While writing login data:", e)

def invalidate_logindata():
    try: os.remove(user_logindata)
    except: pass


class TwitchSigninWindow(pywindow.PyWindow):
    resp_uri = "http://localhost:6767/twitch_auth"
    scope = ["user:edit", "chat:read", "chat:edit"]
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

        inpt = self.add_element("input_token", element_class=pyelement.PyTextInput, row=2)
        inpt.events.EventInteract(self._manual_sign_in)
        btn = self.add_element("btn_manual_signin", element_class=pyelement.PyButton, row=3)
        btn.text = "Sign in with token"
        btn.events.EventInteract(self._manual_sign_in)

        btn = self.add_element("btn_cancel", element_class=pyelement.PyButton, row=4)
        btn.text = "Cancel"
        btn.events.EventInteract(self.destroy)

    def _start_sign_in(self):
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


user_metadata = ".cache/usermeta"
def read_metadata(request=False):
    try:
        with open(user_metadata, "rb") as file:
            import base64, json
            return json.loads(base64.b85decode(file.read()).decode())
    except FileNotFoundError: return request_metadata() if request else None
    except Exception as e: print("ERROR", "While reading user metadata:", e)

user_info_url = "https://api.twitch.tv/helix/users"
user_follows_url = "https://api.twitch.tv/helix/users/follows?from_id={user_id}"
def request_metadata():
    login = read_logindata()
    if not login: return

    try:
        import requests
        r = requests.get(user_info_url, headers=login)
        if r.status_code != 200:
            print("ERROR", "Received invalid status code:", r.status_code, "\n ->", r.json())
            return None

        data = r.json()["data"][0]
        r = requests.get(user_follows_url.format(user_id=data['id']), headers=login)
        if r.status_code != 200:
            print("ERROR", "Received invalid status code:", r.status_code, "\n ->", r.json())
            data["followed"] = []
            return data

        data["followed"] = r.json()["data"]
        return data
    except Exception as e: print("ERROR", "While requesting user metadata:", e)

def write_metadata(data):
    if not data: return

    try:
        with open(user_metadata, "wb") as file:
            import base64, json
            file.write(base64.b85encode(json.dumps(data).encode()))
    except Exception as e: print("ERROR", "While writing user metadata:", e)

def invalidate_metadata():
    try: os.remove(user_metadata)
    except: pass


class TwitchSignOutWorker(pyworker.PyWorker):
    signout_url = "https://id.twitch.tv/oauth2/revoke?client_id={client_id}&token={token}"

    def run(self):
        userdata = read_logindata()
        if userdata:
            import requests
            r = requests.post(self.signout_url.format(client_id=userdata["Client-ID"], token=userdata["Authorization"].split(" ", maxsplit=1)[1]))
            if r.status_code == 200: print("INFO", "Successfully logged out")
            else: print("WARNING", "Failed to deauthorize token:", f"(status={r.status_code}, message={r.content})")
            invalidate_metadata()
            invalidate_logindata()


class TwichOverview(pywindow.PyWindow):
    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, "twitch_overview")
        self.title = "TwitchViewer: Overview"
        self.icon = "assets/icon_twitchviewer.png"
        self._userlogin = self._usermeta = None

        self.layout.row(3, weight=1, minsize=200).column(0, weight=1)
        self.schedule_task(func=self._refresh_status, task_id="refresh_status")

    def create_widgets(self):
        pywindow.PyWindow.create_widgets(self)
        lbl = self.add_element("status", element_class=pyelement.PyTextLabel)
        lbl.text = "Not signed in"
        lbl.set_alignment("center")
        self.add_element("button_signinout", element_class=pyelement.PyButton, column=1)
        self.add_element("sep1", element_class=pyelement.PySeparator, row=1, columnspan=2)

        lbl = self.add_element("followed_label", element_class=pyelement.PyTextLabel, row=2)
        lbl.text = "Followed live channels"
        lbl.set_alignment("center")
        btn = self.add_element("followed_refresh", element_class=pyelement.PyButton, row=2, column=1)
        btn.text = "Refresh"
        btn.accept_input = False
        self.add_element("followed_content", element_class=pyelement.PyScrollableFrame, row=3, columnspan=2)
        self.add_element("sep2", element_class=pyelement.PySeparator, row=4, columnspan=2)

        lbl = self.add_element("custom_label", element_class=pyelement.PyTextLabel, row=5)
        lbl.text = "Join another channel"
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

def create_window():
    if not os.path.isfile(user_metadata): write_metadata(request_metadata())
    client.schedule_task(task_id="show_twitch_overview", create=True)

def destroy_window(): client.schedule_task(task_id="show_twitch_overview")

def initialize(clt, client_id):
    global client, CLIENT_ID
    client = clt
    CLIENT_ID = client_id
    client.add_task(task_id="show_twitch_overview", func=_set_twitch_overview)

def _set_twitch_overview(create=False):
    if create:
        if client.find_window("twitch_overview") is None: client.add_window(window=TwichOverview(client))
    else: client.close_window("twitch_overview")