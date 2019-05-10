import datetime

from modules.utilities import time_counter
from utilities import messagetypes

# DEFAULT MODULE VARIABLES
interpreter = client = None

# MODULE SPECIFIC VARIABLES
last_joke = None

def on_noise_timer(cmd):
	interpreter.put_command(cmd)

def start_timer(arg, argc):
	delay = -1
	if argc > 0:
		try: delay = int(arg[0])
		except ValueError: print("INFO", "Cannot parse argument into a number")

	counter = time_counter.TimeCount(client, "Timer", count_time=delay if delay >= 0 else None, timer_callback=on_noise_timer)
	counter.always_on_top = True
	client.open_window("counter", counter)
	return messagetypes.Reply("Counter started")

def start_catching_noises(arg, argc):
	if argc == 0:
		counter = time_counter.TimeCount(client, "Catching noises", "assets/noise", timer_callback=on_noise_timer)
		counter.always_on_top = True
		client.open_window("counter", counter)
		return messagetypes.Reply("The noises will be caught")

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

def get_random_number(arg, argc):
	try: value = int(arg[0])
	except (IndexError, ValueError): value = 100
	import random
	if value <= 0: return messagetypes.Reply("The number must at least be greater than 0")
	else: return messagetypes.Reply("Your random number between 0 and {} is {}".format(value, random.choice(range(value))))

commands = {
	"counter": start_timer,
	"joke": tell_joke,
	"noise": start_catching_noises,
	"number": get_random_number
}