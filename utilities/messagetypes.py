from traceback import format_exception
import datetime

st = "###"
class Empty():
	""" Base class for console user interaction """
	def __str__(self): return "Empty"
	def get_prefix(self): return "< "
	def get_contents(self): return ()

class Pass(Empty):
	""" Can be used when features are not working yet, while already showing the command exists """
	def __str__(self): return "Pass"
	def get_contents(self): return "Sorry, the elves are still working here, coming soon (TM) to a PyPlayer (TM) near you!", ("reply",)

class Info(Empty):
	""" Used to display information about the syntax of the entered command """
	def __init__(self, message):
		self.date = datetime.datetime.today()
		self.message = message

	def __str__(self): return "Info" + st + self.message
	def get_contents(self): return self.get_prefix() + self.date.strftime("[%I:%M %p] ") + self.message, ("info",)

class Reply(Empty):
	""" Display a message to the user about the result of the given command """
	def __init__(self, message):
		self.date = datetime.datetime.today()
		self.message = message

	def __str__(self): return "Reply" + st + self.message
	def get_contents(self): return self.get_prefix() + self.date.strftime("[%I:%M %p] ") + self.message, ("reply",)

class Question(Empty):
	""" Request more information from the user to process their command without having to re-enter it
	 	(WORK IN PROGRESS: class structure might change) """
	def __init__(self, message, callback, text="", **kwargs):
		self.message = message
		self.callback = callback
		self.text = text
		self.kwargs = kwargs

	def __call__(self, cmd): return self.callback(cmd, len(cmd), **self.kwargs)
	def __str__(self): return st.join(["Question", self.message, self.callback.__name__])
	def get_prefix(self): return " ? "
	def get_contents(self): return self.get_prefix() + self.message, ("reply",), self

class Error(Empty):
	""" Show the user that an error occured while processing their command,
		the error's traceback gets printed to log """
	def __init__(self, error, message=""):
		self.message = message
		self.error = error

	def get_prefix(self): return "! "
	def __str__(self): return "Error" + st + str(self.error) + st + self.message

	def get_contents(self):
		try: print("\n".join(format_exception(None, self.error, self.error.__traceback__)))
		except: print(self.error, self.message)

		if len(self.message) > 0: return (self.get_prefix() + self.message + ", see log for details"), ("error",)
		else: return self.get_prefix() + str(self.error) + ", see log for details", ("error",)

class URL(Empty):
	""" Return a url as a result of the command that will be opened in the default browser """
	def __init__(self, url):
		self.url = url

	def __str__(self): return "URL" + st + self.url

	def get_contents(self):
		import webbrowser
		webbrowser.open(self.url)

def from_str(str):
	str = str.split(st)
	if len(str) > 0:
		try: return globals()[str[0]](*str[1:])
		except: pass
	return Empty()

def from_bytes(bytes):
	return from_str(bytes.decode("UTF-8"))
