import json, os

arg_keys = { "true": True, "false": False, "none": None	}
def parse_arg(arg):
	if not isinstance(arg, str): return arg
	try: return int(arg)
	except: pass

	id = arg.lower()
	if id in arg_keys: return arg_keys[id]
	else: return arg

class ConfigurationItem: pass

class ConfigurationEntry(ConfigurationItem):
	""" Helper class for configuration that represents an entry in a file (everything that isn't a dictionary)
		When no value set, it represents None but can be used as other types representing default values
	 	Ensures that once the value is set, this value can only be updated to value of the same type or None to mark as deleted """
	def __init__(self, value=None):
		self._vl = parse_arg(value)
		self._tp = type(self._vl)

	@property
	def value_type(self): return self._tp

	@property
	def value(self): return self._vl
	@value.setter
	def value(self, v):
		if isinstance(v, Configuration): raise TypeError("Cannot set a configuration entry to a configuration!")

		if v is None: self._vl = None
		elif self._vl is None or self._tp == type(v): self._vl = v
		else: raise TypeError("Cannot assign value with type " + type(v).__name__ + " to entry type " + self._tp.__name__)
		self._tp = type(self._vl)
	@value.deleter
	def value(self): self._vl = None

	def __int__(self):
		try: return int(self._vl)
		except (TypeError, ValueError): return 0

	def __iter__(self): return iter(self._vl) if self._vl is not None else []
	def __str__(self): return str(self._vl) if self._vl is not None else "{empty}"
	def __bool__(self): return bool(self._vl)
	def __descstr__(self): return "ConfigurationEntry(value={}, type={})".format(self._vl, self._tp.__name__)

class ConfigurationList(ConfigurationItem):
	""" Containter class for an option represented by a list of values
		Ensures all items in the list have the same (sub)type """
	def __init__(self, initial_value=None):
		self._items = []
		self._itemtype = None
		if isinstance(initial_value, list):
			for i in initial_value:
				if i is None: continue
				tp = type(i)
				if self._itemtype is None: self._itemtype = tp
				elif tp != self._itemtype: raise TypeError("All items in 'initial_value' must have the same type: '{.__name__}' is not the same as '{.__name__}'".format(tp,self._itemtype))
				else: self._items.append(i)
		elif initial_value is not None: raise TypeError("'initial_value' must either be a list or None, not '{.__name__}'".format(type(initial_value)))

	@property
	def value_type(self):
		""" Get the type for all items in the list, all items in it should have the same type
		 	Returns 'None' when the list is empty """
		return self._itemtype
	@property
	def value(self): return self._items
	@value.setter
	def value(self, vl): print("value!", vl)

	def __getitem__(self, item):
		try: return self._items[item]
		except IndexError: return None

	def _verify_type(self, value):
		tp = type(value)
		if self._itemtype is None: self._itemtype = tp
		elif self._itemtype != tp: raise TypeError("Expected a value of type '{.__name__}' and '{.__name__}' is not the same type".format(self._itemtype, tp))

	def append(self, item):
		""" Add new item to the list, if the list is not empty the type of 'item' must match the other items """
		self._verify_type(item)
		self._items.append(item)

	def remove(self, item):
		""" Remove item from the list, has no effect if the list does not contain this item """
		try: self._items.remove(item)
		except ValueError: pass
		if len(self._items) == 0: self._itemtype = None


