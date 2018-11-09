from ui import pywindow, pyelement

initial_cfg = {"foreground": "white", "background": "gray25", "highlight_color": "cyan", "highlight_delay": 0, "command": "effect deer"}
class TimeCount(pywindow.PyWindow):
	def __init__(self, master, title, icon="", count_time=None):
		super().__init__(master.window, "counter", initial_cfg=initial_cfg)
		self.timer = 0
		self.timer_callback = None
		self.flashes = 0
		self.countdown = 0 if count_time else -1
		self._count_time = count_time

		background_color = self["background"]
		foreground_color = self["foreground"]
		self.set_widget("label", pyelement.PyTextlabel(self.frame))
		self.widgets["label"].display_text = "initializing..."
		self.widgets["label"].configure(background=background_color, foreground=foreground_color)
		self.set_widget("update_button", pyelement.PyButton(self.frame), row=1)
		self.widgets["update_button"].configure(command=self.on_noise_click, background=background_color)
		try: self.widgets["update_button"].image = pyelement.PyImage(file=icon)
		except ValueError: print("WARNING", "Invalid/none specified for icon '{}'".format(icon))
		self.set_widget("reset_button", pyelement.PyButton(self.frame), row=2)
		self.widgets["reset_button"].text = "Reset"
		self.widgets["reset_button"].configure(command=self.on_timer_reset, background=background_color, foreground=foreground_color)

		self.title = title
		self.icon = icon
		self.row_options(1, weight=1)
		self.column_options(0, weight=1)

	def set_delay_time(self, seconds):
		self.highlight_delay = seconds

	def set_callback(self, callback):
		if callable(callback): self.timer_callback = callback

	def update_self(self):
		if self.countdown == 0:
			delay = self._count_time if self._count_time is not None else self["highlight_delay"]
			if delay > 0:
				self.countdown = delay
				self.flashes = 3
				self.flash_highlight()
				if callable(self.timer_callback): self.timer_callback(self["command"])
			else: self.countdown = -1
		elif self.countdown > 0: self.countdown -= 1

		self.widgets["label"].display_text="{timer} | {countdown}".format(timer=self.timer, countdown=self.countdown if self.countdown >= 0 else "--")
		self.timer += 1
		self.after(1, self.update_self)

	def on_noise_click(self):
		if self.countdown >= 0:
			self.timer = 0
			self.disable_highlight()
		else: self.on_timer_reset()

	def on_timer_reset(self):
		self.timer = 0
		self.countdown = self._count_time if self._count_time is not None else self["highlight_delay"]
		self.disable_highlight()

	def enable_highlight(self):
		self.widgets["update_button"].configure(background=self["highlight_color"])

	def disable_highlight(self):
		self.flashes = 0
		self.widgets["update_button"].configure(background=self["background_color"])

	def flash_highlight(self):
		if self.flashes > 0:
			if self.flashes % 2 == 0: self.widgets["update_button"].configure(background=self["highlight_color"])
			else: self.widgets["update_button"].configure(background=self["background"])
			self.flashes -= 1