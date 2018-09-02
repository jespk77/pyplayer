from vlc import MediaPlayer
import os, json

from utilities import messagetypes
try: import keyboard_intercept
except ImportError as e:
	print("[Interception.ERROR] Interception could not be loaded: ", e)
	keyboard_intercept = None

# DEFAULT MODULE VARIABLES
priority = 4
interpreter = None
client = None
platform = None

# MODULE SPECIFIC VARIABLES
trigger_file = "keytriggers"
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
				print("[Interception.ERROR] updating keyfile:", e)
	else: key_cache.clear()

def on_key_down(key):
	global key_cache
	verify_key_cache()
	key = str(key)
	item = key_cache.get(key)
	if item is not None:
		cmd = item.get("command")
		if cmd is not None: interpreter.queue.put_nowait(cmd)
	else: print("[Interception.WARNING] no entry found for keycode", key)

class SoundEffectPlayer:
	def __init__(self):
		self.player = MediaPlayer()
		self.player.audio_output_set("mmdevice")
		self.toggle_duration = 3000
		self.md = None

	def play_effect(self, arg, loop=False):
		if self.player.is_playing():
			if arg == self.last_effect and self.md.get_duration() > self.toggle_duration:
				self.player.stop()
				self.md.release()
				self.md = None
				return

		sound_path = client["directory"].get("sounds")
		if sound_path is not None and not sound_path.endswith("/"): sound_path += "/"
		if sound_path is None or not os.path.isdir(sound_path): print("[EffectPlayer] invalid sound folder:", sound_path); return
		effects = [file for file in os.listdir(sound_path) if arg == os.path.splitext(file)[0]]
		if len(effects) == 1:
			if loop: self.player.set_mrl(sound_path + effects[0], "input-repeat=-1")
			else: self.player.set_mrl(sound_path + effects[0])
			self.md = self.player.get_media()
			self.player.play()
			self.last_effect = os.path.splitext(effects[0])[0]
			return messagetypes.Reply("Playing sound effect: " + self.last_effect)
		else:
			print("[EffectPlayer.INFO] cannot determine sound effect from", arg, ", there are", len(effects), "posibilities")
			return messagetypes.Reply("Cannot determine what sound that should be")

	def stop_player(self):
		self.player.stop()
		self.md = None
		return messagetypes.Empty()

	def on_destroy(self):
		self.player.release()

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
		if not hook_running and keyboard_intercept is not None:
			try:
				keyboard_intercept.initialize(on_key_down)
				hook_running = True
			except Exception as e: return messagetypes.Error(e, "Error loading interception")
		return messagetypes.Reply("Interception started")

def stop_listener(arg, argc):
	if argc == 0:
		global hook_running
		if hook_running and keyboard_intercept is not None:
			keyboard_intercept.join()
			hook_running = False
			return messagetypes.Reply("Interception stopped")
		else: return messagetypes.Reply("Interception not running")

def initialize():
	start_listener(None, 0)
	if len(interpreter.arguments) == 0: interpreter.put_command("effect startup")

def on_destroy():
	global effect_player
	effect_player.on_destroy()
	stop_listener(None, 0)

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