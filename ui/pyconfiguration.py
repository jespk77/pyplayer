import os
if not os.path.isdir(".cfg"): os.mkdir(".cfg")

separator = "::"
def create_entry(value, read_only=False):
	if isinstance(value, dict): return Configuration(value, read_only)
	else: return ConfigurationItem(value, read_only)

class ConfigurationItem:
	def __init__(self, value=None, read_only=False):
		self._value = value
		self._read_only = read_only is True
		self._dirty = False

	@property
	def dirty(self): return self._dirty
	@property
	def is_set(self): return self.value is not None
	@property
	def read_only(self): return self._read_only

	@property
	def value(self): return self._value
	@value.setter
	def value(self, value):
		if self._read_only: raise ValueError("Cannot set read only configuration value")
		self._value = value
		self.mark_dirty()

	def mark_dirty(self): self._dirty = True

	def __getitem__(self, item): raise TypeError("This item does not support subkeys")
	def __setitem__(self, key, value): self.__getitem__(key)
	def __delitem__(self, key): self.__getitem__(key)

	def update(self, other): self.__getitem__("")
	def keys(self): self.__getitem__("")
	def values(self): self.__getitem__("")
	def items(self): self.__getitem__("")

	def get(self, key, default=None): self.__getitem__(key)
	def get_or_create(self, key, create_value=None): self.__getitem__(key)

	def __len__(self): return len(self.value) if self.is_set else 0
	def __str__(self): return f"ConfigurationItem(read_only={self._read_only}, value={str(self.value)})"


class Configuration(ConfigurationItem):
	def __init__(self, value=None, read_only=False):
		ConfigurationItem.__init__(self, {}, read_only)
		if value:
			if isinstance(value, dict): self.update(value)
			else: raise ValueError("Configuration value must be a dict")

	def __getitem__(self, item):
		if isinstance(item, str):
			item = item.split(separator, maxsplit=1)
			if len(item) == 1: return self._value[item[0]].value
			else: return self._value[item[0]][item[1]]
		else: raise ValueError("Keys must be string")

	def __setitem__(self, key, value):
		if self.read_only: raise ValueError("Cannot set read only configuration value")

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

		if isinstance(key, str):
			key = key.split(separator, maxsplit=1)
			if len(key) == 1:
				key = key[0]
				del self._value[key]
			else: del self._value[key[0]][key[1]]
			self.mark_dirty()
		else: raise ValueError("Keys must be string")

	def update(self, other):
		""" Updates the keys from given dictionary or object
			(it must have an 'items' method that works similar as the dictionary method) """
		for k, v in other.items(): self[k] = v

	def keys(self):
		""" Get iterator with all configured keys (return type is equal to dictionary 'keys') """
		return self._value.keys()

	def values(self):
		""" Get iterator with all configured values (return type is equal to dictionary 'values')  """
		return self._value.values()

	def items(self):
		""" Get iterator with all configured key-value pairs (return type is equal to dictionary 'items') """
		return self._value.items()

	def get(self, key, default=None):
		""" Safe alternative for getting a key, returns 'default' when the key wasn't found instead of raising an error """
		try: return self[key]
		except KeyError: return default

	def get_or_create(self, key, create_value=None):
		""" Same as get, but when a key wasn't found the 'create_value' (if given) is set to that value """
		res = self.get(key)
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
		try: res = self._get_item(key)
		except KeyError: res = None
		if res is None and create_value is not None:
			self[key] = create_value
			return self._get_item(key)
		return res

	def set_defaults(self, value):
		""" Sets all non-existent key-value pairs from given dictionary, when a key already exists the currently set value is kept """
		for key, value in value.items():
			self.get_or_create(key, value)

	@property
	def value(self): return {k: v.value for k, v in self.items()}

	def __len__(self): return len(self.value)
	def __str__(self): return f"Configuration(read_only={self.read_only}, value=[{', '.join([f'{k}: {str(v)}' for k, v in self.items()])}]"


class ConfigurationFile(Configuration):
	""" Same as a Configuration, but adds the ability read from/write to file """
	cfg_version = "1b"

	def __init__(self, filepath, cfg_values=None, readonly=False):
		self._file = f".cfg/{filepath}"
		Configuration.__init__(self, value=cfg_values, read_only=readonly)
		self._initialvalues = self._value
		self._file_exists = False
		self.load()

	def load(self):
		""" (Re)load configuration from disk """
		if self._initialvalues: self._value = self._initialvalues
		fl = self._read_file()
		if fl: self.update(fl)
		self._dirty = False

	@property
	def filename(self): return self._file.split("/")[-1]

	def _read_file(self):
		print("VERBOSE", f"Reading configuration file data from '{self.filename}'")
		try:
			error = None
			with open(self._file, "r") as file:
				self._file_exists = True
				import json
				try: return json.load(file)
				except json.JSONDecodeError as e:
					print("ERROR", f"Parsing configuration file '{self._file}':", e)
					error = e

			if error is not None: raise ValueError(f"JSON parsing error: {error}")
		except FileNotFoundError: print("VERBOSE", f"Configuration file '{self._file}' not found")

	def save(self):
		if self.read_only: raise PermissionError("Cannot write a read only configuration")

		print("VERBOSE", f"Trying to save file '{self._file}'")
		if self.dirty or not self._file_exists:
			print("VERBOSE", "Configuration dirty, writing to file...")
			with open(self._file, "w") as file:
				self["_version"] = self.cfg_version
				import json
				json.dump(self.value, file, indent=5)
				file.flush()
				self._file_exists = True
				self._dirty = False