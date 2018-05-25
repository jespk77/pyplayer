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
class Autoplay(enum.Enum):
	OFF = 0
	QUEUE = 1
	ON = 2
autoplay = Autoplay.OFF

# ===== HELPER OPERATIONS =====
def parse_song(arg):
	if len(arg) > 0:
		dir = interpreter.configuration.get("directory", {})
		if arg[0] in dir:
			path = dir[arg[0]]
			arg = arg[1:]
		else:
			path = dir.get(dir["default"])
			if path == None: return (None, None)
		song = media_player.find_song(path=path, keyword=arg)
		return (path, song)
	else:
		meta = media_player.get_current_media()
		try:
			path = meta.path
			song = meta.song
			return (path, song)
		except: return (None, None)

def get_displayname(song):
	return os.path.splitext(song)[0]

# ===== MAIN COMMANDS =====
# - configure autoplay
def command_autoplay_info(arg, argc):
	return messagetypes.Info("'autoplay' ['on', 'off', 'queue']")

def command_autoplay_off(arg, argc):
	if argc == 0:
		global autoplay
		autoplay = Autoplay.OFF
		return messagetypes.Reply("Autoplay is off")

def command_autoplay_on(arg, argc):
	if argc == 0:
		global autoplay
		autoplay = Autoplay.ON
		return messagetypes.Reply("Autoplay is turned on")

def command_autoplay_queue(arg, argc):
	if argc == 0:
		global autoplay
		autoplay = Autoplay.QUEUE
		return messagetypes.Reply("Autoplay is enabled for queued songs")

def command_autoplay_next(arg, argc):
	if argc == 0:
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
		dir = interpreter.configuration.get("directory", {})
		media_player.set_filter(dir.get(dir.get("default"), ""), "")
		return messagetypes.Reply("Filter cleared")

def command_filter(arg, argc):
	if argc > 0:
		dirs = interpreter.configuration.get("directory")
		if isinstance(dirs, dict):
			if arg[0] in dirs: path = dirs[arg[0]]; arg = arg[1:]
			else: path = dirs.get(dirs.get("default"))

			if path != None:
				arg = " ".join(arg)
				media_player.set_filter(path, arg)
				return messagetypes.Reply("Filter set to '" + arg + "' from '" + path + "'")
		return messagetypes.Reply("That won't work, try again")

# - provide song or song tracker information
def command_info_info(arg, argc):
	return messagetypes.Info("'info' ['added' [song, |'current'|], 'played' [song [|'month'|, 'all']], 'reload']")

def command_info_added(arg, argc):
	if argc > 0:
		(path, song) = parse_song(arg)
		if path != None and song != None:
			if not path.endswith("/"): path += "/"
			time = os.path.getctime(path + song)
			time = datetime.fromtimestamp(time)
			return messagetypes.Reply("'" + get_displayname(song) + "' was added on " + str(time.strftime("%b %d, %Y")))
		else: return messagetypes.Reply("That song doesn't even exist")

def command_info_played(arg, argc):
	monthly = True
	if arg[-1] == "all":
		monthly = False
		arg = arg[:-1]

	(path, song) = parse_song(arg)
	if path != None and song != None:
		freq = song_tracker.get_freq(song=get_displayname(song), monthly=monthly)
		if freq > 0:
			if monthly: return messagetypes.Reply("'" + get_displayname(song) + "' played " + str(freq) + " times this month")
			else: return messagetypes.Reply("'" + get_displayname(song) + "' played " + str(freq) + " times overall")
		else: return messagetypes.Reply("'" + get_displayname(song) + " has not been played")
	else: return messagetypes.Reply("That song doesn't even exist")

def command_info_reload(arg, argc):
	if argc == 0:
		song_tracker.load_tracker()
		return messagetypes.Reply("Song tracker reloaded")

def command_music(arg, argc):
	if argc > 0: return messagetypes.Reply("We no longer listen to that command, you probably meant 'player' instead?")

# - player specific commands
def command_pause(arg, argc):
	if argc == 0:
		media_player.pause_player()
		return messagetypes.Empty()

def command_play(arg, argc):
	if argc > 0:
		(path, song) = parse_song(arg)
		if path != None and isinstance(song, str):
			meta = media_player.play_song(path=path, song=song)
			if meta != None: return messagetypes.Reply("Playing: " + meta.display_name)
		elif song != None and len(song) > 1:
			reply = "Multiple songs ({:d} total) found: ".format(len(song))
			count = 0
			for s in song:
				if count > 15: reply += "\n and more..."; break
				else: count += 1
				reply += "\n - " + get_displayname(s)
			return messagetypes.Reply(reply)
		else: return messagetypes.Reply("Cannot find that song")

def command_prev_song(arg, argc):
	if argc == 0:
		item = song_history.get()
		if item != None: media_player.play_song(item[0], item[1])
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
		if path != None and song != None:
			song_queue.put_nowait((path, song))
			return messagetypes.Reply("'" + get_displayname(song) + "' added to queue")
		else: return messagetypes.Reply("There is not a song like that around")

def command_random(arg, argc):
	dirs = interpreter.configuration.get("directory", {})
	if argc > 0 and arg[0] in dirs: path = dirs[arg[0]]; arg = arg[1:]
	else: path = dirs.get(dirs.get("default"))

	if path != None: return messagetypes.Reply(media_player.random_song(path=path, keyword=" ".join(arg)))
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
	}, "music": command_music,
	"player": {
		"": command_play,
		"next_song": command_next_song,
		"pause": command_pause,
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
	media_player.attach_event("media_changed", on_media_change)
	media_player.attach_event("pos_changed", on_pos_change)
	media_player.attach_event("player_updated", on_player_update)
	media_player.attach_event("end_reached", on_end_reached)
	if not song_tracker.is_loaded(): song_tracker.load_tracker()
	dr = interpreter.configuration.get("directory", {})
	media_player.set_filter(path=dr.get(dr.get("default")))

def on_destroy():
	media_player.on_destroy()

def on_media_change(event, player):
	song_history.reset_index()
	client.after(1, client.update_title, media_player.get_current_media().display_name)

def on_pos_change(event, player):
	client.after(1, client.update_progressbar, event.u.new_position)

def on_player_update(event, player):
	md = event.data
	directory = interpreter.configuration.get("directory", {})
	default_directory = directory.get(directory.get("default"), "")
	if not default_directory.endswith("/"): default_directory += "/"

	if md.path == default_directory:
		song_tracker.add(md.display_name)
		try: client.songbrowser.add_count(md.display_name)
		except AttributeError: pass
	song_history.add((md.path, md.song))

def on_end_reached(event, player):
	interpreter.queue.put_nowait("autoplay next")
