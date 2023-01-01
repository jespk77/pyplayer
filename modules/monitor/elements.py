from ui.qt import pyelement

class ObjectLabel(pyelement.PyFrame):
    def __init__(self, parent, element_id):
        pyelement.PyFrame.__init__(self, parent, element_id)
        self.layout.column(1, weight=1).margins(0)

    def create_widgets(self):
        img = self.add_element("icon", element_class=pyelement.PyTextLabel)
        img.height = img.width = 32
        txt = self.add_element("text", element_class=pyelement.PyTextLabel, column=1)
        txt.set_alignment("centerV")

    @property
    def image(self): return self["icon"].display_image
    @image.setter
    def image(self, icon_file): self["icon"].display_image = icon_file

    @property
    def text(self): return self["text"].text
    @text.setter
    def text(self, txt): self["text"].text = txt

class ObjectFrame(pyelement.PyLabelFrame):
    def __init__(self, parent, window_id):
        pyelement.PyLabelFrame.__init__(self, parent, window_id)
        self.layout.row(1, weight=1)

    def create_widgets(self):
        self.add_element("info", element_class=ObjectLabel)

    @property
    def object_image(self): return self["info"].image
    @object_image.setter
    def object_image(self, img): self["info"].image = img

    @property
    def object_name(self): return self["info"].text
    @object_name.setter
    def object_name(self, name): self["info"].text = name

    def update(self):
        pass