class Configuration(ConfigurationItem):
	def __init__(self, initial_value=None, filepath=None):
		self._cfg = {}
		self._error = False
		self._filepath = filepath
		self._file = None
		self._cfgvalue = None

		if initial_value is not None:
			if not isinstance(initial_value, dict):
				raise TypeError("'initial_value' must be dict or None, not " + type(initial_value).__name__)
			else: self.update_dict(initial_value)

		if self._filepath is not None:
			if not os.path.isdir(".cfg"): os.mkdir(".cfg")

			try:
				self._file = open(self._filepath, "r+")
				try: self.update_dict(json.load(self._file))
				except json.JSONDecodeError as e:
					print("ERROR", "Error parsing configuration file:", e)
					self._file.close()
					self._file = None
					self._error = True
			except FileNotFoundError: pass

	@property
	def cfg_file(self): return self._file is not None
	@property
	def error(self): return self._error
	@property
	def value(self): return None
	@value.setter
	def value(self, val):
		if not isinstance(val, dict): raise TypeError

	def update_dict(self, dt):
		self._cfgvalue = None
		if isinstance(dt, dict):
			for key, value in dt.items():
				if value is not None:
					entry_type = type_class.get(type(value), type_class[None])
					self._cfg[key] = entry_type(value)
					if isinstance(value, dict): self._cfg[key] = Configuration(value)
					else: self._cfg[key] = ConfigurationEntry(value)

	def __str__(self): return self.__descstr__()
	def __descstr__(self): return "Configuration({})".format(", ".join(["'{}': {}".format(key, value.__descstr__()) for key, value in self._cfg.items()]))

	def __getitem__(self, key):
		key = str(key).split("::", maxsplit=1)
		if len(key) == 2:
			arg = self._cfg.get(key.pop(0))
			if arg is not None:
				try: return arg[key[0]]
				except AttributeError: return arg
			return ConfigurationEntry()
		else: return self._cfg.get(key[0], ConfigurationEntry())

	def get(self, key, default=None):
		vl = self[key]
		if isinstance(vl, ConfigurationEntry): return vl.value if vl.value is not None else default
		else: return vl

	def __setitem__(self, key, value):
		value = parse_arg(value)
		key = key.split("::", maxsplit=1)
		self._cfgvalue = None
		if len(key) == 2:
			try:
				self._cfg.get(key[0], ConfigurationEntry())[key[1]] = value
				return
			except TypeError: raise TypeError("Key '{}' does not correspond to a configuration, therefore subkeys for this key cannot be set. Update this key on its own instead".format(key[0]))

		arg = self._cfg.get(key[0])
		if arg is not None:
			try: self._cfg[key[0]].value = value
			except TypeError: raise TypeError("Key '{}' corresponds to a configuration, therefore it cannot be directly to another value. Append '::(subkey)' to the index to set subkeys".format(key[0]))
		elif isinstance(value, dict): self._cfg[key[0]] = Configuration(initial_value=value)
		elif isinstance(value, list): self._cfg[key[0]] = ConfigurationList(initial_value=value)
		else: self._cfg[key[0]] = ConfigurationEntry(value)

	def to_dict(self, force_remake=False):
		if self._cfgvalue is not None:
			if not force_remake: return self._cfgvalue
			self._cfgvalue.clear()
		else: self._cfgvalue = {}

		for key, value in self._cfg.items():
			vl = None
			try: vl = value.to_dict()
			except AttributeError: vl = value.value
			except Exception as e: print("ERROR", "Cannot get value for key '{}':", e)

			if vl is None: continue
			if isinstance(vl, ConfigurationItem): print("ERROR", "Invalid value for key '{}':".format(key), vl)
			else: self._cfgvalue[key] = vl
		return self._cfgvalue

	def write_configuration(self, sort_keys=True):
		if self._filepath is not None and self._file is None:
			try: self._file = open(self._filepath, "w+")
			except Exception as e: print("ERROR", "Cannot create configuration file '{}':".format(self._filepath), e)

		if self._file is not None:
			self._file.seek(0)
			self._file.truncate()
			json.dump(self.to_dict(force_remake=True), self._file, indent=5, sort_keys=sort_keys)
			self._file.flush()
			os.fsync(self._file.fileno())

	def __delitem__(self, key):
		self[key] = None

	def __del__(self):
		if self._file is not None: self._file.close()

type_class = {
	dict: Configuration,
	list: ConfigurationList,
	None: ConfigurationEntry
}