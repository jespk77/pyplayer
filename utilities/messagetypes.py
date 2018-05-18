from traceback import format_exception
import webbrowser

st = "###"
class Empty():
	def __init__(self):
		pass
		
	def __str__(self):
		return "Empty"
		
	def get_prefix(self):
		return "< "
		
	def get_contents(self):
		pass
		
class Pass(Empty):
	def __str__(self):
		return "Pass"
		
	def get_contents(self):
		return ("Sorry, the elves are still working here, coming soon (TM) to a PyPlayer (TM) near you!", ("reply",))

class Info(Empty):
	def __init__(self, message):
		self.message = message
		
	def __str__(self):
		return "Info" + st + self.message
		
	def get_contents(self):
		return (self.get_prefix() + self.message, ("info",))

class Reply(Empty):
	def __init__(self, message):
		self.message = message
		
	def __str__(self):
		return "Reply" + st + self.message
		
	def get_contents(self):
		return (self.get_prefix() + self.message, ("reply",))
		
class Error(Empty):
	def __init__(self, error, message=""):
		self.message = message
		self.error = error
		
	def get_prefix(self):
		return "!"
		
	def __str__(self):
		return "Error" + st + str(self.error) + st + self.message
		
	def get_contents(self):
		try: print("\n".join(format_exception(None, self.error, self.error.__traceback__)))
		except: print(self.error, self.message)
		
		if len(self.message) > 0: return ((self.get_prefix() + self.message + ", see log for details"), ("error",))
		else: return (self.get_prefix() + str(self.error) + ", see log for details", ("error",))
		
class URL(Empty):
	def __init__(self, url):
		self.url = url
		
	def __str__(self):
		return "URL" + st + self.url
		
	def get_contents(self):
		webbrowser.open(self.url)
		
def from_str(str):
	str = str.split(st)
	if len(str) > 0:
		try: return globals()[str[0]](*str[1:])
		except: pass
	return Empty()
	
def from_bytes(bytes):
	return from_str(bytes.decode("UTF-8"))
	