from tkinter import ttk
import sys, tkinter, datetime

from console import TextConsole
from interpreter import Interpreter

interp = None
class PyPlayer(tkinter.Frame):
	def __init__(self):
		self.root = tkinter.Tk()
		super().__init__(self.root)
		self.console = TextConsole(root=self.root, command_callback=self.parse_command)
		self.header = tkinter.Label(self.root, background="black", foreground="white")
		try: self.root.iconbitmap("icon.ico")
		except: pass
		self.root.title("PyPlayerTk")
		self.progressbar_style = ttk.Style()
		self.progressbar_style.theme_use("default")
		self.progressbar_style.configure(style="Horizontal.TProgressbar")
		self.progressbar = ttk.Progressbar(self.root, style="Horizontal.TProgressbar", orient="horizontal", mode="determinate", maximum=1.0)
		self.last_cmd = None

		self.header.pack(fill="x")
		self.progressbar.pack(fill="x")
		self.console.pack(fill="both", expand=True)
		self.pack()
		self.console.focus()
		self.tk_focusFollowsMouse()
		self.update_label()

	def update_label(self):
		self.date = datetime.datetime.today()
		self.header.configure(text="PyPlayer " + self.date.strftime("- %a %b %d, %Y %I:%M %p -"))
		self.after(1000, self.update_label)

	def update_title(self, title):
		self.root.title(title)

	def update_progressbar(self, progress):
		if progress > self.progressbar["maximum"]: progress = self.progressbar["maximum"]
		elif progress < 0: progress = 0
		self.progressbar["value"] = progress

	def set_configuration(self, cfg):
		if isinstance(cfg, dict):
			self.console.set_configuration(cfg.get("console"))
			progressbar_options = cfg.get("progressbar", {})
			try: self.progressbar_style.configure(style="Horizontal.TProgressbar", **progressbar_options)
			except Exception as e: print("Error setting progressbar configuration:", e)
		else: print("[PyPlayer] got invalid configuration", cfg)

	def parse_command(self, cmd):
		try: interp.queue.put_nowait(cmd)
		except Exception as e: self.console.set_reply(msg="Cannot send command: " + str(e))

	def add_reply(self, ms=100, args=None):
		if args == None: self.after(ms, self.console.set_reply)
		else: self.after(ms, self.console.set_reply, *args)

	def add_message(self, args, ms=100):
		self.after(ms, self.console.set_notification, *args)

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
	if "memory" in sys.argv:
		print("memory checks enabled")
		try:
			from pympler import tracker
			interp.mem_tracker = tracker.SummaryTracker()
			interp.mem_tracker.print_diff()
		except Exception as e: print("error getting memory tracker:", e)
	client.mainloop()
	print("client closed, destroying client...")
	if interp != None and interp.is_alive(): interp.queue.put(False)
	interp.join()
