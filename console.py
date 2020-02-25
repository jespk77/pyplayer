from ui.tk_legacy import pyelement
from utilities import history

input_mark = "mark_input"
class TextConsole(pyelement.PyTextfield):
	current_end = "end lineend-1c"

	def __init__(self, container, initial_cfg=None):
		pyelement.PyTextfield.__init__(self, container, "console", initial_cfg)
		self.accept_input = False
		self._cmdhistory = history.History()
		self._cmd_cache = ""
		self._question = None

		@self.event_handler.KeyEvent("all")
		def on_key_press(char):
			if not self.accept_input and char != "":
				self._cmd_cache += char

		@self.event_handler.MouseClickEvent("left")
		def _block_action(): return self.event_handler.block

		@self.event_handler.KeyEvent("left")
		def on_left_key():
			if self.position("insert") == self.position(input_mark):
				self.clear_selection()
				return self.event_handler.block

		@self.event_handler.KeyEvent("backspace")
		def on_backspace_key():
			if self.position("insert") == self.position(input_mark):
				try: self.position("sel.first"), self.position("sel.last")
				except: return self.event_handler.block

		@self.event_handler.KeyEvent("home")
		def on_home_key():
			self.cursor = input_mark
			return self.event_handler.block

		@self.event_handler.KeyEvent("escape")
		def _on_escape_key():
			self.set_current_line("")
			return self.event_handler.block

		@self.event_handler.KeyEvent("enter")
		def _on_enter_key():
			cmd = self.get_current_line()
			if len(cmd) > 0:
				self.insert(self.back, "\n")
				self._cmdhistory.add(cmd)
				self.accept_input = False
		self.add_reply(" -PyPlayer ready-", tags=("reply",))

		@self.event_handler.KeyEvent("up")
		def _on_previous_history():
			self.set_current_line(self._cmdhistory.get_previous())
			return self.event_handler.block

		@self.event_handler.KeyEvent("down")
		def _on_next_history():
			self.set_current_line(self._cmdhistory.get_next(""))
			return self.event_handler.block

	def get_current_line(self):
		""" Get the text on the current line """
		return self.get_text(input_mark, self.current_end)
	def set_current_line(self, text=""):
		""" Update the text on the current line, has no effect if called with none """
		if text is not None:
			self.current_pos = self.back
			self.delete(input_mark, self.current_end)
			if text: self.insert(input_mark, text)

	def add_reply(self, reply, tags=(), prefix=None, text=None):
		if not self.accept_input:
			if not prefix: prefix = "> "
			self.insert(self.back, "{}\n".format(reply), tags)
			self.cursor = self.back
			self.insert(self.back, prefix)
			self.place_mark(input_mark, self.cursor, gravity="left")
			if text: self.insert(self.back, text)
			self.accept_input = True
			self.show(self.back)

	def add_notification(self, message, tags=()):
		self.insert("end-1l linestart", "{}\n".format(message), tags)