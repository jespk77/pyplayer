from ui.tk_legacy import pyimage, pywindow, pyelement

initial_cfg = {"foreground": "white", "background": "gray25", "highlight_color": "cyan", "highlight_delay": 0, "command": "effect deer"}
class TimeCount(pywindow.PyWindow):
	def __init__(self, master, title, icon="", count_time=None, timer_callback=None):
		pywindow.PyWindow.__init__(self, master, "counter", initial_cfg=initial_cfg)
		self._timer = 0
		self._timer_callback = timer_callback
		self._countdown = 0 if count_time else -1
		self._count_time = count_time

		self.title = title
		self.icon = icon
		self.content.row(1, weight=1).column(0, weight=1)

	def create_widgets(self):
		background_color = self.configuration["background"]
		foreground_color = self.configuration["foreground"]

		lbl = self.content.place_element(pyelement.PyTextlabel(self.content, "label", initial_cfg={"background": background_color, "foreground": foreground_color}))
		lbl.text = "initializing..."
		ubt = self.content.place_element(
            pyelement.PyButton(self.content, "update_button", initial_cfg={"background": background_color}), row=1)
		@ubt.event_handler_InteractEvent
		def _noise_click(): self.on_noise_click()
		try: ubt.image = pyimage.PyImage(file=self.icon)
		except ValueError: print("WARNING", "Invalid/none specified for icon '{}', button will be left blank".format(self.icon))
		rbt = self.content.place_element(pyelement.PyButton(self.content, "reset_button", initial_cfg={"background": background_color, "foreground": foreground_color}), row=2)
		rbt.text = "Reset"
		@rbt.event_handler.InteractEvent
		def _noise_reset(): self.on_timer_reset()

	def window_tick(self, date):
		if self._countdown == 0:
			delay = self._count_time if self._count_time is not None else self.configuration["highlight_delay"]
			if delay > 0:
				self._countdown = delay
				try: self._timer_callback(self.configuration["command"])
				except Exception as e: print("ERROR", "Calling timer callback:", e)
			else: self._countdown = -1
		elif self._countdown > 0: self._countdown -= 1

		self.content["label"].text="{timer} | {countdown}".format(timer=self._timer, countdown=self._countdown if self._countdown >= 0 else "--")
		self._timer += 1
		pywindow.PyWindow.window_tick(self, date)

	def on_noise_click(self):
		if self._countdown >= 0: self._timer = 0
		else: self.on_timer_reset()

	def on_timer_reset(self):
		self._timer = 0
		self._countdown = self._count_time if self._count_time is not None else self.configuration["highlight_delay"]