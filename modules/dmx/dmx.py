from collections import namedtuple
DMXValueItem = namedtuple("DMXValueItem", ["dmx_value", "name", "image"])

DMX_MAX_VALUE = pow(2, 8) - 1

class DMXChannel:
    def __init__(self, name: str, index=0):
        self._name = name
        self._index = index

    @property
    def name(self): return self._name
    @property
    def is_valid(self): return self._index > 0
    @property
    def channel(self): return self._index
    @channel.setter
    def channel(self, value): self._index = max(0, int(value))

    def to_json(self) -> dict:
        return {
            "name": self._name,
            "index": self._index
        } if self.is_valid else None


class DMXPositionChannel(DMXChannel):
    EXTENDED_DMX_MAX_VALUE = pow(DMX_MAX_VALUE + 1, 2) - 1

    def __init__(self, name, index=0, extended_channel=0):
        DMXChannel.__init__(self, name, index)
        self._extended_channel = extended_channel

    @property
    def is_extended(self): return self.is_valid and self._extended_channel > 0
    @property
    def extended_channel(self): return self._extended_channel
    @extended_channel.setter
    def extended_channel(self, value): self._extended_channel = max(0, int(value))

    def get_position_from_value(self, value : int | tuple[int,int]) -> float:
        if self.is_extended:
            dmx = value[0] * DMX_MAX_VALUE + value[1]
            return max(min(dmx / self.EXTENDED_DMX_MAX_VALUE, 1.0), 0.0)
        else: return max(min(value / DMX_MAX_VALUE, 1.0), 0.0)

    def get_value_from_position(self, position : float) -> int | tuple[int, int]:
        position = max(min(position, 1.0), 0.0)
        if self.is_extended:
            dmx = int(position * self.EXTENDED_DMX_MAX_VALUE)
            return round(dmx / DMX_MAX_VALUE), dmx % DMX_MAX_VALUE
        return int(position * DMX_MAX_VALUE)

    def to_json(self) -> dict:
        dt = DMXChannel.to_json(self)
        if self.is_extended: dt["extended_channel"] = self._extended_channel
        return dt


class DMXValueMapChannel(DMXChannel):
    def __init__(self, name, index=0, value_map : list=None):
        DMXChannel.__init__(self, name, index)
        self._values : list[DMXValueItem] = []
        if value_map: self.set_values(value_map)

    def set_values(self, value_map : list):
        self._values = [DMXValueItem(int(item[0]), item[1], item[2]) for item in sorted(value_map, key=lambda i: i[0])]

    @property
    def dmx_values(self):
        return [item.dmx_value for item in self._values]
    @property
    def names(self):
        return [item.name for item in self._values]
    @property
    def images(self):
        return [item.image for item in self._values]
    @property
    def items(self):
        return [item for item in self._values]

    def get_name_for_value(self, value):
        if value > DMX_MAX_VALUE: return None

        res = None
        for item in self._values:
            if item.dmx_value > value: return res
            else: res = item.name

    def get_value_for_name(self, name):
        for item in self._values:
            if name == item.name: return item.dmx_value
        return None

    def to_json(self):
        dt = DMXChannel.to_json(self)
        dt["value_map"] = self._values
        return dt


from ui.qt import pyelement

class DMXValueTable(pyelement.PyTable):
    def __init__(self, parent, element_id):
        pyelement.PyTable.__init__(self, parent, element_id)
        self.column_labels = [self._prettify_name(field) for field in DMXValueItem._fields]
        self.column_header = self.row_header = self.dynamic_rows = True
        self.column_width = 70, 200, 200
        self.events.EventInteract(self._on_update)

    @staticmethod
    def _prettify_name(field): return field.replace("_", " ").capitalize()

    def _on_update(self, row, column, new_value):
        if not new_value: return

        if column == 0:
            try: value = int(new_value)
            except ValueError: value = -1
            if value < 0: self.set(row, column, "")