from tkinter import ttk
from traceback import format_exception
import datetime, inspect, os

from ui import pywindow, pyelement
from console import TextConsole

class PyPlayerEvent:
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

initial_cfg = { "autosave_delay": 5, "directory":{}, "header_format": "PyPlayer - %a %b %d, %Y %I:%M %p -" }
progressbar_cfg = {"background": "cyan", "foreground": "white"}
header_cfg = { "background": "black", "foreground": "white" }
console_cfg = { "background": "black", "error.foreground": "red", "font":{"family":"terminal","size":10}, "foreground": "white", "info.foreground": "yellow",
				"insertbackground": "white", "reply.foreground": "gray", "selectbackground": "gray30" }

class PyPlayer(pywindow.RootPyWindow):
	def __init__(self):
		pywindow.RootPyWindow.__init__(self, "client", initial_cfg)
		self.add_widget("header", pyelement.PyTextlabel(self), initial_cfg=header_cfg, fill="x")
		self.title_song = ""
		self.icon = "assets/icon"
		self.interp = None

		self.progressbar_style = ttk.Style()
		self.progressbar_style.theme_use("default")
		self.progressbar_style.configure(style="Horizontal.TProgressbar")
		self.add_widget("progressbar", pyelement.PyProgressbar(self), initial_cfg=progressbar_cfg, fill="x").maximum = 1
		self.add_widget("console", TextConsole(self, command_callback=self.parse_command), initial_cfg=console_cfg, fill="both", expand=True).focus()

		self.last_cmd = None
		self.event_handlers = {
			"progressbar_update": [],  # parameters [ progress: int ]
			"tick_second": [],  # parameters [ date: datetime ]
			"title_update": []  # parameters [ title: str ]
		}

		self.focus_followsmouse()
		self.update_label()

	def subscribe_event(self, name, callback):
		if name in self.event_handlers and callable(callback):
			if callback not in self.event_handlers[name]: self.event_handlers[name].append(callback)

	def unsubscribe_event(self, name, callback):
		if name in self.event_handlers:
			self.event_handlers[name].remove(callback)

	def post_event(self, name, data):
		if name in self.event_handlers:
			for c in self.event_handlers[name]:
				try: c(self, data)
				except Exception as e: print("[PyPlayer.ERROR]", "An error occured while processing event '", name, "' -> ", "\n".join(format_exception(None, e, e.__traceback__)), sep="")

	def update_label(self):
		self.date = datetime.datetime.today()
		self.widgets["header"].display_text = self.date.strftime(self["header_format"])
		self.post_event("tick_second", PyPlayerEvent(date=self.date))
		self.after(1, self.update_label)

	def update_title(self, title, checks=None):
		prefix = ""
		for c in (checks if checks is not None else self.interp.arguments): prefix += "[" + str(c) + "] "
		self.title_song = title
		self.title = prefix + title
		self.post_event("title_update", PyPlayerEvent(title=title))

	def update_progressbar(self, progress):
		if progress > self.widgets["progressbar"].maximum: progress = self["progressbar"].maximum
		elif progress < 0: progress = 0
		self.widgets["progressbar"].progress = progress
		self.post_event("progressbar_update", PyPlayerEvent(progress=progress))

	def parse_command(self, cmd):
		try: self.interp.put_command(cmd)
		except Exception as e: self.widgets["console"].set_reply(msg="Cannot send command: " + str(e))

	def add_reply(self, s=0.1, args=None):
		if args is None: self.after(s, self.widgets["console"].set_reply)
		else: self.after(s, self.widgets["console"].set_reply, *args)

	def add_message(self, args, s=0.1):
		self.after(s, self.widgets["console"].set_notification, *args)

class PyLog:
	def __init__(self):
		if not os.path.isdir("logs"): os.mkdir("logs")

		self._filename = "logs/log_{}_0".format(datetime.datetime.today().strftime("%y-%m-%d"))
		self._file = None
		#while self._file is None:
		#	try: self._file = open(self._filename, "x")
		#	except FileExistsError:
		#		try:
		#			suffix = self._filename[-1]
		#			self._filename = self._filename[:-1]
		#			self._filename += int(suffix) + 1
		#		except ValueError: self._filename += "1"

	def __del__(self):
		if self._file is not None: self._file.close()

	@staticmethod
	def _get_class_from_stack(stack):
		return stack[0].f_locals["self"].__class__.__name__

	def _write_to_file(self, log, level):
		if self._file is not None:
			try:
				stack = inspect.stack()[1]
				try: self._file.write("[{}.{}.{}] {}\n".format(PyLog._get_class_from_stack(stack), stack.function, level, log))
				except KeyError: self._file.write("[__main__.{}] {}\n".format(level, log))
			except Exception as e: self._file.write("[?.{}] '{}': ".format(level, log) + "(? -> {})\n".format(e))

	def write_out(self, objects, level="INFO", sep=" ", end="\n", file=None, flush=True):
		self._write_to_file(objects, level)

	def write(self, str):
		file = open(self._filename, "a")
		file.write(str)
		file.close()


	def flush(self):
		if self._file is not None and not self._file.closed:
			self._file.flush()