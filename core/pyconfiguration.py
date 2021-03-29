import os, threading
if not os.path.isdir(".cfg"): os.mkdir(".cfg")

separator = "::"
def create_entry(value, read_only=False):
	if isinstance(value, dict): return Configuration(value, read_only)
	else: return ConfigurationItem(value, read_only)

class ConfigurationItem:
	def __init__(self, value=None, read_only=False):
		self._value, self._default_value = value, None
		self._read_only = read_only is True
		self._dirty = False
		self._lock = threading.RLock()

	@property
	def dirty(self):
		with self._lock: return self._dirty
	@property
	def is_set(self):
		with self._lock: return self.value is not None
	@property
	def read_only(self): return self._read_only

	@property
	def value(self):
		with self._lock: return self._value
	@value.setter
	def value(self, value):
		with self._lock:
			if self._read_only: raise ValueError("Cannot set read only configuration value")
			self._value = value
			self.mark_dirty()

	def mark_dirty(self):
		with self._lock: self._dirty = True

	def _clear_dirty(self):
		self._dirty = False

	def __getitem__(self, item): raise TypeError("This item does not support subkeys")
	def __setitem__(self, key, value): self.__getitem__(key)
	def __delitem__(self, key): self.__getitem__(key)
	def __contains__(self, item): return False

	def update(self, other): self.__getitem__("")
	def keys(self): self.__getitem__("")
	def values(self): self.__getitem__("")
	def items(self): self.__getitem__("")

	def get(self, key, default=None): self.__getitem__(key)
	def get_or_create(self, key, create_value=None): self.__getitem__(key)

	@property
	def default_value(self): return self._default_value
	@default_value.setter
	def default_value(self, val): self._default_value = val

	def __len__(self):
		with self._lock: return len(self.value) if self.is_set else 0
	def __str__(self):
		with self._lock: return f"ConfigurationItem(dirty={self.dirty}, read_only={self.read_only}, value={self.value})"


