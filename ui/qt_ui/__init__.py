__all__ = ["pywindow", "pyelement"]

block_action = 0xBEEF

def log_exception(e):
    import traceback
    traceback.print_exception(type(e), e, e.__traceback__)
    print("")

from . import pywindow, pyelement