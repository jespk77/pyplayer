from threading import Thread
from multiprocessing import Queue
import os, importlib, sys

from utilities import messagetypes

class Interpreter(Thread):
	""" Process commands from modules defined in the modules package
		Each module contains:
			'interpreter': a reference to this instance (only for reading/command queue access)
			'client': a reference to the main window of the client
			'platform': a string that defines the platform the program is run on

		Each module can define:
			'initialize()': [optional] gets called whenever the module is imported/reloaded
			'on_destoy()': [optional] gets called before the client is shut down or a module gets reloaded, use to clean up any previously created data/references
			'priority: int': this defines the order in which a command gets processed by modules, the module with the highest priority (lowest value) get called first, when a module returns a 'messagetype' further processing is stopped
			'commands: dict': defines the commands this module can process, if not defined this module will not receive any commands
				Notes:
					- each command callback receives two argument, the remaining command and the number of words of this command
					- use "" for default commands and "info" to display help messages, the top level cannot have a default command
					- after processing a command the module must return an instance of 'messagetypes', if nothing is returned the interpreter will continue to next module
	"""
	def __init__(self, client):
		super().__init__(name="PyInterpreterThread")
		self._client = client
		self._queue = Queue()
		self._configuration = None
		self._checks = []
		self._platform = sys.platform
		self._set_sys_arg()

		self._modules = []
		for module in [f for f in os.listdir("modules") if f.endswith(".py")]:
			r = self._load_module(module)
			if isinstance(r, messagetypes.Error): client.add_message(r.get_contents())
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
		self._client.update_title("PyPlayerTk", self._checks)

	@property
	def arguments(self): return self._checks

	def print_additional_debug(self):
		if "MemoryLog" in self._checks: self.mem_tracker.print_diff()

	def run(self):
		while True:
			cmd = self._queue.get()
			if cmd is False or len(cmd) == 0:
				self.on_destroy()
				break

			cmd = cmd.split(" ")
			op = None
			self.print_additional_debug()
			if cmd[0] == "reload": op = self._load_module(" ".join(cmd[1:]))

			if op is None:
				try: res = self._parse_cmd(cmd)
				except Exception as e: res = messagetypes.Error(e, "Error parsing command")

				if res is not None and not isinstance(res, messagetypes.Empty):
					op = messagetypes.Error(TypeError("Expected a 'messagetype' object here, not a '{}'".format(type(res).__name__)), "Invalid response from command")
				else: op = res

			if op is False: op = messagetypes.Reply("Invalid command")
			elif not isinstance(op, messagetypes.Empty): op = messagetypes.Reply("No answer :(")
			self.print_additional_debug()
			self._client.add_reply(args=op.get_contents())

	def put_command(self, cmd):
		self._queue.put_nowait(str(cmd))

	def stop_command(self):
		self._queue.put_nowait(False)

	def _parse_cmd(self, cmd):
		for md in self._modules:
			try: cl = md.commands
			except AttributeError:
				print("WARNING", "Module '{}' does not have a 'commands' dictionary, this is most likely not intended...")
				continue

			if "" in cl: raise TypeError("Module '" + md.__name__ + "' contains a default command, this is not allowed in the top level")
			while isinstance(cl, dict):
				if len(cmd) == 0: break
				c = cl.get(cmd[0])
				if c is not None: cl = c
				else: break
				cmd = cmd[1:]

			if isinstance(cl, dict): cl = cl.get("")
			if cl is not None: return cl(cmd, len(cmd))

	def _load_module(self, md):
		if not md.startswith("modules."): md = "modules." + md
		if md.endswith(".py"): md = md[:-3]

		print("INFO", "Searching for module '{}' for (re)load".format(md))
		for m in self._modules:
			if m.__name__ == md:
				print("INFO", "Found existing module, reloading...")
				prev_priority = m.priority
				try: m.on_destroy()
				except AttributeError as a:
					if not "on_destroy" in str(a): print("ERROR", "Couldn't close module '{}' properly: ".format(m.__name__), a)
				except Exception as e: print("ERROR", "Couldn't close module '{}' properly: ".format(m.__name__), e)

				try:
					importlib.reload(m)
					if prev_priority != m.priority: print("WARNING", "Priority has changed on reload, this change will not take effect unless the program is restarted")
					m.interpreter = self
					m.client = self._client
					m.platform = self._platform
				except Exception as e: return messagetypes.Error(e, "Failed to load module '{}'".format(m.__name__))

				try: m.initialize()
				except AttributeError as a:
					if not "initialize" in str(a): raise a
				except Exception as e: return messagetypes.Error(e, "Failed to initialize module '{}'".format(m.__name__))
				return messagetypes.Reply("Successfully reloaded module '{}'".format(m.__name__))

		print("INFO", "No module found, trying to import as new module")
		try:
			m = importlib.import_module(md)
			m.interpreter = self
			m.client = self._client
			m.platform = self._platform
			try: m.initialize()
			except AttributeError as a:
				if "initialize" not in str(a): raise a
			except Exception as e: return messagetypes.Error(e, "Failed to initialize module '{}'".format(md))
			self._modules.append(m)
			self._modules = sorted(self._modules, key= lambda me: me.priority)
			return messagetypes.Reply("Module successfully loaded")
		except Exception as e: return messagetypes.Error(e, "Failed to import module '{}'".format(md))

	def on_destroy(self):
		for module in self._modules:
			try: module.on_destroy()
			except AttributeError: pass
			except Exception as e: print("ERROR", "Couldn't close module '{}' properly:".format(module.__name__), e)
