class ImageData:
	def __init__(self, file=None, url=None):
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

	@property
	def animated(self):
		""" Returns true if this image has animation """
		return len(self._images) > 1

	@property
	def images(self): return self._images
	@property
	def image_count(self): return len(self._images)


from ui import pyelement
class PyImage(pyelement.PyTextlabel):
	PLAYBACK_RATE_MS = 30

	def __init__(self, container, id, img=None):
		if img:
			if isinstance(img, PyImage): img = img._image
			if isinstance(img, ImageData): self._image = img
			else: raise TypeError("Incompatible image type '{.__name__}'".format(type(img)))

		pyelement.PyTextlabel.__init__(self, container, id)
		self._container = container
		self._n = 0
		self._active = False
		self._update_img()
		self.start()

	def start(self):
		if self._image.animated and not self._active:
			print("INFO", "Starting image playback")
			self._active = True
			self._container.schedule(ms=self.PLAYBACK_RATE_MS, loop=True, func=self._update_img)

	def stop(self):
		if self._image.animated and self._active:
			print("INFO", "Stopping image playback")
			self._active = False

	def _update_img(self):
		self._tk.configure(image=self._image.images[self._n])
		self._n = (self._n + 1) % self._image.image_count
		return self._active