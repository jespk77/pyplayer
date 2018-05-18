from sched import scheduler
from time import time, sleep
from threading import Thread
from re import compile
import winsound

def get_time_from_string(delay):
	try:
		hour = delay.split("h")
		if len(hour) > 1:
			delay = "".join(hour[1:])
			hour = int(hour[0])
		else: hour = 0
		
		min = delay.split("m")
		if len(min) > 1:
			delay = "".join(min[1:])
			min = int(min[0])
		else: min = 0
		
		sec = delay.split("s")
		if len(sec) > 0 and sec[0] != "": sec = int(sec[0])
		else: sec = 0
	except ValueError:
		return -1
	
	return hour * 3600 + min * 60 + sec
	
def play_sound(file):
	winsound.PlaySound(file, winsound.SND_FILENAME)

class Timer(Thread):
	PRINT_VALUE = print
	PLAY_SOUND = play_sound
	
	def __init__(self, path, name="0"):
		super().__init__(name="TimerThread-"+str(name))
		self.scheduler = scheduler(time, sleep)
		self.path = path
		
	def add_timer(self, delay = "10s", priority = 1, method = PLAY_SOUND, file = "alarm.wav"):
		if not file.endswith(".wav"): return -1
		delay = get_time_from_string(delay)
		if delay >= 0: 
			self.scheduler.enter(delay, priority, method, kwargs = {"file": self.path + file})
			return delay
		else: return -2
		
	def run(self):
		self.scheduler.run()