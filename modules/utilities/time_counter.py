import tkinter

background_color = "gray25"
foreground_color = "white"
highlight_color = "cyan"

class TimeCount(tkinter.Toplevel):
	def __init__(self, root):
		self.root = root
		super().__init__(background=background_color)
		self.set_properties()
		self.timer = 0
		self.timer_callback = None
		self.flashes = 0
		self.highlight_time = 420
		self.countdown = self.highlight_time
		self.noise = tkinter.PhotoImage(file="noise.png")
		self.label = tkinter.Label(self, text="initializing...", background=background_color, foreground=foreground_color)
		self.update_button = tkinter.Button(self, image=self.noise, state="disabled", command=self.reset_noise, background=background_color)
		self.reset_button = tkinter.Button(self, text="Reset", command=self.reset_timer, background=background_color, foreground=foreground_color)
		self.label.pack(fill="both", expand=True)
		self.update_button.pack(fill="x")
		self.reset_button.pack(fill="x")
		self.after(1000, self.on_update)

	def set_delay_time(self, seconds):
		self.highlight_time = seconds

	def set_properties(self, title="Catching noises", icon="noise", geometry="200x100"):
		print(title, icon, geometry)
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

	def on_update(self):
		self.update_label(self.timer + 1, self.countdown - 1)
		self.after(1000, self.on_update)

	def update_label(self, time, countdown):
		self.timer = time
		if countdown <= 0:
			self.countdown = self.highlight_time
			self.enable_highlight()
			self.flashes = 3
			if self.timer_callback is not None: self.timer_callback()
			self.after(2000, self.flash_highlight)
		else: self.countdown = countdown
		self.label.configure(text=str(self.timer) + " | " + str(self.countdown))

	def reset_noise(self):
		self.update_label(0, self.countdown)
		self.flashes = 0
		self.disable_highlight()

	def reset_timer(self):
		self.update_label(0, self.highlight_time)
		self.flashes = 0
		self.disable_highlight()

	def enable_highlight(self):
		self.update_button.configure(state="normal", background=highlight_color)

	def disable_highlight(self):
		self.update_button.configure(state="disabled", background=background_color)

	def flash_highlight(self):
		if self.flashes > 0:
			if self.flashes % 2 == 0: self.update_button.configure(background=highlight_color)
			else: self.update_button.configure(background="gray")
			self.flashes -= 1
			self.after(2000, self.flash_highlight)

if __name__ == "__main__":
	window = TimeCount()
	window.mainloop()