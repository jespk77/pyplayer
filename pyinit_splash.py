from ui import pywindow, pyelement
import sys

initial_cfg = {"background": "black"}

resolution = 400, 300
program_info_file = "pyplayer.json"
def get_version_string(): return "{0.major}.{0.minor}".format(sys.version_info)

def process_command(cmd, output=print):
	import subprocess
	pc = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	while True:
		data = pc.stdout.readline()
		if data: output(data.decode().rstrip('\n'))
		else: break
	return pc

class PySplashWindow(pywindow.RootPyWindow):
	def __init__(self):
		pywindow.RootPyWindow.__init__(self, "splash", initial_cfg)
		self.decorator = False
		self.center_window(*resolution)
		self.column_options(0, weight=1)
		self.row_options(0, weight=1)

		label_status = pyelement.PyTextlabel(self.window)
		label_status.display_text = "Initializing..."
		self.set_widget("label_status", label_status, row=1)

		self._platform = sys.platform
		self.after(1, self._load_program)
		self.bind("<Button-1>", self.clicked)

	def _load_program(self):
		import json
		with open(program_info_file, "r") as file: cfg = json.load(file)
		vs = get_version_string()
		if cfg["python_version"] != vs:
			print("WARNING", "Installed Python version ({}) different from build version ({}), things might not work correctly".format(vs, cfg["python_version"]))

		modules = {mid: mot for mid, mot in cfg["modules"].items() if mot.get("enabled")}
		self.status_text = "Checking dependencies..."
		dependencies = cfg.get("dependencies", [])
		for module_id, module_options in modules.items():
			dps = module_options.get("dependencies")
			if dps: dependencies += [d for d in dps if d not in dependencies]

		if dependencies:
			print("INFO", "Found dependencies:", dependencies)
			for i in range(len(dependencies)):
				self.status_text = "Checking '{}'"
				self.pip_install(dependencies[i])
		else: print("INFO", "No dependencies found, continuing...")
		self.destroy()

	def pip_install(self, module):
		import sys
		process_command("{} -m pip install {} --user".format(sys.executable, module), output=self.pip_status)

	def pip_status(self, out):
		self.status_text = out.split(" in ")[0]
		self.window.update_idletasks()
	@property
	def status_text(self): return self.widgets["label_status"].display_text
	@status_text.setter
	def status_text(self, vl): self.widgets["label_status"].display_text = vl

	def clicked(self, event=None):
		self.destroy()

if __name__ == "__main__":
	w = PySplashWindow()
	w.start()