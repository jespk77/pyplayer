import sys
import vlc as VLCPlayer

import os, re, random

def get_displayname(filepath):
	return os.path.splitext(filepath)[0]

class MediaPlayerData:
	def __init__(self, path, song):
		self.path = path
		self.song = song
		self.display_name = get_displayname(song)

	def __str__(self):
		return "[MediaData] {!s}: {!s}".format(self.path, self.song)

class MediaPlayerEventUpdate:
	id = 0

	def __init__(self, data):
		self.data = data

	def __str__(self):
		return "MediaPlayerEventUpdate {:d}: {!s}".format(self.id, self.data)

class MediaPlayer():
	blacklist_file = "blacklist"
	end_pos = 0.85

	def __init__(self):
		print("initializing new MediaPlayer instance...")
		self.vlc = VLCPlayer.Instance()
		self.player1 = self.vlc.media_player_new()
		self.player1.audio_output_set("mmdevice")
		self.player2 = self.vlc.media_player_new()
		self.player2.audio_output_set("mmdevice")

		self.paused = False
		self.player_one = True
		self.media = None
		self.media_data = None
		self.updated = False
		self.filter = ["", ""]
		self.update_blacklist()

		self.events = {
			"end_reached": (VLCPlayer.EventType.MediaPlayerEndReached, self.on_song_end, []),
			"media_changed": (VLCPlayer.EventType.MediaPlayerMediaChanged, self.on_media_change, []),
			"paused": (VLCPlayer.EventType.MediaPlayerPaused, self.on_pause, []),
			"playing": (VLCPlayer.EventType.MediaPlayerPlaying, self.on_play, []),
			"pos_changed": (VLCPlayer.EventType.MediaPlayerPositionChanged, self.on_pos_change, []),
			"stopped": (VLCPlayer.EventType.MediaPlayerStopped, self.on_stop, [])
		}

		# register vlc event handlers
		for event in self.events.items():
			event_key, event_value = event
			self.player1.event_manager().event_attach(event_value[0], event_value[1], event_key, self.player1, True)
			self.player2.event_manager().event_attach(event_value[0], event_value[1], event_key, self.player2, False)

		# register custom event handlers
		self.events["player_updated"] = (MediaPlayerEventUpdate, self.on_update, [])

	# === MAIN UTILITIES ===
	def get_active_player(self):
		if self.player_one: return self.player1
		else: return self.player2

	def set_filter(self, path="", keyword=""):
		self.filter = [path, keyword]

	def get_current_media(self):
		return self.media_data

	def update_blacklist(self):
		self.blacklist = []
		try:
			file = open(self.blacklist_file, "r")
			for line in file:
				self.blacklist.append(line)
			file.close()
		except FileNotFoundError: pass

	def list_songs(self, path, keyword=""):
		"""	List all items found in specified directory
			Items that match the full keyword get returned first, if no matches found returns items containing the keyword
				path: the path to search in
				keyword: [optional], returns all items matching this keyword or all items if no argument passed
		"""
		print("looking for songs in", path, "with keyword", keyword)
		res1 = []
		res2 = []
		keyword = keyword.lower()
		if keyword.endswith("."):
			exact = True
			keyword = keyword[:-1]
		else: exact = False

		if os.path.isdir(path):
			with os.scandir(path) as dir:
				for entry in dir:
					if entry.is_file():
						file = entry.name
						song = get_displayname(file.replace(" - ", " ").lower())
						if exact and song == keyword: return [file]
						elif " " + keyword + " " in " " + song + " ": res1.append(file)
						elif keyword == "" or keyword in song: res2.append(file)

		if len(res1) > 0: return res1
		else: return res2

	def find_song(self, path, keyword=None):
		""" Same as list_songs but checks for an index at the end of the keyword for faster option selection
		"""
		if keyword is None: keyword = []
		print("find songs in", path, "with keyword", keyword)
		id = keyword[-1]
		if len(keyword) > 1 and id.isdigit():
			keyword = keyword[:-1]
			id = int(id)
			print("found digit in keyword", id)
		else: id = -1

		songlist = self.list_songs(path=path, keyword=" ".join(keyword))
		if id >= 0 and id < len(songlist):
			print("picking song from list using found index", id)
			return songlist[id]
		elif len(songlist) == 1: return songlist[0]
		else: return songlist

	def play_song(self, path, song):
		""" Plays a song only when the full path and song name are known
			If successful, returns the updated media data set by the player
		"""
		if not path.endswith("/"): path += "/"
		file = path + song
		print("preparing to play", file)
		if not os.path.isfile(file): return
		if self.paused: self.stop_player()

		self.media = self.vlc.media_new(file)
		self.media_data = MediaPlayerData(path, song)
		if self.player_one: print("playing song on player1")
		else: print("playing song on player2")
		player = self.get_active_player()
		player.set_media(self.media)
		player.play()

		self.paused = False
		self.updated = True
		return self.media_data

	def pause_player(self):
		self.paused = not self.paused and self.media != None
		print("pause state set to", self.paused)
		self.player1.set_pause(self.paused)
		self.player2.set_pause(self.paused)

	def stop_player(self):
		self.paused = False
		print("stopping playback")
		self.player1.stop()
		self.player2.stop()
		if self.media != None:
			self.media.release()
			self.media = None
		self.media_data = None

