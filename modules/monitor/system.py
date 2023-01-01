import os
from core import modules

module = modules.Module(__package__)

import clr
clr.AddReference(os.path.join(module.path, "OpenHardwareMonitor", "OpenHardwareMonitorLib"))

from OpenHardwareMonitor.Hardware import Computer, HardwareType

class Component:
    def __init__(self, hardware):
        self._hardware = hardware

    @property
    def name(self): return self._hardware.Name

    def update(self):
        self._hardware.Update()

    def values(self):
        pass

class System:
    """
        Holds data about hardware components available on the system and can be used to query variables
        After creation this class keeps a connection with the system open, therefore after usage it must be closed by calling 'close()' or wrapping it in a 'with' section
    """
    def __init__(self):
        self._system = Computer()
        self._system.Open()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._system.Close()

    def get_mainboard(self):
        """ Gets the  """
        self._system.MainboardEnabled = True
        return [Component(hardware) for hardware in self._system.Hardware if hardware.HardwareType == HardwareType.Mainboard]

    def get_cpu(self):
        self._system.CPUEnabled = True
        return [Component(hardware) for hardware in self._system.Hardware if hardware.HardwareType == HardwareType.CPU]