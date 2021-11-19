import os, random
from collections import namedtuple

from core import messagetypes, modules
module = modules.Module(__package__)

from . import videoplayer
video_player = videoplayer.video_player

def get_displayname(path): return os.path.splitext(path)[0]

def show_video_window(video=None, show=None, series_index=-1):
    window = module.client.find_window(videoplayer.VideoPlayerWindow.window_id)
    if window is None: module.client.add_window(window_class=videoplayer.VideoPlayerWindow, video_file=video, show=show, series_index=series_index)
    else: window.play(video, show, series_index)

def get_tvshow_seasons(show):
    show = module.configuration["shows"].get(show)
    if show is not None and os.path.isdir(show['$path']): return [path.path for path in os.scandir(show['$path']) if path.is_dir()]
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
        if arg[0] in module.configuration["shows"]: return ShowSelection(show=arg[0], season=int(arg[1]) if argc > 1 else "", episode=arg[2] if argc > 2 else "")
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
    module.configuration.save()
    return command_tvshow_continue(arg, argc)

def command_tvshow_stop(arg, argc):
    try: show, _, _ = parse_arg(arg, argc)
    except ValueError: return messagetypes.Reply("Invalid season number")
    if show is None: return messagetypes.Reply("Unknown show")
    show_data = module.configuration["shows"].get(show)

    try:
        del module.configuration[f"shows::{arg[0]}::_episode"]
        module.configuration.save()
    except KeyError: pass
    name = show_data["display_name"] if show_data["display_name"] else arg[0]
    return messagetypes.Reply(f"Stopped series for '{name}'")

def command_tvshow_continue(arg, argc):
    try: show, _, _ = parse_arg(arg, argc)
    except ValueError: return messagetypes.Reply("Invalid season number")
    if show is None: return messagetypes.Reply("Unknown show")
    show_data = module.configuration["shows"].get(show)
    if "_episode" not in show_data: return messagetypes.Reply("No series active")

    try: index = show_data["_episode"]
    except KeyError: index = 0
    videos = get_tvshow_episodes(show)

    try:
        video = videos[index]
        show_video_window(video, arg[0], index)
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

def command_video_next_frame(arg, argc):
    video_player.next_frame()
    return messagetypes.Reply("Video player next frame shown")


module.commands = {
    "tvshow": {
        "": command_tvshow,
        "continue": command_tvshow_continue,
        "random": command_tvshow_random,
        "start": command_tvshow_start,
        "stop": command_tvshow_stop
    },
    "video": {
        "next_frame": command_video_next_frame,
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
    cfg.default_value = {"$path": "", "display_name": "", "intro_time": 10}

@module.Destroy
def destroy():
    video_player.destroy()