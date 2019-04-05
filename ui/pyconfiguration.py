
separator = "::"
def set_entry(entry, value, readonly):
	if entry is not None:
		entry.value = value
		return entry
	elif isinstance(value, dict): return Configuration(value, readonly)
	else: return ConfigurationItem(value)

class ConfigurationItem:
	""" Stores a specific value for a configuration setting """
	def __init__(self, value=None):
		self._value = value
		self._dirty = False

	@property
	def is_set(self): return self._value is not None
	@property
	def dirty(self): return self._dirty
	@property
	def value(self): return self._value
	@value.setter
	def value(self, val):
		if isinstance(val, dict): raise AttributeError("Cannot set value to configuration!")
		self._value = val
		self._dirty = True

	def _write_value(self):
		self._dirty = False
		return self.value

class Configuration:
	""" Object that stores a number of configuration items and/or sub-configuration objects
	 	Each item is bound to a keyword, similar to a dictionary, and getting/setting values is done through higher levels recursively """
	def __init__(self, initial_cfg=None, readonly=False):
		self._value = {}
		self._readonly = readonly
		self.update(initial_cfg)
		self._dirty = False

	def update(self, dt):
		if isinstance(dt, dict):
			for key, value in dt.items():
				if separator in key: raise ValueError("Configuration keys cannot contain the separator '{}'".format(separator))
				self._value[key] = set_entry(None, value, self._readonly)

	def __getitem__(self, key):
		key = key.split(separator, maxsplit=1)
		if len(key) > 1:
			try: return self._value[key[0]][key[1]]
			except TypeError: pass
			raise KeyError(key[1])
		else: return self._value[key[0]].value

	def __setitem__(self, key, value):
		if self._readonly: raise PermissionError("Cannot update this configuration since it was set to read-only!")
		key = key.split(separator, maxsplit=1)
		if len(key) > 1:
			try: self._value[key[0]][key[1]] = value; return
			except TypeError as e: print(e)
			raise KeyError(key[1])
		else: self._value[key[0]] = set_entry(self._value.get(key[0]), value, self._readonly)

	def __delitem__(self, key):
		if self._readonly: raise PermissionError("Cannot delete elements from a read-only configuration!")
		key = key.split(separator, maxsplit=1)
		if len(key) > 1:
			try: self._value[key[0]][key[1]] = None
			except TypeError as e: print(e)
			raise KeyError(key[1])
		else: self._value[key[0]] = None

	def get(self, key, default=None):
		try:
			rs = self[key]
			if rs is not None: return rs
		except KeyError: pass
		return default

	def get_or_create(self, key, create_value=None):
		if self.get(key) is None: self[key] = create_value
		return self.get(key)

	def _write_value(self):
		self._dirty = False
		return { k: v._write_value for k,v in self._value.items() if v.is_set }

	@property
	def item_list(self): return [ (k,v.value) for k,v in self._value.items() ]
	@property
	def is_set(self): return len(self._value) > 0
	@property
	def value(self): return { k: v.value for k,v in self._value.items() if v.is_set }
	@property
	def read_only(self): return self._readonly
	@property
	def dirty(self): return self._dirty

cfg_file_version = "1b"
class ConfigurationFile(Configuration):
	""" Same as a Configuration, but adds the ability read from/write to file """
	def __init__(self, filepath, initial_cfg=None, readonly=False):
		self._file = filepath
		Configuration.__init__(self, initial_cfg, readonly)
		self.load()

	def load(self):
		""" (Re)load configuration from disk """
		self.update(self._read_file())
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
		if not self._dirty:
			with open(self._file, "w") as file:
				import json
				wd = self._write_value()
				wd["_version"] = cfg_file_version
				json.dump(wd, file, indent=5)
			self._dirty = False