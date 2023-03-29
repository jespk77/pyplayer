from core import modules, messagetypes
module = modules.Module(__package__)

from . import chatwindow

def open_chat_gpt(arg, argc):
    module.client.schedule_task(task_id=open_window_id)
    return messagetypes.Reply("Chat window opened")

module.commands = {
    "chatgpt": open_chat_gpt
}

open_window_id = "chatgpt_window_open"
def _open_chat_window():
    if not module.client.find_window(window_id=chatwindow.ChatGPTWindow.main_window_id):
        module.client.add_window(window_class=chatwindow.ChatGPTWindow)

@module.Initialize
def inititalize():
    module.configuration.set_defaults({"api_key": "", "organization_id": ""})
    module.client.add_task(task_id=open_window_id, func=_open_chat_window)