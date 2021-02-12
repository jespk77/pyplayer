class Module:
	_modules = {}
	def __new__(cls, key):
		mod = Module._modules.get(key)
		if mod is None:	Module._modules[key] = mod = super().__new__(cls)
		return mod

	def __init__(self, key):
		if not hasattr(self, "_events"):
			print("VERBOSE", f"Creating new module '{key}'")
			self._events = {}
			self._client = self._interpreter = self._cmds = None

	@property
	def client(self):
		""" Reference to the main window """
		return self._client

	@property
	def interpreter(self):
		""" Reference to the interpreter object """
		return self._interpreter

	@property
	def commands(self):
		""" A dictionary containing all possible commands for this module """
		return self._cmds

	@commands.setter
	def commands(self, commands):
		if not isinstance(commands, dict): raise TypeError("Commands must be a dictionary")
		self._cmds = commands

	def Initialize(self, cb):
		""" Initialize event for this module, called when the module is loaded """
		self._events["init"] = cb

	def Destroy(self, cb):
		""" Destroy event for this module, called when the module is destroyed """
		self._events["destroy"] = cb

	def call_initialize(self, client, interpreter):
		self._client = client
		self._interpreter = interpreter
		cb = self._events.get("init")
		if callable(cb): cb()

	def call_destroy(self):
		cb = self._events.get("destroy")
		if callable(cb): cb()

	def __str__(self): return f"Module[command_count={len(self.commands)}, commands={self.commands.keys()}]"