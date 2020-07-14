from utilities import messagetypes
import json, os, requests, time

if not os.path.isdir(".cache"): os.mkdir(".cache")

# DEFAULT MODULE VARIABLES
interpreter = client = None

CLIENT_ID = "6adynlxibzw3ug8udhyzy6w3yt70pw"

# === Utilities ===
user_logindata = ".cache/userdata"
def read_logindata():
    try:
        with open(user_logindata, "r") as file:
            import base64
            return json.loads(base64.b85decode(file.read()))
    except FileNotFoundError: return None
    except Exception as e: print("ERROR", "While reading login data:", e)

def write_logindata(data):
    if not data: return

    login_data = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {data['access_token']}"}
    try:
        with open(user_logindata, "wb") as file:
            import base64
            file.write(base64.b85encode(json.dumps(login_data).encode()))
    except Exception as e: print("ERROR", "While writing login data:", e)

def invalidate_logindata():
    try: os.remove(user_logindata)
    except: pass


user_metadata = ".cache/usermeta"
cache_expire = 86400
def read_metadata(request=False):
    try:
        with open(user_metadata, "rb") as file:
            import base64
            return json.loads(base64.b85decode(file.read()).decode())
    except FileNotFoundError: return request_metadata() if request else None
    except Exception as e: print("ERROR", "While reading user metadata:", e)

def metadata_expired():
    return not os.path.isfile(user_metadata) or time.time() - os.path.getmtime(user_metadata) > cache_expire

user_info_url = "https://api.twitch.tv/helix/users"
user_follows_url = "https://api.twitch.tv/helix/users/follows?from_id={user_id}"
def request_metadata():
    login = read_logindata()
    if not login: return

    try:
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
            import base64
            file.write(base64.b85encode(json.dumps(data).encode()))
    except Exception as e: print("ERROR", "While writing user metadata:", e)

def invalidate_metadata():
    try: os.remove(user_metadata)
    except: pass


from . import twitchoverview, twitchchat
def command_twitch(arg, argc):
    if argc > 0:
        twitchchat.open_chat_window(arg[0])
        return messagetypes.Reply(f"Twitch chat for '{arg[0]}' opened")
    else:
        twitchoverview.create_window(client)
        return messagetypes.Reply("Openend twitch overview")

def command_twitch_refresh(arg, argc):
    if argc == 0:
        if twitchoverview.refresh_overview(client) is not None: return messagetypes.Reply("Refreshing live channels")
        else: return messagetypes.Reply("Twitch overview window not found")

commands = {
    "twitch": {
        "": command_twitch,
        "refresh": command_twitch_refresh,
    }
}