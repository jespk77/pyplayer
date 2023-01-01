import platform

from ui.qt import pywindow, pyelement
from . import system, cpu

class MonitorWindow(pywindow.PyWindow):
    window_name = "monitor_window"

    def __init__(self, parent):
        self._data = []
        pywindow.PyWindow.__init__(self, parent, MonitorWindow.window_name)
        self.layout.row(0, weight=0).row(1, weight=1)
        self.title = "System Monitor"
        self.icon = "assets/icon"
        self.schedule_task(sec=1, loop=True, task_id="_update_values", func=self._update_values)

    def create_widgets(self):
        info = platform.uname()
        self.add_element("info", element_class=pyelement.PyTextLabel).text = f"{info.node} - {info.system} {info.release}"
        content = self.add_element("content", element_class=pyelement.PyScrollableFrame, row=1)
        self._data.append(cpu.CpuWidget(self))

        for index, element in enumerate(self._data): content.add_element(element=element, row=index)
        content.layout.row(len(self._data), weight=1)

    def _update_values(self):
        for item in self._data:
            try: item.update()
            except Exception as e: print("ERROR", f"Failed to update '{item.element_id}':", e)