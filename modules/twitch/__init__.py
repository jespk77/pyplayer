from utilities import messagetypes
from . import twitchoverview
import os

if not os.path.isdir(".cache"): os.mkdir(".cache")

# DEFAULT MODULE VARIABLES
interpreter = client = None

CLIENT_ID = "6adynlxibzw3ug8udhyzy6w3yt70pw"

def command_twitch(arg, argc):
    twitchoverview.create_window()
    return messagetypes.Reply("Openend twitch overview")

def initialize():
    twitchoverview.initialize(client, CLIENT_ID)

commands = {
    "twitch": {
        "": command_twitch
    }
}