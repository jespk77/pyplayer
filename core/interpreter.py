import importlib, sys

from multiprocessing import Queue
from PyQt5 import QtCore

import pymodules
from core import messagetypes, modules

class _ModuleData:
	def __init__(self, name, properties):
		self._module_id = name
		self._module_properties = properties
		self._events = {}
		self._cmds = {}
		self._module = None

	@property
	def name(self):
		""" The identifier of this module """
		return self._module_id
	@property
	def priority(self):
		""" The command priority for this module, lower values get processed before higher ones """
		return self._module_properties["priority"]
	@property
	def enabled(self):
		""" Whether this module is currently enabled """
		return self._module_properties["enabled"]

	def initialize_module(self, client, interpreter):
		print("VERBOSE", "Importing module...")
		mod = importlib.import_module("." + self.name, "modules")
		try:
			module = None
			print("VERBOSE", "Locating Module instance within module...")
			for attr in mod.__dict__.values():
				if isinstance(attr, modules.Module):
					module = attr
					break

			if module is None: raise TypeError("module must contain an instance of core.modules.Module")
			self._module = module

			print("VERBOSE", f"Initializing module '{self.name}'...")
			self._module.call_initialize(client, interpreter)
		except AttributeError:
			print("ERROR", f"Module '{self.name}' does not define a module attribute and cannot be loaded")
			raise

	def destroy_module(self):
		print("VERBOSE", f"Destroying module '{self.name}'...")
		try: self._module.call_destroy()
		except Exception as e: print("ERROR", f"Destroying module '{self.name}':", e)

	def process_command(self, command): return self._module.get_command_callback(command)
	def process_autocomplete(self, text): return self._module.get_closest_match(text)

	def __str__(self): return f"ModuleData[name={self.name}, priority={self.priority}, module={self._module}]"


class Interpreter(QtCore.QThread):
	"""
	 Process commands from modules defined in the modules package
	 Each module must define an instance of core.modules.Module which supports the following features:
		'@Initialize': event that is fired whenever the module is first imported
		'@Destroy': event that is fired before the client is shut down, use to clean up any previously created data/references
		'commands: dict': defines the commands this module can process, if not defined this module will not receive any commands
			Notes:
				- each command callback receives two arguments, the remaining keywords (in a list split on spaces) and the size of this list
				- use "" for default commands, they are called if no further sublevel fit the given command. Adding a default command on the top level of the dict is not allowed
				- After processing a command the module must return an instance of 'messagetypes', if nothing is returned the interpreter assumes the command was ignored and will continue processing the command further
	"""
	empty_response = messagetypes.Reply("No answer :(")

	CONSOLE = 1
	MEMORY = 2

	def __init__(self, client):
		QtCore.QThread.__init__(self)
		self.setObjectName("InterpreterThread")

		self._client = client
		self._queue = Queue()
		self._args = 0

		self._events = {}
		self.register_event("autocomplete", self._try_autocomplete)
		self.register_event("parse_command", self._parse_command)
		self.register_event("destroy", self._on_destroy)

		self._set_sys_arg()
		self._loaded_modules = []
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
		modules = {mod_id: mod_options for mod_id, mod_options in pymodules.module_cfg.get("modules").items() if mod_options["enabled"]}

		if modules:
			mdl = sorted(modules.items(), key=lambda it: it[1]["priority"])
			for module_id, module_options in mdl:
				try:
					r = self._load_module(module_id, module_options)
					if isinstance(r, messagetypes.Error): self._client.on_notification(*r.get_contents())
				except Exception as e: print("ERROR", f"Loading module '{module_id}', it will not be available", e)

	def _load_module(self, module, options):
		if module in self._loaded_modules: raise RuntimeError(f"Another module with name '{module}' was already registered!")

		try:
			print("VERBOSE", f"Loading '{module}'...")
			md = _ModuleData(module, options)
			try: md.initialize_module(self._client, self)
			except Exception as e: return messagetypes.Error(e, f"Failed to initialize '{module}': module will not be available")

			self._modules.append(md)
			self._loaded_modules.append(module)
			print("VERBOSE", "Module successfully loaded")
			return messagetypes.Reply("Module successfully loaded")
		except Exception as e: return messagetypes.Error(e, f"Failed to import '{module}': module will not be available")

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


	def request_autocomplete(self, line):
		self._queue.put_nowait(("autocomplete", line))

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
		self._events[event_id].add(callback)

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
			if not isinstance(op, messagetypes.Empty): op = self.empty_response
			self.print_additional_debug()
			self._client.on_reply(*op.get_contents())
		except Exception as e:
			print("ERROR", f"Error processing command '{' '.join(command)}'")
			self._client.on_reply(*messagetypes.Error(e, "Error processing command").get_contents())

	def _process_command(self, command):
		print("VERBOSE", f"Processing command '{' '.join(command)}'...")
		command.append("\x00")
		for md in self._modules:
			cb = md.process_command(command)
			if cb is not None: return cb.callback(cb.args, len(cb.args))

	def _try_autocomplete(self, text):
		print("VERBOSE", f"Trying to autocomplete '{text}'...")
		text = text.split(" ")
		suggestions = []
		for md in self._modules:
			option = md.process_autocomplete(text)
			if option is not None: suggestions.append(option)

		suggestions = sorted(suggestions, key=lambda item: len(item.remainder))
		self._client.schedule_task(task_id=self._client.autocomplete_task, suggestions=suggestions)

	def _on_destroy(self):
		print("VERBOSE", "Destroying modules...")
		for md in self._modules: md.destroy_module()