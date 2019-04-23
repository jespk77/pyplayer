import datetime
import humanize

from console import TextConsole
from ui import pywindow, pyelement

import enum
class PyPlayerCloseReason(enum.Enum):
	NONE = 0,
	RESTART = 1,
	MODULE_CONFIGURE = 2

initial_cfg = { "autosave_delay": 5, "directory":{}, "default_path": "", "header_format": "PyPlayer - %a %b %d, %Y %I:%M %p -", "loglevel": "info" }
progressbar_cfg = { "background": "cyan", "troughcolor": "black" }
browser_cfg = { "background": "black", "selectforeground": "cyan" }
console_cfg = { "background": "black", "error.foreground": "red", "font":{"family":"terminal","size":10}, "info.foreground": "yellow",
				"insertbackground": "white", "reply.foreground": "gray", "selectbackground": "gray30" }

class PyPlayer(pywindow.PyWindow):
	def __init__(self, root):
		pywindow.PyWindow.__init__(self, root, id="client", initial_cfg=initial_cfg)
		self.content.place_widget(pyelement.PyTextlabel(self.content, "header_left", initial_cfg={"background": "black", "foreground": "cyan"}))
		self.content.place_widget(pyelement.PyTextlabel(self.content, "header", initial_cfg={"background": "black"}), column=1)
		self.content.place_widget(pyelement.PyTextlabel(self.content, "header_right", initial_cfg={"background": "black", "foreground": "gray"}), column=2)
		self.content.layer.column(1, minsize=30, weight=1)
		self.title_song = ""
		self.icon = "assets/icon"
		self._interp = self._cmd = None

		try:
			import psutil
			self._process = psutil.Process()
			self._boottime = datetime.datetime.fromtimestamp(psutil.boot_time())
		except ImportError:
			print("INFO", "psutil package not found, extra info cannot be displayed")
			self._process = None
			self._boottime = datetime.datetime.today()

		pbar = pyelement.PyProgressbar(self.content, "progressbar", initial_cfg=progressbar_cfg)
		pbar.maximum = 1
		self.content.place_widget(pbar, row=1, columnspan=9)
		@pbar.event_handler.MouseClickEvent("left")
		def on_progressbar_click(x):
			try: self._interp.put_command("player position {}".format(x / pbar.width))
			except Exception as e: print("WARNING", "Error while updating position:", e)

		console = TextConsole(self.content, initial_cfg=console_cfg)
		self.content.place_widget(console, row=3, columnspan=9).set_focus()
		@console.event_handler.KeyEvent("enter")
		def _command_confirm():
			cmd = console.get_current_line().rstrip("\n")
			if len(cmd) > 0:
				print("INFO", "Processing command:", cmd)
				self._interp.put_command(cmd, self._cmd)
			return console.event_handler.block

		self.content.layer.row(3, minsize=100, weight=1)
		self._flags = PyPlayerCloseReason.NONE
		self.focus_followsmouse()
		self.update_loglevel()

	@property
	def flags(self): return self._flags.name.lower()

	def update_loglevel(self, value=None):
		if value is None: value = self.configuration["loglevel"].value
		print("INFO", "Set loglevel:", value)
		import pylogging
		pylogging.get_logger().log_level = value

	def window_tick(self, date):
		self.content["header"].text = date.strftime(self.configuration["header_format"].value)
		uptime = str(date - self._boottime).split(".")[0]
		if self._process is not None: self.content["header_right"].text = "{} / {}".format(uptime, humanize.naturalsize(self._process.memory_info().rss))
		else: self.content["header_right"].text = uptime
		pywindow.PyWindow.window_tick(self, date)

	def update_title(self, title, checks=None):
		prefix = " ".join(["[{}]".format(c) for c in (checks if checks is not None else self._interp.arguments)])
		self.title_song = title
		self.title = prefix + ' ' + title

	def update_title_media(self, media_data, color=None):
		self.update_title(media_data.display_name)
		self.content["progressbar"].progress = 0
		self.content["progressbar"].configure(background=color if color else self.content.configuration["progressbar::background"])

	def update_progressbar(self, progress):
		if progress > self.content["progressbar"].maximum: progress = self.content["progressbar"].maximum
		elif progress < 0: progress = 0
		self.content["progressbar"].progress = progress

	def set_songbrowser(self, browser):
		self.content.place_widget(browser, row=2, columnspan=9)
		if browser is None: self.content.layer.row(2, minsize=0, weight=0).row(3, weight=1)
		else: self.content.layer.row(2, minsize=200, weight=70).row(3, weight=20)

	def show_lyrics(self, title):
		from modules.utilities.lyricviewer import LyricViewer
		wd = self.get_window("lyric_viewer")
		if wd:
			wd = LyricViewer(self.content)
			self.open_window("lyric_viewer", wd)

		title = title.split(" - ", maxsplit=1)
		if len(title) == 2:
			wd.load_lyrics(title[0], title[1])
			return True
		else: return False

	def close_with_reason(self, reason):
		reason = reason.upper()
		try:
			self._flags = PyPlayerCloseReason[reason]
			self.schedule(func=self.destroy)
		except KeyError: raise ValueError("Unknown reason '{}'".format(reason))

	def on_reply(self, reply, tags=(), cmd=None):
		self._cmd = cmd
		self.schedule(func=self.content["console"].add_reply, reply=reply, tags=tags, prefix=" ? " if cmd else None)

	def on_notification(self, message, tags=()):
		self.schedule(func=self.content["console"].add_notification, message=message, tags=tags)