import gc

from utilities import messagetypes

# DEFAULT MODULE VARIABLES
client = interpreter = None

def command_debug_auto_collection(arg, argc):
	if argc == 0: return messagetypes.Reply("The automatic theshold is set to {}".format(gc.get_threshold()))

def command_debug_garbage_collection(arg, argc):
	if argc == 0:
		gc.collect()
		return messagetypes.Reply("Garbage collection done")

def command_window_check(arg, argc):
	if argc == 1:
		try:
			wd = client.get_window(arg[0])
			if wd: return messagetypes.Reply("DEBUG The window '{}' still exists".format(arg[0]))
		except KeyError: pass
		return messagetypes.Reply("DEBUG: The window '{}' does not exist".format(arg[0]))

def command_window_close(arg, argc):
	if argc == 1:
		client.close_window(arg[0])
		return messagetypes.Reply("DEBUG: The window '{}' is closed".format(arg[0]))

commands = {
	"debug":{
		"garbage": {
			"": command_debug_auto_collection,
			"collect": command_debug_garbage_collection
		},
		"window": {
			"": command_window_check,
			"close": command_window_close,
		}
	}
}