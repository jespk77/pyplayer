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
MAX_LIST = 15

class Autoplay(enum.Enum):
	OFF = 0
	QUEUE = 1
	ON = 2
autoplay = Autoplay.OFF
autoplay_ignore = False

# ===== HELPER OPERATIONS =====
def get_song(arg, auto_fix=True):
	dir = client.get_or_create("directory", {}).to_dict()
	if len(arg) > 0:
		path = dir.get(arg[0])
		if path is not None:
			path = path["path"]
			arg.pop(0)
			return path, media_player.find_song(path, " ".join(arg[1:]))

		try: paths = [(key, vl["path"], vl["priority"]) for key, vl in dir.items()]
		except TypeError:
			if not auto_fix: return None, None
			priority = 1
			pdir = { "directory": {} }
			for key, vl in dir.items():
				if key != "default":
					pdir["directory"][key] = { "priority": priority, "path": vl }
					priority += 1
			client.update_configuration(pdir)
			return get_song(arg, False)

		paths.sort(key=lambda a: a[2])
		keyword = " ".join(arg)
		songs = None
		for pt in paths:
			path = pt
			songs = media_player.find_song(pt[1], keyword)
			if len(songs) > 0: break
		return path, songs
	return None, None

def get_displayname(song): return os.path.splitext(song)[0]

def search_youtube(arg, argc, keywords, path):
	if argc > 0 and len(keywords) > 0:
		try: from modules import youtube
		except ImportError: return messagetypes.Reply("Youtube module is not installed")
		if " ".join(arg).lower() == "y": return youtube.command_youtube_find(keywords, len(keywords), path=path)
	return messagetypes.Reply("No song found")

# ===== MAIN COMMANDS =====
# - configure autoplay
def command_autoplay_info(arg, argc):
	return messagetypes.Info("'autoplay' ['on', 'off', 'queue', 'skip']")

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
def command_filter_info(arg, argc):
	return messagetypes.Info("'filter' ['clear', keyword]")

def command_filter_clear(arg, argc):
	if argc == 0:
		dir = client["directory"]
		if isinstance(dir, dict):
			media_player.update_filter(path=dir.get(dir.get("default"), ""), keyword="")
			return messagetypes.Reply("Filter cleared")
		else: return invalid_cfg

def command_filter(arg, argc):
	if argc > 0:
		dirs = client["directory"]
		if isinstance(dirs, dict):
			if arg[0] in dirs: path = dirs[arg[0]]; displaypath = arg.pop(0)
			else: path = dirs.get(dirs.get("default")); displaypath = dirs.get("default")

			if path is not None:
				arg = " ".join(arg)
				media_player.update_filter(path=path, keyword=arg)
				if len(arg) > 0: return messagetypes.Reply("Filter set to '" + arg + "' from '" + displaypath + "'")
				else: return messagetypes.Reply("Filter set to directory '{}'".format(displaypath))
		else: return invalid_cfg

# - provide song or song tracker information
def command_info_info(arg, argc):
	return messagetypes.Info("'info' ['added' [song, |'current'|], 'played' [song [|'month'|, 'all']], 'reload']")

def get_addtime(value, data, path):
	time = datetime.fromtimestamp(os.path.getctime(os.path.join(path[1], data[0])))
	return messagetypes.Reply("'" + value + "' was added on " + str(time.strftime("%b %d, %Y")))

def command_info_added(arg, argc):
	(path, song) = get_song(arg)
	if argc > 0 and arg[0] and path is not None and song is not None:
		if isinstance(song, list):
			if len(song) > 1: return messagetypes.Select("Multiple songs found", get_addtime, [(get_displayname(s), s) for s in song], path=path)
			elif len(song) == 0: return messagetypes.Reply("Nothing found :(")
			else: song = song[0]

		return get_addtime(song, path)
	return messagetypes.Reply("That song doesn't exist and there is no song currently playing")

