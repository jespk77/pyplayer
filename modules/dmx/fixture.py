from core import modules
module = modules.Module(__package__)

from .dmx_controller import DMXController
from .fixture_data import FixtureData

class Fixture:
    def __init__(self, fixture_data : str|FixtureData, start_channel=1):
        if isinstance(fixture_data, str): fixture_data = module.get_fixture_type_by_name(fixture_data)
        if not isinstance(fixture_data, FixtureData): raise TypeError(f"'fixture_data' parameter on Fixture needs to have type FixtureData not {type(fixture_data).__name__}")
        self._data = fixture_data

        start_channel = int(start_channel)
        if start_channel < 1 or start_channel > 512: raise ValueError(f"start channel #{start_channel} out of range 1-512")
        self._start_channel = start_channel
        self._controller : DMXController = module.dmx

    @property
    def data(self): return self._data
    @property
    def start_channel(self): return self._start_channel
    @property
    def name(self): return f"{self.data.name}:{self.start_channel}"

    def _get_channel_value(self, channel):
        return self._controller.get_channel_value(self.start_channel + (channel - 1))

    def _set_channel_value(self, channel, value):
        print("set channel", channel, "to", value)
        self._controller.set_channel_value(self.start_channel + (channel - 1), value)

    @property
    def pan(self) -> float:
        if self._data.has_pan:
            value1 = self._get_channel_value(self._data.pan.channel)
            if self._data.pan.is_extended:
                value2 = self._get_channel_value(self._data.pan.extended_channel)
                return self._data.pan.get_position_from_value((value1, value2))
            else: return self._data.pan.get_position_from_value(value1)
        return 0
    @pan.setter
    def pan(self, value : float):
        if self._data.has_pan:
            if self._data.pan.is_extended:
                value1, value2 = self._data.pan.get_value_from_position(value)
                self._set_channel_value(self._data.pan.channel, value1)
                self._set_channel_value(self._data.pan.extended_channel, value2)
            else:
                value = self._data.pan.get_value_from_position(value)
                self._set_channel_value(self._data.pan.channel, value)

    @property
    def tilt(self) -> float:
        if self._data.has_tilt:
            value1 = self._get_channel_value(self._data.tilt.channel)
            if self._data.tilt.is_extended:
                value2 = self._get_channel_value(self._data.tilt.extended_channel)
                return self._data.tilt.get_position_from_value((value1, value2))
            else: return self._data.tilt.get_position_from_value(value1)
        return 0
    @tilt.setter
    def tilt(self, value : float):
        if self._data.has_tilt:
            if self._data.tilt.is_extended:
                value1, value2 = self._data.tilt.get_value_from_position(value)
                self._set_channel_value(self._data.tilt.channel, value1)
                self._set_channel_value(self._data.tilt.extended_channel, value2)
            else:
                value = self._data.tilt.get_value_from_position(value)
                self._set_channel_value(self._data.tilt.channel, value)

    @property
    def color(self) -> str:
        return self._data.color.get_name_for_value(self._get_channel_value(self._data.color.channel)) if self._data.has_color else ""
    @color.setter
    def color(self, value : str):
        if value is None: raise TypeError("value cannot be None")
        value = self._data.color.get_value_for_name(value)
        self._set_channel_value(self._data.color.channel, value)

    @property
    def gobo(self) -> str:
        return self._data.gobo.get_name_for_value(self._get_channel_value(self._data.gobo.channel)) if self._data.has_gobo else ""
    @gobo.setter
    def gobo(self, value : str):
        if value is None: raise TypeError("value cannot be None")
        value = self._data.gobo.get_value_for_name(value)
        self._set_channel_value(self._data.gobo.channel, value)

    @property
    def shutter(self): return self._get_channel_value(self._data.shutter.channel) if self._data.has_shutter else 0
    @shutter.setter
    def shutter(self, value):
        if self._data.has_shutter: self._set_channel_value(self._data.shutter.channel, value)

    @property
    def strobe(self): return self._get_channel_value(self._data.strobe.channel) if self._data.has_strobe else 0
    @strobe.setter
    def strobe(self, value):
        if self._data.has_strobe: self._set_channel_value(self._data.strobe.channel, int(value))

    @property
    def intensity(self): return self._get_channel_value(self._data.intensity.channel) if self._data.has_intensity else 0
    @intensity.setter
    def intensity(self, value):
        if self._data.has_intensity: self._set_channel_value(self._data.intensity.channel, value)

    def to_json(self):
        return {
            "fixture_data": self._data.name,
            "start_channel": self._start_channel,
        }

    def __repr__(self): return f"Fixture[data={self.data}, start_channel={self.start_channel}]"