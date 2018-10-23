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
	r = requests.get("https://www.youtube.com/results?search_query={}".format(query))

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
	else: print("WARNING", "Invalid respone from server '{}':".format(r.status_code), r.reason)
	return res

def convert(url):
	ensure_yt()
	global yt
	try:
		return yt.download([url])
	except Exception as e:
		print("INFO", "Passed argument was not a valid url:", e)
		return -1
# --- END OF HELPER FUNCTIONS

def command_youtube_get(arg, argc):
	if argc > 0:
		if argc == 1:
			print("INFO", "Only one argument found, this could be a url")
			if not convert(arg[0]): return messagetypes.Reply("File downloaded")

		arg = " ".join(arg)
		print("INFO", "Searching youtube for", arg)
		ls = search(arg)
		res, off = [], []
		for title, link, desc in ls:
			link = link[9:]
			vd = ("  - " + title + ": " + link, link)
			if desc.startswith("Provided to YouTube by"): off.append(vd)
			else: res.append(vd)

		if len(off) > 0:
			if len(off) == 1 and not convert(off[0][1]): return messagetypes.Reply("Official song found and downloaded")
			else: return messagetypes.Reply("Found official videos:\n" + "\n".join([i[0] for i in off]))
		if len(res) > 0: return messagetypes.Reply("Found several videos:\n" + "\n".join([i[0] for i in res]))
		else: return messagetypes.Reply("No videos found")

commands = {
	"youtube": {
		"get": command_youtube_get
	}
}