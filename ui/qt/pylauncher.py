import subprocess, sys

def process_command(cmd, stdin=None, stdout=None, stderr=None, timeout=None, shell=False):
    """ Run a command that can be interacted with using standard IO: 'stdin', 'stdout', 'stderr'
            - If stdin is provided, it must be a bytes object
            - If stdout is provided, it must be callable: all command output is directed to this method'; when not provided all output is ignored
            - If stderr is provided, must be callable, it receives any error messages from the command; when not provided errors are directed to stdout
        Waits for the process to be finished but can be aborted if it takes longer than n seconds using 'timeout' argument
        Supports shell commands by setting 'shell' argument to True
        Returns the finished process when terminated """
    if isinstance(cmd, str): cmd = cmd.split(" ")

    if stderr is None: stderr = stdout
    import subprocess
    if "win" in sys.platform:
        pi = subprocess.STARTUPINFO()
        pi.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    else: pi = None

    pc = subprocess.Popen(cmd, startupinfo=pi, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    while pc.returncode is None:
        try:
            out, err = pc.communicate(stdin, timeout=1)
            if out and stdout: stdout(out.decode())
            if err and stderr: stderr(err.decode())
        except subprocess.TimeoutExpired: pass
        except Exception as e: print("error communicating:", e); break
    pc.wait(timeout)
    return pc

try:
    from PyQt5 import QtCore
    class PyQtErrorHandler:
        def __init__(self, log_callback=print):
            QtCore.qInstallMessageHandler(self._on_log_message)
            self._log_cb = log_callback

        _message_types = {
            QtCore.QtInfoMsg: "INFO",
            QtCore.QtWarningMsg: "WARNING",
            QtCore.QtDebugMsg: "VERBOSE"
        }

        def _on_log_message(self, message_type : QtCore.QtMsgType, context : QtCore.QMessageLogContext, message: str):
            level = self._message_types.get(message_type, 'ERROR')
            # only provide context if there's something useful, context from log messages in low level window code is None
            if context.file or context.function:
                return self._log_cb(level, f"[{context.file}.{context.function} (line {context.line}).{level}]", message)

            return self._log_cb(level, f"[Qt.{level}]", message)
except ImportError: print("Qt not installed: Error handler will not be available")

class PyQtLauncher:
    """ Helper class that can launch the application from a default Python installation,
        ensures all dependencies are installed and the application is up to date before the main application is run """
    def __init__(self, main_file_to_run=None):
        self._minimal_dependencies = ["PyQt5==5.15.6"]
        self._file = main_file_to_run
        print("PyQtLauncher initialized.")

    def start(self):
        print("Preparing for launch...")
        print("Checking minimum required dependencies:", ",".join(self._minimal_dependencies))
        for d in self._minimal_dependencies:
            print("Installing", d, end="")
            process_command(f"{sys.executable} -m pip install {d}", stdout=print)

        if self._file:
            print("Installation complete, launching...")
            subprocess.Popen(f"{sys.executable[:-4]}w.exe {self._file}")
        else: print("Installation complete")

if __name__ == "__main__":
    PyQtLauncher().start()