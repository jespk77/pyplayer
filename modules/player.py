import enum
import os
from datetime import datetime
from multiprocessing import Queue

from modules.utilities.mediaplayer import MediaPlayer
from utilities import messagetypes, song_tracker, history

# DEFAULT MODULE VARIABLES
interpreter = client = None

# MODULE SPECIFIC VARIABLES
media_player = MediaPlayer()
song_queue = Queue()
song_history = history.History()
invalid_cfg = messagetypes.Reply("Invalid directory configuration, check your options")
unknown_song = messagetypes.Reply("That song doesn't exist and there is nothing playing")
no_songs = messagetypes.Reply("No songs found")
MAX_LIST = 15

class Autoplay(enum.Enum):
	OFF = 0
	QUEUE = 1
	ON = 2
autoplay = Autoplay.OFF
autoplay_ignore = False

# ===== HELPER OPERATIONS =====
def get_song(arg):
	dir = client.configuration["directory"]
	if len(arg) > 0:
		path = dir.get(arg[0])
		if path is not None:
			path = path["path"]
			return path, media_player.find_song(path, arg[1:])

		paths = [(key, vl["path"], vl["priority"]) for key, vl in dir.items() if vl["priority"] > 0]
		paths.sort(key=lambda a: a[2])
		songs = None
		for pt in paths:
			path = pt
			songs = media_player.find_song(pt[1], arg)
			if len(songs) > 0: break
		return (path, songs) if songs else (None, None)
	else:
		meta = media_player.current_media
		if meta is not None:
			path = meta.path
			song = meta.display_name, meta.song
			return path, [song]
		return None, None

def get_addtime(display, song, path):
	if isinstance(path, tuple): path = path[1]
	time = datetime.fromtimestamp(os.path.getctime(os.path.join(path, song)))
	return messagetypes.Reply("'" + display + "' was added on " + "{dt:%B} {dt.day}, {dt.year}".format(dt=time))

def get_displayname(song): return os.path.splitext(song)[0]

def get_lyrics(display, song):
	if client.show_lyrics(display): return messagetypes.Reply("Lyrics for '{}' opened in window".format(display))
	else: return messagetypes.Reply("Invalid title")

def get_playcount(display, song, alltime):
	freq = song_tracker.get_freq(song=display, alltime=alltime)
	if freq > 0:
		if not alltime: return messagetypes.Reply("'{}' has played {} times this month".format(display, freq))
		else: return messagetypes.Reply("'{}' has played {} times overall".format(display, freq))
	else: return messagetypes.Reply("'{}' has not been played".format(display))

def play_song(display, song, path):
	if isinstance(path, tuple): path = path[1]
	meta = media_player.play_song(path=path, song=song)
	if meta is not None:
		set_autoplay_ignore(False)
		return messagetypes.Reply("Playing: " + meta.display_name)
	else: return no_songs

def put_queue(display, song, path):
	song_queue.put_nowait((path[1], song))
	return messagetypes.Reply("Song '{}' added to queue".format(display))

def search_youtube(arg, argc, path):
	if argc > 0:
		try: from modules import youtube
		except ImportError: return messagetypes.Reply("Youtube module is not installed")
		if arg[0]: return youtube.command_youtube_find(arg, argc, path=path)
	return no_songs

def set_autoplay_ignore(ignore):
	global autoplay_ignore
	autoplay_ignore = bool(ignore)

def get_songmatches(path, keyword):
	if not path: path = client.configuration["default_path"]
	ls = media_player.find_song(path=client.configuration["directory"].get(path)["path"], keyword=keyword.split(" "))
	if len(ls) == 1: return ls[0]
	else: return None

def album_list(keyword):
	from modules.utilities import albumwindow
	try:
		with os.scandir(albumwindow.album_folder) as dir:
			return [(os.path.splitext(f.name)[0], f.name) for f in dir if f.is_file() and keyword in f.name]
	except FileNotFoundError: return []

def album_process(type, songs):
	for s in songs: interpreter.put_command("{} {} {}.".format(type, "music", s.replace(" - ", " ")))

# ===== MAIN COMMANDS =====
def command_album(arg, argc):
	if argc > 0:
		from modules.utilities import albumwindow
		try: aw = albumwindow.AlbumWindow(client, album_process, "_".join(arg))
		except FileNotFoundError: return messagetypes.Reply("Unknown album")

		client.open_window("albumviewer", aw)
		return messagetypes.Reply("Album opened")

def command_album_add(arg, argc, display=None, album=None):
	from modules.utilities import albumwindow
	if argc > 0 and display is album is None:
		albums = album_list(" ".join(arg))
		if albums: return messagetypes.Select("Multiple albums found", lambda d,a: command_album_add(arg, argc, display=d, album=a), albums)
		else: return messagetypes.Reply("No albums found")

	client.open_window("albumimput", albumwindow.AlbumWindowInput(client, file=album, autocomplete_callback=get_songmatches))
	return messagetypes.Reply("Album editor for '{}' opened".format(display) if display else "Album creator opened")