# ===== OTHER FUNCTIONS =====
	def random_song(self, path="", keyword=""):
		""" Choose a random song from a directory, uses values set in player filter when no arguments are given
		"""
		if path == "": path = self.filter[0]
		if keyword == "": keyword = self.filter[1]
		print("play random song from", path, " keyword ", keyword)
		songlist = self.list_songs(path, keyword)
		if len(songlist) > 0:
			print("choosing random song out of", len(songlist), "items")
			song = None
			tries = 0
			while song == None and tries < 5:
				tries += 1
				s = random.choice(songlist)
				match = False
				for item in self.blacklist:
					if item in s.split(" - ")[0]: match = True; break
				if not match: song = s

			if song != None:
				self.play_song(path, song)
				return "Playing: {}".format(get_displayname(song))
			else: return "No song found that doesn't match something in blacklist, try reducing the number of blacklisted items"
		return "No songs with that filter"

	def get_lyrics(self):
		try:
			print("get lyrics for", self.media_data)
			s = self.media_data.display_name
			if len(s) > 1:
				artist = re.sub("[^0-9a-zA-Z]+", "", s[0]).lower()
				if artist.startswith("the"): artist = artist.lstrip("the")
				return "http://www.azlyrics.com/lyrics/" + artist + "/" + re.sub("[^0-9a-zA-Z]+", "", s[1]).lower() + ".html"
		except: return None

# ===== EVENT HANDLING =====
	def attach_event(self, event, callback):
		""" Attach a new callback handle to the selected event, has no effect if handle was already attached or if it is not callable
			(The attached callback will only be called only with the player that is in foreground when the event occurred)
				event: The name of the event
				callback: The function to be called when the event occurs, must take two arguments: the event that was triggered and the VLC player that triggered the event
		"""
		self.update_event_handler(event, callback, add=True)

	def detach_event(self, event, callback):
		""" Detach a handler that was previously attached using attach_event, has no effect if handle was never attached of if it is not callable
		"""
		self.update_event_handler(event, callback, add=False)

	def update_event_handler(self, event, callback, add):
		if callable(callback) and event in self.events:
			handle = self.events[event]
			if add == (not callback in handle[2]):
				if add: handle[2].append(callback)
				else: handle[2].remove(callback)
		else: print("tried to register unknown event handler id '" + event + "', ignoring this call...")

	def call_attached_handlers(self, name, event, player):
		if name in self.events:
			for cb in self.events[name][2]:
				try: cb(event, player)
				except Exception as e: print("error calling event handler:", e)

	def on_song_end(self, event, name, player, player_one):
		if not self.updated:
			self.media = None
			self.paused = False
			self.call_attached_handlers(name, event, player)

	def on_media_change(self, event, name, player, player_one):
		if self.player_one == player_one:
			self.call_attached_handlers(name, event, player)

	def on_stop(self, event, name, player, player_one):
		if self.player_one == player_one:
			self.call_attached_handlers(name, event, player)

	def on_pause(self, event, name, player, player_one):
		if self.player_one == player_one:
			self.call_attached_handlers(name, event, player)

	def on_play(self, event, name, player, player_one):
		if self.player_one == player_one:
			self.call_attached_handlers(name, event, player)

	def on_pos_change(self, event, name, player, player_one):
		if (self.player_one == self.updated) == player_one:
			pos = event.u.new_position
			if self.updated and pos > self.end_pos:
				self.player_one = not self.player_one
				self.updated = False
				self.call_attached_handlers("player_updated", MediaPlayerEventUpdate(self.media_data), player)
			self.call_attached_handlers(name, event, player)

	def on_update(self, event, name, player, player_one):
		self.call_attached_handlers(name, event, player)

# ====== DESTROY PLAYER INSTANCE =====
	def on_destroy(self):
		self.stop_player()
		print("looks like we're done here, release all player stuffs")
		self.player1.release()
		self.player2.release()
		self.vlc.release()
