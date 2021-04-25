class _MediaController:
    def bind(self, media_player): pass
    def attach_button(self, event, cb): pass

try:
    from winrt.windows.media.playback import MediaPlayer as WM
    from winrt.windows.media import MediaPlaybackStatus, MediaPlaybackType, SystemMediaTransportControlsButton

    class MediaControllerWin(_MediaController):
        def __init__(self):
            self._wplayer = WM()
            self._win_controls = self._wplayer.system_media_transport_controls
            self._win_controls.is_next_enabled = self._win_controls.is_previous_enabled = True
            self._win_controls.is_pause_enabled = self._win_controls.is_play_enabled = False
            self._win_controls.is_enabled = self._win_controls.is_stop_enabled = True
            self._win_controls.add_button_pressed(self._on_button_press)

            self._win_display = self._win_controls.display_updater
            self._win_display.type = MediaPlaybackType.MUSIC
            self._events = {}
            self._update_data("PyPlayer")

        def bind(self, media_player):
            media_player.attach_event("media_changed", self._on_update)
            media_player.attach_event("playing", self._on_play)
            media_player.attach_event("paused", self._on_pause)
            media_player.attach_event("stopped", self._on_stop)
            media_player.attach_event("end_reached", self._on_stop)

        def attach_button(self, event, cb):
            """ Attach the given callback to one of the buttons """
            self._events[event] = cb

        def _call_button(self, event):
            cb = self._events.get(event)
            if cb:
                print("VERBOSE", f"Calling event for button '{event}'")
                try: cb()
                except Exception as e: print("ERROR", f"Calling MediaController event {event}:", e)

        def _update_data(self, title="", artist=""):
            self._win_display.music_properties.artist = artist
            self._win_display.music_properties.title = title
            self._win_display.update()

        def _on_button_press(self, sender, event):
            btn = event.button
            if btn == SystemMediaTransportControlsButton.PLAY: self._call_button("play")
            elif btn == SystemMediaTransportControlsButton.PAUSE: self._call_button("pause")
            elif btn == SystemMediaTransportControlsButton.STOP: self._call_button("stop")
            elif btn == SystemMediaTransportControlsButton.NEXT: self._call_button("next")
            elif btn == SystemMediaTransportControlsButton.PREVIOUS: self._call_button("previous")

        def _on_update(self, event, player):
            song = player.current_media.display_name.split(" - ", maxsplit=1)
            if len(song) > 1: self._update_data(artist=song[0], title=song[1])
            else: self._update_data(title=song[0])

        def _on_play(self, event, player):
            self._win_controls.is_pause_enabled = self._win_controls.is_play_enabled = True
            self._win_controls.playback_status = MediaPlaybackStatus.PLAYING

        def _on_pause(self, event, player):
            self._win_controls.is_pause_enabled = self._win_controls.is_play_enabled = True
            self._win_controls.playback_status = MediaPlaybackStatus.PAUSED

        def _on_stop(self, event, player):
            self._win_controls.is_pause_enabled = self._win_controls.is_play_enabled = False
            self._win_controls.playback_status = MediaPlaybackStatus.STOPPED

    print("INFO", "Initializing Windows Media controller")
    controller = MediaControllerWin()
except ImportError:
    print("INFO", "No controller class found, initializing default one")
    controller = _MediaController()