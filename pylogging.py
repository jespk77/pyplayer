import builtins, datetime, enum, inspect, os, sys

class PyLogLevel(enum.Enum):
	""" Defines the importance of the log message
			when the logger is set to a level, all messages that are below that level are omitted """
	INFO = 0
	WARNING = 1
	ERROR = 2
	NDEFINE = 5
	MESSAGE = 99

	@staticmethod
	def from_arg(level):
		""" Get appropriate enum level safely, providing the 'NDEFINE' value when level cannot be found """
		if isinstance(level, PyLogLevel): return level
		try: level = level.upper()
		except: pass

		try: return PyLogLevel[level]
		except: return PyLogLevel.NDEFINE

	def is_match(self, level):
		""" Returns True if the passed level is equal or greater importance and should be displayed in the log """
		return self.value <= PyLogLevel.from_arg(level).value

	def __str__(self): return self.name

file_format = "logs\pylog_{}{}.log"
class PyLog:
	def __init__(self, log_to_file=True):
		self._level = PyLogLevel.INFO
		if not os.path.isdir("logs"): os.mkdir("logs")

		date_str = datetime.datetime.today().strftime("%y-%m-%d")
		if log_to_file:
			self._file = None
			attempts = 0
			while self._file is None:
				self._filename = file_format.format(date_str, ("_{:02}".format(attempts) if attempts > 0 else ""))
				try: self._file = open(self._filename, "x")
				except FileExistsError: attempts += 1
			sys.stdout = self
		else:
			self._filename = None
			self._file = None

		self._prev_print = builtins.print
		builtins.print = self.print_log
		print("MESSAGE", "Pyplayer log", str(date_str))

	def __del__(self):
		self.on_destroy()
		builtins.print = self._prev_print

	@property
	def log_level(self): return self._level
	@log_level.setter
	def log_level(self, value): self._level = PyLogLevel.from_arg(value)
	@property
	def filename(self): return self._filename

	@staticmethod
	def _get_class_from_stack(stack):
		return stack[0].f_locals["self"].__class__.__name__

	@staticmethod
	def _get_traceback_string(level):
		try:
			stack = inspect.stack()[2]
			try: return "[{}.{}.{}]".format(PyLog._get_class_from_stack(stack), stack.function, PyLogLevel.from_arg(str(level)))
			except KeyError: return "[{}.{}.{}]".format("/".join(stack.filename.split("/")[-3:]), stack.function, PyLogLevel.from_arg(level))
		except Exception as e: return "[<{}>.{}]".format(e, level)

	def print_log(self, *objects, sep=" ", end="\n", file=None, flush=True):
		level = objects[0] if len(objects) > 0 else PyLogLevel.NDEFINE
		l = PyLogLevel.from_arg(level)
		if l != PyLogLevel.NDEFINE: objects = objects[1:]

		if self._level.is_match(level):
			return self._prev_print(datetime.datetime.today().strftime("[%H:%M:%S]"), PyLog._get_traceback_string(level), *objects,
									sep=sep, end=end, file=file, flush=flush)
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

logger = None
def get_logger():
	global logger
	if logger is None: logger = PyLog(log_to_file="console" not in sys.argv)
	return logger

def open_logfile(file=None):
	if not file: file = get_logger().filename
	else: file = "logs\{}.log".format(file)
	if not file or not os.path.isfile(file): raise FileNotFoundError("'{}' is not a file".format(file))
	import webbrowser
	return webbrowser.open(file)