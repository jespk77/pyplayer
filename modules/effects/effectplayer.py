import os, random
import vlc

from core import modules
module = modules.Module(__package__)

from . import videoplayer

loop_effect_command = "effect loop {}"
sounds_path_key = "$sounds_path"
pause_music_key = "pause_music_for_effects"

events = []

class SoundEffectPlayer:
	# sound effects longer than this time (im ms) are stopped when the same command is repeated, instead of replaying
	TOGGLE_DURATION = 3000

	def __init__(self):
		self._player = vlc.MediaPlayer()
		self._player.audio_output_set("mmdevice")
		self._media = self._mrl = None

		# (effect_id, loop)
		self._last_effect = None, False
		event_manager = self._player.event_manager()
		event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self._on_stopped)
		event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

	def _on_stopped(self, event):
		videoplayer.close_player()

	def _on_end_reached(self, event):
		if self._last_effect[0] and self._last_effect[1]:
			module.interpreter.put_command(loop_effect_command.format(self._last_effect[0]))
		elif module.configuration.get(pause_music_key): module.interpreter.put_command("player pause false")
		videoplayer.close_player()

	def play_effect(self, arg, loop=False):
		if self._player.is_playing() and not self._last_effect[1]:
			if arg == self._last_effect and self._media.get_duration() > self.TOGGLE_DURATION:
				self._player.stop()
				self._media.release()
				self._media = None
				return None

		sound_path = module.configuration.get(sounds_path_key)
		if sound_path is None or not os.path.isdir(sound_path):
			print("ERROR", "Invalid sound folder:", sound_path)
			return None

		effects = [file for file in os.listdir(sound_path) if arg == os.path.splitext(file)[0]]
		if len(effects) == 1:
			mrl = os.path.join(sound_path, effects[0])
			if os.path.isdir(mrl):
				print("VERBOSE", "Given keyword corresponds to a directory, picking a random one")
				mrl = os.path.join(mrl, random.choice(os.listdir(mrl)))
				self._last_effect = arg, loop
				self._set_media(mrl)

			else:
				sound_file = os.path.splitext(effects[0])
				# dirty workaround to make ogg files loopable
				# caused by vlc error: 'ogg demux error: No selected seekable stream found'
				if loop and sound_file[1] == ".ogg":
					self._last_effect = sound_file[0], True
					self._set_media(mrl)
				else:
					self._last_effect = sound_file[0], False
					self._set_media(mrl, "input-repeat=-1" if loop else "input-repeat=0")
			return self._last_effect[0]
		else:
			print("VERBOSE", "Cannot determine sound effect from", arg, ", there are", len(effects), "posibilities")
			return None

	def play_last_effect(self): self._set_media()

	def _on_parsed(self, event):
		if self._media.get_parsed_status() == vlc.MediaParsedStatus.done:
			for track in self._media.tracks_get():
				if track.type == vlc.TrackType.video:
					print("VERBOSE", "Found a video track in the parsed media, starting video player")
					return videoplayer.open_player(self)
		else: print("WARNING", f"Parsing of '{self._mrl}' failed")
		videoplayer.close_player()
		self._play()

	def _set_media(self, mrl=None, *args):
		if mrl is not None:
			self._media = vlc.Media(mrl, *args)
			self._media.event_manager().event_attach(vlc.EventType.MediaParsedChanged, self._on_parsed)
			self._mrl = mrl

		if self._media is not None:
			self._player.set_media(self._media)
			self._media.parse_with_options(vlc.MediaParseFlag.local, -1)

	def _play(self):
		if module.configuration.get(pause_music_key): module.interpreter.put_command("player pause true")
		self._player.play()

	def play_on_hwnd(self, hwnd):
		self._player.set_hwnd(hwnd)
		self._play()

	def clear_hwnd(self):
		self._player.stop()
		self._player.set_hwnd(0)

	def stop_player(self):
		self._player.stop()
		self._media.release()
		self._media = self._mrl = None
		if module.configuration.get(pause_music_key): module.interpreter.put_command("player pause false")

	def on_destroy(self):
		self._player.release()