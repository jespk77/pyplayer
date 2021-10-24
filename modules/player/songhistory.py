import os
from core import history, modules
module = modules.Module(__package__)
from ui.qt import pyelement, pywindow
from . import songqueue

if not os.path.isdir(".cache"): os.mkdir(".cache")
song_history_path = os.path.join(".cache", "songhistory")
song_history = history.History(limit=100, file=song_history_path)

historywindow_id = "songhistory_viewer"
class SongHistoryViewer(history.HistoryViewer):
    title = "Song History"

    def __init__(self, parent):
        history.HistoryViewer.__init__(self, parent, historywindow_id, history=song_history)
        self.EventSelect(self._on_item_click)

    def _on_history_update(self, new_history=None):
        if new_history is None: new_history = iter(self._history)
        self["history_view"].itemlist = [module.get_displayname(i[1]) for i in new_history]

    def _on_item_click(self):
        item = self._history[self["history_view"].clicked_index]
        module.media_player.play_song(item[0], item[1])

class PlayerInfoWindow(pywindow.PyWindow):
    window_id = "player_info"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, self.window_id)
        self._set_title_from_tab(0)
        self.icon = "assets/icon"
        self.can_maximize = self.can_minimize = False

    def create_widgets(self):
        tab: pyelement.PyTabFrame = self.add_element("info_tabs", element_class=pyelement.PyTabFrame)
        tab.add_tab("History", frame=SongHistoryViewer(tab))
        tab.add_tab("Queue", frame=songqueue.SongQueueViewer(tab))
        tab.events.EventInteract(self._set_title_from_tab)

    def _set_title_from_tab(self, index):
        if index >= 0:
            try: self.title = self["info_tabs"].get_tab(index).title
            except AttributeError: pass
            else: return

        self.title = "Player Info"