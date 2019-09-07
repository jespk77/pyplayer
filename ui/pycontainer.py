from ui import pyelement, pyconfiguration, pyevents
import tkinter

class BaseWidgetContainer:
	def __init__(self, container, tk, configuration):
		if configuration is None: configuration = pyconfiguration.Configuration()
		elif isinstance(configuration, dict): configuration = pyconfiguration.Configuration(configuration)
		else: raise TypeError("Configuration (when not None) must be a dictionary, not '{.__name__}'".format(type(configuration)))
		self._container = container
		self._event_handler = pyevents.PyElementEvents(self)
		self._tk = tk
		self._elements = {}
		self._subframes = []
		self._cfg = configuration
		self.load_configuration()

	@property
	def event_handler(self): return self._event_handler

	@property
	def configuration(self): return self._cfg
	def load_configuration(self):
		try: self._tk.configure(**{key: value for key, value in self._cfg.value.items() if not isinstance(value, dict)})
		except tkinter.TclError as e: print("ERROR", "Failed to load configuration:", e)

	def row(self, index, minsize=None, padding=None, weight=None):
		""" Customize row behavior at given index:
		 		- minsize: the minimun size this row must have; this row stops shrinking when it is this size (not applied when its empty)
		 		- padding: amount of padding set to the biggest element in this row
		 		- weight: how much this row should expand when the window is resized
		 	Returns itself for simplified updating """
		self._tk.grid_rowconfigure(index, minsize=minsize, pad=padding, weight=weight)
		return self

	def column(self, index, minsize=None, padding=None, weight=None):
		""" Customize column behavior at given index:
				- minsize: the minimun size this column must have; this column stops shrinking when it is this size (not applied when its empty)
				- padding: amount of padding set to the biggest element in this column
				- weight: how much this column should expand when the window is resized
			Returns itself for simplified updating """
		self._tk.grid_columnconfigure(index, minsize=minsize, pad=padding, weight=weight)
		return self

	def place_element(self, element, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		""" Place an element (must be a variant of PyElement) on this widget, use additional arguments to position it in this container
		 	row, rowspan: the row in the frame grid layout and how many rows it should cover
		 	column, columnspan: the column in the frame grid layout and how many columns it should cover
		 	Returns the added element """
		if isinstance(element, pyelement.PyElement):
			self._elements[element.widget_id] = element
			element._tk.grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)
			return self._elements[element.widget_id]
		else: raise ValueError("Placed element must be a 'PyElement', not '{.__name__}'".format(type(element)))

	def place_frame(self, frame, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		""" Create another element container (must be a 'PyFrame' or any of its variants) inside this container,
			supported arguments and their behavior are the same as for elements
			Returns the index of the added container """
		if isinstance(frame, BaseWidgetContainer):
			self._subframes.append(frame)
			frame._tk.grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)
			return len(self._subframes) - 1
		else: raise ValueError("Placed frame must be a 'PyFrame', not '{.__name__}'".format(type(frame)))

	def remove_element(self, id):
		id = id.lower()
		prev_wd = self._elements.get(id)
		if prev_wd:
			try:
				prev_wd.grid_forget()
				prev_wd.destroy()
				del self._elements[id]
			except Exception as e: print("ERROR", "Destroying previously bound widget for '{}':".format(id), e)

	def show(self):
		self._tk.pack(fill="both", expand=True)

	def destroy(self):
		self._tk.destroy()

	def schedule(self, min=0, sec=0, ms=0, func=None, loop=False, **kwargs):
		self._container.schedule(min, sec, ms, func, loop, **kwargs)

	def __getitem__(self, item):
		""" Get the element that was assigned to given name, returns this element or None if nothing bound """
		return self._elements.get(item)

	def __setitem__(self, key, value): raise AttributeError("Cannot set or replace elements directly, use 'place_element' instead!")
	def __delitem__(self, key): raise AttributeError("Cannot delete elements directly, use 'remove_element' instead!")


frame_cfg = { "background": "black" }
class PyFrame(BaseWidgetContainer):
	""" Base element container """
	def __init__(self, parent, configuration=None):
		BaseWidgetContainer.__init__(self, parent, tkinter.Frame(parent._tk, **frame_cfg), configuration)


label_cfg = { "foreground": "white" }
label_cfg.update(frame_cfg)
class PyLabelFrame(BaseWidgetContainer):
	""" Base element container with outline and an optional label """
	def __init__(self, parent, configuration=None):
		BaseWidgetContainer.__init__(self, parent, tkinter.LabelFrame(parent._tk, **label_cfg), configuration)

	@property
	def label(self): return self._tk.cget("text")
	@label.setter
	def label(self, lbl): self._tk.configure(text=lbl)


