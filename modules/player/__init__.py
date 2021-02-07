import enum, os
from datetime import datetime
from multiprocessing import Queue

from .mediaplayer import MediaPlayer
from . import albumwindow, lyricviewer, songbrowser, song_tracker, songhistory

from ui.qt import pyelement
from core import messagetypes, interpreter
module = interpreter.Module()

# MODULE SPECIFIC VARIABLES
media_player = MediaPlayer()
song_queue = Queue()
song_history = None
invalid_cfg = messagetypes.Reply("Invalid directory configuration, check your options")
unknown_song = messagetypes.Reply("That song doesn't exist and there is nothing playing")
no_songs = messagetypes.Reply("No songs found")
MAX_LIST = 15
default_dir_path = "default_directory"

class Autoplay(enum.Enum):
	OFF = 0
	QUEUE = 1
	ON = 2
autoplay = Autoplay.OFF
autoplay_ignore = False

# ===== HELPER OPERATIONS =====
def get_song(arg):
	dir = module.client.configuration["directory"]
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
	song_queue.put_nowait((path[1] if isinstance(path, tuple) else path, song))
	return messagetypes.Reply("Song '{}' added to queue".format(display))

def set_autoplay_ignore(ignore):
	global autoplay_ignore
	autoplay_ignore = bool(ignore)

# ===== MAIN COMMANDS =====
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
		dir = module.client.configuration["directory"]
		if isinstance(dir, dict):
			media_player.update_filter(path=dir.get(module.client.configuration[default_dir_path], {}).get("path", ""), keyword="")
			return messagetypes.Reply("Filter cleared")
		else: return invalid_cfg

def command_filter(arg, argc):
	if argc > 0:
		dirs = module.client.configuration["directory"]
		if isinstance(dirs, dict):
			if arg[0] in dirs:
				displaypath = arg.pop(0)
				path = dirs[displaypath]
			else:
				displaypath = module.client.configuration[default_dir_path]
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
	return lyricviewer.command_lyrics(path, song)

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
		if 0 <= ps <= 1: return messagetypes.Reply("Position updated" if media_player.set_position(ps) else "Position cannot be updated, try restarting the song")
		else: return messagetypes.Reply("Set position must be between 0.0 and 1.0")

def command_play(arg, argc):
	if argc > 0:
		path, song = get_song(arg)
		if path and song: return messagetypes.Select("Multiple songs found", play_song, song, path=path)
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
	dirs = module.client.configuration["directory"]
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
		url = module.client.configuration.get_or_create("rss_url", "")
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

def command_browser(arg, argc):
	sorting = module.client.configuration.get_or_create(songbrowser.default_sort_key, "name")
	if isinstance(sorting, str) and len(sorting) > 0:
		try: return commands["browser"][sorting](arg, argc)
		except KeyError: return messagetypes.Reply(f"Invalid default sorting set in configuration '{sorting}'")
	return messagetypes.Reply(f"No default sorting set '{songbrowser.default_sort_key}' and none or invalid one specified")

def command_stop(arg, argc):
	if argc == 0:
		media_player.stop_player()
		return messagetypes.Empty()

module.commands = {
	"album": {
		"": albumwindow.command_album,
		"add": albumwindow.command_album_add,
		"delete": albumwindow.command_album_remove,
		"list": albumwindow.command_album_list
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
		"history": songhistory.command_history_window,
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
	}, "rss": command_rss,
	"browser": {
		"": command_browser,
		"none": songbrowser.command_browser_remove,
		"name": songbrowser.command_browser_name,
		"played-month": songbrowser.command_browser_played_month,
		"played": songbrowser.command_browser_played_all,
		"recent": songbrowser.command_browser_recent,
		"shuffle": songbrowser.command_browser_shuffle
	}
}

@module.Initialize
def initialize():
	media_player.update_blacklist(module.client.configuration.get_or_create("artist_blacklist", []))
	media_player.attach_event("media_changed", on_media_change)
	media_player.attach_event("pos_changed", on_pos_change)
	media_player.attach_event("player_updated", on_player_update)
	media_player.attach_event("end_reached", on_end_reached)
	media_player.attach_event("stopped", on_stopped)
	if not song_tracker.is_loaded(): song_tracker.load_tracker()

	progress = module.client.add_element("progress_bar", element_class=pyelement.PyProgessbar, row=1, columnspan=3)
	progress.minimum, progress.maximum = 0, 10000
	progress.progress = 0
	@progress.events.EventInteract
	def _on_click(position): module.interpreter.put_command(f"player position {position}")

	module.client.configuration.get_or_create("directory", {})
	module.client.configuration.get_or_create(default_dir_path, "")

	@module.client.events.EventKeyDown("MediaPause")
	@module.client.events.EventKeyDown("MediaPlay")
	@module.client.events.EventKeyDown("MediaTogglePlayPause")
	def _media_play(): module.interpreter.put_command("player pause")

	@module.client.events.EventKeyDown("MediaNext")
	def _media_next(): module.interpreter.put_command("player next")
	@module.client.events.EventKeyDown("MediaPrevious")
	def _media_previous(): module.interpreter.put_command("player previous")
	@module.client.events.EventKeyDown("MediaStop")
	def _media_stop(): module.interpreter.put_command("player stop")

	module.client.add_task(task_id="player_progress_update", func=_set_client_progress)
	module.client.add_task(task_id="player_title_update", func=_set_client_title)

	songhistory.initialize(module.client, media_player)
	global song_history
	song_history = songhistory.song_history

	albumwindow.initialize(module, media_player)
	lyricviewer.initialize(module)
	songbrowser.initialize(module)
	command_filter_clear(None, 0)

@module.Destroy
def on_destroy():
	media_player.on_destroy()

def on_media_change(event, player):
	color = None
	for key, options in module.client.configuration["directory"].items():
		if media_player.current_media.path == options["path"]:
			color = options.get("color")
			break
	module.client.schedule_task(task_id="player_title_update", media=media_player.current_media, color=color)

def on_pos_change(event, player):
	module.client.schedule_task(task_id="player_progress_update", progress=event.u.new_position)

def on_stopped(event, player):
	module.client.schedule_task(task_id="player_progress_update", progress=0)

def on_player_update(event, player):
	md = event.data
	default_directory = module.client.configuration["directory"].get(module.client.configuration[default_dir_path])

	if default_directory is not None and md.path == default_directory["path"]:
		song_tracker.add(md.display_name)
		try: module.client["songbrowser"].add_count(md.display_name)
		except KeyError: pass
	song_history.add((md.path, md.song))

def on_end_reached(event, player):
	module.interpreter.put_command("autoplay next")

def _set_client_progress(progress):
	progress = round(progress * 10000)
	module.client["progress_bar"].progress = progress

def _set_client_title(media, color):
	module.client.update_title(media.display_name)
	songbrowser.title_update(media, color)