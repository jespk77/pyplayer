import os
import vlc

class VideoPlayer:
    def __init__(self):
        self._vlc = vlc.MediaPlayer()
        self._handle = 0
        self._spu_index = -1

        self._events = {}
        event_manager = self._vlc.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda e: self._call_event("end_reached", e))
        event_manager.event_attach(vlc.EventType.MediaPlayerPaused, lambda e: self._call_event("pause", e))
        event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_play)
        event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, lambda e: self._call_event("pos_changed", e))
        event_manager.event_attach(vlc.EventType.MediaPlayerStopped, lambda e: self._call_event("stopped", e))

    def destroy(self):
        print("VERBOSE", "Releasing video player instance")
        self._vlc.release()

    def set_window(self, handle):
        print("VERBOSE", "Updated video player window handle")
        handle = int(handle)
        self._handle = handle
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
            self._vlc.set_hwnd(self._handle)

    def next_frame(self):
        self._vlc.next_frame()

    def restart_video(self):
        self._vlc.set_media(self._vlc.get_media())
        self._vlc.play()

    def stop_video(self):
        print("VERBOSE", "Stopped video playback")
        self._vlc.stop()

    def reset(self):
        print("VERBOSE", "Resetting video player")
        pos, media = self._vlc.get_position(), self._vlc.get_media()
        self._vlc.stop()
        if media is not None:
            self._vlc.set_media(media)
            self._vlc.play()
            self._vlc.set_position(pos)

    @property
    def time(self): return self._vlc.get_time() / 1000
    @time.setter
    def time(self, time):
        if self.playing:
            time = round(time * 1000)
            print("VERBOSE", f"Updating play time to {time}ms...")
            self._vlc.set_time(time)

    @property
    def position(self): return self._vlc.get_position()
    @position.setter
    def position(self, pos):
        if self.playing:
            print("VERBOSE", f"Updating play position to {pos*100}%...")
            self._vlc.set_position(pos)

    @property
    def subtitle_index(self): return self._vlc.video_get_spu()
    @subtitle_index.setter
    def subtitle_index(self, index):
        self._spu_index = index
        self._vlc.video_set_spu(index)
    def subtitle_count(self): return self._vlc.video_get_spu_count()

    def move_time(self, time):
        if self._vlc.is_playing():
            time = round(time * 1000)
            print("VERBOSE", f"Moving play time {time}ms...")
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

    def _on_play(self, event):
        self.subtitle_index = self._spu_index
        self._call_event("play", event)

    def _register_event(self, event_id, cb):
        if cb is not None:
            print("VERBOSE", f"Registering new event handler for '{event_id}'...")
            if not callable(cb): raise TypeError("Event handler must be callable")
            self._events[event_id] = cb
            return cb
        else:
            print("VERBOSE", f"Unregistering event handler for '{event_id}'...")
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
    episode_update_position = 0.95

    def __init__(self, parent, video_file=None, show=None, series_index=-1):
        pywindow.PyWindow.__init__(self, parent, self.window_id)
        self.title = "Video Player"
        self.icon = "assets/icon_video"
        self.layout.row(0, weight=1).column(1, weight=1).column(6, weight=1)

        self.events.EventWindowHide(self._on_hide)
        self.events.EventWindowShow(self._on_show)
        self.events.EventWindowClose(self._on_close)

        self.add_task("play_video", self._play)
        self.add_task("on_play", self._execute_play)
        self.add_task("on_pause", self._execute_pause)
        self.add_task("pos_change", self._execute_pos_change)
        self.add_task("on_stop", self._execute_stop)
        self._register_events()

        self._playing = self._pause_minimize = self._ended = False
        self._show_id = show
        self._updated, self._series_index = True, series_index
        if video_file is not None: self.play(video_file, show, series_index)

    def create_widgets(self):
        self.add_element("content", element_class=pyelement.PyLabelFrame, columnspan=8)

        progress = self.add_element("progress", element_class=pyelement.PyProgessbar, row=1, columnspan=8)
        progress.minimum, progress.value, progress.maximum = 0, 0, 10000
        progress.color = module.configuration.get("#progressbar_color")
        @progress.events.EventInteract
        def _on_click(position): module.interpreter.put_command(f"video position {position}")

        btn = self.add_element("prev_episode_btn", element_class=pyelement.PyButton, row=2, column=0)
        btn.text, btn.hidden = "Previous episode", True
        btn.events.EventInteract(lambda : self._add_episode(-1))

        btn1 = self.add_element("backward_btn", element_class=pyelement.PyButton, row=2, column=2)
        btn1.text, btn1.accept_input = "<<", False
        btn1.events.EventInteract(self.backward)
        btn2 = self.add_element("playpause_btn", element_class=pyelement.PyButton, row=2, column=3)
        btn2.text, btn2.accept_input = "Play", True
        btn2.events.EventInteract(self._on_play_btn)
        btn2.events.EventRightClick(self._reset)
        next_frame_btn = self.add_element("next_frame_btn", element_class=pyelement.PyButton, row=2, column=4)
        next_frame_btn.text, next_frame_btn.accept_input = "Frame >", False
        next_frame_btn.events.EventInteract(self.next_frame)
        btn3 = self.add_element("forward_btn", element_class=pyelement.PyButton, row=2, column=5)
        btn3.text, btn3.accept_input = ">>", False
        btn3.events.EventInteract(self.forward)

        btn4 = self.add_element("next_episode_btn", element_class=pyelement.PyButton, row=2, column=7)
        btn4.text, btn4.hidden = "Next episode", True
        btn4.events.EventInteract(lambda : self._add_episode(1))

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

        @self.events.EventKeyDown("PageDown")
        def _forward_intro():
            if self.show_data is not None:
                self.forward(self.show_data.get("intro_time", 10))
            return self.events.block_action

        @self.events.EventKeyDown("E")
        def _next_frame():
            self.next_frame()
            return self.events.block_action

        @self.events.EventKeyDown("Slash")
        def _quick_minimize():
            self.minimized = True
            return self.events.block_action

        @self.events.EventKeyDown("V")
        def _show_subtitles():
            video_player.subtitle_index = video_player.subtitle_count() if video_player.subtitle_index < 0 else -1
            return self.events.block_action

    def play(self, video_file, show_id=None, series_index=-1):
        self.schedule_task(task_id="play_video", video_file=video_file, show_id=show_id, series_index=series_index)

    @staticmethod
    def pause(): module.interpreter.put_command("video pause")
    @staticmethod
    def stop(): module.interpreter.put_command("video stop")
    @staticmethod
    def forward(amount=5): module.interpreter.put_command(f"video time +{amount}")
    @staticmethod
    def backward(amount=5): module.interpreter.put_command(f"video time -{amount}")
    @staticmethod
    def next_frame(): module.interpreter.put_command("video next_frame")

    @property
    def show_data(self): return module.configuration["shows"].get(self._show_id, {})

    @property
    def episode_index(self): return self.show_data.get("_episode", -1) if self._series_index >= 0 else -1
    @episode_index.setter
    def episode_index(self, index):
        index = max(index, 0)
        module.configuration[f"shows::{self._show_id}::_episode"] = index
        module.configuration.save()

    def _add_episode(self, index=1, play_next=True):
        if self._series_index >= 0 and index != 0:
            self.episode_index = self._series_index + index
            if play_next: module.interpreter.put_command(f"tvshow continue {self._show_id}")

    def _on_close(self):
        self.stop()
        self._unregister_events()

    def _play(self, video_file, show_id, series_index):
        if isinstance(video_file, tuple): display_name, video = video_file
        else: display_name = video = video_file
        self._show_id = show_id
        self._updated, self._series_index = True, series_index

        print("VERBOSE", f"Trying to play '{video}'...")
        if os.path.isfile(video):
            video_player.set_window(self["content"].handle)
            video_player.play_video(video)
            show_data = self.show_data
            self.title = f"{show_data['display_name'] + ' | ' if show_data and show_data['display_name'] else ''}{display_name}"
            self.activate()

            self["next_episode_btn"].hidden = self["prev_episode_btn"].hidden = self._series_index < 0
        else: print("WARNING", "Tried to play invalid file")

    def _on_show(self):
        if self._pause_minimize:
            print("VERBOSE", "Video player no longer hidden, continue playback")
            module.interpreter.put_command("video pause false")
            self._pause_minimize = False
        video_player.set_window(self["content"].handle)

    def _on_hide(self):
        if self._playing:
            print("VERBOSE", "Video player hidden, pause playback")
            module.interpreter.put_command("video pause true")
            self._pause_minimize = True

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

    def _reset(self):
        video_player.reset()

    def _on_play_btn(self):
        if self._ended: video_player.restart_video()
        else: self.pause()

    def _on_play(self, _): self.schedule_task(task_id="on_play")
    def _execute_play(self):
        self["playpause_btn"].text = "Pause"
        self["backward_btn"].accept_input = self["forward_btn"].accept_input = self["next_frame_btn"].accept_input = True
        self._playing = True
        self._ended = False

    def _on_pause(self, _): self.schedule_task(task_id="on_pause")
    def _execute_pause(self):
        self["playpause_btn"].text = "Play"
        self._playing = False

    def _on_pos_change(self, e): self.schedule_task(task_id="pos_change", time=video_player.position)
    def _execute_pos_change(self, time):
        self["progress"].value = time * 10000
        if self._updated and time > self.episode_update_position:
            self._updated = False
            if self._series_index >= 0:
                print("VERBOSE", "Update position in the episode reached, increasing index")
                self._add_episode(1, False)

    def _on_stop(self, _): self.schedule_task(task_id="on_stop")
    def _execute_stop(self):
        self["playpause_btn"].text = "Play"
        self["progress"].value = 10000
        self["backward_btn"].accept_input = self["forward_btn"].accept_input = self["next_frame_btn"].accept_input = False
        self._ended = True