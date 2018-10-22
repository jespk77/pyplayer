from ui import pyelement
from utilities import history

input_mark = "mark_input"
class TextConsole(pyelement.PyTextfield):
	current_start = "end-1l linestart+2c"
	current_end = "end lineend-1c"

	_prefixes = {
		"command": "> "
	}

	def __init__(self, root, command_callback=print):
		pyelement.PyTextfield.__init__(self, root)
		self._cmdhistory = history.History()
		self.cmd_cache = ""
		self.cmd_callback = command_callback

		self.bind("<Key>", self.on_key_press).bind("<Button-1>", self.block_action).bind("<B1-Motion>", self.block_action)
		self.bind("<Left>", self.on_left_key).bind("<Up>", lambda event: self.on_set_command_from_history(event, previous=True))
		self.bind("<Down>", lambda event: self.on_set_command_from_history(event, previous=False))
		self.bind("<BackSpace>", self.on_backspace_key).bind("<Return>", self.on_command_confirm)
		self.bind("<Escape>", self.clear_current_line).bind("<Home>", self.on_home_key)
		self.set_prefix()

	def clear_current_line(self, event=None):
		if event is not None: self.last_line = None
		self.current_pos = self.back
		self.delete(self.current_start, self.current_end)
		return self.block_action

	def set_current_line(self, text):
		self.clear_current_line()
		self.insert(self.current_start, text)

	def get_focused(self, event):
		self.focus_set()
		return self.block_action

	def on_command_confirm(self, event):
		self.last_action = "send"
		cmd = self.get(self.current_start, self.current_end)
		if len(cmd) > 0:
			self._cmdhistory.add(cmd)
			self.insert("end", "\n")
			self.configure(state="disabled")
			if self.cmd_callback is not None: self.cmd_callback(cmd)
		return self.block_action

	def on_set_command_from_history(self, event, previous=False):
		self.clear_current_line(event)
		self.insert("end", self._cmdhistory.get_previous(self._cmdhistory.head) if previous else self._cmdhistory.get_next(""))
		self.mark_set("insert", "end")
		return self.block_action

	def set_prefix(self, prefix="command"):
		prefix = self._prefixes.get(prefix, prefix)
		self.insert("end", prefix)
		self.mark_set(input_mark, "insert")
		self.mark_gravity(input_mark, "left")

	def set_reply(self, msg=None, tags=()):
		if not self.can_user_interact():
			if msg is not None: self.insert("end", msg + "\n", tags)
			self.set_prefix()
			self.insert("end", self.cmd_cache)
			self.see("end")
			self.mark_set("insert", "end")
			self.tag_remove("sel", self.front, self.back)
			self.cmd_cache = ""

	def set_notification(self, msg, tags=()):
		self.insert("end-1l linestart", msg + "\n", tags)

	def on_left_key(self, event):
		if self.index("insert") == self.index(input_mark):
			try: self.tag_remove("sel", self.front, self.back)
			except: pass
			return self.block_action

	def on_backspace_key(self, event):
		if self.index("insert") == self.index(input_mark):
			try: self.index("sel.first"), self.index("sel.last")
			except: return self.block_action

	def on_home_key(self, event):
		self.mark_set("insert", self.current_start)
		return self.block_action

	def on_key_press(self, event):
		self.focus_set()
		if not self.accept_input and event.char != "":
			self.cmd_cache += event.char