canvas_cfg = { "highlightthickness": 0 }
canvas_cfg.update(frame_cfg)
class PyCanvas(BaseWidgetContainer):
	""" Dynamic container that supports drawing figures """
	def __init__(self, parent, configuration=None):
		BaseWidgetContainer.__init__(self, parent, tkinter.Canvas(parent._tk, **canvas_cfg), configuration)

	@property
	def horizontal_command(self): return self._tk.cget("xscrollcommand")
	@horizontal_command.setter
	def horizontal_command(self, cmd): self._tk.configure(xscrollcommand=cmd)

	@property
	def vertical_command(self): return self._tk.cget("yscrollcommand")
	@vertical_command.setter
	def vertical_command(self, cmd): self._tk.configure(yscrollcommand=cmd)

	@property
	def horizontal_view(self): return self._tk.xview
	@property
	def vertical_view(self): return self._tk.yview

	@property
	def scrollregion(self): return self._tk.cget("scrollregion")
	@scrollregion.setter
	def scrollregion(self, rg): self._tk.configure(scrollregion=rg)

	def scroll_to(self, x=0, y=0):
		""" Scroll element to specified position, if no position specified the top left position is used """
		self._tk.xview_moveto(x)
		self._tk.yview_moveto(y)

	def get_bounds(self, tag="all"):
		""" Get the size (in pixels) of the element with the given tag
		 	If no tag specified the bounding box of the complete element is returned """
		return self._tk.bbox(tag)


