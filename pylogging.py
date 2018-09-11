import builtins, datetime, enum, inspect, os, sys

class PyLogLevel(enum.Enum):
	""" Defines the importance of the log message
			when the logger is set to a level, all messages that are below that level are omitted """
	INFO = 0
	WARNING = 1
	NDEFINE = 1
	ERROR = 2
	MESSAGE = 99

	@staticmethod
	def from_arg(level):
		""" Get appropriate enum level safely, providing the 'NDEFINE' value when level cannot be found """
		if isinstance(level, PyLogLevel): return level

		try: return PyLogLevel[level]
		except: return PyLogLevel.NDEFINE

	def is_match(self, level):
		""" Returns True if the passed level is equal or greater importance and should be displayed in the log """
		return self.value <= PyLogLevel.from_arg(level).value

	def __str__(self): return self.name

class PyLog:
	def __init__(self, log_level="WARNING", log_to_file=True):
		self._level = PyLogLevel.from_arg(log_level)
		if not os.path.isdir("logs"): os.mkdir("logs")

		today = datetime.datetime.today()
		if log_to_file:
			self._filename = "logs/pylog_{}".format(today.strftime("%y-%m-%d"))
			self._file = None
			attempts = 0
			while self._file is None:
				if attempts > 20: raise RuntimeError("PyLog: too many attempts to create log file")
				fname = self._filename + "_" + str(attempts) if attempts > 0 else self._filename
				try:
					self._file = open(fname, "x")
					self._filename = fname
				except FileExistsError: attempts += 1
			sys.stdout = self
		else:
			self._filename = None
			self._file = None

		self._prev_print = builtins.print
		builtins.print = self.print_log
		print("MESSAGE", "Pyplayer log", str(today))

	def __del__(self):
		self.on_destroy()
		builtins.print = self._prev_print

	@staticmethod
	def _get_class_from_stack(stack):
		return stack[0].f_locals["self"].__class__.__name__

	@staticmethod
	def _get_traceback_string(level):
		try:
			stack = inspect.stack()[2]
			try: return "[{}.{}.{}]".format(PyLog._get_class_from_stack(stack), stack.function, str(level))
			except KeyError: return "[__main__.{}]".format(level)
		except Exception as e: return "[<{}>.{}]".format(e, level)

	def print_log(self, *objects, sep=" ", end="\n", file=None, flush=True):
		level = objects[0] if len(objects) > 0 else PyLogLevel.NDEFINE
		l = PyLogLevel.from_arg(level)
		if l != PyLogLevel.NDEFINE: objects = objects[1:]

		if self._level.is_match(level): return self._prev_print(PyLog._get_traceback_string(level), *objects, sep=sep, end=end, file=file, flush=flush)
		return False

	def write(self, str):
		if self._file is not None:
			self._file.write(str)
			self.flush()
		else: sys.__stdout__.write(str)

	def flush(self):
		if self._file is not None:
			if not self._file.closed: self._file.flush()
		else: sys.__stdout__.flush()

	def on_destroy(self):
		if self._file is not None:
			self._file.close()

def intialize_logging(level="WARNING"):
	sys.stdout = PyLog(level)

def destroy_logging():
	try: sys.stdout.on_destroy()
	except AttributeError: pass