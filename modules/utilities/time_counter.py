from ui import pywindow, pyelement
import tkinter

class TimeCount(pywindow.PyWindow):
	def __init__(self, root):
		super().__init__(root, "Counter")
		self.timer = 0
		self.timer_callback = None
		self.flashes = 0
		self.countdown = -1
		self.noise = tkinter.PhotoImage(file="assets/noise.png")

		background_color = self["background_color"]
		foreground_color = self["foreground_color"]

		self.add_widget("label", pyelement.PyTextlabel(self), fill="both", expand=True)
		self.widgets["label"].display_text = "initializing..."
		self.widgets["label"].configure(background=background_color, foreground=foreground_color)
		self.add_widget("update_button", pyelement.PyButton(self), fill="x")
		self.widgets["update_button"].configure(image=self.noise, command=self.on_noise_click, background=background_color)
		self.add_widget("reset_button", pyelement.PyButton(self), fill="x")
		self.widgets["reset_button"].text = "Reset"
		self.widgets["reset_button"].configure(command=self.on_timer_reset, background=background_color, foreground=foreground_color)
		self.set_properties()
		self.update_self()

	def set_delay_time(self, seconds):
		self.highlight_delay = seconds

	def set_properties(self, title="Catching noises", icon="assets/noise"):
		self.title = title
		self.icon = icon + ".ico"
		self.noise = pyelement.PyImage(icon + ".png")
		self.widgets["update_button"].configure(image=self.noise)
		self.always_on_top = True

	def set_callback(self, callback):
		if callable(callback): self.timer_callback = callback

	def update_self(self):
		if self.countdown == 0:
			self.countdown = self["highlight_delay"]
			self.flashes = 3
			self.flash_highlight()
			self.widgets["update_button"].accept_input = True
			if callable(self.timer_callback): self.timer_callback()
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
		self.countdown = self["highlight_delay"]
		self.disable_highlight()

	def enable_highlight(self):
		self.widgets["update_button"].configure(background=self["highlight_color"]).accept_input = True

	def disable_highlight(self):
		self.flashes = 0
		self.widgets["update_button"].configure(background=self["background_color"]).accept_input = False

	def flash_highlight(self):
		if self.flashes > 0:
			if self.flashes % 2 == 0: self.widgets["update_button"].configure(background=self["highlight_color"])
			else: self.widgets["update_button"].configure(background=self["background_color"])
			self.flashes -= 1