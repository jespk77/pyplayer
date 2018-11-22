import datetime, os, json
from utilities import messagetypes

# DEFAULT MODULE VARIABLES
priority = 0
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
cfg_folder = ".cfg/"
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
	time_widget = client.widgets["header_left"]
	if timer is not None and time_widget is not None:
		timer -= second_time
		if timer.total_seconds() == 0:
			timer = None
			client.widgets["header_left"].display_text = ""
			client.unsubscribe_event("tick_second", on_tick)
			interpreter.put_command("effect ftl_distress_beacon")
		else: client.widgets["header_left"].display_text = str(timer)#"\u23f0 " + str(timer)
	else: timer = None

# ===== MAIN COMMANDS =====
def command_cfg(arg, argc):
	if argc > 0:
		path = cfg_folder + arg[0]
		write_file = False
		if arg[0] in client.children:
			wd = client.children[arg.pop(0)]
			argc -= 1
		else:
			if os.path.isfile(path):
				arg = arg[1:]
				argc -= 1
				write_file = True
				file = open(path, "r")
				try: wd = json.load(file)
				except json.JSONDecodeError as e:
					file.close()
					return messagetypes.Reply("Error parsing configuration file: {}".format(e))
			else: wd = client

		if argc >= 2:
			arg[1] = " ".join(arg[1:])
			try:
				cl = wd[arg[0]]
				if isinstance(cl, dict) or isinstance(cl, list): return messagetypes.Reply("Cannot set a nested option")
			except KeyError: pass

			if arg[1] == "none":
				del wd[arg[0]]
				reply = "Configuration option '{}' deleted".format(arg[0])
			else:
				try:
					wd[arg[0]] = arg[1]
					reply = "Configuration option '{}' updated to '{}'".format(arg[0], wd[arg[0]])
				except TypeError as e: reply = str(e)

			if write_file:
				file = open(path, "w")
				json.dump(wd, file, indent=5)
				file.close()
			else: wd.write_configuration()
			return messagetypes.Reply(reply)
		elif argc == 1:
			try: vl = wd[arg[0]]
			except KeyError: vl = None
			if vl is not None: return messagetypes.Reply("Configuration option '{}' is set to '{}'".format(arg[0], vl))
			else: return messagetypes.Reply("Configuration option '{}' is not set".format(arg[0]))
		else: return messagetypes.Reply("cfg {module} option1{::option2...} ['get', 'set' value]")

def command_timer(arg, argc):
	if argc == 1:
		time = get_time_from_string(arg[0])
		if time is not None:
			if isinstance(time, datetime.timedelta):
				global timer
				timer = time
				client.widgets["header_left"].display_text = str(timer)#"\u23f0 {}".format(timer)
				client.subscribe_event("tick_second", on_tick)
				return messagetypes.Reply("Timer set")
			else: return messagetypes.Reply(str(time))
		else: return messagetypes.Reply("Cannot decode time syntax, try again...")

commands = {
	"cfg": command_cfg,
	"timer": command_timer
}