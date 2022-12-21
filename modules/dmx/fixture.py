import json, os
from datetime import datetime
from typing import Union, Tuple, List

from PyDMXControl.profiles.Generic import Custom as DMXFixture

class Fixture(DMXFixture):
    template_path = "fixtures"

    def __init__(self, template, start_channel):
        self._template_data = {}
        self._load_template(template)
        DMXFixture.__init__(self, channels=self._template_data["channels"], start_channel=start_channel)

    def _load_template(self, template):
        if not os.path.isdir(self.template_path): os.mkdir(self.template_path)

        template_file = os.path.join(self.template_path, template)
        try:
            with open(template_file) as file: self._data = json.load(file)
            return True
        except FileNotFoundError: pass
        except Exception as e: print("ERROR", f"Loading template '{template_file}':", e)
        raise ValueError(f"Invalid template provided: '{template}'")

    ##########################
    # the package uses 0 based index but DMX uses 1 based index so all indices need a conversion
    def has_channel(self, channel: Union[str, int]) -> bool:
        if isinstance(channel, int): channel -= 1
        return DMXFixture.has_channel(self, channel)
    __contains__ = has_channel

    def get_channel_id(self, channel: Union[str, int]) -> int:
        if isinstance(channel, int): channel -= 1
        return DMXFixture.get_channel_id(self, channel)

    def get_channel_value(self, channel: Union[str, int]) -> Tuple[int, datetime]:
        if isinstance(channel, int): channel -= 1
        return DMXFixture.get_channel_value(self, channel)
    __getitem__ = get_channel_value

    def set_channel(self, channel: Union[str, int], value: int) -> 'DMXFixture':
        if isinstance(channel, int): channel -= 1
        return DMXFixture.set_channel(self, channel, value)
    __setitem__ = set_channel

    def set_channels(self, *args: Union[int, List[int], None], **kwargs) -> 'DMXFixture':
        if "start" in kwargs: kwargs["start"] += 1
        return DMXFixture.set_channels(self, *args, **kwargs)
    ##########################

    def set_all_values(self):
        """ Sets all channels to the current value again, used to make sure the connection stays alive """
        DMXFixture.set_channels(self.__channels)