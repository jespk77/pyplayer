import sys, os

def update_program():
	git_url = "https://github.com/jespk77/pyplayer.git"
	git_branch = "experimental"
	print("checking for updates...")
	if "win" in sys.platform:
		print("Windows detected")
		import git
		try:
			gt = git.Repo()
			print("fetching...", gt.git.execute("git fetch --all"), sep="\n")
			print("updating...", gt.git.execute("git reset --hard origin/" + git_branch))
		except git.exc.InvalidGitRepositoryError:
			print("PyPlayer not found, downloading from branch {}...".format(git_branch))
			gt = git.Repo.clone_from(url=git_url, to_path="")
		gt.close()
	elif "linux" in sys.platform:
		print("Linux detected")
		try:
			print("fetching...")
			if os.system("git fetch --all"):
				print("PyPlayer not found, downloading from branch {}...".format(git_branch))
				os.system("git clone {} -b {}".format(git_url, git_branch))
			else:
				print("updating...")
				os.system("git reset --hard origin/" + git_branch)
		except Exception as e: print("ERROR", "Updating player:", e)

	else: raise OSError("platform not supported! sorry! (unless you're using macOS: in that case sorry not sorry)")

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
