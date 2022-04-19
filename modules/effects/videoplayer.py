from core import modules

from ui.qt import pywindow, pyelement

class EffectPlayer(pywindow.PyWindow):
    window_name = "effect_player"

    def __init__(self, parent, player):
        self._player = player
        pywindow.PyWindow.__init__(self, parent, self.window_name)
        self.layout.row(0, weight=1).column(0, weight=1).margins(0)
        self.title = "Effect player"
        self.icon = "assets/icon"

        self.make_borderless()
        #self.always_on_top = True
        self.fill_window()
        @self.events.EventWindowClose
        def _on_close(): self._player.clear_hwnd()

        self.play()

    def create_widgets(self):
        self.add_element("content", element_class=pyelement.PyFrame)

    def play(self):
        self._player.play_on_hwnd(self["content"].handle)

module = modules.Module(__package__)
def open_player(player):
    window = module.client.find_window(EffectPlayer.window_name)
    if window is None:
        print("VERBOSE", "No effect player found, creating a new one")
        module.client.add_window(window_class=EffectPlayer, player=player)
    else: window.play()

def close_player():
    print("VERBOSE", "Closing effect player")
    module.client.close_window(EffectPlayer.window_name)