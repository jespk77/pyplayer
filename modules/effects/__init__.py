from core import messagetypes, modules

from . import effectplayer

effect_player = effectplayer.SoundEffectPlayer()
module = modules.Module(__package__)

def play_effect(arg, argc, loop=False):
	if argc > 0:
		effect = effect_player.play_effect(" ".join(arg), loop)
		if effect is not None: return messagetypes.Reply(f"{'Looping' if loop else 'Playing'} sound effect '{effect}'")
	return messagetypes.Reply("No sound effect found")

def play_last_effect(arg, argc):
	effect_player.play_last_effect()
	return messagetypes.Reply("Replaying last effect")

def stop_effect(arg, argc):
	if argc == 0:
		effect_player.stop_player()
		return messagetypes.Reply("Effect player stopped")

@module.Initialize
def initialize():
	module.configuration.get_or_create(effectplayer.sounds_path_key, "")
	module.configuration.get_or_create(effectplayer.pause_music_key, False)

@module.Destroy
def on_destroy():
	global effect_player
	effect_player.on_destroy()

module.commands = {
	"effect": {
		"last": play_last_effect,
		"loop": lambda arg, argc: play_effect(arg, argc, True),
		"stop": stop_effect,
		"": play_effect
	}
}