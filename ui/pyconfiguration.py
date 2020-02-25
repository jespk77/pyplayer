separator = "::"
def create_entry(value, read_only=False):
	if isinstance(value, dict): return Configuration(value, read_only)
	else: return ConfigurationItem(value, read_only)


class ConfigurationItem:
	""" Stores a specific value for a configuration setting """
	def __init__(self, value=None, read_only=False):
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
	def _getitem(self, key): self.__getitem__(key)
	def __getitem__(self, item): raise AttributeError("ConfigurationItem is not a valid container!")
	def __setitem__(self, key, value): self.__getitem__(key)
	def __delitem__(self, key): self.__getitem__(key)
	def __str__(self): return "ConfigurationItem({!s})".format(self._value)


class Configuration(ConfigurationItem):
	""" Object that stores a number of configuration items and/or sub-configuration objects
	 	Each item is bound to a keyword, similar to a dictionary, and getting/setting values is done through higher levels recursively """
	def __init__(self, cfg_values=None, read_only=False):
		if cfg_values: ConfigurationItem.__init__(self, value={ key: create_entry(value, read_only) for key, value in cfg_values.items() })
		else: ConfigurationItem.__init__(self, value={})
		self._dirty = False


	def _getitem(self, key):
		if not isinstance(key, str): raise ValueError("Getting keys must be given as string")

		key = key.split(separator, maxsplit=1)
		if len(key) > 1: return self._value.__getitem__(key[0])._getitem(key[1])
		else: return self._value[key[0]]

	def _createitem(self, key, add_value):
		try: return self._getitem(key)
		except KeyError:
			self[key] = add_value
			return self._getitem(key)


	def __getitem__(self, key):
		return self._getitem(key).value

	def __setitem__(self, key, value):
		if self.read_only: raise RuntimeError("Cannot update this configuration since it was set to read-only!")
		elif not isinstance(key, str): raise ValueError("Getting keys must be given as string!")

		key = key.split(separator, maxsplit=1)
		if len(key) == 1:
			try: cval = self._getitem(key[0])
			except KeyError: cval = None
			nval = create_entry(value, self.read_only)
			tc, tn = type(cval), type(nval)
			if cval and tc is not tn: raise TypeError("Incompatible types: '{.__name__}' and '{.__name__}'!".format(tc, tn))
			self._value[key[0]] = nval
		else:
			if key[0] not in self._value: self._value[key[0]] = Configuration()
			self._value[key[0]][key[1]] = value
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


	def keys(self):
		""" Get iterator with all configured keys (return type is equal to dictionary 'keys') """
		return self.value.keys()
	def values(self):
		""" Get iterator with all configured values (return type is equal to dictionary 'values')  """
		return self.value.values()
	def items(self):
		""" Get iterator with all configured key-value pairs (return type is equal to dictionary 'items') """
		return self.value.items()

	@property
	def is_set(self): return len(self._value) > 0
	@property
	def value(self): return { k: v.value for k,v in self._value.items() if v.is_set }
	@property
	def dirty(self): return self._dirty


class ConfigurationFile(Configuration):
	""" Same as a Configuration, but adds the ability read from/write to file """
	cfg_version = "1b"
	def __init__(self, filepath, cfg_values=None, readonly=False):
		self._file = filepath
		Configuration.__init__(self, cfg_values=cfg_values, read_only=readonly)
		self._initialvalues = self._value
		self._file_exists = False
		self.load()

	def load(self):
		""" (Re)load configuration from disk """
		if self._initialvalues: self._value = self._initialvalues
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
				self._file_exists = True
				import json
				try: return json.load(file)
				except json.JSONDecodeError as e:
					print("ERROR", "Parsing configuration file '{}':".format(self._file), e)
				raise ValueError("JSON parsing error:" + str(e))
		except FileNotFoundError: print("INFO", "Configuration file '{}' not found".format(self._file))

	def save(self):
		if self.read_only: raise PermissionError("Cannot write configuration file when it is set to read only")

		print("INFO", "Trying to save file '{}'".format(self._file))
		if self.dirty or not self._file_exists:
			with open(self._file, "w") as file:
				print("INFO", "Writing configuration to file '{}'".format(self._file))
				self["_version"] = self.cfg_version
				import json
				json.dump(self.value, file, indent=5)
				file.flush()
				self._dirty = False
