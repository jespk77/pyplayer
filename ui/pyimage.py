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
	def data(self): return self._bin

	@property
	def images(self): return self._images
	@property
	def image_count(self): return len(self._images)


from ui import pyelement
class PyImage(pyelement.PyTextlabel):
	PLAYBACK_RATE_MS = 30

	def __init__(self, container, id, img=None, file=None, url=None):
		if file or url: img = ImageData(file=file, url=url)

		if img:
			if isinstance(img, PyImage): img = img._image
			if isinstance(img, ImageData): self._image = img
			else: raise TypeError("Incompatible image type '{.__name__}'".format(type(img)))
		else: raise ValueError("Missing image data!")

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

import os
if not os.path.isdir(".cache"): os.mkdir(".cache")
from ui import pyconfiguration
class ImageCache:
	""" Container for a number of images, each image is bound to a unique identifier (that must be hashable)
	  	fetch_url: a url to fetch new images from, this must be a string containing a '{key}' segment in which the given key is inserted """
	def __init__(self, folder, fetch_url):
		self._img_storage = {}
		self._dir = ".cache/" + folder
		if not os.path.isdir(self._dir): os.mkdir(self._dir)
		self._cfg = pyconfiguration.ConfigurationFile(os.path.join(folder, "data"))

		self._fturl = fetch_url
		self.expiration_date = self._cfg.get_or_create("expiration_date", 0)

	def clear(self):
		""" Remove all images from cache """
		import shutil
		shutil.rmtree(self._dir)
		self._img_storage.clear()

	def load_image(self, key):
		""" Ensure an image exists for given key, has no effect if key already bound """
		if not key in self._img_storage:
			filepath = os.path.join(self._dir, key)
			try: img = ImageData(file=filepath)
			except Exception as e:
				if not isinstance(e, FileNotFoundError):
					print("ERROR", "While reading '{}' from cache:".format(filepath), e)
				img = ImageData(url=self._fturl.format(key=key))
				with open(filepath, "wb") as file: file.write(img.data.getvalue())

			self._img_storage[key] = img
			return img

	def get_image(self, key):
		""" Get image with bound identifier, if the key was not set already the image is fetched from url """
		img = self._img_storage.get(key)
		if not img:
			try: return self.load_image(key)
			except Exception as e:
				print("ERROR", "Cannot load image into cache properly!", e)
				return None
		return img

	def __getitem__(self, item):
		img = self.get_image(item)
		if not img: raise KeyError(item)
		else: return img

	def __delitem__(self, key):
		del self._img_storage[key]

	@property
	def expiration_date(self): return self._expiry
	@expiration_date.setter
	def expiration_date(self, value):
		self._expiry = value
		import time
		if time.time() - os.path.getmtime(self._dir) < self._expiry: self.clear()