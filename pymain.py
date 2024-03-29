import os, socket, sys
import traceback

import pymodules, pyplayerqt
from ui.qt import pyelement, pywindow, pylauncher

resolution = 225, 325
process_command = pylauncher.process_command

class PySplashWindow(pywindow.RootPyWindow):
    def __init__(self):
        pywindow.RootPyWindow.__init__(self, "splash")
        self.title = "Initializing PyPlayer"
        self.icon = "assets/icon.png"
        self.layout.row(1, weight=1)

        self._update = False
        self._actions = {}
        self._force_configure = False
        self._main_window = None

        self.make_borderless()
        self.center_window(*resolution, fit_to_size=True)
        self.schedule_task(func=self._check_modules if "no_update" in sys.argv else self._check_connection)

    def create_widgets(self):
        pywindow.RootPyWindow.create_widgets(self)
        self.add_element("header", element_class=pyelement.PyTextLabel, row=0, column=0)
        btn = self.add_element("close_btn", element_class=pyelement.PyButton, row=0, column=1)
        btn.width, btn.text = 30, "X"
        @btn.events.EventInteract
        def _on_click(): self.destroy()
        logo = self.add_element("logo_img", element_class=pyelement.PyTextLabel, row=1, columnspan=2)
        logo.display_image = "assets/logo.png"
        status_bar = self.add_element("status_bar", element_class=pyelement.PyTextLabel, row=2, columnspan=2)
        status_bar.set_alignment("center")
        status_bar.text, status_bar.wrapping = "Initializing...", True

    @property
    def status_text(self): return self["status_bar"].text
    @status_text.setter
    def status_text(self, status): self["status_bar"].text = status

    # STEP 1a: wait for active connection
    def _check_connection(self):
        print("VERBOSE", "Waiting for an active internet connection before trying to update")
        self.status_text = "Checking for updates..."
        try: socket.create_connection(("https://github.com", 443), 10)
        except socket.error: pass
        self.schedule_task(func=self._update_program)

    # STEP 1b: Check for updates
    def _update_program(self):
        print("INFO", "Checking for updates")
        try:
            pc = process_command("git pull", stdout=self._git_status)
            if pc.returncode == 0:
                if self._update: self._do_restart()
                else: self.schedule_task(func=self._check_modules)
                return
        except Exception as e: print("ERROR", "Updating program", e)

        print("WARNING", "Failed to update, ignoring update...")
        self.status_text = "Failed to update, continuing in 5 seconds..."
        self.schedule_task(sec=5, func=self._check_modules)

    # STEP 1c: Display git update status
    def _git_status(self, out):
        out = out.split("\n")
        if len(out) > 1:
            for o in out:
                if o.startswith("Updating"):
                    self.status_text = o
                    self._update = True
                    break
        elif len(out) == 1: self.status_text = out[0]

    # STEP 2: Check modules
    def _check_modules(self):
        self.status_text = "Loading modules..."
        if self._force_configure or pymodules.check_for_new_modules():
            print("INFO", "Module list has changed, opening module configuration")
            self.add_window(window=pymodules.PyModuleConfigurationWindow(self, self._configure_modules_complete))
            self.hidden = True
        else: self.schedule_task(sec=1, func=self._load_modules)

    def _configure_modules_complete(self):
        print("INFO", "Module data updated")
        self.hidden = False
        self.schedule_task(sec=1, func=self._load_modules if not self._force_configure else self._do_restart)

    # STEP 3: Load modules
    def _load_modules(self):
        self.close_window("module_select")
        self._main_window = pyplayerqt.PyPlayer(self, "client")
        self.schedule_task(sec=1, func=self._load_program)

    # STEP 4: Load main program
    def _load_program(self):
        self.status_text = "Loading PyPlayer..."
        self._actions[pyplayerqt.PyPlayerCloseReason.RESTART] = self._do_restart
        self._actions[pyplayerqt.PyPlayerCloseReason.MODULE_CONFIGURE] = self._do_module_configure
        self.title = "PyPlayer"
        self.add_window(window=self._main_window)

    def on_close(self, client):
        print("INFO", "PyPlayer closed with reason:", client.flags)
        close_cb = self._actions.get(client.flags)
        self.close_window("client")
        if close_cb: close_cb()
        else: self.destroy()

    def _do_restart(self):
        print("INFO", "Restarting PyPlayer")
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _do_module_configure(self):
        print("INFO", "Opening module configurator")
        self.hidden = False
        self.status_text = "Opening module configuration..."
        self._force_configure = True
        self.schedule_task(sec=1, func=self._check_modules)

def handle_except(error_type, error_value, error_traceback):
    print("ERROR", f"Unhandled exception occurred:\n{''.join(traceback.format_exception(error_type, error_value, error_traceback))}")

def handle_unraisable(args):
    print("ERROR", f"Unraisable exception occurred:\n{''.join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))}")

if __name__ == "__main__":
    import pylogging
    log = pylogging.get_logger()
    if "dev" in sys.argv: log.log_level = "verbose"

    sys.excepthook = handle_except
    sys.unraisablehook = handle_unraisable

    window_error_handler = pylauncher.PyQtErrorHandler(lambda level, context, message: log.print_log(level, message, context=context))
    PySplashWindow().start()