def command_album_remove(arg, argc):
	if argc > 0:
		import os
		from modules.utilities import albumwindow
		filename = albumwindow.album_format.format("_".join(arg), "json")
		try: os.remove(filename)
		except FileNotFoundError: return messagetypes.Reply("Unknown album")
		return messagetypes.Reply("Album deleted")

def command_album_list(arg, argc):
	albumlist = album_list(" ".join(arg))
	if albumlist: return messagetypes.Reply("Found albums:\n  - " + "\n  - ".join([a[1] for a in albumlist]))
	else: return messagetypes.Reply("No albums found")

# - configure autoplay
def command_autoplay_ignore(arg, argc):
	if argc == 0:
		set_autoplay_ignore(True)
		return messagetypes.Reply("Autoplay will be skipped for one song")

def command_autoplay_off(arg, argc):
	if argc == 0:
		global autoplay
		autoplay = Autoplay.OFF
		return messagetypes.Reply("Autoplay is off")

def command_autoplay_on(arg, argc):
	if argc == 0:
		global autoplay
		autoplay = Autoplay.ON
		set_autoplay_ignore(False)
		return messagetypes.Reply("Autoplay is turned on")

def command_autoplay_queue(arg, argc):
	if argc == 0:
		global autoplay
		autoplay = Autoplay.QUEUE
		set_autoplay_ignore(False)
		return messagetypes.Reply("Autoplay is enabled for queued songs")

def command_autoplay_next(arg, argc):
	if argc == 0:
		global autoplay_ignore
		if autoplay_ignore:
			set_autoplay_ignore(False)
			return messagetypes.Empty()

		global autoplay
		if autoplay.value > 0 and not song_queue.empty():
			song = song_queue.get_nowait()
			media_player.play_song(path=song[0], song=song[1])
		elif autoplay.value > 1: media_player.random_song()
		return messagetypes.Empty()

# - configure random song filter
def command_filter_clear(arg, argc):
	if argc == 0:
		dir = client.configuration["directory"]
		if isinstance(dir, dict):
			media_player.update_filter(path=dir.get(client.configuration["default_path"], {}).get("path", ""), keyword="")
			return messagetypes.Reply("Filter cleared")
		else: return invalid_cfg

def command_filter(arg, argc):
	if argc > 0:
		dirs = client.configuration["directory"]
		if isinstance(dirs, dict):
			if arg[0] in dirs:
				displaypath = arg.pop(0)
				path = dirs[displaypath]
			else:
				displaypath = client.configuration["default_path"]
				path = dirs.get(displaypath)

			if path is not None:
				arg = " ".join(arg)
				media_player.update_filter(path=path["path"], keyword=arg)
				if len(arg) > 0: return messagetypes.Reply("Filter set to '" + arg + "' from '" + displaypath + "'")
				else: return messagetypes.Reply("Filter set to directory '{}'".format(displaypath))
		return invalid_cfg

# - provide song or song tracker information
def command_info_added(arg, argc):
	(path, song) = get_song(arg)
	if path is not None and song is not None: return messagetypes.Select("Multiple songs found", get_addtime, song, path=path)
	else: return messagetypes.Info("PyHelper (the original) was created on August 19, 2016 - PyPlayer was introduced on May 14, 2018")

def command_info_played(arg, argc):
	if argc > 0 and arg[-1] == "all":
		alltime = True
		arg.pop(-1)
	else: alltime = False

	path, song = get_song(arg)
	if path is not None and song is not None: return messagetypes.Select("Multiple songs found", get_playcount, song, alltime=alltime)
	else: return unknown_song

def command_info_reload(arg, argc):
	if argc == 0:
		song_tracker.load_tracker()
		return messagetypes.Reply("Song tracker reloaded")

def command_lyrics(arg, argc):
	path, song = get_song(arg)
	if path is not None and song is not None: return messagetypes.Select("Multiple songs found", get_lyrics, song)
	else: return unknown_song

def command_mute(arg, argc):
	if argc == 0:
		media_player.mute_player()
		return messagetypes.Reply("Player mute toggled")

# - player specific commands
def command_pause(arg, argc):
	if argc == 0:
		media_player.pause_player()
		return messagetypes.Empty()

def command_position(arg, argc):
	if argc == 1:
		try: ps = float(arg[0])
		except ValueError: return messagetypes.Reply("Cannot figure out what that number is")
		if 0 < ps < 1: return messagetypes.Reply("Position updated" if media_player.set_position(ps) else "Position cannot be updated, try restarting the song")
		else: return messagetypes.Reply("Set position must be between 0.0 and 1.0")

def command_play(arg, argc):
	if argc > 0:
		path, song = get_song(arg)
		if path and song: return messagetypes.Select("Multiple songs found", play_song, song, path=path)
		elif len(arg) > 1: return messagetypes.Question("Can't find that song, search for it on youtube?", search_youtube, text=arg, path=path)
		else: return no_songs

def command_last_random(arg, argc):
	if argc == 0:
		return messagetypes.Pass()

def command_prev_song(arg, argc):
	if argc == 0:
		item = song_history.get_previous(song_history.head)
		if item is not None:
			set_autoplay_ignore(False)
			media_player.play_song(item[0], item[1])
		return messagetypes.Empty()

