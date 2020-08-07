class History():
	"""
		Collection that keeps a list of items in the order they were added
		They are retrieved one by one using get, adding a new item automatically resets the index
		Amount of items stored can be limited by adding a limit argument
	"""
	def __init__(self, limit=-1):
		if limit == 0: raise ValueError("Size of 0 would not be very useful!")
		self._limit = max(-1, limit)
		self._history = []
		self._index = -1

	@property
	def limit(self):
		""" Get the maximum amount of items allowed in the list or -1 if no limit was set """
		return self.limit

	@property
	def head(self):
		""" Get the element that is currently at the bottom of the list
		 	returns None if the list is empty """
		try: return self._history[0]
		except IndexError: return None

	@property
	def tail(self):
		""" Get the element that is currently at the top of the list
		 	returns None if the list is empty """
		try: return self._history[-1]
		except IndexError: return None

	def _ensure_limit(self):
		if 0 < self._limit < len(self._history):
			self._history.pop(0)

	def reset_index(self):
		self._index = max(0, len(self._history))
		self._last_action = None

	def add(self, element):
		""" Adds a new item to collection
				- when an item is already in the list it will be moved to the front (losing its previous place in history)
				- when max size is specified and the list is full, the oldest element is removed
		"""
		try: self._history.remove(element)
		except ValueError: pass

		self._history.append(element)
		self._ensure_limit()
		self.reset_index()

	def peek_previous(self):
		""" Get the element that is one below the current index
			(the element that would be returned by 'get_previous', but without affecting the index)
			Returns None if the list is empty or the bottom was reached """
		try: return self._history[self._index - 1]
		except IndexError: return None

	def get_previous(self, default=None):
		""" Go up one spot in the list and return this element
		 	Returns specified default value or None when the bottom was reached """
		self._index -= 1
		if self._index < 0:
			self._index = 0
			return default
		else: return self._history[self._index]

	def peek_next(self):
		""" Get the element that is one above the current index
			(the element that would be returned by 'get_next', but without affecting the index)
			Returns None if the list is empty or the top was reached """
		try: return self._history[self._index + 1]
		except IndexError: return None

	def get_next(self, default=None):
		""" Go down one spot in the list and return this element
			Returns specified default value of None when the top was reached """
		self._index += 1
		if self._index >= len(self._history):
			self._index = len(self._history)
			return default
		else: return self._history[self._index]

	def __str__(self): return "{}[history={}, index={}, limit={}]".format(self.__class__.__name__, self._history, self._index, self._limit)