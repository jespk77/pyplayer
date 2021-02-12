import os, vlc

from core import messagetypes, modules
module = modules.Module(__package__)

# MODULE SPECIFIC VARIABLES
loop_effect_command = "effect loop {}"
sounds_path_key = "sounds_path"

class SoundEffectPlayer:
	# sound effects longer than this time (im ms) are stopped when the same command is repeated, instead of replaying
	TOGGLE_DURATION = 3000

	def __init__(self):
		self._player = vlc.MediaPlayer()
		self._player.audio_output_set("mmdevice")
		self._media = None

		# (effect_id, loop)
		self._last_effect = None, False
		self._player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

	def _on_end_reached(self, event):
		if self._last_effect[0] and self._last_effect[1]:
			module.interpreter.put_command(loop_effect_command.format(self._last_effect[0]))

	def play_effect(self, arg, loop=False):
		if self._player.is_playing() and not self._last_effect[1]:
			if arg == self._last_effect and self._media.get_duration() > self.TOGGLE_DURATION:
				self._player.stop()
				self._media.release()
				self._media = None
				return

		sound_path = module.configuration.get(sounds_path_key)
		if sound_path is None or not os.path.isdir(sound_path):
			print("ERROR", "Invalid sound folder:", sound_path)
			return

		effects = [file for file in os.listdir(sound_path) if arg == os.path.splitext(file)[0]]
		if len(effects) == 1:
			mrl = os.path.join(sound_path, effects[0])
			if os.path.isdir(mrl):
				print("VERBOSE", "Given keyword corresponds to a directory, picking a random one")
				import random
				mrl = os.path.join(mrl, random.choice(os.listdir(mrl)))
				self._last_effect = arg, loop
				self._media = vlc.Media(mrl)

			else:
				sound_file = os.path.splitext(effects[0])
				# dirty workaround to make ogg files loopable
				# caused by vlc error: 'ogg demux error: No selected seekable stream found'
				if loop and sound_file[1] == ".ogg":
					self._last_effect = sound_file[0], True
					self._media = vlc.Media(mrl)
				else:
					self._last_effect = sound_file[0], False
					self._media = vlc.Media(mrl, "input-repeat=-1" if loop else "input-repeat=0")

			self._player.set_media(self._media)
			self._player.play()
			return messagetypes.Reply("Playing sound effect: " + self._last_effect[0])
		else:
			print("VERBOSE", "Cannot determine sound effect from", arg, ", there are", len(effects), "posibilities")
			return messagetypes.Reply("Cannot determine what sound that should be")

	def stop_player(self):
		self._player.stop()
		self._media.release()
		self._media = None
		return messagetypes.Empty()

	def on_destroy(self):
		self._player.release()

effect_player = SoundEffectPlayer()
def play_effect_loop(arg, argc):
	if argc > 0: return effect_player.play_effect(" ".join(arg), True)

def play_effect(arg, argc):
	if argc > 0: return effect_player.play_effect(" ".join(arg), False)

def stop_effect(arg, argc):
	if argc == 0: return effect_player.stop_player()

@module.Initialize
def initialize():
	module.configuration.get_or_create(sounds_path_key, "")

@module.Destroy
def on_destroy():
	global effect_player
	effect_player.on_destroy()

module.commands = {
	"effect":{
		"loop": play_effect_loop,
		"stop": stop_effect,
		"": play_effect
	}
}