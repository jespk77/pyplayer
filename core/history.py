import json, os
from ui.qt import pyelement

class History:
	"""
	 Collection that keeps a list of items in the order they were added
	 They are retrieved one by one using get, adding a new item automatically resets the index to the end
	 Amount of items stored can be limited by adding a limit argument
	"""
	def __init__(self, limit=0, file=None):
		self._limit = max(0, limit)
		self._history = []
		self._index = 0
		self._index_updated = self._history_updated = None

		self._file = file
		if self._file is not None:
			self._save_file = True
			if not self._file.endswith(".ht"): self._file += ".ht"
			self._load_file()
		else: self._save_file = False

	def _load_file(self):
		try:
			with open(self._file, "r") as file: data = json.load(file)
			self._history.extend(data["history"])
			self._index, self._limit = data["index"], data["limit"]
		except FileNotFoundError: self._save_file = False

	def _delete_file(self):
		if self._file is not None:
			try: os.remove(self._file)
			except FileNotFoundError: pass

	def save(self):
		""" Saves the current history to file, has no effect if no save file was set """
		if self._save_file:
			data = {
				"history": self._history,
				"index": self._index,
				"limit": self._limit
			}
			with open(self._file, "w") as file: json.dump(data, file)
		else: self._delete_file()

	@property
	def save_file(self):
		""" Get the destination the history will be saved to or None if not set """
		return self._file
	@save_file.setter
	def save_file(self, file):
		self._delete_file()
		self._file = file
		if not file: self._save_file = False

	@property
	def can_save(self):
		""" True if the history can be saved to file """
		return self._save_file
	@can_save.setter
	def can_save(self, save):
		if save and self._file is None: raise ValueError("Cannot save to file without setting a destination")
		self._save_file = bool(save)

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

class HistoryViewer(pyelement.PyFrame):
	def __init__(self, parent, window_id, history):
		self._history = history
		pyelement.PyFrame.__init__(self, parent, window_id)

		history_index_update, history_update = "history_index_update", "history_update"
		self.window.add_task(history_index_update, self._on_index_update)
		self.window.add_task(history_update, self._on_history_update)
		self._history.OnIndexUpdated(lambda index: self.window.schedule_task(task_id=history_index_update, new_index=index))
		self._history.OnHistoryUpdated(lambda hist: self.window.schedule_task(task_id=history_update, new_history=hist))

		@self.events.EventDestroy
		def _on_destroy():
			self._history.OnIndexUpdated(None)
			self._history.OnHistoryUpdated(None)

	def create_widgets(self):
		items = self.add_element("history_view", element_class=pyelement.PyItemlist)
		items.auto_select = False
		self._on_history_update()
		self._on_index_update()

		row = 1
		if self._history.save_file is not None:
			check = self.add_element("history_save", element_class=pyelement.PyCheckbox, row=row)
			check.checked = self._history.can_save
			check.text = "Save to file"
			@check.events.EventInteract
			def _change_save(): self._history.can_save = check.checked
			row += 1

		btn = self.add_element("history_clear", element_class=pyelement.PyButton, row=row)
		btn.text = "Clear"
		@btn.events.EventInteract
		def _on_history_clear(): self._history.clear()

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
	def EventSelect(self): return self["history_view"].events.EventDoubleClick