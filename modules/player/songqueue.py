from collections import deque
from core import modules
module = modules.Module(__package__)

from ui.qt import pyelement

class SongQueue:
    def __init__(self):
        self._queue = deque()
        self._on_update = None

    def OnUpdate(self, cb):
        """ Fired when the queue changes """
        self._on_update = cb

    def _call_update(self):
        if callable(self._on_update):
            try: self._on_update(iter(self._queue))
            except Exception as e: print("ERROR", "Calling update event:", e)

    def add(self, song):
        """ Add a new song to the end of the queue """
        self._queue.append(song)
        self._call_update()

    def clear(self):
        """ Remove all songs from the queue """
        self._queue.clear()
        self._call_update()

    def remove(self, song):
        """ Remove a specific song from the queue, has no effect if the song isn't in the queue """
        try: self._queue.remove(song)
        except KeyError: pass
        else: self._call_update()

    def get_next(self):
        """ Returns the next song and removes it from the queue or None if the queue is empty """
        try: item = self._queue.popleft()
        except IndexError: item = None
        else: self._call_update()
        return item

    def peek_next(self):
        """ Returns the next song without removing it from the list or None if the queue is empty """
        try: return self._queue[0]
        except IndexError: return None

    def _move(self, song, index, n):
        if index is None:
            try: index = self._queue.index(song)
            except ValueError: return 0
        elif song is None: song = self._queue[index]
        else: raise ValueError("Must specify song or index")

        del self._queue[index]
        index = min(max(index - n, 0), len(self._queue))
        self._queue.insert(index, song)
        self._call_update()
        return index

    def move_up(self, song=None, index=None, n=1):
        """
         Moves the specified song or index forward n spaces (or until it reaches the front), has no effect if the song isn't in the queue
         Returns the new index of the song or 0 if the song wasn't found
        """
        return self._move(song, index, n)

    def move_down(self, song=None, index=None, n=1):
        """
         Moves the specified song or index backward n spaces (or until it reaches the back), has no effect if the song isn't in the queue
         Returns the new index of the song or 0 if the song wasn't found
        """
        return self._move(song, index, -n)

    def __contains__(self, item): return self._queue.__contains__(item)
    def __iter__(self): return self._queue.__iter__()
    def __len__(self): return self._queue.__len__()
    def __str__(self): return f"SongQueue[song_count={len(self._queue)}]"

    def __getitem__(self, index): return self._queue.__getitem__(index)
    def __setitem__(self, index, value):
        self._queue.__setitem__(index, value)
        self._call_update()
    def __delitem__(self, index):
        self._queue.__delitem__(index)
        self._call_update()

song_queue = SongQueue()
class SongQueueViewer(pyelement.PyFrame):
    title = "Song Queue"

    def __init__(self, parent, queue=None):
        self._queue = queue if queue is not None else song_queue
        pyelement.PyFrame.__init__(self, parent, "song_queue")

        queue_update = "queue_update"
        self.window.add_task(queue_update, self._on_queue_update)
        self._queue.OnUpdate(lambda q: self.window.schedule_task(task_id=queue_update, items=q))
        self._on_queue_update(self._queue)
        @self.events.EventDestroy
        def _on_close(): self._queue.OnUpdate(None)

    def create_widgets(self):
        self.add_element("lbl", element_class=pyelement.PyTextLabel).text = "Items in queue:"
        items: pyelement.PyItemlist = self.add_element("items", element_class=pyelement.PyItemlist, row=1, columnspan=2)
        btn = self.add_element("queue_up", element_class=pyelement.PyButton, row=2)
        btn.text = "Move up"
        @btn.events.EventInteract
        def _move_item_up():
            if len(self._queue) > 0: items.selected_index = self._queue.move_up(index=items.selected_index)

        btn2: pyelement.PyButton = self.add_element("queue_down", element_class=pyelement.PyButton, row=2, column=1)
        btn2.text = "Move down"
        @btn2.events.EventInteract
        def _move_item_down():
            if len(self._queue) > 0: items.selected_index = self._queue.move_down(index=items.selected_index)

        btn3 = self.add_element("queue_del", element_class=pyelement.PyButton, row=3)
        btn3.text = "Delete"
        @btn3.events.EventInteract
        def _delete_item():
            if len(self._queue) > 0: del self._queue[items.selected_index]

        btn4 = self.add_element("queue_clear", element_class=pyelement.PyButton, row=3, column=1)
        btn4.text = "Clear"
        @btn4.events.EventInteract
        def _clear_queue(): self._queue.clear()

    def _on_queue_update(self, items):
        queue = self["items"]
        selection = queue.selected_index
        queue.itemlist = [module.get_displayname(item[1]) for item in items]
        queue.selected_index = selection