class PyScrollableFrame(PyFrame):
	""" Element container with fixed grid that can be larger than the window size, view can be adjusted with mouse scrolling and/or scrollbars """
	_content_tag = "content_frame"
	_mouse_sensitivity = 100

	def __init__(self, parent, configuration=None):
		PyFrame.__init__(self, parent, configuration)
		self._scrollable = PyCanvas(self)
		self._content = PyFrame(self._scrollable)
		PyFrame.place_frame(self, self._scrollable)
		self._scrollable.row(0, weight=1).column(0, weight=1)
		self._scrollbar_x = self._scrollbar_y = None
		self._enable_scroll = False

		PyFrame.row(self, 0, weight=1)
		PyFrame.column(self, 0, weight=1)
		self._scrollable._tk.create_window((0,0), window=self._content._tk, anchor="center", tags=self._content_tag)

		@self._scrollable.event_handler.ElementResize
		def canvas_resize(width, height):
			if not self._scrollbar_x: self._scrollable._tk.itemconfigure(self._content_tag, width=width)
			if not self._scrollbar_y: self._scrollable._tk.itemconfigure(self._content_tag, height=height)
		@self._content.event_handler.ElementResize
		def content_resize(): self._scrollable.scrollregion = self._scrollable.get_bounds()

		@self.event_handler.MouseEnter
		def enable_scroll(): self._enable_scroll = True
		@self.event_handler.MouseLeave
		def disable_scroll(): self._enable_scroll = False

		@self.event_handler.MouseScrollEvent(include_children=True)
		def scroll_mouse(delta):
			if self._enable_scroll:	self._scrollable._tk.yview_scroll(-(delta//self._mouse_sensitivity), "units")

	@property
	def content(self): return self._content

	def clear_content(self):
		""" Remove all previously placed elements """
		for f in self._content._subframes:
			try: f.destroy()
			except Exception as e: print("ERROR", "Closing subframe", e)
		self._scrollable.scroll_to()

	_horizontal_id = "horizontal_scrollbar"
	@property
	def scrollbar_x(self): return self._scrollbar_x is not None
	@scrollbar_x.setter
	def scrollbar_x(self, enable):
		if not self.scrollbar_x and enable:
			print("INFO", "Adding horizontal scrollbar")
			self._scrollbar_x = pyelement.PyScrollbar(self, self._horizontal_id)
			self._scrollbar_x.orientation = "horizontal"
			self._scrollbar_x.attach_to(self._scrollable)
			PyFrame.place_element(self, self._scrollbar_x, row=1, sticky="ew")
			PyFrame.row(self, 1, minsize=15)

		if self.scrollbar_x and not enable:
			print("INFO", "Removing horizontal scrollbar")
			self._scrollbar_x = None
			PyFrame.remove_element(self, self._horizontal_id)
			PyFrame.row(self, 1, minsize=0)

	_vertical_id = "vertical_scrollbar"
	@property
	def scrollbar_y(self): return self._scrollbar_y is not None
	@scrollbar_y.setter
	def scrollbar_y(self, enable):
		if not self._scrollbar_y and enable:
			print("INFO", "Adding vertical scrollbar")
			self._scrollbar_y = pyelement.PyScrollbar(self, self._vertical_id)
			self._scrollbar_y.orientation = "vertical"
			self._scrollbar_y.attach_to(self._scrollable)
			PyFrame.place_element(self, self._scrollbar_y, column=1, sticky="ns")
			PyFrame.column(self, 1, minsize=15)

		if self.scrollbar_x and not enable:
			print("INFO", "Removing vertical scrollbar")
			self._scrollbar_y = None
			PyFrame.remove_element(self, self._vertical_id)
			PyFrame.column(self, 1, minsize=0)

	def row(self, index, minsize=None, padding=None, weight=None): return self._content.row(index, minsize, padding, weight)
	def column(self, index, minsize=None, padding=None, weight=None): return self._content.column(index, minsize, padding, weight)
	def place_element(self, element, row=0, column=0, rowspan=1, columnspan=1, sticky="news"): return self._content.place_element(element, row, column, rowspan, columnspan, sticky)
	def place_frame(self, frame, row=0, column=0, rowspan=1, columnspan=1, sticky="news"): return self._content.place_frame(frame, row, column, rowspan, columnspan, sticky)
	def remove_element(self, id): return self._content.remove_element(id)
	def __getitem__(self, item): return self._content[item]


class PyItemBrowser(PyLabelFrame):
	""" Similar to a frame except there is no static grid, instead elements are stored in a list and automatically organized so they fit the window width """
	def __init__(self, parent, configuration=None):
		PyLabelFrame.__init__(self, parent, configuration)
		self._content = PyCanvas(self)
		PyLabelFrame.place_frame(self, self._content)
		PyLabelFrame.column(self, 0, weight=1)
		PyLabelFrame.row(self, 0, weight=1)
		self._items = []
		self._minx, self._miny = 50, 50

		@self._content.event_handler.ElementResize
		def _content_resize(width):
			self._reorganize(width)

	def update_frame(self):
		""" Trigger a refresh for this browser without resizing the frame
		 	Note: can cause lag/stutter when used frequently: don't call this from within a loop """
		self._reorganize()

	def _reorganize(self, new_width=None):
		if new_width is None:
			self._content._tk.update_idletasks()
			new_width = int(self._content._tk.cget("width"))

		column_count = new_width // self._minx
		column_offset = (new_width - (self._minx * column_count)) / column_count
		row = 0
		for i, element in enumerate(self._items):
			row = i // column_count
			column = i % column_count
			e_id = "element_{}".format(i)
			self._content._tk.coords(e_id, column * (self._minx + column_offset), row * self._miny)
			self._content._tk.itemconfigure(e_id, width=self._minx + column_offset, height=self._miny)
		self._content._tk.configure(height=(row + 1) * self.min_height)

	@property
	def content(self): return self._content

	@property
	def itemlist(self): return self._items
	@itemlist.setter
	def itemlist(self, vl):
		""" Replace all existing items with a new list """
		self.clear_content()
		self._items = vl

	@property
	def min_width(self): return self._minx
	@min_width.setter
	def min_width(self, x):
		""" Set the minimum width (in pixels) for all containing elements, causes an update when set
		 	The minimum value allowed is 10 """
		if x < 10: raise ValueError("Minimum width is 10")
		self._minx = x
		self._reorganize()

	@property
	def min_height(self): return self._miny
	@min_height.setter
	def min_height(self, y):
		""" Set the minimum height (in pixels) for all containing elements, causes an update when set
		 	The minimum allowed value is 10 """
		if y < 10: raise ValueError("Minimum height is 10")
		self._miny = y
		self._reorganize()

	def clear_content(self):
		""" Removes all previously added elements """
		for item in self.content._subframes:
			try: item.destroy()
			except Exception as e: print("ERROR", "While clearing content:", e)
		self._items.clear()

	def _add_element(self, element):
		if not isinstance(element, pyelement.PyElement): raise TypeError("Can only bind instances of PyElement, not '{.__name__}'".format(type(element)))
		self._content._tk.create_window((0,0), window=element._tk, anchor="nw", tag="element_{}".format(len(self._items)))
		self._items.append(element)

	def append_element(self, element):
		""" Add an element (or a list of elements) to the end of the itemlist, all elements must be instances of PyElement """
		if isinstance(element, list):
			for e in element: self._add_element(e)
		else: self._add_element(element)

	def _unsupported(self): raise TypeError("This operation is not supported for this type")
	def row(self, *args): self._unsupported()
	def column(self, *args): self._unsupported()
	def place_element(self, *args): self._unsupported()
	def place_frame(self, *args): self._unsupported()
	def remove_element(self, *args): self._unsupported()