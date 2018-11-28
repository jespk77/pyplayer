from utilities import messagetypes

# DEFAULT MODULE VARIABLES
priority = 10
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
yt = None
download_options = {
    "format": "bestaudio/best",
	"outtmpl": "%(title)s.%(ext)s",
    "postprocessors": [{
		"key": "FFmpegExtractAudio",
		"preferredcodec": "mp3",
		"preferredquality": "320"
    }]
}

# --- MODULE HELPER FUNCTIONS ---
def ensure_yt():
	global yt, download_options
	if yt is None:
		import youtube_dl, os
		dir = client["directory"].get("youtube")
		if dir is not None: download_options["outtmpl"] = os.path.join(dir, download_options["outtmpl"])
		yt = youtube_dl.YoutubeDL(download_options)

def _check_link(tag):
	if tag.has_attr("class"):
		if tag.name == "a": return "yt-uix-tile-link" in tag["class"]
		elif tag.name == "div": return "yt-lockup-description" in tag["class"]
	return False

def search(query):
	import requests
	query = query.replace(" ", "+")
	try: r = requests.get("https://www.youtube.com/results?search_query={}".format(query))
	except Exception as e:
		print("ERROR", "Executing Youtube request:", e)
		return None

	res = []
	if r.status_code == 200:
		from bs4 import BeautifulSoup
		html = BeautifulSoup(r.content, features="html.parser")
		ls = iter(html.find_all(_check_link))
		while True:
			try:
				header, desc = next(ls), next(ls)
				if header["href"].startswith("/"): res.append((header["title"], header["href"], str(desc.contents[0])))
			except StopIteration: break
			except KeyError: pass
			except Exception as e: print("ERROR", "Parsing youtube html tag:", e)
	else: print("WARNING", "Invalid response from server '{}':".format(r.status_code), r.reason)
	return res

def convert(url, filename=None):
	if not filename: filename = download_options["outtmpl"]

	ensure_yt()
	global yt
	try:
		yt.params["outtmpl"] = filename + ".%(ext)s"
		return yt.download([url])
	except Exception as e:
		print("INFO", "Passed argument was not a valid url:", e)
		return -1

def process_song(cmd, data=None, url=None, path=None):
	import os
	cmd = " ".join(cmd)
	if path is None: path = client["directory"].get("youtube")
	res = convert(url, os.path.join(path, cmd))
	if res == 0:
		if path is not None: interpreter.put_command("player {} {}".format(path, cmd))
		return messagetypes.Reply("Song downloaded as '{}'".format(cmd))
	else: return messagetypes.Reply("Error downloading file: code {}".format(res))

def handle_url(value, data=None, path=None):
	if value is not None and data is not None:
		return messagetypes.Question("What should the file be named?", process_song, text=value, url=data[0], path=path)
	else: return messagetypes.Reply("Nothing found")
# --- END OF HELPER FUNCTIONS

def command_youtube_find(arg, argc, path=None):
	if argc > 0:
		if argc > 1 and arg[-1] == "all":
			scan_official = False
			arg.pop(-1)
		else: scan_official = True

		arg = " ".join(arg)
		ls = search(arg)
		if ls is None: return messagetypes.Reply("There was an error looking for file, see log for details...")

		res = []
		for title, link, desc in ls: res.append((title, link[9:], desc))
		if scan_official:
			officals = [(title, link, desc) for title, link, desc in res if desc.startswith("Provided to YouTube by")]
			if len(officals) > 0: return messagetypes.Select("Found official videos:", handle_url, choices=officals, path=path)
		return messagetypes.Select("Found multiple videos:", handle_url, choices=res, path=path)

commands = {
	"youtube": {
		"find": command_youtube_find
	}
}