import json, os

arg_keys = { "true": True, "false": False, "none": None	}
def parse_arg(arg):
	if not isinstance(arg, str): return arg
	try: return int(arg)
	except: pass

	id = arg.lower()
	if id in arg_keys: return arg_keys[id]
	else: return arg

class ConfigurationEntry:
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

class Configuration:
	def __init__(self, initial_value=None, filepath=None):
		self._cfg = {}
		self._error = False
		if initial_value is not None:
			if not isinstance(initial_value, dict):
				raise TypeError("[Configuration] 'initial_value' must be dict or None, not " + type(initial_value).__name__)
			else: self._parse_dict(initial_value)

		if filepath is not None:
			self._file = open(filepath, "r+")
			try: self._parse_dict(json.load(self._file))
			except json.JSONDecodeError as e:
				print("[Configuration] Error parsing configuration file:", e)
				self._file.close()
				self._file = None
				self._error = True
		else: self._file = None

	@property
	def cfg_file(self): return self._file is not None
	@property
	def error(self): return self._error

	def _parse_dict(self, dt):
		for key, value in dt.items():
			if isinstance(value, dict): self._cfg[key] = Configuration(value)
			else: self._cfg[key] = ConfigurationEntry(value)

	def __str__(self): return self.__descstr__()
	def __descstr__(self):
		s = "Configuration("
		for key, value in self._cfg.items(): s += "'{}': ".format(key) + value.__descstr__() + ", "
		return s + ")"

	def __getitem__(self, key):
		key = key.split("::", maxsplit=1)
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
		if len(key) == 2:
			try: self._cfg.get(key[0])[key[1]] = value; return
			except TypeError as e:
				raise TypeError("Key '{}' does not correspond to a configuration, therefore subkeys for this key cannot be set. Update this key on its own instead|".format(key[0]) + str(e))

		arg = self._cfg.get(key[0])
		if arg is not None:
			try: arg.value = value
			except TypeError:
				raise TypeError("Key '{}' corresponds to a configuration, therefore it cannot be directly to another value. Append '::(subkey)' to the index to set subkeys".format(key[0]))
		else: self._cfg[key[0]] = ConfigurationEntry(value)

	def to_dict(self):
		cfg = {}
		for key, value in self._cfg.items():
			try: cfg[key] = value.to_dict()
			except AttributeError:
				vl = value.value
				if vl is not None: cfg[key] = value.value
		return cfg

	def write_configuration(self, sort_keys=True):
		if self._file is not None:
			self._file.seek(0)
			self._file.truncate()
			json.dump(self.to_dict(), self._file, indent=5, sort_keys=sort_keys)
			self._file.flush()
			os.fsync(self._file.fileno())

	def __delitem__(self, key):
		self[key] = None

	def __del__(self):
		if self._file is not None: self._file.close()