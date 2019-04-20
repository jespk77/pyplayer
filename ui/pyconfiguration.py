separator = "::"
def create_entry(value, read_only=False):
	if isinstance(value, dict): return Configuration(read_only, **value)
	else: return ConfigurationItem(read_only, value)


class ConfigurationItem:
	""" Stores a specific value for a configuration setting """
	def __init__(self, read_only=False, value=None):
		self._value = value
		self._readonly = read_only
	@property
	def is_set(self): return self._value is not None
	@property
	def read_only(self): return self._readonly
	@property
	def value(self): return self._value
	@value.setter
	def value(self, val):
		if self.read_only: raise RuntimeError("This attribute was marked as read only and cannot be updated!")
		self._value = val

	def __len__(self):
		try: return len(self.value)
		except TypeError: return 1 if self.value is not None else 0
	def __getitem__(self, item): raise KeyError(item)
	def __setitem__(self, key, value): raise KeyError(key)
	def __delitem__(self, key): raise KeyError(key)
	def __str__(self): return "ConfigurationItem({!s})".format(self.value)


class Configuration(ConfigurationItem):
	""" Object that stores a number of configuration items and/or sub-configuration objects
	 	Each item is bound to a keyword, similar to a dictionary, and getting/setting values is done through higher levels recursively """
	def __init__(self, read_only=False, **cfg_values):
		ConfigurationItem.__init__(self, read_only, value={ key: create_entry(value, read_only) for key, value in cfg_values.items() })
		self._dirty = False

	def __getitem__(self, key):
		key = key.split(separator, maxsplit=1)
		if len(key) > 1: return self._value[key[0]][key[1]]
		else: return self._value[key[0]]

	def __setitem__(self, key, value):
		if self.read_only: raise RuntimeError("Cannot update this configuration since it was set to read-only!")

		key = key.split(separator, maxsplit=1)
		if len(key) == 1:
			cval = self.get(key[0])
			nval = create_entry(value, self.read_only)
			if cval and type(cval) is not type(nval): raise TypeError("Incompatible types!")
			self._value[key[0]] = nval
		else: self._value[key[0]][key[1]] = value
		self._dirty = True

	def __delitem__(self, key):
		if self.read_only: raise RuntimeError("Cannot delete elements from a read-only configuration!")

		key = key.split(separator, maxsplit=1)
		if len(key) > 1: del self._value[key[0]][key[1]]
		else: del self._value[key[0]]
		self._dirty = True

	def __len__(self): return len(self.value)
	def __str__(self): return "Configuration({!s})".format(self._value)

	def get(self, key, default=None):
		""" Get the value bound to given key, returns 'default' argument if nothing bound """
		try: return self[key]
		except KeyError: return default

	def get_or_create(self, key, create_value=None):
		""" Same as get, but when a key wasn't found the second argument (if not None) is bound to that key """
		if self.get(key) is None and create_value is not None: self[key] = create_value
		return self.get(key)

	def configuration_get(self, key):
		""" Get the configuration object bound to given key or None if nothing bound """
		key = key.split(separator, maxsplit=1)
		if len(key) > 1:
			cfg = self._value.get(key[0])
			if cfg and cfg.is_set: return cfg.configuration_get(key[1])
			else: return None
		else: return self._value.get(key[0])

	@property
	def is_set(self): return len(self._value) > 0
	@property
	def value(self): return { k: v.value for k,v in self._value.items() if v.is_set }
	@property
	def dirty(self): return self._dirty


cfg_file_version = "1b"
class ConfigurationFile(Configuration):
	""" Same as a Configuration, but adds the ability read from/write to file """
	def __init__(self, filepath, readonly=False, **cfg_values):
		self._file = filepath
		Configuration.__init__(self, readonly, **cfg_values)
		self._initialvalues = cfg_values
		self.load()

	def load(self):
		""" (Re)load configuration from disk """
		self._value = self._initialvalues
		fl = self._read_file()
		if fl:
			for key, option in fl.items(): self[key] = option
		self._dirty = False

	@property
	def filename(self): return self._file

	def _read_file(self):
		print("INFO", "Reading configuration file data from '{}'".format(self.filename))
		try:
			with open(self._file, "r") as file:
				import json
				try: return json.load(file)
				except json.JSONDecodeError as e:
					print("ERROR", "Parsing configuration file '{}':".format(self._file), e)
				raise ValueError(e)
		except FileNotFoundError: print("WARNING", "Configuration file '{}' not found!".format(self._file))

	def save(self):
		if self.read_only: raise PermissionError("Cannot write configuration file when it is set to read only")

		print("INFO", "Writing configuration to file '{}' (if dirty)".format(self._file))
		if not self.dirty:
			with open(self._file, "w") as file:
				self["_version"] = cfg_file_version
				import json
				json.dump(self.value, file, indent=5)
				self._dirty = False