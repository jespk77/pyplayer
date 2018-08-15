import datetime
from utilities import messagetypes
from ui import pyelement

# DEFAULT MODULE VARIABLES
priority = 0
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
cfg_file = "cfg"
timer = None
time_str = ""
second_time = datetime.timedelta(seconds=1)
last_drink = 0
drink_delay = 0

def get_time_from_string(delay):
	try:
		hour = delay.split("h")
		if len(hour) > 1:
			delay = "".join(hour[1:])
			hour = int(hour[0])
		else: hour = 0

		min = delay.split("m")
		if len(min) > 1:
			delay = "".join(min[1:])
			min = int(min[0])
		else: min = 0

		sec = delay.split("s")
		if len(sec) > 0 and sec[0] != "": sec = int(sec[0])
		else: sec = 0
	except ValueError: return None
	if hour == min == sec == 0: return None
	return datetime.timedelta(hours=hour, minutes=min, seconds=sec)

def on_tick(client, event):
	timer_check()

def timer_check():
	global timer
	time_widget = client.widgets.get("timer")
	if timer is not None and time_widget is not None:
		timer -= second_time
		if timer.total_seconds() == 0:
			timer = None
			client.remove_widget("timer")
			client.unsubscribe_event("tick_second", on_tick)
			interpreter.queue.put_nowait("effect ftl_distress_beacon")
		else: client.widgets["timer"].display_text = "\u23f0 " + str(timer)
	else: timer = None

def widget_get(name=None):
	if name is None: return client
	return client.children.get(name)

# ===== MAIN COMMANDS =====
# - cfg commmand
def command_cfg(arg, argc):
	pass

def command_cfg_get(arg, argc):
	if 1 <= argc <= 2:
		wd = widget_get(arg.pop(0) if argc == 2 else None)
		if wd is None: return None

		value = wd[arg[0]]
		if len(str(value)) == 0: return messagetypes.Reply("Unknown option '{}'".format(arg[0]))
		return messagetypes.Reply("'{}' is set to '{}'".format(arg[0], value))

def command_cfg_remove(arg, argc):
	if 1 <= argc <= 2:
		wd = widget_get(arg.pop(0) if argc == 2 else None)
		if wd is None: return None

		del wd[arg[0]]
		return messagetypes.Reply("'{}' has been deleted")

def command_cfg_set(arg, argc, save=True):
	if 2 <= argc <= 3:
		wd = widget_get(arg.pop(0) if argc == 3 else None)
		if wd is None: return None
		elif not isinstance(wd.configuration.get(arg[0], ""), str): return messagetypes.Reply("Cannot set a nested configuration option")

		wd[arg[0]] = arg[1]
		return messagetypes.Reply("'{}' has been updated to '{}'".format(arg[0], wd[arg[0]]))

def command_timer(arg, argc):
	if argc == 1:
		time = get_time_from_string(arg[0])
		if time is not None:
			if isinstance(time, datetime.timedelta):
				global timer
				timer = time
				client.add_widget("timer", pyelement.PyTextlabel(client.widgets["header"]), side="left").display_text = "\u23f0 {}".format(timer)
				client.subscribe_event("tick_second", on_tick)
				return messagetypes.Reply("Timer set")
			else: return messagetypes.Reply(str(time))
		else: return messagetypes.Reply("Cannot decode time syntax, try again...")

commands = {
	"cfg": {
		"": command_cfg_get,
		"set": command_cfg_set,
		"remove": command_cfg_remove,
		"list": 0
	}, "timer": command_timer
}