def command_next_song(arg, argc):
	if argc == 0:
		if not song_queue.empty(): return command_queue_next([], 0)
		else: return command_random([], 0)

def command_queue_clear(arg, argc):
	if argc == 0:
		while not song_queue.empty(): song_queue.get_nowait()
		return messagetypes.Reply("Queue cleared")

def command_queue_next(arg, argc):
	if argc == 0:
		if not song_queue.empty():
			item = song_queue.get_nowait()
			media_player.play_song(path=item[0], song=item[1])
			set_autoplay_ignore(False)
			return messagetypes.Empty()
		else: return messagetypes.Reply("Queue is empty")

def command_queue(arg, argc):
	if argc > 0:
		(path, song) = get_song(arg)
		if path is not None and song is not None: return messagetypes.Select("Multiple songs found", put_queue, song, path=path)
		else: return unknown_song

def command_random(arg, argc):
	dirs = client.configuration["directory"]
	path = ""
	if argc > 0:
		try:
			path = dirs[arg[0]]["path"]
			arg.pop(0)
		except KeyError: pass
	set_autoplay_ignore(False)
	return messagetypes.Reply(media_player.random_song(path=path, keyword=" ".join(arg)))

def command_reset(arg, argc):
	if argc == 0:
		media_player.reset()
		return messagetypes.Reply("Media player was reset")

def play_rss(display, url):
	media_player.play_url(url, display)
	return messagetypes.Reply("Playing: {}".format(display))

def get_audio_link(links):
	for l in links:
		if l["type"].startswith("audio/"): return l["href"]
	return ""

def command_rss(arg, argc):
	n = 1
	if argc == 1:
		try: n = int(arg.pop(0))
		except ValueError: return messagetypes.Reply("Invalid number")
		argc -= 1

	if argc == 0:
		url = client.configuration.get_or_create("rss_url", "")
		if url:
			import feedparser
			fp = feedparser.parse(url)
			if not fp.entries: return messagetypes.Reply("Nothing found on 'rss_url'")
			else:
				try:
					entry_list = fp.entries
					if len(entry_list) > n: entry_list = entry_list[:n]
					return messagetypes.Select("Which item should be played?", play_rss, [(et["title"], get_audio_link(et["links"])) for et in entry_list], text="0")
				except: return messagetypes.Reply("Invalid data returned")
		else: return messagetypes.Reply("What url? Enter one using key 'rss_url'")

def command_stop(arg, argc):
	if argc == 0:
		media_player.stop_player()
		return messagetypes.Empty()

commands = {
	"album": {
		"": command_album,
		"add": command_album_add,
		"delete": command_album_remove,
		"list": command_album_list
	}, "autoplay": {
		"next": command_autoplay_next,
		"off": command_autoplay_off,
		"on": command_autoplay_on,
		"skip": command_autoplay_ignore,
		"queue": command_autoplay_queue
	}, "filter": {
		"": command_filter,
		"none": command_filter_clear
	}, "info": {
		"added": command_info_added,
		"played": command_info_played,
		"reload": command_info_reload
	}, "lyrics": command_lyrics,
	"player": {
		"": command_play,
		"last_random": command_last_random,
		"mute": command_mute,
		"next": command_next_song,
		"next_song": command_next_song,
		"pause": command_pause,
		"position": command_position,
		"previous": command_prev_song,
		"prev_song": command_prev_song,
		"random": command_random,
		"reset": command_reset,
		"stop": command_stop
	}, "queue": {
		"": command_queue,
		"clear": command_queue_clear,
		"next": command_queue_next
	}, "rss": command_rss
}

def initialize():
	media_player.update_blacklist(client.configuration.get_or_create("artist_blacklist", []).value)
	media_player.attach_event("media_changed", on_media_change)
	media_player.attach_event("pos_changed", on_pos_change)
	media_player.attach_event("player_updated", on_player_update)
	media_player.attach_event("end_reached", on_end_reached)
	media_player.attach_event("stopped", on_stopped)
	if not song_tracker.is_loaded(): song_tracker.load_tracker()

	client.configuration.get_or_create("directory", {})
	client.configuration.get_or_create("default_directory", "")
	command_filter_clear(None, 0)

def on_destroy():
	media_player.on_destroy()

def on_media_change(event, player):
	color = None
	for key, options in client.configuration["directory"].items():
		if media_player.current_media.path == options["path"]:
			color = options.get("color")
			break
	client.schedule(func=client.update_title_media, media_data=media_player.current_media, color=color)

def on_pos_change(event, player):
	client.schedule(func=client.update_progressbar, progress=event.u.new_position)

def on_stopped(event, player):
	client.schedule(func=client.update_progressbar, progress=0)

def on_player_update(event, player):
	md = event.data
	default_directory = client.configuration["directory"].get(client.configuration["default_path"])

	if default_directory is not None and md.path == default_directory["path"]:
		song_tracker.add(md.display_name)
		try: client.widgets["songbrowser"].add_count(md.display_name)
		except KeyError: pass
	song_history.add((md.path, md.song))

def on_end_reached(event, player):
	interpreter.put_command("autoplay next")
