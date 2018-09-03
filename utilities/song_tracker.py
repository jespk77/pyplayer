from datetime import datetime
from collections import Counter
import calendar, os

tracker = None
tracker_file = ""
is_dirty = False
listeners = []

def is_loaded():
	return tracker is not None

def load_tracker():
	global tracker, tracker_file, is_dirty
	m = datetime.today()
	tracker_file = "statistics/" + calendar.month_name[m.month].lower() + str(m.year)
	tracker = load_file(tracker_file)
	is_dirty = False

def load_file(file):
	global tracker_file
	if not os.path.isdir("statistics"): os.mkdir("statistics")
	if not file.startswith("statistics/"): tracker_file = "statistics/" + file
	c = Counter()
	try:
		d = open(tracker_file, "r")
		for item in d:
			item = item.replace("\n", "").split("%", maxsplit=1)
			if len(item) == 2:
				try: c[item[0]] = int(item[1])
				except ValueError: pass
		d.close()
	except FileNotFoundError: open(tracker_file, "w+").close()
	return c

def save_tracker():
	global tracker, tracker_file, is_dirty
	if is_dirty:
		file = open(tracker_file, "w")
		for item, count in tracker.items():
			file.write(item + "%" + str(count) + "\n")
		file.close()
	is_dirty = False

def add(song, n=1):
	global tracker, is_dirty
	tracker[song] += n
	is_dirty = True
	save_tracker()
	for l in listeners: l(song, n)

def get_songlist(alltime=False):
	if not alltime: return tracker

	songlist = Counter()
	for item in os.listdir("statistics"):
		if item != "player": songlist.update(load_file(item))
	return songlist

def get_freq(song, alltime=False):
	ls = get_songlist(alltime)
	if song in ls: return ls[song]
	else: return 0