if __name__ == "__main__":
    from ui.qt import pylauncher
    launcher = pylauncher.PyQtLauncher("pymain.py")
    launcher.start()
else: print("This script must be called as main")