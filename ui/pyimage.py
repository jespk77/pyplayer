from ui import pyelement
class PyImage(pyelement.PyTextlabel):
	PLAYBACK_RATE_MS = 30

	def __init__(self, container, id, url=None, file=None):
		from io import BytesIO
		self._bin = None

		if url:
			try:
				from urllib.request import urlopen
				with urlopen(url) as u: self._bin = BytesIO(u.read())
			except ImportError: print("ERROR", "Cannot import image from url, required library 'urllib.request' not found")

		elif file:
			with open(file, "rb") as fl: self._bin = BytesIO(fl.read())

		if not self._bin: raise TypeError("Invalid or missing argument!")

		try:
			from PIL import Image, ImageTk, ImageSequence
			img = Image.open(self._bin)
			self._images = [ImageTk.PhotoImage(i) for i in ImageSequence.Iterator(img)]
		except ImportError:
			print("WARNING", "Required 'Pillow' library not found, functionality limited!")
			import base64, tkinter
			self._images = [tkinter.PhotoImage(data=base64.encodebytes(self._bin.read()))]

		pyelement.PyTextlabel.__init__(self, container, id)
		self._container = container
		self._n = 0
		self._active = False
		self._update_img()
		self.start()

	@property
	def animated(self): return len(self._images) > 1

	def start(self):
		if self.animated and not self._active:
			print("INFO", "Starting image playback")
			self._active = True
			self._container.schedule(ms=self.PLAYBACK_RATE_MS, loop=True, func=self._update_img)

	def stop(self):
		if self.animated and self._active:
			print("INFO", "Stopping image playback")
			self._active = False

	def _update_img(self):
		self._tk.configure(image=self._images[self._n])
		self._n = (self._n + 1) % len(self._images)
		return self._active