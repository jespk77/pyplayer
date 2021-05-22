import os

import vlc

class VideoPlayer:
    def __init__(self):
        self._vlc = vlc.MediaPlayer()

        self._events = {}
        event_manager = self._vlc.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda e: self._call_event("end_reached", e))
        event_manager.event_attach(vlc.EventType.MediaPlayerPaused, lambda e: self._call_event("pause", e))
        event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, lambda e: self._call_event("play", e))
        event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, lambda e: self._call_event("pos_changed", e))
        event_manager.event_attach(vlc.EventType.MediaPlayerStopped, lambda e: self._call_event("stopped", e))

    def destroy(self):
        print("VERBOSE", "Releasing video player instance")
        self._vlc.release()

    def set_window(self, handle):
        print("VERBOSE", "Updated video player window handle")
        self._vlc.set_hwnd(handle)

    @property
    def playing(self): return self._vlc.is_playing()

    def play_video(self, path):
        print("VERBOSE", f"Playing video '{path}'...")
        self._vlc.set_mrl(path)
        self._vlc.play()

    def pause_video(self, pause=None):
        if pause is None:
            print("VERBOSE", "Toggled play/pause state")
            self._vlc.pause()
        else:
            if isinstance(pause, str): pause = True if pause.lower() == "true" else (False if pause.lower() == "false" else None)
            else: pause = bool(pause)
            if pause is None: raise ValueError("Unsupported argument")

            print("VERBOSE", f"Set video paused to {pause}")
            self._vlc.set_pause(pause)

    def stop_video(self):
        print("VERBOSE", "Stopped video playback")
        self._vlc.stop()

    @property
    def time(self): return self._vlc.get_time() / 1000
    @time.setter
    def time(self, time):
        if self.playing:
            time = round(time * 1000)
            print("VERBOSE", f"Updating play time to {time}s...")
            self._vlc.set_time(time)

    @property
    def position(self): return self._vlc.get_position()
    @position.setter
    def position(self, pos):
        if self.playing:
            print("VERBOSE", f"Updating play position to {pos*100}%...")
            self._vlc.set_position(pos)

    def move_time(self, time):
        if self._vlc.is_playing():
            time = round(time * 1000)
            print("VERBOSE", f"Moving play time {time}s...")
            self._vlc.set_time(self._vlc.get_time() + time)

    def move_position(self, pos):
        if self._vlc.is_playing():
            print("VERBOSE", f"Moving current position {pos*100}%...")
            self._vlc.set_position(self._vlc.get_position() + pos)

    def EventEndReached(self, cb): return self._register_event("end_reached", cb)
    def EventPause(self, cb): return self._register_event("pause", cb)
    def EventPlay(self, cb): return self._register_event("play", cb)
    def EventPosition(self, cb): return self._register_event("pos_changed", cb)
    def EventStop(self, cb): return self._register_event("stop", cb)

    def _register_event(self, event_id, cb):
        if cb is not None:
            print("VERBOSE", f"Registring new event handler for '{event_id}'...")
            if not callable(cb): raise TypeError("Event handler must be callable")
            self._events[event_id] = cb
            return cb
        else:
            print("VERBOSE", f"Unegistring event handler for '{event_id}'...")
            try: del self._events[event_id]
            except KeyError: pass

    def _call_event(self, event_id, event):
        cb = self._events.get(event_id)
        if cb is not None:
            try: cb(event)
            except Exception as e: print("ERROR", f"While calling event handler for '{event_id}':", e)

video_player = VideoPlayer()
from ui.qt import pywindow, pyelement

from core import modules
module = modules.Module(__package__)

