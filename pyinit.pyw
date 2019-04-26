import datetime
import sys

from ui import pywindow, pyelement, pyimage
from utilities import commands

resolution = 350, 200
program_info_file = "pyplayer.json"


class PySplashWindow(pywindow.PyTkRoot):
	def __init__(self):
		pywindow.PyTkRoot.__init__(self, "splash")
		self.center_window(*resolution)
		self.content.layer.column(0, weight=1, minsize=260).row(1, weight=1)
		head = pyelement.PyTextlabel(self.content, "header")
		self.content.place_widget(head)

		btn = pyelement.PyButton(self.content, "close_window", initial_cfg={"highlightthickness": 0, "borderwidth": 0})
		btn.text = "X"
		btn.command = self.destroy
		self.content.place_widget(btn, column=1)

		logo = pyimage.PyImage(file="assets/logo")
		logo_label = pyelement.PyTextlabel(self.content, "logo_image")
		logo_label.image = logo
		self.content.place_widget(logo_label, row=1, columnspan=2)

		label_status = pyelement.PyTextlabel(self.content, "label_status", initial_cfg={"cursor": "watch"})
		label_status.text = "Initializing..."
		self.content.place_widget(label_status, row=2, columnspan=2)

		self._cfg = self._interp = None
		self._platform = sys.platform
		self._update_data = None
		self._actions = {
			"module_configure": self._module_configure,
			"restart": self._restart
		}

		self.schedule(sec=1, func=self._update_program)

	def _update_program(self):
		if "no_update" not in sys.argv:
			print("INFO", "Doing an update check!")
			self.status_text = "Checking for updates..."
			pc = commands.process_command("git pull -s recursive -Xtheirs", stdout=self._git_status)

			if pc.returncode:
				self.status_text = "Failed to update PyPlayer, continuing in 5 seconds..."
				return self.schedule(sec=5, func=self._load_modules)
			commands.process_command("git rev-parse HEAD", stdout=self.git_hash)
		else:
			self.status_text = "Updating skipped."
			self.schedule(sec=1, func=self._load_modules, dependency_check=False)

	def _git_status(self, out):
		out = out.split("\n")
		if len(out) > 1:
			for o in out:
				if o.startswith("Updating"): self.status_text = o; break
		elif len(out) == 1: self.status_text = out[0]
		self.force_update()

	def git_hash(self, out):
		hash = self.configuration.get_or_create("hash", "none")
		out = out.rstrip("\n")
		if hash != out:
			print("INFO", "Git hash updated from '{}' to '{}', checking dependencies".format(hash, out))
			self.configuration["hash"] = out
			self.schedule(sec=1, func=self._load_modules)
		else:
			print("INFO", "Git hash equal to last time, skip dependency checking")
			self.schedule(sec=1, func=self._load_modules, dependency_check=False)

	def _git_update(self, out):
		out = out.split('\n')
		self._update_data = out[0], datetime.datetime.strptime(out[1], "%Y-%m-%d %H:%M:%S %z")

	def _load_modules(self, dependency_check=True):
		commands.process_command("git log -1 --pretty=%B%ci", stdout=self._git_update)
		import json
		with open(program_info_file, "r") as file:
			try: self._cfg = json.load(file)
			except json.JSONDecodeError as e:
				self.status_text = "Cannot load 'pyplayer.json': {}, exiting in 5 seconds...".format(e)
				self.schedule(sec=5, func=self.destroy)
				return

		vs = commands.get_python_version()
		if self._cfg["python_version"] != vs:
			print("WARNING", "Installed Python version ({}) different from build version ({}), things might not work correctly".format(vs, self._cfg["python_version"]))

		try:
			with open("modules.json", "r") as file:
				import json
				self._cfg["modules"] = json.load(file)
		except (FileNotFoundError, json.JSONDecodeError):
			print("INFO", "Invalid module configuration, launching module options window...")
			return self.schedule(sec=1, func=self._module_configure)

		self._loaded_modules = { mid: mot for mid, mot in self._cfg["modules"].items() if mot.get("enabled") }
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
				for dp in dependencies: commands.process_command(pip_install.format(sys.executable, dp), stdout=self._pip_status)
			else: print("INFO", "No dependencies found, continuing...")
		self.status_text = "Loading PyPlayer..."
		self.schedule(sec=1, func=self._load_program)

	def _pip_status(self, out):
		try:
			self.status_text = out.split(" in ")[0]
			self.force_update()
		except: pass

	def _load_program(self):
		print("INFO", "Creating PyPlayer and interpreter")
		from PyPlayerTk import PyPlayer
		from interpreter import Interpreter
		import pylogging
		pylogging.get_logger()

		client = PyPlayer(self)
		self._interp = Interpreter(client, modules=self._loaded_modules)
		client._interp = self._interp
		@client.event_handler.WindowDestroy
		def on_close():
			self.on_close(client)

		self.open_window("client", client)
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
	def status_text(self): return self.content["label_status"].text
	@status_text.setter
	def status_text(self, vl):
		self.content["label_status"].text = vl.split("\n")[0]

	def on_close(self, client):
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
		ms = module_select.ModuleSelector(self, modules)
		ms.event_handler.WindowDestroy(lambda: self._module_done(ms))

		self.status_text = "Modules configured, restarting..."
		self.open_window("module_select", ms)
		self.hidden = True

	def _module_done(self, selector):
		if selector.confirm:
			self.hidden = False
			self._cfg["modules"] = selector.modules
			import json
			with open("modules.json", "w") as file: json.dump(self._cfg["modules"], file)
			self.schedule(sec=1, func=self._restart)
		else: self.schedule(sec=1, func=self._terminate)

	def _restart(self):
		print("INFO", "Restarting player!")
		import os
		os.execl(sys.executable, sys.executable, *sys.argv)

	def _terminate(self):
		print("INFO", "Pyplayer closed, shutting down!")
		if self._interp is not None and self._interp.is_alive():
			self._interp.stop()
			self._interp.join()
		self.schedule(sec=2, func=self.destroy)

if __name__ == "__main__":
	w = PySplashWindow()
	w.start()