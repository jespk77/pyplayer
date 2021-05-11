import os

import vlc

class VideoPlayer:
    def __init__(self):
        self._vlc = vlc.MediaPlayer()

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
    def time(self, time): self._vlc.set_time(float(time) * 1000)

    @property
    def position(self): return self._vlc.get_position()
    @position.setter
    def position(self, pos): self._vlc.set_position(float(pos))

    def move_time(self, time):
        if self._vlc.is_playing():
            time = round(time * 1000)
            print("VERBOSE", f"Moving play time {time} s...")
            self._vlc.set_time(self._vlc.get_time() + time)

    def move_position(self, pos):
        if self._vlc.is_playing():
            print("VERBOSE", f"Moving current position {pos*100}%...")
            self._vlc.set_position(self._vlc.get_position() + pos)

video_player = VideoPlayer()
from ui.qt import pywindow, pyelement

from core import modules
module = modules.Module(__package__)

class VideoPlayerWindow(pywindow.PyWindow):
    window_id = "video_player_window"

    def __init__(self, parent, video_file=None):
        pywindow.PyWindow.__init__(self, parent, self.window_id)
        self.title = "Video Player"
        self.icon = "assets/icon_video"
        self.layout.row(0, weight=1).column(0, weight=1).column(4, weight=1)

        self.events.EventWindowHide(self._on_hide)
        self.events.EventWindowShow(self._on_show)
        self.events.EventWindowClose(self._on_close)

        self.add_task("play_video", self._play)
        if video_file is not None: self.play(video_file)

    def create_widgets(self):
        self.add_element("content", element_class=pyelement.PyLabelFrame, columnspan=5)
        self.add_element("filler1", element_class=pyelement.PyFrame, row=1)

        btn = self.add_element("backward_btn", element_class=pyelement.PyButton, row=1, column=1)
        btn.text = "<<"
        btn.events.EventInteract(self.backward)
        btn2 = self.add_element("playpause_btn", element_class=pyelement.PyButton, row=1, column=2)
        btn2.text = "Pause"
        btn2.events.EventInteract(self.pause)
        btn3 = self.add_element("forward_btn", element_class=pyelement.PyButton, row=1, column=3)
        btn3.text = ">>"
        btn3.events.EventInteract(self.forward)
        self.add_element("filler2", element_class=pyelement.PyFrame, row=1, column=4)

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

    def play(self, video_file): self.schedule_task(task_id="play_video", video_file=video_file)
    def pause(self): module.interpreter.put_command("video pause")
    def stop(self): module.interpreter.put_command("video stop")
    def forward(self, amount=5): module.interpreter.put_command(f"video time +{amount}")
    def backward(self, amount=5): module.interpreter.put_command(f"video time -{amount}")

    def _on_close(self): self.stop()

    def _play(self, video_file):
        if isinstance(video_file, tuple): display_name, video = video_file
        else: display_name = video = video_file

        print("VERBOSE", f"Trying to play '{video}'...")
        if os.path.isfile(video):
            video_player.set_window(self["content"].handle)
            video_player.play_video(video)
            self.title = f"Video Player: {display_name}"
        else: print("WARNING", "Tried to play invalid file")

    def _on_show(self):
        print("VERBOSE", "Video player no longer hidden, continue playback")
        module.interpreter.put_command("video pause false")

    def _on_hide(self):
        print("VERBOSE", "Video player hidden, pause playback")
        module.interpreter.put_command("video pause true")