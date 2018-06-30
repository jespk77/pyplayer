from utilities import messagetypes
from modules.utilities import time_counter, drink_window

# DEFAULT MODULE VARIABLES
priority = 7
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
noise_timer = None
drink_timer = None
drink_reminder = None
drink_count = 0

def on_noise_timer():
	interpreter.queue.put_nowait("effect deer")

def on_drink_timer(level):
	interpreter.queue.put_nowait("effect splash")

def start_catching_noises(arg, argc):
	if argc == 0:
		global noise_timer
		if noise_timer is not None:
			try: noise_timer.destroy()
			except: pass
		noise_timer = time_counter.TimeCount(client)
		noise_timer.set_callback(on_noise_timer)
		return messagetypes.Reply("The noises will be caught")

def start_drink_reminder(arg, argc):
	if argc < 2:
		try: delay = int(arg[0])
		except: delay = 10

		global drink_reminder
		if drink_reminder is not None:
			try: drink_reminder.destroy()
			except: pass

		drink_reminder = drink_window.DrinkReminderWindow(client, delay)
		drink_reminder.set_callback(on_drink_timer)
		return messagetypes.Reply("Drink reminders will be happening every {!s} minute(s)".format(delay))

def get_drink_count(arg, argc):
	if argc == 0:
		global drink_count
		return messagetypes.Reply("There have been {!s} refills today".format(drink_count))

def refill_drink(arg, argc):
	if argc == 0:
		global drink_reminder, drink_count
		if drink_reminder is not None:
			res = drink_reminder.refill()
			if res: drink_count += 1
			return messagetypes.Reply("Drink refilled")
		else: return start_drink_reminder(arg, argc)

commands = {
	"noise": start_catching_noises,
	"water": {
		"": start_drink_reminder,
		"count": get_drink_count,
		"refill": refill_drink
	}
}