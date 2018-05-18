class ArgumentEmpty:
    def __repr__(self):
        return ""

class ArgumentExact(ArgumentEmpty):
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return "'{!s}'".format(self.id)

class ArgumentCommand(ArgumentEmpty):
    def __init__(self, id, arg_list):
        self.id = id
        self.arg_list = arg_list

    def __repr__(self):
        return "{} [".format(self.id) + " ".join([repr(arg) for arg in self.arg_list]) + "]"