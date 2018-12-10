from ui import pywindow, pyelement

initial_cfg = {"background": "black"}

resolution = 300, 400
class PySplashWindow(pywindow.RootPyWindow):
	def __init__(self):
		pywindow.RootPyWindow.__init__(self, "splash", initial_cfg)
		self.center_window(*resolution)
		self.decorator = False

		label_img = pyelement.PyImage(file="assets/icon")
		label_img_frame = pyelement.PyCanvas(self.window)
		label_img_frame.create_image(0, 0, image=label_img)
		self.set_widget("label_img", label_img_frame, initial_cfg)
		label_status = pyelement.PyTextlabel(self.window)
		label_status.display_text = "Initializing..."
		self.set_widget("label_status", label_status)

		self.after(1, self._load_program)
		self.bind("<Button-1>" , self.clicked)

	def _load_program(self):
		self.widgets["label_status"].display_text = "Progressing"

	def clicked(self, event=None):
		self.destroy()

if __name__ == "__main__":
	w = PySplashWindow()
	w.start()