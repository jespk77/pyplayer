from ui import pywindow, pyelement
import sys

initial_cfg = {"background": "black"}

resolution = 400, 300
program_info_file = "pyplayer.json"
def get_version_string(): return "{0.major}.{0.minor}".format(sys.version_info)

def process_command(cmd, stdin=None, stdout=None, stderr=None, timeout=None):
	""" Run a command that can be interacted with using standard IO: 'stdin', 'stdout', 'stderr'
			- If stdin is provided, it must be a bytes object
			- If stdout is provided, it must be callable: all command output is directed to this method' when not provided all output is ignored
			- If stderr is provided, must be callable, it receives any error messages from the command; when not provided errors are directed to stdout
	 	Waits for the process to be finished but can be aborted if it takes longer than n seconds using timeout argument
	 	Returns the finished process when termated """
	if stderr is None: stderr = stdout
	import subprocess
	pc = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	while not pc.poll():
		try:
			out, err = pc.communicate(stdin)
			if out and stdout: stdout(out.decode().rstrip('\n'))
			elif err and stderr: stderr(err.decode().rstrip('\n'))
		except Exception as e: print("error communicating:", e); break
	pc.wait(timeout)
	return pc

class PySplashWindow(pywindow.RootPyWindow):
	def __init__(self):
		pywindow.RootPyWindow.__init__(self, "splash", initial_cfg)
		self.decorator = False
		self.center_window(*resolution)
		self.column_options(0, weight=1)
		self.row_options(0, weight=1)

		img = pyelement.PyCanvas(self.window)
		self.set_widget("splash_logo", img, row=0, initial_cfg={"background": "black", "borderwidth": 0})
		label_status = pyelement.PyTextlabel(self.window)
		label_status.display_text = "Initializing..."
		self.set_widget("label_status", label_status, row=1, initial_cfg={"background": "black", "foreground": "white"})

		self._cfg = None
		self._platform = sys.platform
		self._clickclose = False
		self.bind("<Button-1>", self.on_click)
		self.after(1, self._update_program)

	def _update_program(self):
		if "no_update" not in sys.argv:
			print("INFO", "Doing an update check!")
			self.status_text = "Checking for updates..."
			pc = process_command("git pull", stdout=self._git_status)
			if pc.returncode:
				print("INFO", "Cannot update directly, trying to do a hard reset")
				process_command("git reset --hard")
				pc = process_command("git pull", stdout=self._git_status)

			if pc.returncode:
				self.status_text = "Failed to update PyPlayer, continuing in 5 seconds or click to close..."
				self._clickclose = True
				return self.after(5, self._load_program)
		else: self.status_text = "Updating skipped"
		self.after(1, self._load_program)

	def _git_status(self, out):
		self.status_text = out
		self.window.update_idletasks()

	def _load_program(self):
		self._clickclose = True
		import json
		with open(program_info_file, "r") as file:
			try: self._cfg = json.load(file)
			except json.JSONDecodeError as e:
				self.status_text = "Cannot load 'modules.json': {}, exiting in 5 seconds...".format(e)
				self.after(5, self.destroy)
				return
		vs = get_version_string()
		if self._cfg["python_version"] != vs:
			print("WARNING", "Installed Python version ({}) different from build version ({}), things might not work correctly".format(vs, self._cfg["python_version"]))

		modules = {mid: mot for mid, mot in self._cfg["modules"].items() if mot.get("enabled")}
		self.status_text = "Checking dependencies..."
		dependencies = self._cfg.get("dependencies", [])
		for module_id, module_options in modules.items():
			dps = module_options.get("dependencies")
			if dps: dependencies += [d for d in dps if d not in dependencies]

		if dependencies:
			print("INFO", "Found dependencies:", dependencies)
			pip_install = "{} -m pip install {}"
			if self._platform == "linux": pip_install += " --user"
			for i in range(len(dependencies)):
				self.status_text = "Checking '{}'"
				process_command(pip_install.format(sys.executable, dependencies[i]), stdout=self._pip_status)
		else: print("INFO", "No dependencies found, continuing...")
		self.after(5, self.destroy)

	def _pip_status(self, out):
		try:
			self.status_text = out.split(" in ")[0]
			self.window.update_idletasks()
		except: pass

	@property
	def status_text(self): return self.widgets["label_status"].display_text
	@status_text.setter
	def status_text(self, vl): self.widgets["label_status"].display_text = vl

	def on_click(self, event=None):
		if self._clickclose: self.destroy()

if __name__ == "__main__":
	w = PySplashWindow()
	w.start()