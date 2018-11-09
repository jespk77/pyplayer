from tkinter import ttk
from traceback import format_exception
import datetime

from ui import pywindow, pyelement
from console import TextConsole

class PyPlayerEvent:
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

initial_cfg = { "autosave_delay": 5, "directory":{"default": ""}, "header_format": "PyPlayer - %a %b %d, %Y %I:%M %p -", "loglevel": "warning" }
progressbar_cfg = {"background": "cyan", "foreground": "white"}
header_cfg = { "background": "black", "foreground": "white" }
browser_cfg = { "background": "black", "foreground": "white", "selectforeground": "cyan" }
console_cfg = { "background": "black", "error.foreground": "red", "font":{"family":"terminal","size":10}, "foreground": "white", "info.foreground": "yellow",
				"insertbackground": "white", "reply.foreground": "gray", "selectbackground": "gray30" }

class PyPlayer(pywindow.RootPyWindow):
	def __init__(self):
		pywindow.RootPyWindow.__init__(self, "client", initial_cfg)
		self.set_widget("header_left", pyelement.PyTextlabel(self.frame), initial_cfg=header_cfg)
		self.set_widget("header", pyelement.PyTextlabel(self.frame), initial_cfg=header_cfg, column=1)
		self.set_widget("header_right", pyelement.PyTextlabel(self.frame), initial_cfg=header_cfg, column=2)
		self.column_options(1, minsize=30, weight=1)
		self.title_song = ""
		self.icon = "assets/icon"
		self.interp = None

		self.set_widget("progressbar", pyelement.PyProgressbar(self.frame), initial_cfg=progressbar_cfg, row=1, columnspan=9).maximum = 1
		self.set_widget("console", TextConsole(self, command_callback=self.parse_command), initial_cfg=console_cfg, row=3, columnspan=9).focus()
		self.row_options(3, minsize=100, weight=1)

		self.last_cmd = None
		self.event_handlers = {
			"progressbar_update": [],  # parameters [ progress: int ]
			"tick_second": [],  # parameters [ date: datetime ]
			"title_update": []  # parameters [ title: str ]
		}

		self.focus_followsmouse()
		self.update_label()
		self.update_loglevel()

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
				except Exception as e: print("ERROR", "An error occured while processing event '", name, "' -> ", "\n".join(format_exception(None, e, e.__traceback__)), sep="")

	def update_loglevel(self):
		import pylogging
		pylogging.get_logger().log_level = self["loglevel"]

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

	def set_songbrowser(self, browser):
		self.set_widget("songbrowser", browser, row=2, columnspan=9)
		if browser is None:
			self.row_options(2, weight=0)
			self.row_options(3, weight=1)
		else:
			self.row_options(2, minsize=200, weight=70)
			self.row_options(3, weight=20)

	def show_lyrics(self, title):
		from modules.utilities.lyricviewer import LyricViewer
		wd = self.children.get("lyric_viewer")
		if wd is not None: create_new = not wd.is_alive
		else: create_new = True

		if create_new:
			wd = LyricViewer(self.window)
			self.open_window("lyric_viewer", wd)

		title = title.split(" - ", maxsplit=1)
		if len(title) == 2:
			wd.load_lyrics(title[0], title[1])
			return True
		else: return False

	def parse_command(self, cmd, dt=None):
		try: self.interp.put_command(cmd, dt)
		except Exception as e: self.widgets["console"].set_reply(msg="Cannot send command: " + str(e))

	def add_reply(self, args):
		self.after(.1, self.widgets["console"].set_reply, *args)

	def add_message(self, args, s=0.1):
		self.after(s, self.widgets["console"].set_notification, *args)