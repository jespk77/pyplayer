import subprocess
import sys

def get_python_version(): return "{0.major}.{0.minor}".format(sys.version_info)

def process_command(cmd, stdin=None, stdout=None, stderr=None, timeout=None):
	""" Run a command that can be interacted with using standard IO: 'stdin', 'stdout', 'stderr'
			- If stdin is provided, it must be a bytes object
			- If stdout is provided, it must be callable: all command output is directed to this method'; when not provided all output is ignored
			- If stderr is provided, must be callable, it receives any error messages from the command; when not provided errors are directed to stdout
	 	Waits for the process to be finished but can be aborted if it takes longer than n seconds using 'timeout' argument
	 	Returns the finished process when termated """
	if isinstance(cmd, str): cmd = cmd.split(" ")

	if stderr is None: stderr = stdout
	import subprocess
	if "win" in sys.platform:
		pi = subprocess.STARTUPINFO()
		pi.dwFlags |= subprocess.STARTF_USESHOWWINDOW
	else: pi = None

	pc = subprocess.Popen(cmd, startupinfo=pi, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	while pc.returncode is None:
		try:
			out, err = pc.communicate(stdin, timeout=1)
			if out and stdout: stdout(out.decode())
			if err and stderr: stderr(err.decode())
		except subprocess.TimeoutExpired: pass
		except Exception as e: print("error communicating:", e); break
	pc.wait(timeout)
	return pc

def install_dependencies(dependencies):
	"""
		Install one or more dependencies with pip
		Returns True if the dependencies were successfully installed, False otherwise
	"""
	if isinstance(dependencies, list): dependencies = " ".join(dependencies)
	process = process_command(f"{sys.executable} -m pip install {dependencies}", stderr=_install_error)
	return process.returncode == 0

def install_dependency_file(dependency_file):
	"""
		Install dependencies with pip from a file, this file is installed with the requirements.txt rules
		Returns True if the dependencies were successfully installed, False otherwise
	"""
	process = process_command(f"{sys.executable} -m pip install -r {dependency_file}", stderr=_install_error)
	return process.returncode == 0

def _install_error(text):
	print("ERROR", "While installing dependencies with pip\n", text)