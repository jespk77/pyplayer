import os
from utilities import history, messagetypes

client = media_player = song_history = None

def get_displayname(item): return os.path.splitext(item)[0]

historywindow_id = "songhistory_viewer"
class SongHistoryViewer(history.HistoryViewer):
    def __init__(self, parent):
        history.HistoryViewer.__init__(self, parent, historywindow_id, history=song_history)
        self.title = "Song History"
        self.EventClick(self._on_item_click)

    def _on_history_update(self, new_history=None):
        if new_history is None: new_history = iter(self._history)
        self["history_view"].itemlist = [get_displayname(i[1]) for i in new_history]

    def _on_item_click(self):
        item = self._history[self["history_view"].clicked_index]
        media_player.play_song(item[0], item[1])

def command_history_window(arg, argc):
    if client.find_window(historywindow_id) is None: client.add_window(window_class=SongHistoryViewer)
    return messagetypes.Reply("Song history window opened")


def initialize(cl, mp):
    global client, media_player, song_history
    client = cl
    media_player = mp
    song_history = history.History()