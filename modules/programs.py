from modules.utilities.time_counter import TimeCount

# DEFAULT MODULE VARIABLES
priority = 7
interpreter = None
client = None

# MODULE SPECIFIC VARIABLES
noise_timer = None

def on_noise_timer():
	interpreter.queue.put_nowait("effect deer")

def start_catching_noises(arg, argc):
	global noise_timer
	if noise_timer is not None:
		try: noise_timer.destroy()
		except: pass
	noise_timer = TimeCount(client)
	noise_timer.set_callback(on_noise_timer)

commands = {
	"noise": start_catching_noises
}