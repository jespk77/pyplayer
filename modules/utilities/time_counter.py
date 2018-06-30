import tkinter

background_color = "gray25"
foreground_color = "white"
highlight_color = "cyan"

class TimeCount(tkinter.Toplevel):
	highlight_delay = 20

	def __init__(self, root):
		super().__init__(root, background=background_color)
		self.set_properties()
		self.timer = 0
		self.timer_callback = None
		self.flashes = 0
		self.countdown = -1
		self.noise = tkinter.PhotoImage(file="assets/noise.png")
		self.label = tkinter.Label(self, text="initializing...", background=background_color, foreground=foreground_color)
		self.update_button = tkinter.Button(self, image=self.noise, command=self.on_noise_click, background=background_color)
		self.reset_button = tkinter.Button(self, text="Reset", command=self.on_timer_reset, background=background_color, foreground=foreground_color)
		self.label.pack(fill="both", expand=True)
		self.update_button.pack(fill="x")
		self.reset_button.pack(fill="x")
		self.update_self()

	def set_delay_time(self, seconds):
		self.highlight_delay = seconds

	def set_properties(self, title="Catching noises", icon="assets/noise", geometry="200x100"):
		self.title(title)
		try:
			self.iconbitmap(icon + ".ico")
			self.noise = tkinter.PhotoImage(file=icon + ".png")
			self.update_button.configure(image=self.noise)
		except: pass
		self.geometry(geometry)
		self.wm_attributes("-topmost", 1)

	def set_callback(self, callback):
		if callable(callback): self.timer_callback = callback

	def update_self(self):
		if self.countdown == 0:
			self.countdown = TimeCount.highlight_delay
			self.flashes = 3
			self.flash_highlight()
			self.update_button.configure(state="normal")
			if callable(self.timer_callback): self.timer_callback()
		elif self.countdown > 0: self.countdown -= 1

		self.label.configure(text="{timer} | {countdown}".format(timer=self.timer, countdown=self.countdown if self.countdown >= 0 else "--"))
		self.timer += 1
		self.after(1000, self.update_self)

	def on_noise_click(self):
		if self.countdown >= 0:
			self.timer = 0
			self.disable_highlight()
		else: self.on_timer_reset()

	def on_timer_reset(self):
		self.timer = 0
		self.countdown = TimeCount.highlight_delay
		self.disable_highlight()

	def enable_highlight(self):
		self.update_button.configure(state="normal", background=highlight_color)

	def disable_highlight(self):
		self.flashes = 0
		self.update_button.configure(state="disabled", background=background_color)

	def flash_highlight(self):
		if self.flashes > 0:
			if self.flashes % 2 == 0: self.update_button.configure(background=highlight_color)
			else: self.update_button.configure(background="gray")
			self.flashes -= 1
			self.after(2000, self.flash_highlight)

if __name__ == "__main__":
	window = TimeCount(None)
	window.mainloop()