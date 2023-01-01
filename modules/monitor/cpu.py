import platform
from ui.qt import pyelement

from . import elements, system

class CpuWidget(elements.ObjectFrame):
    def __init__(self, parent, system):
        elements.ObjectFrame.__init__(self, parent, "cpu_frame")
        self._system : hardware_monitor.HardwareMonitor = system
        self.update()

    def create_widgets(self):
        elements.ObjectFrame.create_widgets(self)
        self.object_image = "modules/monitor/assets/cpu.png"
        self.object_name = platform.processor()
        data : pyelement.PyTable = self.add_element("data", element_class=pyelement.PyTable, row=1)
        data.columns, data.rows = 2, psutil.cpu_count()
        data.column_labels, data.row_labels = ["Usage", "Frequency"], [f"Core #{core}" for core in range(data.rows)]
        data.height = (data.rows + 1) * data.row_height

    def update(self):
        cpu_usage = psutil.cpu_percent(percpu=True)
        cpu_freq = psutil.cpu_freq()
        data : pyelement.PyTable = self["data"]
        for row in range(data.rows):
            data.set(row=row, column=0, value=f"{cpu_usage[row]}%")
            data.set(row=row, column=1, value=f"{round(cpu_freq.current)} Hz")
        data.resize_fit(column=True)