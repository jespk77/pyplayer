import json, os.path

from .dmx import DMXChannel, DMXPositionChannel, DMXValueChannel

class FixtureData:
    PATH = ".fixtures/data", "{name}.fxt"
    _fixtures = {}

    @staticmethod
    def get_fixtures(reload=False):
        fixtures = []
        if reload or not FixtureData._fixtures:
            try:
                for item in os.scandir(FixtureData.PATH[0]):
                    if item.is_file() and item.name.endswith(".fxt"):
                        fixtures.append(FixtureData(item.name.split(".")[0]))
            except FileNotFoundError: pass
        else: fixtures.extend(FixtureData._fixtures.values())
        return fixtures

    @staticmethod
    def remove_fixture(name):
        if fixture := FixtureData._fixtures.get(name):
            fixture.remove()

    def __new__(cls, name, *args, **kwargs):
        fixture = FixtureData._fixtures.get(name)
        if fixture: return fixture

        instance = super().__new__(cls)
        try:
            with open(FixtureData.get_filename(name), "r") as file:
                instance.__init__(name, **json.load(file))
        except FileNotFoundError:
            instance.__init__(name, *args, **kwargs)
        FixtureData._fixtures[name] = instance
        return instance

    def __init__(self, name : str, display_name="", channel_count=1, pan : DMXPositionChannel|dict=None, tilt : DMXPositionChannel|dict=None,
                 color : DMXValueChannel|dict=None, gobo : DMXValueChannel|dict=None,
                 shutter : DMXChannel|dict=None, strobe : DMXChannel|dict=None, intensity : DMXChannel|dict=None):
        if hasattr(self, "name"): return # already initialized

        self._name = name
        self.display_name = display_name if display_name else name
        self.channel_count = channel_count
        self._pan = DMXPositionChannel(**pan) if isinstance(pan, dict) else pan
        self._tilt = DMXPositionChannel(**tilt) if isinstance(tilt, dict) else tilt
        self._color = DMXValueChannel(**color) if isinstance(color, dict) else color
        self._gobo = DMXValueChannel(**gobo) if isinstance(gobo, dict) else gobo
        self._shutter = DMXChannel(**shutter) if isinstance(shutter, dict) else shutter
        self._strobe = DMXChannel(**strobe) if isinstance(strobe, dict) else strobe
        self._intensity = DMXChannel(**intensity) if isinstance(intensity, dict) else intensity

    @property
    def name(self): return self._name
    @staticmethod
    def get_filename(name): return os.path.join(FixtureData.PATH[0], FixtureData.PATH[1].format(name=name))
    @property
    def filename(self): return self.get_filename(self.name)

    @staticmethod
    def _check_property_type(property_name, value, property_type : type):
        if value is not None:
            if isinstance(value, dict): value = property_type(**value)

            if type(value) != property_type:
                raise TypeError(f"'{property_name}' on fixture data when not None must have type '{property_type.__name__}'")
        return value

    @property
    def has_pan(self): return self._pan is not None and self._pan.is_valid
    @property
    def pan(self):
        # make one if it doesn't exist so data can still be set
        if self._pan is None: self._pan = DMXPositionChannel("pan")
        return self._pan
    @pan.setter
    def pan(self, value):
        value = self._check_property_type("pan", value, DMXPositionChannel)
        self._pan = value

    @property
    def has_tilt(self): return self._tilt is not None and self._tilt.is_valid
    @property
    def tilt(self):
        # make one if it doesn't exist so data can still be set
        if self._tilt is None: self._tilt = DMXPositionChannel("tilt")
        return self._tilt
    @tilt.setter
    def tilt(self, value):
        value = self._check_property_type("tilt", value, DMXPositionChannel)
        self._tilt = value

    @property
    def has_color(self): return self._color is not None and self._color.is_valid
    @property
    def color(self):
        # make one if it doesn't exist so data can still be set
        if self._color is None: self._color = DMXValueChannel("color")
        return self._color
    @color.setter
    def color(self, value):
        value = self._check_property_type("color", value, DMXValueChannel)
        self._color = value

    @property
    def has_gobo(self): return self._gobo is not None and self._gobo.is_valid
    @property
    def gobo(self):
        # make one if it doesn't exist so data can still be set
        if self._gobo is None: self._gobo = DMXValueChannel("gobo")
        return self._gobo
    @gobo.setter
    def gobo(self, value):
        value = self._check_property_type("gobo", value, DMXValueChannel)
        self._gobo = value

    @property
    def has_shutter(self): return self._shutter is not None and self._shutter.is_valid
    @property
    def shutter(self):
        # make one if it doesn't exist so data can still be set
        if self._shutter is None: self._shutter = DMXChannel("shutter")
        return self._shutter
    @shutter.setter
    def shutter(self, value):
        value = self._check_property_type("shutter", value, DMXChannel)
        self._shutter = value

    @property
    def has_strobe(self): return self._strobe is not None and self._strobe.is_valid
    @property
    def strobe(self):
        # make one if it doesn't exist so data can still be set
        if self._strobe is None: self._strobe = DMXChannel("strobe")
        return self._strobe
    @strobe.setter
    def strobe(self, value):
        value = self._check_property_type("strobe", value, DMXChannel)
        self._strobe = value

    @property
    def has_intensity(self): return self._intensity is not None and self._intensity.is_valid
    @property
    def intensity(self):
        # make one if it doesn't exist so data can still be set
        if self._intensity is None: self._intensity = DMXChannel("intensity")
        return self._intensity
    @intensity.setter
    def intensity(self, value):
        value = self._check_property_type("intensity", value, DMXChannel)
        self._intensity = value

    def save(self, name=""):
        if not self._name:
            if name: self._name = name
            else: raise ValueError("Cannot save a fixture without a name")

        for fixture in FixtureData._fixtures.values():
            if fixture is self: continue
            if fixture.name == self.name: raise ValueError("Another fixture with the same name already exists")

        data = {}
        if self.display_name: data["display_name"] = self.display_name
        if self.channel_count > 0: data["channel_count"] = self.channel_count
        if self.has_pan: data["pan"] = self.pan.to_json()
        if self.has_tilt: data["tilt"] = self.tilt.to_json()
        if self.has_color: data["color"] = self.color.to_json()
        if self.has_gobo: data["gobo"] = self.gobo.to_json()
        if self.has_shutter: data["shutter"] = self.shutter.to_json()
        if self.has_strobe: data["strobe"] = self.strobe.to_json()
        if self.has_intensity: data["intensity"] = self.intensity.to_json()
        if not data:
            print("VERBOSE", f"Skip saving fixture '{self.name}' since it has no data")
            return

        print("VERBOSE", f"Saving fixture '{self.name}' to file...")
        folder = ""
        for directory in self.PATH[0].split("/"):
            folder += f"{directory}/"
            if not os.path.isdir(folder): os.mkdir(folder)

        with open(self.filename, "w") as file:
            json.dump(data, file, indent=5)

    def remove(self):
        try: os.remove(self.filename)
        except FileNotFoundError: pass
        try: del FixtureData._fixtures[self.name]
        except KeyError: pass