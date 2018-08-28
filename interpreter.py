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
		self._modules = []
		self._load_modules()
		self._queue = Queue()
		self._configuration = None
		self._checks = []
		self._platform = sys.platform
		self._set_sys_arg()
		for md in self._modules:
			md.interpreter = self
			md.client = self._client
			md.platform = self._platform
			try: md.initialize()
			except AttributeError: pass
			except Exception as e: self._client.add_message(args=messagetypes.Error(e, "Error initializing '" + md.__name__ + "'").get_contents())
		self.start()

	def _set_sys_arg(self):
		if "console" in sys.argv: self._checks.append("ConsoleLog")

		if "memory" in sys.argv:
			print("[Interpreter.INFO] Memory logging enabled")
			try:
				from pympler import tracker
				self.mem_tracker = tracker.SummaryTracker()
				self.mem_tracker.print_diff()
				self._checks.append("MemoryLog")
			except Exception as e: print("[Interpreter.ERROR] Cannot load memory tracker:", e)
		self._client.update_title("PyPlayerTk", self._checks)

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
			if cmd[0] == "reload": op = self._reload_module(" ".join(cmd[1:]))

			if op is None:
				try: res = self._parse_cmd(cmd)
				except Exception as e: res = messagetypes.Error(e, "Error parsing command")

				if res is not None and not isinstance(res, messagetypes.Empty):
					op = messagetypes.Error(TypeError("Expected a 'messagetype' object here, not a '{}'".format(type(res).__name__)), "Invalid response from command")
				else: op = res

			if op is None: op = messagetypes.Reply("No answer :(").get_contents()
			elif op is False: op = messagetypes.Reply("Invalid command").get_contents()
			else: op = op.get_contents()
			self.print_additional_debug()
			self._client.add_reply(args=op)

	def put_command(self, cmd):
		self._queue.put_nowait(str(cmd))

	def stop_command(self):
		self._queue.put_nowait(False)

	def _parse_cmd(self, cmd):
		for md in self._modules:
			try: cl = md.commands
			except AttributeError: continue

			if "" in cl: raise TypeError("Module '" + md.__name__ + "' contains a default command, this is not allowed in the top level")
			while isinstance(cl, dict):
				if len(cmd) == 0: break
				c = cl.get(cmd[0])
				if c is not None: cl = c
				else: break
				cmd = cmd[1:]

			if isinstance(cl, dict): cl = cl.get("")
			if cl is not None: return cl(cmd, len(cmd))

	def _load_modules(self):
		modules = []
		for file in os.listdir("modules"):
			if file.endswith(".py"):
				fl = open("modules/" + file, "r")
				header = fl.readline(0)
				if header.startswith("#") and self._platform != header[1:]: continue
				fl.close()

				try:
					md = importlib.import_module("modules." + file[:-3])
					modules.append(md)
				except Exception as e: print("[Interpreter.ERROR] Error importing module '{}':".format(file), e)

		self._modules = sorted(modules, key=lambda md: md.priority)

	def _reload_module(self, module):
		md_list = []
		dirty = False
		for md in self._modules:
			if "modules." + module == md.__name__:
				try: md.on_destroy()
				except AttributeError: pass
				except Exception as e: print("[Interpreter.ERROR] Cleaning up module '{}':".format(md), e)

				try: importlib.reload(md)
				except Exception as e: return messagetypes.Error(e, "Error reloading '" + module + "'")

				md_list.append(md)
				md.interpreter = self
				md.client = self._client
				try: md.initialize()
				except AttributeError: pass
				except Exception as e: return messagetypes.Error(e, "Error initializing module '" + str(md) + "'")
				dirty = True
			else: md_list.append(md)

		if not dirty:
			try: lib = importlib.import_module("modules." + module)
			except Exception as e: return messagetypes.Error(e, "Error importing module '" + module + "'")

			lib.interpreter = self
			lib.client = self._client
			try: lib.initialize()
			except AttributeError: pass
			except Exception as e: return messagetypes.Error(e, "Error initializing module '{}'".format(module))
			md_list.append(lib)

		self._modules = sorted([ module for module in md_list ], key=lambda module: module.priority)
		return messagetypes.Reply("Module '" + module + "' reloaded (all related settings were reset)")

	def on_destroy(self):
		for module in self._modules:
			try: module.on_destroy()
			except: pass
