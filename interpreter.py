from threading import Thread
from multiprocessing import Queue
import os, importlib, sys

from utilities import messagetypes

class Interpreter(Thread):
	""" Process commands from modules defined in the modules package
		Each module contains:
			'interpreter': a reference to this instance (only for reading/command queue access)
			'client': a reference to the main window of the client

		Each module can define:
			'initialize()': [optional] gets called whenever the module is imported/reloaded
			'set_configuration(cfg: dict)': [optional] gets called whenever the client configuration is updated
			'on_destoy()': [optional] gets called before the client is shut down or a module gets reloaded, use to clean up any previously created data/references
			'priority: int': this defines the order in which a command gets processed by modules, the module with the highest priority (lowest value) get called first, when a module returns a 'messagetype' further processing is stopped
			'commands: dict': defines the commands this module can process, if not defined this module will not receive any commands
				Notes:
					- each command callback receives two argument, the remaining command and the number of words of this command
					- use "" for default commands and "info" to display help messages, the top level cannot have a default command
					- after processing a command the module must return an instance of 'messagetypes', if nothing is returned the interpreter will continue to next module
	"""
	def __init__(self, client):
		super().__init__(name="InterpreterThread")
		self.client = client
		self.modules = sorted([ importlib.import_module(name="modules." + module[:-3]) for module in os.listdir("modules") if module.endswith(".py") ], key=lambda module: module.priority)
		self.queue = Queue()
		self.configuration = None
		self.checks = []
		self.set_sys_arg()
		for md in self.modules:
			try:
				md.interpreter = self
				md.client = self.client
				md.initialize()
			except AttributeError: pass
			except Exception as e: self.client.add_message(args=messagetypes.Error(e, "Error initializing '" + md.__name__ + "'").get_contents())
		self.start()

	def set_sys_arg(self):
		if "console" in sys.argv: self.checks.append("ConsoleLog")

		if "memory" in sys.argv:
			print("memory checks enabled")
			try:
				from pympler import tracker
				self.mem_tracker = tracker.SummaryTracker()
				self.mem_tracker.print_diff()
				self.checks.append("MemoryLog")
			except Exception as e:
				print("error getting memory tracker:", e)
		self.client.update_title("PyPlayerTk", self.checks)
	def print_additional_debug(self):
		if "MemoryLog" in self.checks: self.mem_tracker.print_diff()

	def run(self):
		while True:
			cmd = self.queue.get()
			if cmd is False or len(cmd) == 0:
				self.on_destroy()
				break

			cmd = cmd.split(" ")
			op = None
			self.print_additional_debug()
			if cmd[0] == "reload": op = self.reload_module(" ".join(cmd[1:]))
			if op is None:
				res = None
				try: res = self.parse_cmd(cmd)
				except Exception as e: res = messagetypes.Error(e, "Error parsing command")

				if res is not None and not isinstance(res, messagetypes.Empty):
					op = messagetypes.Error(TypeError("expected a 'messagetype' object here, not the " + str(type(res)) + " that you're giving me!"), "Invalid response from command")
				else: op = res

			if op is None: op = messagetypes.Reply("No answer :(").get_contents()
			elif op is False: op = messagetypes.Reply("Invalid command").get_contents()
			else: op = op.get_contents()
			self.print_additional_debug()
			self.client.add_reply(args=op)

	def parse_cmd(self, cmd):
		for md in self.modules:
			try: cl = md.commands
			except AttributeError: continue

			if "" in cl: raise TypeError("module '" + md.__name__ + "' contains a default command, this is not allowed in the top level")
			while isinstance(cl, dict):
				if len(cmd) == 0: break
				c = cl.get(cmd[0])
				if c is not None: cl = c
				else: break
				cmd = cmd[1:]

			if isinstance(cl, dict): cl = cl.get("", None)

			if cl is not None: return cl(cmd, len(cmd))

	def reload_module(self, module):
		md_list = []
		dirty = False
		for md in self.modules:
			if module == md.__name__.split(".")[-1]:
				try: md.on_destroy()
				except AttributeError: pass
				except Exception as e: print("[Interpreter] error cleaning up module '{!s}':".format(md), e)

				try: importlib.reload(md)
				except Exception as e: return messagetypes.Error(e, "Error reloading '" + module + "'")

				md_list.append(md)
				md.interpreter = self; md.client = self.client;
				try: md.initialize()
				except AttributeError: pass
				except Exception as e: return messagetypes.Error(e, "Error initializing module '" + str(md) + "'")

				try: md.set_configuration(self.configuration)
				except AttributeError: pass
				except Exception as e: return messagetypes.Error(e, "Error updating configuration")
				dirty = True
			else: md_list.append(md)

		if not dirty:
			try:
				lib = importlib.import_module("modules." + module)
				try: lib.interpreter = self; lib.client = self.client; lib.initialize()
				except AttributeError: pass
				md_list.append(lib)
			except Exception as e: return messagetypes.Error(e, "Error importing module '" + module + "'")

		self.modules = sorted([ module for module in md_list ], key=lambda module: module.priority)
		return messagetypes.Reply("Module '" + module + "' reloaded (all related settings were reset)")

	def on_destroy(self):
		for module in self.modules:
			try: module.on_destroy()
			except: pass
