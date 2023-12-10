import os, random
import vlc as VLCPlayer


def get_displayname(filepath):
	return os.path.splitext(filepath)[0]

class DynamicClass:
	def __init__(self, **kwargs):
		for it in kwargs.items(): self.__setattr__(*it)
	def __str__(self): return "{}({})".format(self.__class__.__name__, ", ".join(["{}='{}'".format(*it) for it in self.__dict__.items()]))

class MediaPlayerData(DynamicClass):
	def __init__(self, path, song, **kwargs):
		self.path = path
		self.song = song
		self.display_name = get_displayname(song)
		DynamicClass.__init__(self, **kwargs)

class MediaPlayerEventUpdate(DynamicClass):
	id = 0
	def __init__(self, data, **kwargs):
		self.data = data
		DynamicClass.__init__(self, **kwargs)

class MediaPlayer:
	""" Helper class for playing music using the vlc python bindings
	 	When a new song is started when the last song is almost done,
	 	the player will start the new song without stopping the previous for smooth transitioning  """
	end_pos = 0.85

	def __init__(self):
		print("VERBOSE", "Initializing new MediaPlayer instance...")
		self._vlc = VLCPlayer.Instance()
		self._player1 = self._vlc.media_player_new()
		self._player1.audio_output_set("mmdevice")
		self._player2 = self._vlc.media_player_new()
		self._player2.audio_output_set("mmdevice")

		self._paused = False
		self._player_one = True
		self._media = self._media_data = None
		self._updated = False
		self._filter = self._blacklist = self._last_random = None
		self._last_position = 0

		self._events = {
			"end_reached": (VLCPlayer.EventType.MediaPlayerEndReached, self.on_song_end, []),
			"media_changed": (VLCPlayer.EventType.MediaPlayerMediaChanged, self.on_event_default, []),
			"paused": (VLCPlayer.EventType.MediaPlayerPaused, self.on_event_default, []),
			"playing": (VLCPlayer.EventType.MediaPlayerPlaying, self.on_event_default, []),
			"pos_changed": (VLCPlayer.EventType.MediaPlayerPositionChanged, self.on_pos_change, []),
			"stopped": (VLCPlayer.EventType.MediaPlayerStopped, self.on_event_default, []),
			"volume_changed": (VLCPlayer.EventType.MediaPlayerAudioVolume, self.on_event_default, []),
			"muted": (VLCPlayer.EventType.MediaPlayerMuted, self.on_event_default, []),
			"unmuted": (VLCPlayer.EventType.MediaPlayerUnmuted, self.on_event_default, []),
		}

		# register vlc event handlers
		for event in self._events.items():
			event_key, event_value = event
			self._player1.event_manager().event_attach(event_value[0], event_value[1], event_key, self._player1, True)
			self._player2.event_manager().event_attach(event_value[0], event_value[1], event_key, self._player2, False)

		# register custom event handlers
		self._events["player_updated"] = (MediaPlayerEventUpdate, self.on_update, [])

	# === PLAYER PROPERTIES ===
	@property
	def active_player(self):
		""" Get the player that is currenty playing music (this player is currently using the assigned media)
			Returns this player or None if there is nothing playing """
		play1 = self._player1.is_playing()
		play2 = self._player2.is_playing()
		if play1: return self._player2 if play2 and self._updated else self._player1
		elif play2:	return self._player1 if play1 and self._updated else self._player2
		else: return None
	@property
	def next_player(self):
		""" Returns the player that should be used to play the next song """
		return self._player1 if self._player_one else self._player2
	@property
	def current_media(self):
		""" Returns information about the current song playing, or None if nothing playing """
		return self._media_data

	@property
	def filter_path(self): return self._filter[0] if self._filter is not None else ""
	@property
	def filter_keyword(self): return self._filter[1] if self._filter is not None else ""
	def update_filter(self, path="", keyword=""):
		""" Set a filter for random song picking using path and keyword
		 	(will override the blacklist that was set on this player) """
		self._filter = [path, keyword]

	@property
	def blacklist(self): return self._blacklist
	def update_blacklist(self, blacklist):
		""" Update the player blacklist, all songs from artist in this list will not be picked as random song
		 	This list is ignored when a filter is set or when choosing a specific song """
		if blacklist is not None and not isinstance(blacklist, list): raise TypeError("Blacklist must be a list!")
		self._blacklist = blacklist

	# === PLAYER UTILITIES ===
	def list_songs(self, path, keyword="", exact_search=False):
		"""	List all items found in specified directory
			Items that match the full keyword get returned first, if no matches found returns items containing the keyword
				path: the path to search in
				keyword: [optional], returns all items matching this keyword or all items if no argument passed
				exact_search: [optional], set true to only look for songs with an exact match """
		print("VERBOSE", f"looking for songs in '{path}' with keyword(s) '{keyword}'")
		res1 = []
		res2 = []
		keyword = keyword.lower()

		if os.path.isdir(path):
			with os.scandir(path) as dir:
				for entry in dir:
					if entry.is_file():
						file = entry.name
						song = get_displayname(file.replace(" - ", " ").lower())
						if exact_search and song == keyword: return [file]
						elif " " + keyword + " " in " " + song + " ": res1.append(file)
						elif keyword == "" or keyword in song: res2.append(file)

		if len(res1) > 0:
			print("VERBOSE", f"Found {len(res1)} exact match(es)")
			return res1
		else:
			print("VERBOSE", f"Found {len(res2)} match(es) containing required keyword(s)")
			return res2

	def find_song(self, path, keyword=None):
		""" Find songs in given path that contain given keyword, where keyword should be a string list separated by spaces
			- when the keyword ends with a '.' only an exact match (if it exists) is returned
			- when the keyword ends with a number, this number will be used for picking one from the found selection (if in range)
			-> Returns a list of songs found where each item is a tuple: (displayname, song) """
		exact = False
		index = -1
		if keyword and len(keyword) > 0:
			if keyword[-1].endswith("."):
				exact = True
				keyword[-1] = keyword[-1][:-1]
			else:
				try:
					index = int(keyword[-1])
					keyword.pop(-1)
				except ValueError: pass

		keyword = " ".join(keyword)
		ls = self.list_songs(path, keyword, exact_search=exact)
		if 0 <= index < len(ls): return [(get_displayname(ls[index]), ls[index])]
		else: return [(get_displayname(s), s) for s in ls]

	def play_song(self, path, song):
		""" Plays a song only when the full path and song name are known and they exist in the given path
			Returns the updated media data generated by the player if the file exists, or None otherwise """
		print("VERBOSE", f"Preparing to play '{song}' from '{path}'")
		if not os.path.isfile(os.path.join(path, song)): return None
		else: return self._play(path=path, song=song)

	def play_url(self, url, displayname=None):
		""" Plays a song from given url, this can be a url to an internet file or a complete path to a local file
			Use displayname to provide a custom name this file must be displayed as, when not provided it defaults to the filename from the url
		 	Returns the updated media data generated by the player """
		if not displayname: displayname = url.split("/")[-1]
		return self._play(url=url, display_meta=displayname)

	def _play(self, path='', song='', url=None, display_meta=''):
		if self._paused: self.stop_player()

		if song:
			self._media_data = MediaPlayerData(path, song)
			url = os.path.join(path, song)
		elif url: self._media_data = MediaPlayerData('', display_meta)

		if self._media is not None: self._media.release()
		self._media = self._vlc.media_new(url)
		player = self.next_player
		player.set_media(self._media)
		player.play()

		self._paused = False
		self._updated = True
		return self._media_data


	def reset(self):
		""" Stops the player and attempts to restart the last played song from the last known position
		 	In case of a transition this plays the song that was set last and aborts playing any other songs active
		 	It does not however reset the update flag and won't trigger the 'player_updated' again (if it was already called) """
		if self._media:
			self._player1.stop()
			self._player2.stop()
			self._player_one = True
			self._player1.set_media(self._media)
			self._player1.play()
			self._player1.set_position(self._last_position)


	def get_position(self): return self.active_player.get_position()

	def set_position(self, pos):
		""" Update the position the player is currently at, has no effect if the player is stopped/finished
		 	Returns true if the position was updated, false otherwise"""
		if self._media is not None:
			print("VERBOSE", "Trying to update player position to {}".format(pos))
			pl = self.active_player
			if pl is not None:
				pl.set_position(pos)
				pl.play()
				return True
			else: return False
		else:
			print("VERBOSE", "Cannot update position since no previous media was found")
			return False

	def pause_player(self, pause=None):
		""" Toggle player pause (has no effect if nothing is playing) """
		if pause is not None:
			if isinstance(pause, bool): self._paused = pause
			elif isinstance(pause, str): self._paused = (pause.lower() == "true" or pause.lower() == "1")
			else: raise ValueError("Unsupported type")
		else: self._paused = not self._paused and self._media_data is not None

		self._player1.set_pause(self._paused)
		self._player2.set_pause(self._paused)

	def stop_player(self):
		""" Stop playback """
		self._paused = False
		self._player1.stop()
		self._player2.stop()
		self._media_data = None

	@property
	def volume(self): return self._player1.audio_get_volume()
	@volume.setter
	def volume(self, volume):
		volume = min(max(volume, 0), 100)
		self._player1.audio_set_volume(volume)
		self._player2.audio_set_volume(volume)

	@property
	def mute(self): return self._player1.audio_get_mute()
	@mute.setter
	def mute(self, mute):
		self._player1.audio_set_mute(mute)
		self._player2.audio_set_mute(mute)

