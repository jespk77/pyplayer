def update_program():
	git_url = "https://github.com/jespk77/pyplayer.git"
	git_branch = "experimental"
	git_path = ".gitplayer"
	print("checking for updates...")
	import os, subprocess, shutil
	res = subprocess.run(["git", "fetch", "-all"])
	if res.returncode == 128:
		print("Pyplayer was not found, installing new version...")
		if os.path.isdir(git_path): shutil.rmtree(git_path)
		res = subprocess.run(["git", "clone", git_url, git_path, "-b", git_branch])
	else: res = subprocess.run(["git", "reset", "--hard", "origin/", git_branch])

	if res.returncode != 0:
		print("Cannot download pyplayer...")
		sys.exit(-1)

	if os.path.isdir(git_path):
		print("Moving downloaded player to main folder")
		for file in os.listdir(git_path): shutil.move(git_path + "/" + file, file)
		os.rmdir(git_path)

import sys
if "no_update" in sys.argv: print("skipping update checks")
else: update_program()

from PyPlayerTk import PyPlayer
from interpreter import Interpreter
import pylogging
pylogging.PyLog(log_level="INFO", log_to_file="console" not in sys.argv)

print("initializing client...")
client = PyPlayer()
interp = Interpreter(client)
client.interp = interp
client.start()
print("client closed, destroying client...")
if interp is not None and interp.is_alive(): interp.stop_command()
interp.join()

try: sys.stdout.on_destroy()
except AttributeError: pass