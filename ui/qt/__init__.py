__all__ = ["pywindow", "pyelement"]

# pyqt documentation:
# https://doc.qt.io/qtforpython/modules.html

def log_exception(e):
    import traceback
    traceback.print_exception(type(e), e, e.__traceback__)
    print("")

from . import pywindow, pyelement, pynetwork
network_manager = pynetwork.NetworkManager()