def command_info_played(arg, argc):
	alltime = False
	if argc > 0 and arg[-1] == "all":
		alltime = True
		arg = arg[:-1]

	(path, song) = parse_song(arg)
	if path is not None and song is not None:
		if isinstance(song, list): return messagetypes.Reply("More than one song found, be more specific")
		freq = song_tracker.get_freq(song=get_displayname(song), alltime=alltime)
		if freq > 0:
			if not alltime: return messagetypes.Reply("'" + get_displayname(song) + "' played " + str(freq) + " times this month")
			else: return messagetypes.Reply("'" + get_displayname(song) + "' played " + str(freq) + " times overall")
		else: return messagetypes.Reply("'" + get_displayname(song) + " has not been played")
	else: return messagetypes.Reply("That song doesn't even exist")

def command_info_reload(arg, argc):
	if argc == 0:
		song_tracker.load_tracker()
		return messagetypes.Reply("Song tracker reloaded")

def command_lyrics(arg, argc):
	path, song = parse_song(arg)
	if path is not None and song is not None:
		try: song = get_displayname(song)
		except TypeError: return messagetypes.Reply("Multiple songs found, be more specific")

		if client.show_lyrics(song): return messagetypes.Reply("Lyrics for '{}' opened in window".format(song))
		else: return messagetypes.Reply("Invalid title")
	else: return messagetypes.Reply("No song found")

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
		(path, song) = parse_song(arg)
		if path is not None and isinstance(song, str):
			meta = media_player.play_song(path=path, song=song)
			if meta is not None: return messagetypes.Reply("Playing: " + meta.display_name)
		elif song is not None and len(song) > 1:
			reply = "Multiple songs ({:d} total) found: ".format(len(song))
			count = 0
			for s in song:
				if count > MAX_LIST: reply += "\n and more..."; break
				else:
					reply += "\n {}. {}".format(count, get_displayname(s))
					count += 1
			return messagetypes.Reply(reply)
		else: return messagetypes.Question("Can't find that song, search for it on youtube?", search_youtube, keywords=arg, path=path)

def command_last_random(arg, argc):
	if argc == 0:
		r = media_player.play_last_random()
		if r is not None: return messagetypes.Reply("Playing: " + r.display_name)
		else: return messagetypes.Reply("There haven't been any randomly picked songs")

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
		(path, song) = parse_song(arg)
		if isinstance(song, list):
			r = "Found multiple choices:"
			for item in song: r += "\n - {}".format(get_displayname(item))
			return messagetypes.Reply(r)

		if path is not None and song is not None:
			song_queue.put_nowait((path, song))
			return messagetypes.Reply("'" + get_displayname(song) + "' added to queue")
		else: return messagetypes.Reply("There is not a song like that around here")

def command_random(arg, argc):
	dirs = client["directory"]
	if not isinstance(dirs, dict): return invalid_cfg

	if argc > 0 and arg[0] in dirs: path = dirs[arg[0]]; arg = arg[1:]
	else: path = ""

	if path is not None: return messagetypes.Reply(media_player.random_song(path=path, keyword=" ".join(arg)))
	else: return messagetypes.Reply("I've never heard of that path")

def command_stop(arg, argc):
	if argc == 0:
		media_player.stop_player()
		return messagetypes.Empty()

commands = {
	"autoplay": {
		"next": command_autoplay_next,
		"info": command_autoplay_info,
		"off": command_autoplay_off,
		"on": command_autoplay_on,
		"skip": command_autoplay_ignore,
		"queue": command_autoplay_queue
	}, "filter": {
		"info": command_filter_info,
		"": command_filter,
		"none": command_filter_clear
	}, "info": {
		"info": command_info_info,
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
	media_player.update_blacklist(client.get_or_create("artist_blacklist", []))
	media_player.attach_event("media_changed", on_media_change)
	media_player.attach_event("pos_changed", on_pos_change)
	media_player.attach_event("player_updated", on_player_update)
	media_player.attach_event("end_reached", on_end_reached)
	media_player.attach_event("stopped", on_stopped)
	if not song_tracker.is_loaded(): song_tracker.load_tracker()

	dr = client.get_or_create("directory", {})
	media_player.update_filter(path=dr.get(dr.get("default")))

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
	if not default_directory.endswith("/"): default_directory += "/"

	if md.path == default_directory:
		song_tracker.add(md.display_name)
		try: client.widgets["songbrowser"].add_count(md.display_name)
		except KeyError: pass
	song_history.add((md.path, md.song))

def on_end_reached(event, player):
	interpreter.put_command("autoplay next")
