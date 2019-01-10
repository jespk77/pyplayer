from ui import pywindow, pyelement
import sys

resolution = 350, 200
program_info_file = "pyplayer.json"
def get_version_string(): return "{0.major}.{0.minor}".format(sys.version_info)

def process_command(cmd, stdin=None, stdout=None, stderr=None, timeout=None):
	""" Run a command that can be interacted with using standard IO: 'stdin', 'stdout', 'stderr'
			- If stdin is provided, it must be a bytes object
			- If stdout is provided, it must be callable: all command output is directed to this method'; when not provided all output is ignored
			- If stderr is provided, must be callable, it receives any error messages from the command; when not provided errors are directed to stdout
	 	Waits for the process to be finished but can be aborted if it takes longer than n seconds using 'timeout' argument
	 	Returns the finished process when termated """
	if stderr is None: stderr = stdout
	import subprocess
	if "win" in sys.platform:
		pi = subprocess.STARTUPINFO()
		pi.dwFlags |= subprocess.STARTF_USESHOWWINDOW
	else: pi = None

	pc = subprocess.Popen(cmd.split(" "), startupinfo=pi, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	while pc.returncode is None:
		try:
			out, err = pc.communicate(stdin, timeout=1)
			if out and stdout: stdout(out.decode())
			if err and stderr: stderr(err.decode())
		except subprocess.TimeoutExpired: pass
		except Exception as e: print("error communicating:", e); break
	pc.wait(timeout)
	return pc

class PySplashWindow(pywindow.RootPyWindow):
	def __init__(self):
		pywindow.RootPyWindow.__init__(self, "splash", {"background": "black", "locked": True})
		self.decorator = False
		self.center_window(*resolution)
		self.column_options(0, weight=1)
		self.row_options(0, weight=1)

		img = pyelement.PyCanvas(self.window)
		self._logo = pyelement.PyImage(file="assets/logo")
		try: img.create_image(resolution[0]//2, resolution[1]//2, image=self._logo)
		except: pass
		self.set_widget("splash_logo", img, row=0, initial_cfg={"background": "gray10", "highlightthickness": 0, "cursor": "watch"})

		label_status = pyelement.PyTextlabel(self.window)
		label_status.display_text = "Initializing..."
		self.set_widget("label_status", label_status, row=2, initial_cfg={"background": "gray10", "foreground": "white", "cursor": "watch"})
		self.after(1, self._update_program)

	def _enable_clickclose(self, event):
		self.after(1, self.destroy)

	def _git_status(self, out):
		out = out.split("\n")
		if len(out) > 1:
			for o in out:
				if o.startswith("Updating"): self.status_text = o; break
		elif len(out) == 1: self.status_text = out[0]
		self.window.update_idletasks()

	def _git_hash(self, out):
		hash = self.get_or_create("hash", "none")
		out = out.rstrip("\n")
		if hash != out:
			print("INFO", "Git hash updated from '{}' to '{}', checking dependencies".format(hash, out))
			self["hash"] = out
			self.after(1, self._load_modules if "no_module" in sys.argv else self._load_moduleselect, False)
		else:
			print("INFO", "Git hash equal to last time, skip dependency checking")
			self.after(1, self._load_modules)

	def _update_program(self):
		if "no_update" not in sys.argv:
			print("INFO", "Doing an update check!")
			self.status_text = "Checking for updates..."
			pc = process_command("git pull -s recursive -Xtheirs", stdout=self._git_status)

			if pc.returncode:
				self.status_text = "Failed to update PyPlayer, continuing in 5 seconds or click to close..."
				self.bind("<Button-1>", self._enable_clickclose)
			else: process_command("git rev-parse HEAD", stdout=self._git_hash)
		else: self.status_text = "Updating skipped."
		self.after(1, self._load_moduleselect)

	def _load_module_file(self):
		import json
		try:
			with open(program_info_file, "r") as file:
				self._info = json.load(file)
				return self._info["modules"]
		except FileNotFoundError:
			print("ERROR", "Cannot find file '{}', loading cannot continue...".format(program_info_file))
			self.status_text = "ERROR: Cannot find '{}', click to close...".format(program_info_file)
		except json.JSONDecodeError as e:
			print("ERROR", "Parsing '{}' as JSON:".format(program_info_file), e)
			self.status_text = "ERROR: Parsing '{}' (see log for details), click to close..."
		except Exception as e:
			print("ERROR", "Processing '{}' as JSON:".format(program_info_file), e)
			self.status_text = "Something went wrong"
		self.bind("<Button-1>", self._enable_clickclose)


	def _load_moduleselect(self):
		mds = self._load_module_file()
		if mds:
			from utilities import module_select
			ms = module_select.ModuleSelector(self.window, mds)
			ms.bind("<Destroy>", lambda e: self._done_moduleselect(e, ms))
			self.hidden = True
			self.open_window("module_select", ms)

	def _done_moduleselect(self, event, wd):
		if len(str(event.widget).split('.')) < 3:
			print("INFO", "Module selector closed, continuing to load modules...")
			self.hidden = False
			self._info["modules"] = wd.modules
			print(self._info["modules"])
			self.after(1, self._load_modules)

	def _load_modules(self, dependency_check=True):
		if dependency_check:
			self.status_text = "Checking dependencies..."
			dependencies = set(self._info.get("dependencies", []))
			for module_options in self._info["modules"].values():
				for d in module_options.get("dependencies", []): dependencies.add(d)

			if dependencies:
				print("INFO", "Found dependencies:", dependencies)
				pip_install = "{} -m pip install {}"
				if sys.platform == "linux": pip_install += " --user"
				self.status_text = "Checking dependencies"
				for dp in dependencies: process_command(pip_install.format(sys.executable, dp), stdout=self._pip_status)
			else: print("INFO", "No dependencies found, continuing...")
		self.status_text = "Loading PyPlayer..."
		self.after(1, self._load_program)

	def _pip_status(self, out):
		try:
			self.status_text = out.split(" in ")[0]
			self.window.update_idletasks()
		except: pass

	def _load_program(self):
		print("INFO", "Creating PyPlayer and interpreter")
		from PyPlayerTk import PyPlayer
		from interpreter import Interpreter
		import pylogging
		pylogging.get_logger()

		print("initializing client...")
		client = PyPlayer(self.window)
		self._interp = Interpreter(client, modules=self._info["modules"])
		client.interp = self._interp
		client.bind("<Destroy>", self.on_close, add=True)
		self.open_window("client", client)
		client.hidden = False
		self.hidden = True

	@property
	def status_text(self): return self.widgets["label_status"].display_text
	@status_text.setter
	def status_text(self, vl):
		self.widgets["label_status"].display_text = vl.split("\n")[0]

	def on_close(self, event):
		wn = str(event.widget)
		if len(wn.split(".")) <= 2:
			print("INFO", "Pyplayer closed, shutting down!")
			if self._interp is not None and self._interp.is_alive():
				self._interp.stop_command()
				self._interp.join()
			self.after(2, self.destroy)

if __name__ == "__main__":
	w = PySplashWindow()
	w.start()