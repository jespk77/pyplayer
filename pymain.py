from ui.qt import pyelement, pywindow, pylauncher
import os, sys

resolution = 225, 325
process_command = pylauncher.process_command

class PySplashWindow(pywindow.RootPyWindow):
    def __init__(self):
        pywindow.RootPyWindow.__init__(self, "splash")
        self.title = "Initializing PyPlayer"
        self.icon = "assets/icon.png"
        self.layout.row(1, weight=1)

        self._dependency_check = False
        self._actions = {}
        self._force_configure = False

        self.make_borderless()
        self.center_window(*resolution, fit_to_size=True)
        self.schedule_task(sec=1, func=self._load_modules if "no_update" in sys.argv else self._update_program)

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

    # STEP 1: Check for updates
    def _update_program(self):
        print("INFO", "Checking for updates")
        self["status_bar"].text = "Checking for updates..."
        pc = process_command("git pull", stdout=self._git_status)
        if pc.returncode:
            print("INFO", "Failed to update, there must be local changes, trying to merge them")
            pc = process_command("git stash && git pull && git stash pop", stdout=self._git_status, shell=True)

        if pc.returncode:
            print("WARNING", "Failed to update, ignoring update...")
            self["status_bar"].text = "Failed to update, continuing in 5 seconds..."
            return self.schedule_task(sec=5, func=self._load_modules)
        process_command("git rev-parse HEAD", stdout=self._git_hash)

    # STEP 1a: Display git update status
    def _git_status(self, out):
        out = out.split("\n")
        if len(out) > 1:
            for o in out:
                if o.startswith("Updating"): self["status_bar"].text = o; break
        elif len(out) == 1: self["status_bar"].text = out[0]

    # STEP 1b: Checking git hash
    def _git_hash(self, out):
        hash = self.configuration.get("hash")
        out = out.rstrip("\m")
        print("VERBOSE", "Comparing current hash", out, "with previous hash", hash)
        if hash != out:
            print("INFO", "Git hash updated, checking depencies")
            self.configuration["hash"] = out
            self._dependency_check = True
        self.schedule_task(sec=1, func=self._load_modules)

    # STEP 2: Check modules
    def _load_modules(self):
        self["status_bar"].text = "Loading modules..."
        modules = [(md.name, md.path) for md in os.scandir("modules") if md.is_dir()]
        module_cfg = self.configuration.get_or_create("modules", {})
        if self._force_configure or list(module_cfg.keys()) != [m[0] for m in modules]:
            print("INFO", "Module list has changed, opening module configuration")
            import pymodules
            self.add_window(window=pymodules.PyModuleConfigurator(self, modules, module_cfg))
            self.hidden = True
        else: self.schedule_task(sec=1, func=self._load_dependencies)

    def set_module_data(self, module_data):
        print("INFO", "Module data updated")
        self.configuration["modules"] = module_data
        self.hidden = False
        self._dependency_check = True
        self.save_configuration()
        self.schedule_task(func=self._load_dependencies if not self._force_configure else self._do_restart)

    # STEP 3: Check module dependencies
    def _load_dependencies(self):
        self.close_window("module_select")
        if self._dependency_check:
            self["status_bar"].text = "Checking dependencies..."
            module_data = self.configuration["modules"]
            dependencies = set()
            for mod_id, mod_data in [(i,d) for i,d in module_data.items() if d.get("enabled")]:
                deps = mod_data.get("dependencies")
                if deps: dependencies.update(deps)

            print("INFO", "Found dependencies:", dependencies)
            self["status_bar"].text = f"Verifying {len(dependencies)} dependencies..."
            pip_install = "{} -m pip install {}"
            if sys.platform == "linux": pip_install += "--user"
            for d in dependencies:
                self["status_bar"].text = f"Installing '{d}'"
                process_command(pip_install.format(sys.executable, d))
            self["status_bar"].text = "Dependency check complete"
        else: self["status_bar"].text = "Loading PyPlayer..."
        self.schedule_task(sec=1, func=self._load_program)

    # STEP 4: Load main program
    def _load_program(self):
        import pyplayerqt
        self._actions[pyplayerqt.PyPlayerCloseReason.RESTART] = self._do_restart
        self._actions[pyplayerqt.PyPlayerCloseReason.MODULE_CONFIGURE] = self._do_module_configure
        self.title = "PyPlayer"
        self.add_window("client", window_class=pyplayerqt.PyPlayer)

    def on_close(self, client):
        print("INFO", "PyPlayer closed with reason:", client.flags)
        close_cb = self._actions.get(client.flags)
        self.close_window("client")
        if close_cb: close_cb()
        else: self.destroy()

    def _do_restart(self):
        print("INFO", "Restarting PyPlayer")
        import os
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _do_module_configure(self):
        print("INFO", "Opening module configurator")
        self.hidden = False
        self["status_bar"].text = "Opening module configuration..."
        self._force_configure = True
        self.schedule_task(sec=1, func=self._load_modules)

if __name__ == "__main__":
    import pylogging
    log = pylogging.get_logger()
    if "dev" in sys.argv: log.log_level = "verbose"
    PySplashWindow().start()