class Configuration(ConfigurationItem):
	def __init__(self, value=None, read_only=False):
		ConfigurationItem.__init__(self, {}, read_only)
		if value:
			if isinstance(value, dict): self.update(value)
			else: raise ValueError("Configuration value must be a dict")

	@property
	def dirty(self):
		if self._dirty: return True
		for val in self.values():
			if val.dirty: return True
		return False

	def _clear_dirty(self):
		self._dirty = False
		for val in self.values(): val._clear_dirty()

	def __getitem__(self, item):
		with self._lock:
			if isinstance(item, str):
				item = item.split(separator, maxsplit=1)
				if len(item) == 1: return self._value[item[0]].value
				else: return self._value[item[0]][item[1]]
			else: raise ValueError("Keys must be string")

	def __setitem__(self, key, value):
		if self.read_only: raise ValueError("Cannot set read only configuration value")

		with self._lock:
			if isinstance(key, str):
				key = key.split(separator, maxsplit=1)
				if len(key) == 1:
					key = key[0]
					current = self._value.get(key)
					new = create_entry(value)
					if current is not None and type(current) is Configuration and len(current) and type(new) is ConfigurationItem:
						raise ValueError(f"Cannot set a whole configuration to a single value for key '{key}'")
					else: self._value[key] = new
				else:
					res = self.get(key[0])
					if res is None: self[key[0]] = {}
					self._value[key[0]][key[1]] = value
				self.mark_dirty()
			else: raise ValueError("Keys must be string")

	def __delitem__(self, key):
		if self.read_only: raise ValueError("Cannot delete read only configuration value")

		with self._lock:
			if isinstance(key, str):
				key = key.split(separator, maxsplit=1)
				if len(key) == 1:
					key = key[0]
					del self._value[key]
				else: del self._value[key[0]][key[1]]
				self.mark_dirty()
			else: raise ValueError("Keys must be string")

	def __contains__(self, item):
		with self._lock:
			if isinstance(item, str):
				item = item.split(separator, maxsplit=1)

				if len(item) > 1:
					try: return self._value[item[0]].__contains__(item[1])
					except KeyError: return False
				else: return self._value.__contains__(item[0])
			else: raise ValueError("Keys must be string")

	def update(self, other):
		""" Updates the keys from given dictionary or object
			(it must have an 'items' method that works similar as the dictionary method) """
		with self._lock:
			for k, v in other.items(): self[k] = v

	def keys(self):
		""" Get iterator with all configured keys (return type is equal to dictionary 'keys') """
		with self._lock: return self._value.keys()

	def values(self):
		""" Get iterator with all configured values (return type is equal to dictionary 'values')  """
		with self._lock: return self._value.values()

	def items(self):
		""" Get iterator with all configured key-value pairs (return type is equal to dictionary 'items') """
		with self._lock: return self._value.items()

	def get(self, key, default=None):
		""" Safe alternative for getting a key, returns 'default' when the key wasn't found instead of raising an error """
		with self._lock:
			try: return self[key]
			except KeyError: return default

	def get_or_create(self, key, create_value=None):
		""" Same as get, but when a key wasn't found the 'create_value' (if given) is set to that value """
		with self._lock:
			res = self.get(key)

			if create_value is None: create_value = self.default_value
			if res is None and create_value is not None:
				self[key] = create_value
				return self.get(key)
			return res

	def _get_item(self, key):
		key = key.split(separator, maxsplit=1)
		if len(key) == 1: return self._value[key[0]]
		else: return self._value[key[0]]._get_item(key[1])

	def get_or_create_configuration(self, key, create_value=None):
		""" Same as 'get_or_create' but returns a configuration object instead of a value """
		with self._lock:
			try: res = self._get_item(key)
			except KeyError: res = None

			if create_value is None: create_value = self.default_value
			if res is None and create_value is not None:
				self[key] = create_value
				return self._get_item(key)
			return res

	def set_defaults(self, value):
		""" Sets all non-existent key-value pairs from given dictionary, when a key already exists the currently set value is kept """
		with self._lock:
			for key, value in value.items(): self.get_or_create(key, value)

	@property
	def value(self):
		with self._lock: return {k: v.value for k, v in self.items()}

	@property
	def can_add_new(self): return self._default_value is not None

	@property
	def default_value(self): return self._default_value
	@default_value.setter
	def default_value(self, val):
		if val is not None and not isinstance(val, dict): raise TypeError("Can only add new values from a dictionary")
		self._default_value = val

	def rename(self, from_key, to_key):
		"""
		 Rename the options for a specific key to a different key
		 Raises a KeyError if the target key already exists
		"""
		if to_key in self: raise KeyError(f"'{to_key}' already exists")
		with self._lock:
			self._value[to_key] = self._value[from_key]
			del self._value[from_key]

	def __len__(self):
		with self._lock: return len(self.value)
	def __str__(self):
		with self._lock: return f"Configuration(dirty={self.dirty}, read_only={self.read_only}, value=[{', '.join([f'{k}: {str(v)}' for k, v in self.items()])}]"


class ConfigurationFile(Configuration):
	""" Same as a Configuration, but adds the ability read from/write to file """
	cfg_version = "2"

	def __init__(self, filepath, cfg_values=None, readonly=False):
		self._file = ".cfg/" + filepath
		if not self._file.endswith(".cfg"): self._file += ".cfg"
		Configuration.__init__(self, value=cfg_values, read_only=readonly)
		self._initialvalues = self._value
		self.load()

	def load(self):
		""" (Re)load configuration from disk """
		with self._lock:
			if self._initialvalues: self._value = self._initialvalues
			fl = self._read_file()
			if fl: self.update(fl)
			self._clear_dirty()

	@property
	def filename(self): return self._file.split("/")[-1]

	def _read_file(self):
		with self._lock:
			print("VERBOSE", f"Reading configuration file data from '{self.filename}'")
			import json
			try:
				with open(self._file, "r") as file:
					cfg_data = json.load(file)
					cfg_version = cfg_data.get("_version", "undefined")
					if cfg_version != self.cfg_version:
						print("WARNING", f"Configuration version mismatch: from {cfg_version} to {self.cfg_version}. Continuing to load but things might not work as expected")
					return cfg_data
			except json.JSONDecodeError as e: print("ERROR", f"Parsing configuration file '{self._file}':", e)
			except FileNotFoundError: print("VERBOSE", f"Configuration file '{self._file}' not found")

	def save(self):
		with self._lock:
			if self.read_only: raise PermissionError("Cannot write a read only configuration")

			print("VERBOSE", f"Trying to save file '{self._file}'")
			if self.dirty:
				print("VERBOSE", "Configuration dirty, writing to file...")
				with open(self._file, "w") as file:
					self["_version"] = self.cfg_version
					import json
					json.dump(self.value, file, indent=5)
					file.flush()
					self._clear_dirty()