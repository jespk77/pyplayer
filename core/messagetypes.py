import datetime
from traceback import format_exception

st = "###"
class Empty():
	""" Base class for console user interaction, can be used to finish given command without specifying a reply message """
	def __str__(self): return "{}{}".format(type(self).__name__, ["{}={}".format(k,v) for k,v in self.__dict__.items() if not k.startswith("__")])
	def get_prefix(self): return "< "
	def get_contents(self): return self.get_prefix() + "Command processed (but no reply added)", ("reply",)

class Pass(Empty):
	""" Can be used when features are not working yet, while already showing the command exists """
	def get_contents(self): return "Sorry, the elves are still working here, coming soon (TM) to a PyPlayer (TM) near you!", ("reply",)

class Info(Empty):
	""" Used to display information about the syntax of the entered command """
	def __init__(self, message):
		self._date = datetime.datetime.today()
		self._message = message
	def get_contents(self): return self.get_prefix() + self._date.strftime("[%I:%M %p] ") + self._message, ("info",)

class Reply(Empty):
	""" Display a message to the user about the result of the given command """
	def __init__(self, message):
		self._date = datetime.datetime.today()
		self._message = message
	def get_contents(self): return self.get_prefix() + self._date.strftime("[%I:%M %p] ") + self._message, ("reply",)

class Question(Empty):
	""" Request more information from the user to process their command without having to re-enter it
	 	The 'callback' is called with the answer from the user (same arguments as a regular command + extra keywords provided)
	 	Use the 'text' argument to give the user an initial suggestion for faster selection """
	def __init__(self, message, callback, text="", **kwargs):
		self._message = message
		self._callback = callback
		self._text = text
		self._kwargs = kwargs

	def __call__(self, cmd): return self._callback(cmd, len(cmd), **self._kwargs)
	def get_prefix(self): return " ? "
	def get_contents(self): return self.get_prefix() + self._message, ("reply",), self, " - ", self._text

class Select(Question):
	""" Provide a list of options to let the user choose from, they can either use index or keyword to filter items
		Each request reduces the list, when there is only one left (or zero if no matches) the callback is called with remaining value
		When the list is empty the callback is called with a 'None' value """
	def __init__(self, message, callback, choices, **kwargs):
		Question.__init__(self, message, callback, **kwargs)
		self._choices = choices

	def __call__(self, cmd):
		cmd = " ".join(cmd)
		if len(cmd) == 0: return Reply("Selection aborted")

		try:
			n = int(cmd)
			if 0 <= n < len(self._choices): self._choices = self._choices[n:n+1]
			else: raise ValueError
		except ValueError:
			self._choices = [o for o in self._choices if cmd.lower() in o[0].lower()]

		res = self._execute_callback()
		if res is not None: return res
		else: return self

	def _execute_callback(self):
		if len(self._choices) == 1: return self._callback(*self._choices[0], **self._kwargs)

	def _display_options(self):
		return "\n".join(["  {}. {}".format(i, self._choices[i][0]) for i in range(len(self._choices))])

	def get_contents(self):
		if len(self._choices) > 30: return "< {} options is way too many! Refine your keyword a little".format(len(self._choices)), ("reply",)

		res = self._execute_callback()
		if res is not None: return res.get_contents()
		elif len(self._choices) == 0: return "< Nothing found", ("reply",)
		else: return self.get_prefix() + self._message + "\n" + self._display_options() + "\n < Select item:", ("reply",), self, " - ", self._text

class Error(Empty):
	""" Show the user that an error occured while processing their command,
		the error's traceback gets printed to log """
	def __init__(self, error, message=""):
		self._message = message
		self._error = error

	def get_prefix(self): return "! "
	def get_contents(self):
		if len(self._message) > 0:
			print("ERROR", self._message, self._error)
			return (self.get_prefix() + self._message + ", see log for details"), ("error",)
		else:
			print("ERROR", "Executing command raised an exception", self._error)
			self.get_prefix() + str(self._error) + ", see log for details", ("error",)

class URL(Empty):
	""" Return a url as a result of the command that will be opened in the default browser """
	def __init__(self, url, message=None):
		self._url = url
		self._msg = message if message else "URL opened"

	def get_contents(self):
		import webbrowser
		webbrowser.open(self._url)
		return self.get_prefix() + self._msg, ("reply",)

def from_str(str):
	str = str.split(st)
	if len(str) > 0:
		try: return globals()[str[0]](*str[1:])
		except: pass
	return Empty()

def from_bytes(bytes):
	return from_str(bytes.decode("UTF-8"))
