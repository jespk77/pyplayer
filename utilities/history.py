class History():
	def __init__(self, max_size=-1):
		self.max_size = max_size
		self.history = []
		self.index = -1
		
	def add(self, element):
		try: self.history.remove(element)
		except: pass
		self.history.append(element)
		self.reset_index()
		
	def get(self, move_index=True):
		if len(self.history) > 0:
			res = self.history[self.index]
			if move_index and self.index > 0: self.index -= 1
			return res
		else: return None
			
	def reset_index(self):
		self.index = len(self.history) - 1