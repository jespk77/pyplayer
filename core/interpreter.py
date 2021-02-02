import importlib, sys

from multiprocessing import Queue
from PyQt5 import QtCore
from weakref import WeakSet

import pymodules
from core import messagetypes

class Module:
	def __init__(self, name, properties):
		self._module_id = name
		self._module_properties = properties
		self._events = {}
		self._cmds = {}
		self._client = self._interpreter = None

	@property
	def name(self):
		""" The identifier of this module """
		return self._module_id
	@property
	def priority(self):
		""" The command priority for this module, lower values get processed before higher ones """
		return self._module_properties["priority"]

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
		if not callable(cb): raise TypeError("Event callback must be callable")
		self._events["init"] = cb

	def Destroy(self, cb):
		""" Destroy event for this module, called when the module is destroyed """
		if not callable(cb): raise TypeError("Event callback must be callable")
		self._events["destroy"] = cb

	def initialize_module(self, client, interpreter):
		print("VERBOSE", f"Initializing module '{self.name}'...")
		self._client = client
		self._interpreter = interpreter
		self._call_event("init")

	def destroy_module(self):
		print("VERBOSE", f"Destroying module '{self.name}'...")
		self._call_event("destroy")

	def _call_event(self, event_id):
		event_cb = self._events.get(event_id)
		if event_cb is not None:
			try: event_cb()
			except Exception as e: print("ERROR", f"Processing event '{event_id}' for module '{self.name}':", e)


