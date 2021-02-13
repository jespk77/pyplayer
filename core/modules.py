from collections import namedtuple
CommandResult = namedtuple("CommandResult", ["callback", "args"])
CommandSuggest = namedtuple("CommandSuggest", ["command", "options", "remainder"])

from . import pyconfiguration

class Module:
	_modules = {}
	def __new__(cls, key):
		md = Module._modules.get(key)
		if md is None:	Module._modules[key] = md = super().__new__(cls)
		return md

	def __init__(self, key):
		if not hasattr(self, "_events"):
			print("VERBOSE", f"Creating new module '{key}'")
			self._events = {}
			self._client = self._interpreter = self._cmds = None
			self._cfg = pyconfiguration.ConfigurationFile(f"{key}.cfg")

	@property
	def client(self):
		""" Reference to the main window """
		return self._client
	@property
	def interpreter(self):
		""" Reference to the interpreter object """
		return self._interpreter
	@property
	def configuration(self):
		""" The configuration for this module """
		return self._cfg

	@property
	def commands(self):
		""" A dictionary containing all possible commands for this module """
		return self._cmds

	@commands.setter
	def commands(self, commands):
		if not isinstance(commands, dict): raise TypeError("Commands must be a dictionary")
		if "" in commands: raise ValueError("A default command is not allowed on the top level")
		self._cmds = commands

	def Initialize(self, cb):
		""" Initialize event for this module, called when the module is loaded """
		self._events["init"] = cb

	def Destroy(self, cb):
		""" Destroy event for this module, called when the module is destroyed """
		self._events["destroy"] = cb

	@property
	def is_loaded(self):
		""" Is True if the module has been loaded """
		return self._interpreter is not None

	def call_initialize(self, client, interpreter):
		print("VERBOSE", "Initialization event received")
		self._client = client
		self._interpreter = interpreter
		cb = self._events.get("init")
		if callable(cb): cb()

	def call_destroy(self):
		print("VERBOSE", "Destroy event received")
		cb = self._events.get("destroy")
		if callable(cb): cb()
		self._cfg.save()

	def get_command_callback(self, command):
		cmds = self.commands
		if cmds is None: return None

		for index, arg in enumerate(command):
			cmd = cmds.get(arg)
			if cmd is None:
				cmds = cmds.get("")
				if cmds is not None: return CommandResult(cmds, command[index:-1])
			else: cmds = cmd

			if callable(cmds): return CommandResult(cmds, command[index+1:-1])
			elif cmds is None: return None

	def get_closest_match(self, search):
		cmds = self.commands
		if cmds is None: return None

		command, options, index = [], None, 0
		for index, arg in enumerate(search):
			if callable(cmds):
				index -= 1
				break

			options = [key for key in cmds.keys() if key.startswith(arg)]
			if len(options) > 1:
				if index < len(search) - 1 and arg in options:
					options.clear()
					cmds = cmds[arg]
					command.append(arg)
				else: break
			elif len(options) == 1:
				val = options.pop()
				command.append(val)
				cmds = cmds[val]
			else:
				index -= 1
				break

		if command or options: return CommandSuggest(' '.join(command), options if options else None, ' '.join(search[index+1:]))
		else: return None

	def __str__(self): return f"Module[loaded={self.is_loaded}, commands=({','.join(self.commands.keys())})]"