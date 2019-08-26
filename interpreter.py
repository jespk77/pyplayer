import importlib, sys

from multiprocessing import Queue
from threading import Thread
from weakref import WeakSet

from utilities import messagetypes


class Interpreter(Thread):
	""" Process commands from modules defined in the modules package
		Each module contains:
			'interpreter': a reference to this instance (only for reading/command queue access)
			'client': a reference to the main window of the client

		Each module can define:
			'initialize()': [optional] gets called whenever the module is imported/reloaded
			'on_destoy()': [optional] gets called before the client is shut down or a module gets reloaded, use to clean up any previously created data/references
			'dependencies': dict: this defines the dependencies that need to be installed using pip, this should be a dictionary where key is the name that needs to be loaded (this name will be set as a module attribure with the import assigned)
			'commands: dict': defines the commands this module can process, if not defined this module will not receive any commands
				Notes:
					- each command callback receives two arguments, the remaining keywords (in a list split on spaces) and the size of this list
					- use "" for default commands, the top level of the dictionary cannot have a default command
					- after processing a command the module must return an instance of 'messagetypes', if nothing is returned the interpreter assumes the command was ignored and will continue processing the command further
	"""
	def __init__(self, client, modules=None):
		super().__init__(name="PyInterpreterThread")
		self._client = client
		self._queue = Queue()
		self._configuration = None
		self._checks = []
		self._platform = sys.platform

		self._events = {}
		self._handlers = []
		self._handlers.append(self.register_event("parse_command", self._parse_command))
		self._handlers.append(self.register_event("destroy", self._on_destroy))
		self._handlers.append(self.register_event("title_update", self._client.update_title))
		self._set_sys_arg()

		self._modules = []
		if modules:
			mdl = sorted(modules.items(), key=lambda it: it[1]["priority"])
			for module_id, module_options in mdl:
				try:
					r = self._load_module(module_id)
					if isinstance(r, messagetypes.Error): client.on_notification(*r.get_contents())
				except Exception as e: print("ERROR", f"While loading '{module_id}':", e)
		self.start()

	def _set_sys_arg(self):
		if "console" in sys.argv: self._checks.append("ConsoleLog")

		if "memory" in sys.argv:
			print("INFO", "Memory logging enabled")
			try:
				from pympler import tracker
				self.mem_tracker = tracker.SummaryTracker()
				self.mem_tracker.print_diff()
				self._checks.append("MemoryLog")
			except Exception as e: print("ERROR", "Cannot load memory tracker:", e)
		self._notify_event("title_update", "PyPlayerTk", self._checks)


	@property
	def arguments(self):
		""" A list with all debug arguments the interpreter was started with """
		return self._checks

	def print_additional_debug(self):
		if "MemoryLog" in self._checks: self.mem_tracker.print_diff()


	def run(self):
		""" Main interpreter execution thread, completely event-driven
		 	All registered handlers are executed in the order they were added """
		print("INFO", "Interpreter thread started")
		while True:
			event, *args = self._queue.get()
			print("INFO", f"Processing event '{event}' with data:", ','.join(args))
			if event is False:
				self._notify_event("destroy")
				return
			else: self._notify_event(event, *args)


	def put_command(self, cmd, callback=None):
		""" Add command to be interpreted, this will be processed as soon as all previous commands have finished processing
			[optional] takes a 'callback' keyword that accepts a function, this will be called (in the interpreter thread) before the regular processing,
				this callback is treated with the same rules as regular command processing callbacks; if it doesn't return anything will continue processing in all modules
		 	This operation uses a multiprocessing.queue and therefore is thread-safe and uses the 'put' operation without wait and therefore will not block """
		if callback and not callable(callback): raise TypeError("Callback must be callable when specified!")
		self._queue.put_nowait(("parse_command", cmd, callback))

	def put_event(self, event_id, *args):
		""" Call all listeners (that are still alive) on specified event id with all given extra keywords
			* Has no effect if the event id is empty or non-existent
			* Any event listeners that can't handle given arguments are not called
			This operation uses a multiprocessing.queue and therefore is thread-safe and uses the 'put' operation without wait and therefore will not block """
		self._queue.put_nowait((event_id, *args))

	def stop(self):
		""" Terminate the interpreter, any commands already queued will still be handled but commands added after this call are ignored
			Once the interpreter has finished the 'on_destroy' method is called that cleans up all loaded modules before it is destroyed
		 	This operation uses a multiprocessing.queue and therefore is thread-safe and uses the 'put' operation without wait and therefore will not block """
		print("INFO", "Received end event, terminating interpreter...")
		self._queue.put_nowait((False,))


	def register_event(self, event_id, callback):
		""" Register listener to specified event id, a new event id will be created if it doesn't exist
			* If the callback was already registered, this call has no effect
			* This object does not increase the reference counter for the callback; if the callback container is destroyed the callback is no longer called
			Returns the callback registered to manually increase the reference count if needed """
		print("INFO", f"Registering callback '{callback.__name__}' for event '{event_id}'")
		if not callable(callback): raise TypeError(f"Event callback for '{event_id}' must be callable!")
		if event_id not in self._events: self._events[event_id] = WeakSet()
		self._events[event_id].add(callback)
		return callback

	def unregister_event(self, event_id, callback):
		""" Remove listener from specified event id, this call has no effect if the event id doesn't exist or the callback was not registered
		 	Returns True if the callback was found and removed, or False otherwise """
		print("INFO", f"Unregistering callback '{callback.__name__}' for event '{event_id}'")
		event_list = self._events.get(event_id)
		if event_list:
			try:
				event_list.remove(callback)
				return True
			except KeyError: pass
		return False

	def _notify_event(self, event_id, *args, **kwargs):
		print("INFO", f"Notifying listeners for the '{event_id}' event")
		event_list = self._events.get(event_id)
		errs = None
		if event_list:
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
				except Exception as e: res = messagetypes.Error(e, "Error parsing command")

				if res is not None and not isinstance(res, messagetypes.Empty):
					op = messagetypes.Error(TypeError(f"Expected a 'messagetype' object, not a '{type(res).__name__}'"), "Invalid response from command")
				else: op = res

			print("INFO", "Got command result:", op)
			if not isinstance(op, messagetypes.Empty): op = messagetypes.Reply("No answer :(")
			self.print_additional_debug()
			self._client.on_reply(*op.get_contents())
		except Exception as e:
			print("ERROR", f"Error processing command '{command}':", e)
			self._client.on_reply(*messagetypes.Error(e, "Error processing command").get_contents())

	def _process_command(self, command):
		print("INFO", f"Processing command '{' '.join(command)}'...")
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
			print("INFO", f"Loading '{md}'...")
			m = importlib.import_module(md)
			m.interpreter = self
			m.client = self._client
			m.platform = self._platform

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