class VideoPlayerWindow(pywindow.PyWindow):
    window_id = "video_player_window"

    def __init__(self, parent, video_file=None, show=None):
        pywindow.PyWindow.__init__(self, parent, self.window_id)
        self.title = "Video Player"
        self.icon = "assets/icon_video"
        self.layout.row(0, weight=1).column(0, weight=1).column(4, weight=1)

        self.events.EventWindowHide(self._on_hide)
        self.events.EventWindowShow(self._on_show)
        self.events.EventWindowClose(self._on_close)

        self.add_task("play_video", self._play)
        self.add_task("on_play", self._execute_play)
        self.add_task("on_pause", self._execute_pause)
        self.add_task("pos_change", self._execute_pos_change)
        self.add_task("on_stop", self._execute_stop)
        self._register_events()
        if video_file is not None: self.play(video_file, show)

    def create_widgets(self):
        self.add_element("content", element_class=pyelement.PyLabelFrame, columnspan=5)
        self.add_element("filler1", element_class=pyelement.PyFrame, row=1)

        progress = self.add_element("progress", element_class=pyelement.PyProgessbar, row=1, columnspan=5)
        progress.minimum, progress.value, progress.maximum = 0, 0, 10000
        progress.color = module.configuration.get("#progressbar_color")
        @progress.events.EventInteract
        def _on_click(position): module.interpreter.put_command(f"video position {position}")

        btn = self.add_element("backward_btn", element_class=pyelement.PyButton, row=2, column=1)
        btn.text, btn.accept_input = "<<", False
        btn.events.EventInteract(self.backward)
        btn2 = self.add_element("playpause_btn", element_class=pyelement.PyButton, row=2, column=2)
        btn2.text, btn2.accept_input = "Play", True
        btn2.events.EventInteract(self.pause)
        btn3 = self.add_element("forward_btn", element_class=pyelement.PyButton, row=2, column=3)
        btn3.text, btn3.accept_input = ">>", False
        btn3.events.EventInteract(self.forward)
        self.add_element("filler2", element_class=pyelement.PyFrame, row=2, column=4)

        @self.events.EventKeyDown("Space")
        def _pause():
            self.pause()
            return self.events.block_action

        @self.events.EventKeyDown("Left")
        def _backward():
            self.backward()
            return self.events.block_action

        @self.events.EventKeyDown("Right")
        def _forward():
            self.forward()
            return self.events.block_action

    def play(self, video_file, show_data=None): self.schedule_task(task_id="play_video", video_file=video_file, show_data=show_data)
    def pause(self): module.interpreter.put_command("video pause")
    def stop(self): module.interpreter.put_command("video stop")
    def forward(self, amount=5): module.interpreter.put_command(f"video time +{amount}")
    def backward(self, amount=5): module.interpreter.put_command(f"video time -{amount}")

    def _on_close(self):
        self.stop()
        self._unregister_events()

    def _play(self, video_file, show_data):
        if isinstance(video_file, tuple): display_name, video = video_file
        else: display_name = video = video_file

        print("VERBOSE", f"Trying to play '{video}'...")
        if os.path.isfile(video):
            video_player.set_window(self["content"].handle)
            video_player.play_video(video)
            self.title = f"Video Player: {show_data['display_name'] + ' - ' if show_data and show_data['display_name'] else ''}{display_name}"
        else: print("WARNING", "Tried to play invalid file")

    def _on_show(self):
        print("VERBOSE", "Video player no longer hidden, continue playback")
        module.interpreter.put_command("video pause false")

    def _on_hide(self):
        print("VERBOSE", "Video player hidden, pause playback")
        module.interpreter.put_command("video pause true")

    def _register_events(self):
        video_player.EventPlay(self._on_play)
        video_player.EventPause(self._on_pause)
        video_player.EventPosition(self._on_pos_change)
        video_player.EventEndReached(self._on_stop)
        video_player.EventStop(self._on_stop)

    def _unregister_events(self):
        video_player.EventPlay(None)
        video_player.EventPause(None)
        video_player.EventPosition(None)
        video_player.EventEndReached(None)
        video_player.EventStop(None)

    def _on_play(self, _): self.schedule_task(task_id="on_play")
    def _execute_play(self):
        self["playpause_btn"].text = "Pause"
        self["backward_btn"].accept_input = self["forward_btn"].accept_input = True

    def _on_pause(self, _): self.schedule_task(task_id="on_pause")
    def _execute_pause(self): self["playpause_btn"].text = "Play"
    def _on_pos_change(self, e): self.schedule_task(task_id="pos_change", time=e.u.new_position)
    def _execute_pos_change(self, time): self["progress"].value = time * 10000

    def _on_stop(self, _): self.schedule_task(task_id="on_stop")
    def _execute_stop(self):
        self["progress"].value = 10000
        self["backward_btn"].accept_input = self["forward_btn"].accept_input = False