class Interpreter(QtCore.QThread):
	"""
	 Process commands from modules defined in the modules package
	 Each module contains:
		'interpreter': a reference to this instance (only for reading/command queue access)
		'client': a reference to the main window of the client

	 Each module can define:
		'initialize()': [optional] gets called whenever the module is imported/reloaded
		'on_destoy()': [optional] gets called before the client is shut down or a module gets reloaded, use to clean up any previously created data/references
		'commands: dict': defines the commands this module can process, if not defined this module will not receive any commands
			Notes:
				- each command callback receives two arguments, the remaining keywords (in a list split on spaces) and the size of this list
				- use "" for default commands, the top level of the dictionary cannot have a default command
				- after processing a command the module must return an instance of 'messagetypes', if nothing is returned the interpreter assumes the command was ignored and will continue processing the command further
	"""
	CONSOLE = 1
	MEMORY = 2

	def __init__(self, client):
		QtCore.QThread.__init__(self)
		self.setObjectName("InterpreterThread")

		self._client = client
		self._queue = Queue()
		self._args = 0

		self._events = {}
		self.register_event("parse_command", self._parse_command)
		self.register_event("destroy", self._on_destroy)

		self._set_sys_arg()
		self._modules = []
		self._load_modules()

	def _set_sys_arg(self):
		if "console" in sys.argv: self._args &= self.CONSOLE

		if "memory" in sys.argv:
			try:
				from pympler import tracker
				print("INFO", "Memory logging enabled")
				self._mem_tracker = tracker.SummaryTracker()
				self._mem_tracker.print_diff()
				self._args &= self.MEMORY
			except ImportError: print("ERROR", "Cannot do memory tracking without installing Pympler")
			except Exception as e: print("ERROR", "Loading memory tracker:", e)

	def _load_modules(self):
		modules = pymodules.module_cfg.get("modules")

		if modules:
			mdl = sorted(modules.items(), key=lambda it: it[1]["priority"])
			for module_id, module_options in mdl:
				try:
					r = self._load_module(module_id)
					if isinstance(r, messagetypes.Error): self._client.on_notification(*r.get_contents())
				except Exception as e: print("ERROR", f"Loading module '{module_id}', it will not be available", e)

	@property
	def arguments(self):
		""" All debug arguments the interpreter was started with """
		l = []
		if self._args & self.CONSOLE: l.append("[Console]")
		if self._args & self.MEMORY: l.append("[MemoryLog]")
		return " ".join(l)

	def print_additional_debug(self):
		if self._args & self.MEMORY != 0: self._mem_tracker.print_diff()

	def run(self):
		"""
		 Main interpreter execution thread, completely event-driven
		 All registered handlers are executed in the order they were added
		"""
		print("INFO", "Interpreter thread started")
		while True:
			event, *args = self._queue.get()
			print("VERBOSE", f"Processing event '{event}' with data:", args)
			if event is False:
				self._notify_event("destroy")
				return
			else: self._notify_event(event, *args)


	def put_command(self, cmd, callback=None):
		"""
		 Add command to be interpreted, this will be processed as soon as all previous commands have finished processing
		 [optional] takes a 'callback' keyword that accepts a function, this will be called (in the interpreter thread) before the regular processing,
		 this callback is treated with the same rules as regular command processing callbacks; if it doesn't return anything will continue processing in all modules
		 This operation uses a multiprocessing.queue and therefore is thread-safe and uses the 'put' operation without wait and therefore will not block
		"""
		if callback and not callable(callback): raise TypeError("Callback must be callable when specified!")
		self._queue.put_nowait(("parse_command", cmd, callback))

	def put_event(self, event_id, *args):
		"""
		 Call all listeners (that are still alive) on specified event id with all given extra keywords
		 * Has no effect if the event id is empty or non-existent
		 * Any event listeners that can't handle given arguments are not called
		 This operation uses a multiprocessing.queue and therefore is thread-safe and uses the 'put' operation without wait and therefore will not block
		"""
		self._queue.put_nowait((event_id, *args))

	def stop(self):
		"""
		 Terminate the interpreter, any commands already queued will still be handled but commands added after this call are ignored
		 Once the interpreter has finished the 'on_destroy' method is called that cleans up all loaded modules before it is destroyed
		 This operation uses a multiprocessing.queue and therefore is thread-safe and uses the 'put' operation without wait and therefore will not block
		"""
		print("VERBOSE", "Received end event, terminating interpreter...")
		self._queue.put_nowait((False,))


	def register_event(self, event_id, callback):
		"""
		 Register listener to specified event id, a new event id will be created if it doesn't exist
		  * If the callback was already registered, this call has no effect
		"""
		print("VERBOSE", f"Registering callback '{callback.__name__}' for event '{event_id}'")
		if not callable(callback): raise TypeError(f"Event callback for '{event_id}' must be callable!")
		if event_id not in self._events: self._events[event_id] = set()
		self._events[event_id].append(callback)

	def unregister_event(self, event_id, callback):
		"""
		 Remove listener from specified event id, this call has no effect if the event id doesn't exist or the callback was not registered
		 Returns True if the callback was found and removed, or False otherwise
		"""
		print("VERBOSE", f"Unregistering callback '{callback.__name__}' for event '{event_id}'")
		event_list = self._events.get(event_id)
		if event_list:
			try:
				event_list.remove(callback)
				return True
			except KeyError: pass
		return False

	def _notify_event(self, event_id, *args, **kwargs):
		print("VERBOSE", f"Notifying listeners for the '{event_id}' event")
		event_list = self._events.get(event_id)
		if event_list is None: return print("ERROR", f"Unknown event id '{event_id}', event ignored...")

		errs = None
		for cb in event_list:
			try:
				try: cb(*args, **kwargs)
				except TypeError as t:
					if "{.__name__}() takes".format(cb) not in t: raise
					else: print("ERROR", f"Invalid callback! Nonmatching number of variables for '{cb.__name__}' in event '{event_id}'")
			except Exception as e:
				print("ERROR", f"Processing event callback '{event_id}':", e)
				errs = e
		return errs

	def _parse_command(self, command, cb=None):
		try:
			command = command.split(" ")
			op = None
			self.print_additional_debug()
			if cb is not None: op = cb(command)

			if op is None:
				try: res = self._process_command(command)
				except Exception as e: res = messagetypes.Error(e, "Error processing command")

				if res is not None and not isinstance(res, messagetypes.Empty):
					op = messagetypes.Error(TypeError(f"Expected a 'messagetype' object, not a '{type(res).__name__}'"), "Invalid response from command")
				else: op = res

			print("VERBOSE", "Got command result:", op)
			if not isinstance(op, messagetypes.Empty): op = messagetypes.Reply("No answer :(")
			self.print_additional_debug()
			self._client.on_reply(*op.get_contents())
		except Exception as e:
			print("ERROR", f"Error processing command '{' '.join(command)}'")
			self._client.on_reply(*messagetypes.Error(e, "Error processing command").get_contents())

	def _process_command(self, command):
		print("VERBOSE", f"Processing command '{' '.join(command)}'...")
		for md in self._modules:
			try: cl = md.commands
			except AttributeError:
				print("WARNING", f"'{md.__name__}' does not have a 'commands' dictionary, this is most likely not intended...")
				continue

			if "" in cl: raise TypeError(f"'{md.__name__}' contains a default command, this is not allowed in the top level")
			while isinstance(cl, dict):
				if len(command) == 0: break
				c = cl.get(command[0])
				if c is not None: cl = c
				else: break
				command = command[1:]

			if isinstance(cl, dict): cl = cl.get("")
			if cl is not None: return cl(command, len(command))


	def _load_module(self, md):
		if not md.startswith("modules."): md = "modules." + md
		if md in [n.__name__ for n in self._modules]: raise RuntimeError(f"Another module with name '{md}' was already registered!")
		try:
			print("VERBOSE", f"Loading '{md}'...")
			m = importlib.import_module(md)
			m.interpreter = self
			m.client = self._client
			m.platform = ""

			try: m.initialize()
			except AttributeError as a:
				if "initialize" not in str(a): raise
			except Exception as e: return messagetypes.Error(e, f"Failed to initialize '{md}': module will not be available")

			self._modules.append(m)
			return messagetypes.Reply("Module successfully loaded")
		except Exception as e: return messagetypes.Error(e, f"Failed to import '{md}': module will not be available")


	def _on_destroy(self):
		for module in self._modules:
			try: module.on_destroy()
			except AttributeError: pass
			except Exception as e: print("ERROR", f"'{module.__name__}' was not destroyed properly:", e)
