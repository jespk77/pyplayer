import datetime
import sys

from ui import pywindow, pyelement

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
		pywindow.RootPyWindow.__init__(self, "splash")
		self.decorator = False
		self.center_window(*resolution)
		self.column_options(0, weight=1, minsize=260)
		self.row_options(1, weight=1)

		img = pyelement.PyCanvas(self.window)
		self._logo = pyelement.PyImage(file="assets/logo")
		try: img.create_image(resolution[0]//2, resolution[1]//2, image=self._logo)
		except: pass

		head = pyelement.PyTextlabel(self.window)
		self.set_widget("header", head)

		btn = pyelement.PyButton(self.window)
		btn.text = "X"
		btn.command = self.destroy
		self.set_widget("close_window", btn, row=0, column=1, initial_cfg={"highlightthickness": 0, "borderwidth": 0})
		self.set_widget("splash_logo", img, row=1, columnspan=2, initial_cfg={"highlightthickness": 0, "cursor": "watch"})

		label_status = pyelement.PyTextlabel(self.window)
		label_status.display_text = "Initializing..."
		self.set_widget("label_status", label_status, row=2, columnspan=2, initial_cfg={"foreground": "white", "cursor": "watch"})

		self._cfg = self._interp = None
		self._platform = sys.platform
		self._update_data = None
		self._actions = {
			"module_configure": self._module_configure,
			"restart": self._restart
		}

		self.after(1, self._update_program)

	def _update_program(self):
		if "no_update" not in sys.argv:
			print("INFO", "Doing an update check!")
			self.status_text = "Checking for updates..."
			pc = process_command("git pull -s recursive -Xtheirs", stdout=self._git_status)

			if pc.returncode:
				self.status_text = "Failed to update PyPlayer, continuing in 5 seconds..."
				return self.after(5, self._load_modules)
			process_command("git rev-parse HEAD", stdout=self.git_hash)
		else:
			self.status_text = "Updating skipped."
			self.after(1, self._load_modules, False)

	def _git_status(self, out):
		out = out.split("\n")
		if len(out) > 1:
			for o in out:
				if o.startswith("Updating"): self.status_text = o; break
		elif len(out) == 1: self.status_text = out[0]
		self.window.update_idletasks()

	def git_hash(self, out):
		hash = self.get_or_create("hash", "none")
		out = out.rstrip("\n")
		if hash != out:
			print("INFO", "Git hash updated from '{}' to '{}', checking dependencies".format(hash, out))
			self["hash"] = out
			self.after(1, self._load_modules)
		else:
			print("INFO", "Git hash equal to last time, skip dependency checking")
			self.after(1, self._load_modules, False)

	def _git_update(self, out):
		out = out.split('\n')
		self._update_data = out[0], datetime.datetime.strptime(out[1], "%Y-%m-%d %H:%M:%S %z")

	def _load_modules(self, dependency_check=True):
		process_command("git log -1 --pretty=%B%ci", stdout=self._git_update)
		import json
		with open(program_info_file, "r") as file:
			try: self._cfg = json.load(file)
			except json.JSONDecodeError as e:
				self.status_text = "Cannot load 'pyplayer.json': {}, exiting in 5 seconds...".format(e)
				self.after(5, self.destroy)
				return

		vs = get_version_string()
		if self._cfg["python_version"] != vs:
			print("WARNING", "Installed Python version ({}) different from build version ({}), things might not work correctly".format(vs, self._cfg["python_version"]))

		try:
			with open("modules.json", "r") as file:
				import json
				self._cfg["modules"] = json.load(file)
		except (FileNotFoundError, json.JSONDecodeError):
			print("INFO", "Invalid module configuration, launching module options window...")
			return self.after(1, self._module_configure)

		self._loaded_modules = {mid: mot for mid, mot in self._cfg["modules"].items() if mot.get("enabled")}
		if dependency_check:
			self.status_text = "Checking dependencies..."
			dependencies = set(self._cfg.get("dependencies", []))
			for module_id, module_options in self._loaded_modules.items():
				dps = module_options.get("dependencies")
				if dps: dependencies.update(dps)

			if dependencies:
				print("INFO", "Found dependencies:", dependencies)
				pip_install = "{} -m pip install {}"
				if self._platform == "linux": pip_install += " --user"
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
		client = PyPlayer(self)
		self._interp = Interpreter(client, modules=self._loaded_modules)
		client.interp = self._interp
		client.bind("<Destroy>", lambda e: self.on_close(e, client), add=True)
		self.open_window("client", client)
		client.hidden = False
		self.hidden = True

	@property
	def update_message(self):
		if not self._update_data: return '???'
		else: return self._update_data[0]
	@property
	def update_date(self):
		if not self._update_data: return '???'
		else: return self._update_data[1].strftime("%a %b %d, %Y - %I:%M %p")

	@property
	def status_text(self): return self.widgets["label_status"].display_text
	@status_text.setter
	def status_text(self, vl):
		self.widgets["label_status"].display_text = vl.split("\n")[0]

	def on_close(self, event, client):
		wn = str(event.widget)
		if len(wn.split(".")) <= 2:
			cd = self._actions.get(client.flags, self._terminate)
			if cd: cd()

	def _module_configure(self):
		import os, json
		print("INFO", "Opening module configuration window")
		self.status_text = "Configuring modules..."
		modules = self._cfg.get("modules")
		if not modules: self._cfg["modules"] = modules = {}

		for m in ["modules/{}".format(mfile) for mfile in os.listdir("modules") if mfile.endswith(".json")]:
			with open(m, "r") as file: mop = json.load(file)
			mid = mop["id"]
			del mop["id"]
			mop["enabled"] = mop["required"]

			if mid not in modules:
				mop["new"] = True
				modules[mid] = mop

		from utilities import module_select
		ms = module_select.ModuleSelector(self.window, modules)
		ms.bind("<Destroy>", lambda e: self._module_done(e, ms))
		self.status_text = "Modules configured, restarting..."
		self.open_window("module_select", ms)
		self.hidden = True

	def _module_done(self, event, selector):
		if len(str(event.widget).split(".")) == 2:
			if selector.confirm:
				self.hidden = False
				self._cfg["modules"] = selector.modules
				import json
				with open("modules.json", "w") as file: json.dump(self._cfg["modules"], file)
				self.after(1, self._restart)
			else: self.after(1, self._terminate)

	def _restart(self):
		print("INFO", "Restarting player!")
		import os
		os.execl(sys.executable, sys.executable, *sys.argv)

	def _terminate(self):
		print("INFO", "Pyplayer closed, shutting down!")
		if self._interp is not None and self._interp.is_alive():
			self._interp.stop_command()
			self._interp.join()
		self.after(2, self.destroy)

if __name__ == "__main__":
	w = PySplashWindow()
	w.start()