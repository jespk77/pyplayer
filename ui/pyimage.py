from PIL import Image, ImageTk
class PyImage(ImageTk.PhotoImage):
	""" Load an image that can be used for display on widgets; can be cached on disk for efficiency, written to a bin file
	 	Accepts url from where the image is downloaded or a path to a local file or a path to a previously created bin file """
	def __init__(self, file=None, url=None, bin_file=None, **kwargs):
		self._bytes = self._img = None

		if url:
			self._ensure_empty()
			from urllib.request import urlopen
			import io
			u = urlopen(url)
			self._bytes = io.BytesIO(u.read())
			u.close()
			self._img = Image.open(self._bytes)
			ImageTk.PhotoImage.__init__(self, self._img, **kwargs)

		if bin_file:
			self._ensure_empty()
			import io
			self._bytes = io.BytesIO()
			with open(bin_file, "rb") as bfile:
				self._img = Image.open(bfile, self._bytes)
			ImageTk.PhotoImage.__init__(self, self._img, **kwargs)

		if file:
			self._ensure_empty()
			import os
			img, ext = os.path.splitext(file)
			if not ext: file = "{}.png".format(file)

			self._img = file
			try: ImageTk.PhotoImage.__init__(self, file=file, **kwargs)
			except FileNotFoundError as e:
				print("ERROR", "Loading image:", e)
				self._img = "assets/blank.png"
				ImageTk.PhotoImage.__init__(self, file=self._img)

		if not self._img: raise ValueError("Must specify either 'url', 'bin_file' or 'file'")

	def _ensure_empty(self):
		if self._bytes: raise ValueError("Cannot create multiple images!")

	def write(self, filename, format=None, from_coords=None):
		if self._bytes is not None:
			with open(filename, "wb") as file:
				file.write(self._bytes.getvalue())