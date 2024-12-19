from core import modules
module = modules.Module(__package__)

from .fixture_data import FixtureData
from PyDMXControl.profiles.defaults import Fixture as DMXFixture

class Fixture:
    def __init__(self, fixture_data : str|FixtureData, start_channel=0):
        if isinstance(fixture_data, str): fixture_data = module.get_fixture_type_by_name(fixture_data)
        if not isinstance(fixture_data, FixtureData): raise TypeError("'fixture_data' parameter on Fixture needs to have type FixtureData")
        self._data = fixture_data
        self._fixture = DMXFixture(start_channel=int(start_channel))

    @property
    def data(self): return self._data
    @property
    def start_channel(self): return self._fixture.start_channel

    @property
    def pan(self) -> float:
        if self._data.has_pan:
            value1 = self._fixture.get_channel_value(self._data.pan.channel)
            if self._data.pan.is_extended:
                value2 = self._fixture.get_channel_value(self._data.pan.extended_channel)
                return self._data.pan.get_position_from_value((value1, value2))
            else: return self._data.pan.get_position_from_value(value1)
        return 0
    @pan.setter
    def pan(self, value : float):
        if self._data.has_pan:
            if self._data.pan.is_extended:
                value1, value2 = self._data.pan.get_value_from_position(value)
                self._fixture.set_channel(self._data.pan.channel, value1)
                self._fixture.set_channel(self._data.pan.extended_channel, value2)
            else: self._fixture.set_channel(self._data.pan.channel, self._data.pan.get_value_from_position(value))

    @property
    def tilt(self) -> float:
        if self._data.has_tilt:
            value1 = self._fixture.get_channel_value(self._data.tilt.channel)
            if self._data.tilt.is_extended:
                value2 = self._fixture.get_channel_value(self._data.tilt.extended_channel)
                return self._data.tilt.get_position_from_value((value1, value2))
            else: return self._data.tilt.get_position_from_value(value1)
        return 0
    @tilt.setter
    def tilt(self, value : float):
        if self._data.has_tilt:
            if self._data.tilt.is_extended:
                value1, value2 = self._data.tilt.get_value_from_position(value)
                self._fixture.set_channel(self._data.tilt.channel, value1)
                self._fixture.set_channel(self._data.tilt.extended_channel, value2)
            else: self._fixture.set_channel(self._data.tilt.channel, self._data.tilt.get_value_from_position(value))

    @property
    def color(self) -> str:
        return self._data.color.get_name_for_value(self._fixture.get_channel_value(self._data.color.channel)) if self._data.has_color else ""
    @color.setter
    def color(self, value : str):
        self._fixture.set_channel(self._data.color.channel, self._data.color.get_value_for_name(value))

    @property
    def gobo(self) -> str:
        return self._data.gobo.get_name_for_value(self._fixture.get_channel_value(self._data.gobo.channel)) if self._data.has_gobo else ""
    @gobo.setter
    def gobo(self, value : str):
        self._fixture.set_channel(self._data.gobo.channel, self._data.gobo.get_value_for_name(value))

    @property
    def shutter(self) -> int: return self._fixture.get_channel_value(self._data.shutter.channel) if self._data.has_shutter else 0
    @shutter.setter
    def shutter(self, value : int):
        if self._data.has_shutter: self._fixture.set_channel(self._data.shutter.channel, value)

    @property
    def strobe(self) -> int: return self._fixture.get_channel_value(self._data.strobe.channel) if self._data.has_strobe else 0
    @strobe.setter
    def strobe(self, value : int):
        if self._data.has_strobe: self._fixture.set_channel(self._data.strobe.channel, value)

    @property
    def intensity(self) -> int: return self._fixture.get_channel_value(self._data.intensity.channel) if self._data.has_intensity else 0
    @intensity.setter
    def intensity(self, value : int):
        if self._data.has_intensity: self._fixture.set_channel(self._data.intensity.channel, value)

    def to_json(self):
        return {
            "fixture_data": self._data.name,
            "start_channel": self._fixture.start_channel,
        }