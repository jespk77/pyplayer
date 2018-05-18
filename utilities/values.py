pair_separator = "::"
class Value:
	def __str__(self):
		return str(self.get_value())

	def get_value(self):
		raise TypeError("tried to get value of none type")
		
class ValueStr(Value):
	def __init__(self, s):
		self.s = str(s)
		
	def __str__(self):
		return "'" + self.s + "'"
	
	def get_value(self):
		return self.s
		
class ValueEntry(Value):
	def __init__(self, id, value):
		self.id = str(id)
		self.value = parse(value)
		
	def __str__(self):
		return "'" + self.id + "': " + self.value.__str__()
		
	def get_value(self):
		return { self.id: self.value.get_value() }
		
def parse(arg):
	pair = arg.split(pair_separator, maxsplit=1)
	if len(pair) == 2:
		try: return ValueEntry(pair[0], pair[1])
		except: pass
	return ValueStr(arg)