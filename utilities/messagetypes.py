from traceback import format_exception
import datetime

st = "###"
class Empty():
	""" Base class for console user interaction """
	def __name__(self): return type(self).__name__
	def __str__(self): return self.__name__()
	def get_prefix(self): return "< "
	def get_contents(self): return ()

class Pass(Empty):
	""" Can be used when features are not working yet, while already showing the command exists """
	def get_contents(self): return "Sorry, the elves are still working here, coming soon (TM) to a PyPlayer (TM) near you!", ("reply",)

class Info(Empty):
	""" Used to display information about the syntax of the entered command """
	def __init__(self, message):
		self.date = datetime.datetime.today()
		self.message = message

	def __str__(self): return self.__name__() + st + self.message
	def get_contents(self): return self.get_prefix() + self.date.strftime("[%I:%M %p] ") + self.message, ("info",)

class Reply(Empty):
	""" Display a message to the user about the result of the given command """
	def __init__(self, message):
		self.date = datetime.datetime.today()
		self.message = message

	def __str__(self): return self.__name__() + st + self.message
	def get_contents(self): return self.get_prefix() + self.date.strftime("[%I:%M %p] ") + self.message, ("reply",)

class Question(Empty):
	""" Request more information from the user to process their command without having to re-enter it
	 	The 'callback' is called with the answer from the user (same arguments as a regular command + extra keywords provided)
	 	Use the 'text' argument to give the user an initial suggestion for faster selection """
	def __init__(self, message, callback, text="", **kwargs):
		self.message = message
		self.callback = callback
		self.text = text
		self.kwargs = kwargs

	def __call__(self, cmd): return self.callback(cmd, len(cmd), **self.kwargs)
	def __str__(self): return st.join([self.__name__(), self.message, self.callback.__name__])
	def get_prefix(self): return " ? "
	def get_contents(self): return self.get_prefix() + self.message, ("reply",), self

class Select(Question):
	""" Provide a list of options to let the user choose from, they can either use index or keyword to filter items
		Each request reduces the list, when there is only one left (or zero if no matches) the callback is called with remaining value
		When the list is empty the callback is called with a 'None' value """
	def __init__(self, message, callback, choices, **kwargs):
		Question.__init__(self, message, callback, **kwargs)
		self.choices = choices

	def __call__(self, cmd):
		cmd = " ".join(cmd)
		if len(cmd) == 0: return Reply("Selection aborted")

		try:
			n = int(cmd)
			if 0 <= n < len(self.choices): self.choices = self.choices[n:n+1]
			else: raise ValueError
		except ValueError:
			self.choices = [o for o in self.choices if cmd.lower() in o[0].lower()]

		res = self._callback()
		if res is not None: return res
		else: return self

	def _callback(self):
		if len(self.choices) == 1: return self.callback(*self.choices[0], **self.kwargs)

	def _display_options(self):
		return "\n".join(["  {}. {}".format(i, self.choices[i][0]) for i in range(len(self.choices))])

	def get_contents(self):
		if len(self.choices) > 30: return "< {} options is way too many! Refine your keyword a little".format(len(self.choices)), ("reply",)

		res = self._callback()
		if res is not None: return res.get_contents()
		elif len(self.choices) == 0: return "< Nothing found", ("reply",)
		else: return self.get_prefix() + self.message + "\n" + self._display_options() + "\n < Select item:", ("reply",), self

class Error(Empty):
	""" Show the user that an error occured while processing their command,
		the error's traceback gets printed to log """
	def __init__(self, error, message=""):
		self.message = message
		self.error = error

	def get_prefix(self): return "! "
	def __str__(self): return self.__name__() + st + str(self.error) + st + self.message

	def get_contents(self):
		try: print("ERROR", "\n".join(format_exception(None, self.error, self.error.__traceback__)))
		except: print(self.error, self.message)

		if len(self.message) > 0: return (self.get_prefix() + self.message + ", see log for details"), ("error",)
		else: return self.get_prefix() + str(self.error) + ", see log for details", ("error",)

class URL(Empty):
	""" Return a url as a result of the command that will be opened in the default browser """
	def __init__(self, url):
		self.url = url

	def __str__(self): return self.__name__() + st + self.url

	def get_contents(self):
		import webbrowser
		webbrowser.open(self.url)
		return self.get_prefix() + "URL opened", ("reply",)

def from_str(str):
	str = str.split(st)
	if len(str) > 0:
		try: return globals()[str[0]](*str[1:])
		except: pass
	return Empty()

def from_bytes(bytes):
	return from_str(bytes.decode("UTF-8"))
