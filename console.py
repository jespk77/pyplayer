from ui import pyelement
from utilities import history

class TextConsole(pyelement.PyTextfield):
	current_start = "end-1l linestart+2c"
	current_end = "end lineend-1c"

	def __init__(self, root, command_callback=print):
		pyelement.PyTextfield.__init__(self, root)
		self._cmdhistory = history.History()
		self.cmd_cache = ""
		self.cmd_callback = command_callback

		self.bind("<Key>", self.on_key_press).bind("<Button-1>", self.block_action).bind("<B1-Motion>", self.block_action)
		self.bind("<BackSpace>", self.on_backspace_key).bind("<Return>", self.on_command_confirm).bind("<Escape>", self.clear_current_line).bind("<Home>", self.on_home_key)
		self.bind("<Left>", self.on_left_key).bind("<Up>", self.on_set_command_from_history).bind("<Down>", self.on_set_command_from_history)
		self.insert("end", "> ")

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

	def on_set_command_from_history(self, event):
		if event.keysym == "Up":
			cmd = self._cmdhistory.get_previous(self._cmdhistory.head)
		elif event.keysym == "Down":
			cmd = self._cmdhistory.get_next()
		else: cmd = None

		self.clear_current_line(event)
		if not cmd is None: self.insert("end", cmd)
		self.mark_set("insert", "end")
		return self.block_action

	def set_reply(self, msg=None, tags=()):
		if not self.can_user_interact():
			if msg is not None: self.insert("end", msg + "\n", tags)
			self.insert("end", "> " + self.cmd_cache)
			self.see("end")
			self.mark_set("insert", "end")
			self.tag_remove("sel", "0.0", "end")
			self.cmd_cache = ""

	def set_notification(self, msg, tags=()):
		self.insert("end-1l linestart", msg + "\n", tags)

	def on_left_key(self, event):
		if str(self.index("insert")).endswith(".2"):
			return self.block_action

	def on_backspace_key(self, event):
		if str(self.index("insert")).endswith(".2"):
			try: self.index("sel.first"), self.index("sel.last")
			except: return self.block_action

	def on_home_key(self, event):
		self.mark_set("insert", self.current_start)
		return self.block_action

	def on_key_press(self, event):
		self.focus_set()
		if self.cget("state") == "disabled" and event.char != "":
			self.cmd_cache += event.char