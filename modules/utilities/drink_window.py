import pygame, tkinter
from pygame import locals as pygame_locals

#pygame version
class Water:
	max_level = 318
	top_offset = 35
	color = (0, 222, 255)

	def __init__(self, left, width, level=max_level):
		self.rect = pygame.Rect(left, 0, width, 0)
		self.level = 0
		self.set_level(level)

	def set_level(self, level):
		if level < 0: level = 0
		elif level > self.max_level: level = self.max_level
		self.level = level
		self.rect.top = (self.max_level - self.level) + self.top_offset
		self.rect.height = self.level

class DrinkReminderScreen:
	background = (0, 5, 15)

	def initialize(self, is_master=True):
		print("initialize pygame")
		pygame.init()
		self.screen = pygame.display
		if is_master:
			self.screen.set_caption("Stay hydrated")
			self.screen.set_icon(pygame.image.load("assets/glass_icon.png"))
		print("creating pygame window")
		self.window = self.screen.set_mode((270, 400))

		print("create pygame objects")
		self.glass = pygame.image.load("assets/glass.png")
		self.bbox = self.glass.get_rect()
		self.bbox.left = 35
		self.bbox.top = 15
		self.water = Water(self.bbox.left + 3, self.bbox.width - 7)

	def run(self):
		for event in pygame.event.get():
			if event.type == pygame_locals.QUIT: return False

		self.water.set_level(self.water.level - 1)
		self.screen.update()
		self.window.fill(color=self.background)
		self.window.fill(color=self.water.color, rect=self.water.rect)
		self.window.blit(self.glass, self.bbox)
		return True

	def on_destroy(self):
		pygame.quit()

#tkinter version
class WaterTk:
	color = "#00aafe"
	max_level = 313
	max_height = 353

	def __init__(self, x, width):
		self.x = x
		self.width = width
		self.level = WaterTk.max_level

	def set_level(self, level):
		if level < 0: self.level = 0
		elif level > WaterTk.max_level: self.level = WaterTk.max_level
		else: self.level = level

	@property
	def y(self):
		return WaterTk.max_height - self.level

	@property
	def height(self):
		return WaterTk.max_height


class DrinkReminderWindow(tkinter.Toplevel):
	width = 270
	height = 400
	reminder_splits = 5

	def __init__(self, root, delay):
		super().__init__(root)
		self.title("Stay hydrated")
		self.wm_iconbitmap("assets/hydrated.ico")
		self.geometry("{!s}x{!s}".format(self.width, self.height))
		self.wm_attributes("-topmost", 1)
		self.resizable(False, False)

		self.is_filling = False
		self.delay = round((delay*DrinkReminderWindow.reminder_splits*60*1000)/WaterTk.max_level)
		self.level_per_split = round(WaterTk.max_level / DrinkReminderWindow.reminder_splits)
		self.last_split_level = 0
		self.after(self.delay, self.update)
		self.callback = None
		self.background = tkinter.Canvas(self, width=self.width, height=self.height)
		self.background.pack()
		self.background.create_rectangle(0, 0, self.width, self.height, fill="#00050f")
		self.water = WaterTk(40, 230)
		self.water_rect = self.background.create_rectangle(self.water.x, self.water.y, self.water.width, self.water.height, fill=WaterTk.color)
		self.glass_img = tkinter.PhotoImage(file="assets/glass.png")
		self.background.create_image(self.width/2, self.height/2, image=self.glass_img)

	def set_callback(self, callback):
		if callable(callback): self.callback = callback

	def update_waterlevel(self):
		self.background.coords(self.water_rect, self.water.x, self.water.y, self.water.width, self.water.height)

	def refill(self):
		self.is_filling = True
		self.after(50, self.update_fill)
		return self.water.level == 0

	def update_fill(self):
		if self.is_filling:
			self.is_filling = self.water.level < WaterTk.max_level
			self.water.set_level(self.water.level + 2)
			self.update_waterlevel()
			self.after(50, self.update_fill)
			self.last_split_level = 0
		else: self.after(self.delay, self.update)

	def update(self):
		if not self.is_filling:
			self.water.set_level(self.water.level - 1)
			self.update_waterlevel()
			if self.last_split_level >= self.level_per_split:
				if callable(self.callback): self.callback(self.water.level)
				self.last_split_level = 0
			else: self.last_split_level += 1
			
			if self.water.level > 0: self.after(self.delay, self.update)
			elif callable(self.callback): self.callback(self.water.level)

if __name__ == "__main__":
	window = DrinkReminderScreen()
	clock = pygame.time.Clock()
	window.initialize()
	running = True
	while running:
		running = window.run()
		clock.tick(60)
	window.on_destroy()