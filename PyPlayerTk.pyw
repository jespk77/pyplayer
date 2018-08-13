from tkinter import ttk
import sys, datetime

from ui import pywindow, pyelement
from console import TextConsole
from interpreter import Interpreter

client = None
interp = None
class PyPlayerEvent:
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

class PyPlayer(pywindow.RootPyWindow):
	def __init__(self):
		pywindow.RootPyWindow.__init__(self, "client")
		self.add_widget("header", pyelement.PyTextlabel(self), fill="x")
		self.title_song = ""
		self.icon = "assets/icon.ico"

		self.progressbar_style = ttk.Style()
		self.progressbar_style.theme_use("default")
		self.progressbar_style.configure(style="Horizontal.TProgressbar")
		self.add_widget("progressbar", pyelement.PyProgressbar(self), fill="x")
		self.add_widget("console", TextConsole(self, command_callback=self.parse_command), fill="both", expand=True).focus()

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
				except Exception as e: print("An error occured while processing event '", name, "' ->", e)

	def update_label(self):
		self.date = datetime.datetime.today()
		self.widgets["header"].display_text = self.date.strftime(self["header_format"])
		self.post_event("tick_second", PyPlayerEvent(date=self.date))
		self.after(1, self.update_label)

	def update_title(self, title, checks=None):
		prefix = ""
		for c in (checks if checks is not None else interp.checks): prefix += "[" + str(c) + "] "
		self.title_song = title
		self.title = prefix + title
		self.post_event("title_update", PyPlayerEvent(title=title))

	def update_progressbar(self, progress):
		if progress > self.widgets["progressbar"].maximum: progress = self["progressbar"].maximum
		elif progress < 0: progress = 0
		self.widgets["progressbar"].progress = progress
		self.post_event("progressbar_update", PyPlayerEvent(progress=progress))

	def parse_command(self, cmd):
		try: interp.queue.put_nowait(cmd)
		except Exception as e: self.widgets["console"].set_reply(msg="Cannot send command: " + str(e))

	def add_reply(self, s=0.1, args=None):
		if args is None: self.after(s, self.widgets["console"].set_reply)
		else: self.after(s, self.widgets["console"].set_reply, *args)

	def add_message(self, args, s=0.1):
		self.after(s, self.widgets["console"].set_notification, *args)

class PyLog:
	filename = "log"
	def __init__(self):
		file = open(self.filename, "w")
		file.write(str(datetime.datetime.today()) + " ")
		file.close()

	def write(self, str):
		file = open(self.filename, "a")
		file.write(str)
		file.close()

	def flush(self):
		pass

if __name__ == "__main__":
	if "console" not in sys.argv:
		sys.stdout = PyLog()
		print("PyPlayer: file logging enabled")

	print("initializing client...")
	client = PyPlayer()
	interp = Interpreter(client)
	client.start()
	print("client closed, destroying client...")
	if interp is not None and interp.is_alive(): interp.queue.put(False)
	interp.join()
