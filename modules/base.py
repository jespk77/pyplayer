import datetime

from ui import pyconfiguration
from utilities import messagetypes

# DEFAULT MODULE VARIABLES
interpreter = client = None

# MODULE SPECIFIC VARIABLES
cfg_folder = ".cfg/"

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
	else: return hour, min, sec

# ===== MAIN COMMANDS =====
def command_cfg(arg, argc):
	if argc > 0:
		cg = client.get_window(arg[0])
		if cg is None:
			import os
			file = os.path.join(cfg_folder, arg[0])
			if os.path.isfile(file):
				cg = pyconfiguration.ConfigurationFile(filepath=file)
				arg.pop(0)
			else: cg = client
		else: arg.pop(0)

		if len(arg) > 1:
			arg = [arg[0], " ".join(arg[1:])]
			key, value = arg
			if value == "none":
				try:
					del cg.configuration[key]
					msg = messagetypes.Reply("Option '{}' was deleted".format(key))
				except Exception as e: return messagetypes.Reply(str(e))
			else:
				try:
					cg.configuration[key] = value
					msg = messagetypes.Reply("Option '{}' is updated to '{}'".format(key, value))
				except Exception as e: return messagetypes.Reply(str(e))
			cg.write_configuration()
			return msg
		elif len(arg) == 1:
			try: return messagetypes.Reply("Option '{}' is set to '{}'".format(arg[0], cg.configuration[arg[0]].value))
			except KeyError: return messagetypes.Reply("Option '{}' was not found".format(arg[0]))

def command_debug_memory(arg, argc):
	if argc == 0:
		import gc
		gc.collect()
		return messagetypes.Reply("DEBUG: Garbage collection finished")

def command_log_open(arg, argc):
	if argc == 0:
		import pylogging
		try:
			if pylogging.open_logfile(): return messagetypes.Reply("Log file opened")
			else: return messagetypes.Reply("Cannot open log file")
		except FileNotFoundError: return messagetypes.Reply("Log file not found! Are you using console?")

def command_log_clear(arg, argc, all=False):
	if argc == 0:
		import os
		logs = [file for file in os.listdir("logs") if file.endswith(".log")]
		try:
			if all: logs.pop(0)
			else: logs = logs[10:]

			import shutil
			for f in logs:
				try: os.remove("logs\{}".format(f))
				except Exception as e: print("ERROR", "Trying to remove '{}':".format(f), e)
		except IndexError: pass
		return messagetypes.Reply("Cleared all log files (except for the current)" if all else "Cleaned up log files except for the last 10")

def command_module_configure(arg, argc):
	if argc == 0:
		client.close_with_reason("module_configure")
		return messagetypes.Reply("Module configuration loading...")

def command_restart(arg, argc):
	if argc == 0:
		client.close_with_reason("restart")
		return messagetypes.Reply("Restarting Pyplayer...")

def command_timer(arg, argc):
	if argc == 1:
		time = get_time_from_string(arg[0])
		if time is not None:
			try:
				client.set_timer(*time)
				return messagetypes.Reply("Timer set")
			except ValueError as e: return messagetypes.Reply(str(e))
		else: return messagetypes.Reply("Cannot decode time syntax, try again...")

version_command = ["git", "log", "-1", "--pretty=%H//%ci"]
version_output = None
def command_version(arg, argc):
	if argc == 0:
		if not version_output:
			from utilities import commands
			def get_output(o): global version_output; version_output = o
			commands.process_command(version_command, stdout=get_output)

		try:
			version, date = version_output.split("//")
			date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z\n")
			return messagetypes.Reply("The current version is {version:.7}, it was released on {date}".format(version=version, date=date.strftime("%b %d, %Y")))
		except Exception as e:
			print("ERROR", "Processing git version command:", e)
			return messagetypes.Reply("Unable to get version number")

def initialize():
	cmds = client.configuration.get_or_create("startup_commands", []).value
	for c in cmds: interpreter.put_command(c)

commands = {
	"cfg": command_cfg,
	"log": {
		"": command_log_open,
		"clean": command_log_clear,
		"clear": lambda arg,argc: command_log_clear(arg, argc, all=True)
	},
	"modules": command_module_configure,
	"restart": command_restart,
	"timer": command_timer,
	"version": command_version
}