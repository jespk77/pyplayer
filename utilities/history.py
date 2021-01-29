from ui.qt import pywindow, pyelement

class History:
	"""
	 Collection that keeps a list of items in the order they were added
	 They are retrieved one by one using get, adding a new item automatically resets the index to the end
	 Amount of items stored can be limited by adding a limit argument
	"""
	def __init__(self, limit=0):
		self._limit = max(0, limit)
		self._history = []
		self._index = 0
		self._index_updated = self._history_updated = None

	@property
	def limit(self):
		""" Get the maximum amount of items allowed in the list or 0 if no limit was set """
		return self._limit

	@property
	def head(self):
		""" The element that is currently at the bottom of the list or None if it's empty """
		try: return self._history[0]
		except IndexError: return None

	@property
	def tail(self):
		""" The element that is currently at the top of the list or None if it's empty """
		try: return self._history[-1]
		except IndexError: return None

	def _ensure_limit(self):
		if 0 < self._limit < len(self._history): self._history.pop(0)

	def _reset_index(self):
		self._index = max(0, len(self._history))
		self._call_index_update()

	def add(self, element):
		""" Adds a new item to collection
				- when an item is already in the list it will be moved to the front (losing its previous place in history)
				- when max size is specified and the list is full, the oldest element is removed
			Returns the new size of the collection
		"""
		try: self._history.remove(element)
		except ValueError: pass

		self._history.append(element)
		self._ensure_limit()
		self._call_history_update()
		self._reset_index()
		return len(self._history)

	def peek_previous(self):
		"""
		 Get the element that is one below the current index
		 Similar to 'get_previous' but without affecting the index
		 Returns None if the list is empty or the bottom was reached
		"""
		try: return self._history[self._index - 1]
		except IndexError: return None

	def get_previous(self, default=None):
		"""
		 Go up one spot in the list and return this element
		 Returns specified default value or None when the bottom was reached
		"""
		self._index -= 1
		if self._index < 0:
			self._index = 0
			return default
		else:
			self._call_index_update()
			return self._history[self._index]

	def peek_next(self):
		"""
		 Get the element that is one above the current index
		 Similar to 'get_next' but without affecting the index
		 Returns None if the list is empty or the top was reached
		"""
		try: return self._history[self._index + 1]
		except IndexError: return None

	def get_next(self, default=None):
		"""
		 Go down one spot in the list and return this element
		 Returns specified default value of None when the top was reached
		"""
		self._index += 1
		if self._index >= len(self._history):
			self._index = len(self._history)
			return default
		else:
			self._call_index_update()
			return self._history[self._index]

	@property
	def index(self):
		""" Returns the current position in the history or -1 if the history is empty """
		return self._index - 1

	def clear(self):
		""" Removes all items from history """
		self._history.clear()
		self._call_history_update()
		self._index = 0
		self._call_index_update()

	def OnIndexUpdated(self, cb):
		"""
		 Called when the index of the history is updated
		 Callback receives the updated index as parameter
		"""
		self._index_updated = cb

	def _call_index_update(self):
		if callable(self._index_updated):
			try: self._index_updated(self.index)
			except Exception as e: print("ERROR", "Executing index update:", e)

	def OnHistoryUpdated(self, cb):
		"""
		 Called when the history is updated
		 Callback receives an iterator of the new history as parameter
		"""
		self._history_updated = cb

	def _call_history_update(self):
		if callable(self._history_updated):
			try: self._history_updated(iter(self._history))
			except Exception as e: print("ERROR", "Executing history update:", e)

	def __getitem__(self, item): return self._history[item]
	def __setitem__(self, key, value): raise ValueError("Cannot modify history directly")
	def __delitem__(self, key): raise ValueError("Cannot delete history items directly")
	def __len__(self): return len(self._history)
	def __iter__(self): return iter(self._history)
	def __str__(self): return f"History[history={self._history}, index={self._index}, limit={self._limit}]"

class HistoryViewer(pywindow.PyWindowDocked):
	def __init__(self, parent, window_id, history):
		self._history = history
		pywindow.PyWindowDocked.__init__(self, parent, window_id)
		self.title = "History Viewer"

		self.events.EventWindowClose(self._on_close)
		self.add_task("on_index_update", self._on_index_update)
		self.add_task("on_history_update", self._on_history_update)
		self._history.OnIndexUpdated(lambda index: self.schedule_task(task_id="on_index_update", new_index=index))
		self._history.OnHistoryUpdated(lambda hist: self.schedule_task(task_id="on_history_update", new_history=hist))

	def _on_close(self):
		self._history.OnIndexUpdated(None)
		self._history.OnHistoryUpdated(None)

	def create_widgets(self):
		items = self.add_element("history_view", element_class=pyelement.PyItemlist)
		items.auto_select = False
		self._on_history_update()
		self._on_index_update()

		btn = self.add_element("history_clear", element_class=pyelement.PyButton, row=1)
		btn.text = "Clear"
		@btn.events.EventInteract
		def _on_history_clear():
			self._history.clear()

	def _on_index_update(self, new_index=None):
		if new_index is None: new_index = self._history.index
		if new_index >= 0:
			items = self["history_view"]
			items.set_selection(new_index)
			items.move_to(new_index)

	def _on_history_update(self, new_history=None):
		if new_history is None: new_history = iter(self._history)
		self["history_view"].itemlist = [str(i) for i in new_history]

	@property
	def EventClick(self): return self["history_view"].events.EventDoubleClick