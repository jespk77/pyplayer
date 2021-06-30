import os, random
from collections import namedtuple

from core import messagetypes, modules
module = modules.Module(__package__)

from . import videoplayer
video_player = videoplayer.video_player

def get_displayname(path): return os.path.splitext(path)[0]

def show_video_window(video=None, show=None):
    window = module.client.find_window(videoplayer.VideoPlayerWindow.window_id)
    if window is None: module.client.add_window(window_class=videoplayer.VideoPlayerWindow, video_file=video, show=show)
    else: window.play(video)

def get_tvshow_seasons(show):
    if os.path.isdir(show['$path']): return [path.path for path in os.scandir(show['$path']) if path.is_dir()]
    else: return []

def get_episode_list(season):
    if os.path.isdir(season): return [(get_displayname(ep), os.path.join(season, ep)) for ep in os.listdir(season)]
    else: return []

def get_tvshow_episodes(show, season=None):
    seasons = get_tvshow_seasons(show)
    if len(seasons) == 0: return seasons

    if season:
        try: return get_episode_list(seasons[season - 1])
        except IndexError: return []
    else: return sum([get_episode_list(s) for s in seasons], [])

ShowSelection = namedtuple("ShowSelection", ["show", "season", "episode"], defaults=[None,None])
def parse_arg(arg, argc):
    if argc > 0:
        show_data = module.configuration.get(f"shows::{arg[0]}")
        if show_data is not None: return ShowSelection(show=show_data, season=int(arg[1]) if argc > 1 else "", episode=arg[2] if argc > 2 else "")
    return None, None, None

def play_video(video, path, show):
    if video is not None and path is not None:
        show_video_window((video,path), show)
        return messagetypes.Reply(f"Now playing '{video}'")
    else: return messagetypes.Reply("No episode found")

def command_tvshow(arg, argc):
    try: show, season, episode = parse_arg(arg, argc)
    except ValueError: return messagetypes.Reply("Invalid season number")
    if show is None: return messagetypes.Reply("Unknown show")

    videos = get_tvshow_episodes(show, season)
    if len(videos) == 0: return messagetypes.Reply("No episodes found")

    try: v = videos[int(episode) - 1]
    except (ValueError,IndexError):
        matches = [v for v in videos if episode in v[0].split(" - ", maxsplit=1)[0]]
        if len(matches) > 0: return messagetypes.Select("Multiple episodes found", play_video, matches, show=show)
    else: return play_video(*v, show)
    return messagetypes.Reply("No episode found")

def command_tvshow_random(arg, argc):
    try: show, season, _ = parse_arg(arg, argc)
    except ValueError: return messagetypes.Reply("Invalid season number")
    if show is None: return messagetypes.Reply("Unknown show")

    videos = get_tvshow_episodes(show, season)
    if len(videos) == 0: return messagetypes.Reply("No episodes found")

    video = random.choice(videos)
    show_video_window(video, show)
    return messagetypes.Reply(f"Now playing '{video[0]}'")

def command_tvshow_start(arg, argc):
    try: show, _, _ = parse_arg(arg, argc)
    except ValueError: return messagetypes.Reply("Invalid season number")
    if show is None: return messagetypes.Reply("Unknown show")

    module.configuration[f"shows::{arg[0]}::_episode"] = 0
    name = show["display_name"] if show["display_name"] else arg[0]
    return messagetypes.Reply(f"Started new series for '{name}'")

def command_tvshow_stop(arg, argc):
    try: show, _, _ = parse_arg(arg, argc)
    except ValueError: return messagetypes.Reply("Invalid season number")
    if show is None: return messagetypes.Reply("Unknown show")

    try: del module.configuration[f"shows::{arg[0]}::_episode"]
    except KeyError: pass
    name = show["display_name"] if show["display_name"] else arg[0]
    return messagetypes.Reply(f"Stopped series for '{name}'")

def command_tvshow_continue(arg, argc):
    try: show, _, _ = parse_arg(arg, argc)
    except ValueError: return messagetypes.Reply("Invalid season number")
    if show is None: return messagetypes.Reply("Unknown show")

    try: index = show["_episode"]
    except KeyError: index = 0
    videos = get_tvshow_episodes(show)
    module.configuration[f"shows::{arg[0]}::_episode"] = index + 1

    try:
        video = videos[index]
        show_video_window(video, module.configuration.get(f"shows::{arg[0]}"))
        return messagetypes.Reply(f"Now playing '{video[0]}'")
    except IndexError: return messagetypes.Reply("End of series reached")

def command_video_pause(arg, argc):
    video_player.pause_video(arg[0] if argc > 0 else None)
    return messagetypes.Empty()

def command_video_stop(arg, argc):
    video_player.stop_video()
    return messagetypes.Empty()

def _move_cb(arg, callback):
    if arg[0].startswith("+"):
        try: callback(float(arg[1:]))
        except ValueError: return messagetypes.Reply("Invalid number")
        else: return messagetypes.Reply("Video player time set forward")
    elif arg[0].startswith("-"):
        try: callback(-float(arg[1:]))
        except ValueError: return messagetypes.Reply("Invalid number")
        else: return messagetypes.Reply("Video player time set backward")

def command_video_pos(arg, argc):
    if argc > 0:
        move = _move_cb(arg[0], video_player.move_position)
        if move is not None: return move

        try: video_player.position = float(arg[0])
        except ValueError: return messagetypes.Reply("Invalid number")
        else: return messagetypes.Reply("Video player position updated")

def command_video_time(arg, argc):
    if argc > 0:
        move = _move_cb(arg[0], video_player.move_time)
        if move is not None: return move

        try: video_player.time = float(arg[0])
        except ValueError: return messagetypes.Reply("Invalid number")
        else: return messagetypes.Reply("Video player time updated")


module.commands = {
    "tvshow": {
        "": command_tvshow,
        "continue": command_tvshow_continue,
        "random": command_tvshow_random,
        "start": command_tvshow_start,
        "stop": command_tvshow_stop
    },
    "video": {
        "pause": command_video_pause,
        "position": command_video_pos,
        "stop": command_video_stop,
        "time": command_video_time
    }
}

@module.Initialize
def init():
    module.configuration.get_or_create("#progressbar_color", "#00ffff")
    cfg = module.configuration.get_or_create_configuration("shows", {})
    cfg.default_value = {"$path": "", "display_name": ""}

@module.Destroy
def destroy():
    video_player.destroy()