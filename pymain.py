from ui.qt import pyelement, pywindow, pylauncher
import os, json

resolution = 225, 325
process_command = pylauncher.process_command

class PySplashWindow(pywindow.RootPyWindow):
    def __init__(self):
        pywindow.RootPyWindow.__init__(self, "splash")
        self.title = "Initializing PyPlayer"
        self.icon = "assets/icon.png"
        self.layout.row(1, weight=1)

        self.make_borderless()
        self.center_window(*resolution, fit_to_size=True)
        self.schedule_task(sec=1, func=self._load_modules)

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

    def _load_modules(self):
        self["status_bar"].text = "Loading modules..."
        modules = [(md.name, md.path) for md in os.scandir("modules") if md.is_dir()]
        module_cfg = self.configuration.get_or_create("modules", {})
        if list(module_cfg.keys()) != [m[0] for m in modules]:
            print("INFO", "Module list has changed, opening module configuration")
            #todo: forward to module configurator
            for module_id, module_path in modules:
                try:
                    with open(os.path.join(module_path, "package.json")) as file:
                        print("INFO", f"Loading module '{module_id}'")
                        module_data = json.load(file)
                        self.configuration[f"modules::{module_id}"] = module_data
                except FileNotFoundError:
                    print("WARNING", f"Skipping invalid module '{module_id}': package.json not found")
                    continue
                except Exception as e:
                    self["status_bar"].text = f"Failed to load module '{module_id}, shutting down in 5 seconds"
                    print("ERROR", "Loading module", module_id, "->", e)
                    return self.schedule_task(sec=5, func=self.destroy)
        self.schedule_task(sec=1, func=self._load_program)

    def _load_program(self):
        from pyplayerqt import PyPlayer
        client = self.add_window("client", window_class=PyPlayer)
        client.start_interpreter(self.configuration["modules"])

        client.hidden = False
        self.hidden = True

if __name__ == "__main__":
    import pylogging, sys
    log = pylogging.get_logger()
    if "dev" in sys.argv: log.log_level = "verbose"
    PySplashWindow().start()