# ===== OTHER FUNCTIONS =====
	def random_song(self, path="", keyword=""):
		""" Choose a random song from a directory, uses values set in player filter when no arguments are given """
		if path == "": path = self.filter_path
		if keyword == "": keyword = self.filter_keyword

		print("VERBOSE", f"Play random song from '{path}', keyword={keyword}")
		songlist = []
		for word in keyword.split("|"): songlist.extend(self.list_songs(path, word.strip()))

		if len(songlist) > 0:
			song = None
			tries = 0
			while song is None and tries < 3:
				tries += 1
				s = random.choice(songlist)
				match = False
				if self._blacklist is not None:
					for item in self._blacklist:
						if item.lower() == s.split(" - ", maxsplit=1)[0].lower():
							match = True
							print("INFO", "Found blacklist item '{}', tried {} times now".format(item, tries))
							break
				if not match: song = s

			if song is not None:
				self._last_random = (path, song)
				self.play_song(path, song)
				return "Playing: {}".format(get_displayname(song))
			else: return "No song found that doesn't match something in blacklist, try reducing the number of blacklisted items"
		return "No songs with that filter"

	def play_last_random(self):
		if self._last_random is not None:
			return self.play_song(self._last_random[0], self._last_random[1])
		else: return None

# ===== EVENT HANDLING =====
	def attach_event(self, event, callback):
		""" Attach a new callback handle to the selected event, has no effect if handle was already attached or if it is not callable
			(The attached callback will only be called only with the player that is in foreground when the event occurred)
				event: The name of the event
				callback: The function to be called when the event occurs, must take two arguments: the event that was triggered and the current player instance """
		self.update_event_handler(event, callback, add=True)

	def detach_event(self, event, callback):
		""" Detach a handler that was previously attached using attach_event, has no effect if handle was never attached of if it is not callable """
		self.update_event_handler(event, callback, add=False)

	def update_event_handler(self, event, callback, add):
		if event in self._events:
			if not callable(callback): raise TypeError("'callable' argument must be callable")
			handle = self._events[event]
			if add == (not callback in handle[2]):
				if add: handle[2].append(callback)
				else: handle[2].remove(callback)
		else: print("INFO", "Tried to register unknown event handler id '" + event + "', ignoring this call...")

	def call_attached_handlers(self, name, event):
		if name in self._events:
			for cb in self._events[name][2]:
				try: cb(event, self)
				except Exception as e: print("ERROR", f"Calling event handler '{name}':", e)

	def on_song_end(self, event, name, player, player_one):
		if not self._updated:
			self._paused = False
			self._media_data = None
			self.call_attached_handlers(name, event)

	def on_event_default(self, event, name, player, player_one):
		if self._player_one == player_one:
			self.call_attached_handlers(name, event)

	def on_pos_change(self, event, name, player, player_one):
		if (self._player_one == self._updated) == player_one:
			pos = player.get_position()
			self._last_position = pos
			if self._updated and pos > MediaPlayer.end_pos:
				self._player_one = not self._player_one
				self._updated = False
				self.call_attached_handlers("player_updated", MediaPlayerEventUpdate(self._media_data))
			self.call_attached_handlers(name, event)

	def on_update(self, event, name, player, player_one):
		self.call_attached_handlers(name, event)

# ====== DESTROY PLAYER INSTANCE =====
	def on_destroy(self):
		print("VERBOSE", "Looks like we're done here, release all player stuffs")
		self._player1.release()
		self._player2.release()
		self._vlc.release()
