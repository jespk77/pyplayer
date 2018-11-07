from utilities import messagetypes
from modules.utilities import time_counter, drink_window
import datetime

# DEFAULT MODULE VARIABLES
priority = 7
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
drink_timer = None
drink_reminder = None
drink_count = 0
last_joke = None

def on_noise_timer(cmd):
	interpreter.put_command(cmd)

def on_drink_timer(level):
	interpreter.put_command("effect splash")

def start_timer(arg, argc):
	delay = -1
	if argc > 0:
		try: delay = int(arg[0])
		except ValueError: print("INFO", "Cannot parse argument into a number")

	counter = time_counter.TimeCount(client, "Timer", count_time=delay if delay >= 0 else None)
	counter.set_callback(on_noise_timer)
	counter.always_on_top = True
	return messagetypes.Reply("Counter started")

def start_catching_noises(arg, argc):
	if argc == 0:
		counter = time_counter.TimeCount(client, "Catching noises", "assets/noise")
		counter.set_callback(on_noise_timer)
		counter.always_on_top = True
		client.open_window("noise_counter", counter)
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

def tell_joke(arg, argc):
	if argc == 0:
		global last_joke
		current = datetime.datetime.today()
		if last_joke is not None:
			delta = current - last_joke
			s = 3600 - delta.total_seconds()
			if s > 0: return messagetypes.Reply("We're still recovering from that last joke, wait {}m{}s for the next one".format(int(s / 60), int(s % 60)))
		last_joke = current
		import pyjokes
		return messagetypes.Reply(pyjokes.get_joke())

commands = {
	"counter": start_timer,
	"joke": tell_joke,
	"noise": start_catching_noises,
	"water": {
		"": start_drink_reminder,
		"count": get_drink_count,
		"refill": refill_drink
	}
}