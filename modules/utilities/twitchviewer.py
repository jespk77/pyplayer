import requests, tkinter

from modules.utilities.twitchchat import TwitchChat

class TwitchViewer(tkinter.Toplevel):
	channel_meta_url = "https://api.twitch.tv/kraken/channels/{channel}?client_id={client_id}"

	def __init__(self, root, configuration, channel):
		self.configuration = configuration
		self.is_alive = True
		if "login" in self.configuration:
			print("getting metadata for channel", channel)
			self.channel_meta = requests.get(self.channel_meta_url.format(channel=channel, client_id=configuration["login"]["client-id"])).json()
			if "error" in self.channel_meta: self.error = self.channel_meta["error"]
			else: self.error = None
		else: self.error = "No login information specified"

		super().__init__(root)
		self.root = root
		self.title("PyPlayer - TwitchViewer")
		self.iconbitmap("icon.ico")
		self.bind("<Destroy>", self.on_destroy)
		if self.error is None:
			print("no errors, starting chat...")
			self.bind("<Destroy>", self.disconnect)
			self.attributes("-topmost", "true")
			self.geometry("390x500")
			self.chat = TwitchChat(self)
			self.chat.set_configuration(configuration)
			self.chat.pack(side="right", fill="both", expand=True)
			self.set_title()
			self.start()
		else:
			self.label = tkinter.Label(self)
			self.label.configure(text="Error getting metadata for '{}': ".format(channel) + str(self.error))
			self.label.pack()

	def set_title(self):
		title = self.channel_meta["display_name"]
		if self.channel_meta["status"] is not None: title += " - " + self.channel_meta["status"]
		if self.channel_meta["game"] is not None: title += " [" + self.channel_meta["game"] + "]"
		self.title(title)

	def start(self):
		self.chat.connect(self.channel_meta)
		self.after(500, self.chat.run)

	def disconnect(self, event):
		self.chat.disconnect()
		self.chat.destroy()
		self.on_destroy()

	def on_destroy(self):
		self.is_alive = False