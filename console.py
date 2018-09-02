from ui import pyelement

class TextConsole(pyelement.PyTextfield):
	current_start = "end-1l linestart+2c"
	current_end = "end lineend-1c"

	def __init__(self, root, command_callback=print):
		pyelement.PyTextfield.__init__(self, root)
		self.cmd_history = []
		self.cmd_history_index = -1
		self.last_action = None
		self.last_line = None
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
			try: self.cmd_history.remove(cmd)
			except Exception: pass

			self.cmd_history.append(cmd)
			self.cmd_history_index = len(self.cmd_history) - 1
			self.insert("end", "\n")
			self.configure(state="disabled")
			if self.cmd_callback is not None: self.cmd_callback(cmd)
		return self.block_action

	def on_set_command_from_history(self, event):
		last_index = len(self.cmd_history) - 1
		if last_index >= 0:
			self.mark_set("insert", "end")
			if event.keysym == "Up":
				if self.last_line is None: self.last_line = self.get(self.current_start, self.current_end)
				if self.last_action == "down" and self.cmd_history_index > 0: self.cmd_history_index -= 1
				self.set_current_line(self.cmd_history[self.cmd_history_index])
				if self.cmd_history_index > 0: self.cmd_history_index -= 1; self.last_action = "up-move"
				else: self.last_action = "up"
			elif event.keysym == "Down":
				if self.last_action == "up-move" and self.cmd_history_index < last_index: self.cmd_history_index += 1
				if self.cmd_history_index < last_index:
					self.cmd_history_index += 1
					self.set_current_line(self.cmd_history[self.cmd_history_index])
				elif self.last_line is not None:
					self.cmd_history_index += 1
					self.set_current_line(self.last_line)
					self.last_line = None
				self.last_action = "down"
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
			try: self.selection_get()
			except: return self.block_action

	def on_home_key(self, event):
		self.mark_set("insert", self.current_start)
		return self.block_action

	def on_key_press(self, event):
		self.focus_set()
		if self.cget("state") == "disabled" and event.char != "":
			self.cmd_cache += event.char