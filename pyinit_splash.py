from ui import pywindow, pyelement
import sys

initial_cfg = {"background": "black"}

resolution = 300, 400
program_info_file = "pyplayer.json"
def get_version_string(): return "{0.major}.{0.minor}".format(sys.version_info)

class PySplashWindow(pywindow.RootPyWindow):
	def __init__(self):
		pywindow.RootPyWindow.__init__(self, "splash", initial_cfg)
		self.center_window(*resolution)
		self.decorator = False
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

		self.status_text = "Checking dependencies..."

		for module_id, module_options in cfg["modules"].items():
			pass

	def pip_install(self, module):
		from pip._internal import main
		main(["install", "--upgrade", module, "--user"])

	def pip_list_upgrades(self):
		from pip._internal import main
		main(["list", "--outdated"])

	@property
	def status_text(self): return self.widgets["label_status"].display_text
	@status_text.setter
	def status_text(self, vl): self.widgets["label_status"].display_text = vl

	def clicked(self, event=None):
		self.destroy()

if __name__ == "__main__":
	w = PySplashWindow()
	w.start()