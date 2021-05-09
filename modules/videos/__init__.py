import os, random
from collections import namedtuple

from core import messagetypes, modules
module = modules.Module(__package__)

from . import videoplayer
video_player = videoplayer.video_player

def get_displayname(path): return os.path.splitext(path)[0]

def show_video_window(video=None):
    window = module.client.find_window(videoplayer.VideoPlayerWindow.window_id)
    if window is None: module.client.add_window(window_class=videoplayer.VideoPlayerWindow, video_file=video)
    else: window.play(video)

def get_tvshow_seasons(show):
    dr = module.configuration.get(f"shows::{show}")
    if dr is not None: return [path.path for path in os.scandir(dr['$path']) if path.is_dir()]
    else: return None

def get_episode_list(season): return [(get_displayname(ep), os.path.join(season, ep)) for ep in os.listdir(season)]
def get_tvshow_episodes(show, season=None):
    seasons = get_tvshow_seasons(show)
    if seasons is not None:
        if season is not None: return get_episode_list(seasons[season - 1])
        else: return sum([get_episode_list(s) for s in seasons], [])
    else: return None

ShowSelection = namedtuple("ShowSelection", ["show", "season", "episode"], defaults=[None,None])
def parse_arg(arg, argc):
    if argc > 1:
        show, sel = arg[0], arg[1]
        return ShowSelection(show=show, season=int(sel[0]), episode=sel[1:])
    elif argc == 1: return ShowSelection(show=arg[0])
    else: return None, None

def command_tvshow(arg, argc):
    show, season, episode = parse_arg(arg, argc)
    videos = get_tvshow_episodes(show, season)
    if videos is None: return messagetypes.Reply("Unknown show")
    if len(videos) == 0: return messagetypes.Reply("No episodes found")

    for v in videos:
        if v[0].startswith(episode):
            show_video_window(v)
            return messagetypes.Reply(f"Now playing '{v[0]}'")
    return messagetypes.Reply("No episode found")

def command_tvshow_random(arg, argc):
    show, season, _ = parse_arg(arg, argc)
    videos = get_tvshow_episodes(show, season)
    if videos is None: return messagetypes.Reply("Unknown show")
    if len(videos) == 0: return messagetypes.Reply("No episodes found")

    video = random.choice(videos)
    show_video_window(video)
    return messagetypes.Reply(f"Now playing '{video[0]}'")

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

        try: video_player.position = arg[0]
        except ValueError: return messagetypes.Reply("Invalid number")
        else: return messagetypes.Reply("Video player position updated")

def command_video_time(arg, argc):
    if argc > 0:
        move = _move_cb(arg[0], video_player.move_time)
        if move is not None: return move

        try: video_player.time = arg[0]
        except ValueError: return messagetypes.Reply("Invalid number")
        else: return messagetypes.Reply("Video player time updated")


module.commands = {
    "tvshow": {
        "": command_tvshow,
        "random": command_tvshow_random,
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
    cfg = module.configuration.get_or_create_configuration("shows", {})
    cfg.default_value = {"$path": "", "display_name": ""}

@module.Destroy
def destroy():
    video_player.destroy()