from datetime import datetime
from multiprocessing import Queue
import os, enum

from utilities import messagetypes, song_tracker, history
from modules.utilities.mediaplayer import MediaPlayer

# DEFAULT MODULE VARIABLES
priority = 2
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
media_player = MediaPlayer()
song_queue = Queue()
song_history = history.History()
invalid_cfg = messagetypes.Reply("Invalid directory configuration, check your options")
unknown_song = messagetypes.Reply("That song doesn't exist and there is nothing playing")
MAX_LIST = 15

class Autoplay(enum.Enum):
	OFF = 0
	QUEUE = 1
	ON = 2
autoplay = Autoplay.OFF
autoplay_ignore = False

# ===== HELPER OPERATIONS =====
def update_cfg():
	print("INFO", "Found old directory configuration, trying to update it automatically")
	dir = client["directory"]
	priority = 1
	pdir = {"directory": {}}
	for key, vl in dir.items():
		if key != "default":
			pdir["directory"][key] = {"priority": priority, "path": vl}
			priority += 1
		else: client["default_path"] = vl
	client.update_configuration(pdir)
	client["version"] = 1

def get_song(arg):
	dir = client["directory"]
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
		return path, songs
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
	if meta is not None: return messagetypes.Reply("Playing: " + meta.display_name)
	else: return unknown_song

def put_queue(display, song, path):
	song_queue.put_nowait((path[1], song))
	return messagetypes.Reply("Song '{}' added to queue".format(display))

def search_youtube(arg, argc, keywords, path):
	if argc > 0 and len(keywords) > 0:
		try: from modules import youtube
		except ImportError: return messagetypes.Reply("Youtube module is not installed")
		if " ".join(arg).lower() == "y": return youtube.command_youtube_find(keywords, len(keywords), path=path)
	return unknown_song

# ===== MAIN COMMANDS =====
# - configure autoplay
def command_autoplay_ignore(arg, argc):
	if argc == 0:
		global autoplay_ignore
		autoplay_ignore = True
		return messagetypes.Reply("Autoplay will be skipped for one song")

def command_autoplay_off(arg, argc):
	if argc == 0:
		global autoplay, autoplay_ignore
		autoplay = Autoplay.OFF
		autoplay_ignore = False
		return messagetypes.Reply("Autoplay is off")

def command_autoplay_on(arg, argc):
	if argc == 0:
		global autoplay, autoplay_ignore
		autoplay = Autoplay.ON
		autoplay_ignore = False
		return messagetypes.Reply("Autoplay is turned on")

def command_autoplay_queue(arg, argc):
	if argc == 0:
		global autoplay, autoplay_ignore
		autoplay = Autoplay.QUEUE
		autoplay_ignore = False
		return messagetypes.Reply("Autoplay is enabled for queued songs")

def command_autoplay_next(arg, argc):
	if argc == 0:
		global autoplay_ignore
		if autoplay_ignore:
			autoplay_ignore = False
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
		dir = client["directory"]
		if isinstance(dir, dict):
			media_player.update_filter(path=dir[client["default_path"]]["path"], keyword="")
			return messagetypes.Reply("Filter cleared")
		else: return invalid_cfg

def command_filter(arg, argc):
	if argc > 0:
		dirs = client["directory"]
		if isinstance(dirs, dict):
			if arg[0] in dirs:
				displaypath = arg.pop(0)
				path = dirs[displaypath]
			else:
				displaypath = client["default_path"]
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
	else: return unknown_song

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
		if 0 < ps < 1:
			media_player.set_position(ps)
			return messagetypes.Reply("Position updated")
		else: return messagetypes.Reply("Set position must be between 0.0 and 1.0")

def command_play(arg, argc):
	if argc > 0:
		(path, song) = get_song(arg)
		if path is not None and song is not None: return messagetypes.Select("Multiple songs found", play_song, song, path=path)
		else: return messagetypes.Question("Can't find that song, search for it on youtube?", search_youtube, keywords=arg, path=path)

def command_last_random(arg, argc):
	if argc == 0:
		return messagetypes.Pass()

def command_prev_song(arg, argc):
	if argc == 0:
		item = song_history.get_previous(song_history.head)
		if item is not None: media_player.play_song(item[0], item[1])
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
			return messagetypes.Empty()
		else: return messagetypes.Reply("Queue is empty")

def command_queue(arg, argc):
	if argc > 0:
		(path, song) = get_song(arg)
		if path is not None and song is not None: return messagetypes.Select("Multiple songs found", put_queue, song, path=path)
		else: return unknown_song

def command_random(arg, argc):
	dirs = client["directory"]
	if argc > 0:
		try:
			path = dirs[arg[0]]["path"]
			arg.pop(0)
		except KeyError: path = ""
	else: path = ""
	return messagetypes.Reply(media_player.random_song(path=path, keyword=" ".join(arg)))

def command_stop(arg, argc):
	if argc == 0:
		media_player.stop_player()
		return messagetypes.Empty()

commands = {
	"autoplay": {
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
		# TODO: progressbar not updating if song was restarted
		#"position": command_position,
		"previous": command_prev_song,
		"prev_song": command_prev_song,
		"random": command_random,
		"stop": command_stop
	}, "queue": {
		"": command_queue,
		"clear": command_queue_clear,
		"next": command_queue_next
	}
}

def initialize():
	if client["version"] == 0: update_cfg()
	media_player.update_blacklist(client.get_or_create("artist_blacklist", []))
	media_player.attach_event("media_changed", on_media_change)
	media_player.attach_event("pos_changed", on_pos_change)
	media_player.attach_event("player_updated", on_player_update)
	media_player.attach_event("end_reached", on_end_reached)
	media_player.attach_event("stopped", on_stopped)
	if not song_tracker.is_loaded(): song_tracker.load_tracker()

	client.get_or_create("directory", {})
	command_filter_clear(None, 0)

def on_destroy():
	media_player.on_destroy()

def on_media_change(event, player):
	client.after(.5, client.update_title, media_player.current_media.display_name)

def on_pos_change(event, player):
	client.after(.5, client.update_progressbar, event.u.new_position)

def on_stopped(event, player):
	client.after(.5, client.update_progressbar, 0)

def on_player_update(event, player):
	md = event.data
	directory = client["directory"]
	default_directory = directory.get(directory.get("default"), "")

	if md.path == default_directory:
		song_tracker.add(md.display_name)
		try: client.widgets["songbrowser"].add_count(md.display_name)
		except KeyError: pass
	song_history.add((md.path, md.song))

def on_end_reached(event, player):
	interpreter.put_command("autoplay next")
