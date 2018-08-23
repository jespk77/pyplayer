import sys, git

def update_program():
	git_url = "https://github.com/jkr-77/pyplayer.git"
	git_branch = "experimental"
	try:
		gt = git.Repo()
		print("checking for updates...")
		print(gt.git.checkout(git_branch))
		gt.close()
	except git.exc.InvalidGitRepositoryError:
		print("downloading pyplayer...")
		gt = git.Repo.clone_from(url=git_url, to_path="")
		gt.close()

if "developer" in sys.argv: print("running in developer mode: skipping update checks")
else: update_program()
from PyPlayerTk import PyPlayer, PyLog
from interpreter import Interpreter
if "console" not in sys.argv:
	sys.stdout = PyLog()
	print("PyPlayer: file logging enabled")

print("initializing client...")
client = PyPlayer()
interp = Interpreter(client)
client.interp = interp
client.start()
print("client closed, destroying client...")
if interp is not None and interp.is_alive(): interp.queue.put(False)
interp.join()