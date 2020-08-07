import datetime

from core import messagetypes

# DEFAULT MODULE VARIABLES
interpreter = client = None

# MODULE SPECIFIC VARIABLES
last_joke = None

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
	"joke": tell_joke,
	"number": get_random_number
}