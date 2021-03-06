from utilities import messagetypes

interpreter = client = None

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

def command_log_open(arg, argc):
	if argc == 0:
		import pylogging
		try:
			if pylogging.open_logfile(): return messagetypes.Reply("Log file opened")
			else: return messagetypes.Reply("Cannot open log file")
		except FileNotFoundError: return messagetypes.Reply("Log file not found. Are you using console?")

def command_log_clear(arg, argc, all=False):
	if argc == 0:
		import os, pylogging
		logs = [file for file in os.listdir(pylogging.log_folder) if file.endswith(".log")]
		try:
			if all: logs.pop(0)
			else: logs = logs[10:]

			import shutil
			for f in logs:
				try: os.remove(os.path.join(pylogging.log_folder, f))
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

import datetime
timer = None
one_second = datetime.timedelta(seconds=1)

def command_timer(arg, argc):
	if argc == 1:
		time = get_time_from_string(arg[0])
		if time is not None:
			try:
				global timer
				timer = datetime.timedelta(hours=time[0], minutes=time[1], seconds=time[2])
				@client.update_left_header
				def _timer_update(date):
					global timer
					if timer.total_seconds() > 0:
						client["header_left"].text = "\u23f0 {!s}".format(timer)
						timer -= one_second
					else:
						timer = None
						client["header_left"].text = ""
						client.update_left_header(None)
						interpreter.put_command(client.configuration.get_or_create("timer_command", ""))

				client["header_left"].text = "\u23f0 {!s}".format(timer)
				return messagetypes.Reply("Timer set")
			except ValueError as e: return messagetypes.Reply(str(e))
		else: return messagetypes.Reply("Cannot decode time syntax, try again...")

version_command = ["git", "log", "-1", "--pretty=%H//%ci"]
version_output = None
def command_version(arg, argc):
	if argc == 0:
		global version_output
		if not version_output:
			from utilities import commands
			def get_output(o): global version_output; version_output = o
			commands.process_command(version_command, stdout=get_output)

		try:
			import datetime
			version, date = version_output.split("//")
			date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z\n")
			return messagetypes.Reply("The current version is {version:.7}, it was released on {date}".format(version=version, date=date.strftime("%b %d, %Y")))
		except Exception as e:
			print("ERROR", "Processing git version command:", e)
			return messagetypes.Reply("Unable to get version number")

import psutil, humanize
process = psutil.Process()
boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())

def initialize():
	cmds = client.configuration.get_or_create("startup_commands", [])
	for c in cmds: interpreter.put_command(c)

	@client.update_right_header
	def _right_header(date):
		global process, boot_time
		client["header_right"].text = f"{str(date - boot_time).split('.')[0]} / {humanize.naturalsize(process.memory_info().rss)}"

commands = {
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