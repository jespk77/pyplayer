import json, os, vlc

from utilities import messagetypes
try:
	import utilities.keyboard_intercept as keyboard_intercept
except ImportError:
	print("WARNING", "Interception library cannot be loaded, hotkey command activation disabled")
	keyboard_intercept = None

# DEFAULT MODULE VARIABLES
interpreter = client = None

# MODULE SPECIFIC VARIABLES
trigger_file = "keytriggers"
loop_effect_command = "effect loop {}"
hook_running = False
key_cache = {}
key_cache_date = -1

def verify_key_cache():
	global trigger_file, key_cache, key_cache_date
	if os.path.isfile(trigger_file):
		mtm = os.stat(trigger_file).st_mtime
		if mtm > key_cache_date:
			key_cache_date = mtm
			try:
				file = open(trigger_file, "r")
				key_cache = json.load(file)
				file.close()
			except Exception as e:
				key_cache.clear()
				print("ERROR", "Updating keyfile:", e)
	else: key_cache.clear()

def on_key_down(key):
	global key_cache
	verify_key_cache()
	key = str(key)
	item = key_cache.get(key)
	if item is not None:
		cmd = item.get("command")
		if cmd is not None: interpreter.put_command(cmd)
	else: print("WARNING", "no entry found for keycode", key)

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
			interpreter.put_command(loop_effect_command.format(self._last_effect[0]))

	def play_effect(self, arg, loop=False):
		if self._player.is_playing() and not self._last_effect[1]:
			if arg == self._last_effect and self._media.get_duration() > self.TOGGLE_DURATION:
				self._player.stop()
				self._media.release()
				self._media = None
				return

		sound_path = client["directory"].get("sounds", {}).get("path")
		if sound_path is None or not os.path.isdir(sound_path):
			print("ERROR", "Invalid sound folder:", sound_path)
			return

		effects = [file for file in os.listdir(sound_path) if arg == os.path.splitext(file)[0]]
		if len(effects) == 1:
			mrl = os.path.join(sound_path, effects[0])
			if os.path.isdir(mrl):
				print("INFO", "Given keyword corresponds to a directory, picking a random one")
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
			print("INFO", "Cannot determine sound effect from", arg, ", there are", len(effects), "posibilities")
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

def start_listener(arg, argc):
	global hook_running
	if argc == 0:
		if not hook_running: start_keyboard_hook()
		return messagetypes.Reply("Interception started")

def stop_listener(arg, argc):
	if argc == 0:
		global hook_running
		if hook_running: pause_keyboard_hook()
		return messagetypes.Reply("Interception stopped")

def initialize():
	try: start_listener(None, 0)
	except: pass

def on_destroy():
	global effect_player
	effect_player.on_destroy()
	pause_keyboard_hook()

def start_keyboard_hook():
	global hook_running
	if keyboard_intercept is not None: keyboard_intercept.initialize(on_key_down)
	hook_running = True

def pause_keyboard_hook():
	global hook_running
	if keyboard_intercept is not None: keyboard_intercept.join()
	hook_running = False

commands = {
	"effect":{
		"loop": play_effect_loop,
		"stop": stop_effect,
		"": play_effect
	}, "interception":{
		"start": start_listener,
		"pause": stop_listener
	}
}