class Parameter:
    def __init__(self, name, default_value, min_value=None, max_value=None):
        self._name = name
        self._description = ""
        self._default_value = default_value
        self._limits = min_value, max_value

    @property
    def name(self): return self._name

    @property
    def description(self): return f"{self._description}\nDefault value is {self.default_value}"
    @description.setter
    def description(self, description): self._description = description

    @property
    def default_value(self): return self._default_value
    @property
    def min_value(self): return self._limits[0]
    @property
    def max_value(self): return self._limits[1]

model = Parameter("model", "gpt-3.5-turbo")

temperature = Parameter("temperature", 1, 0., 2.)
temperature.description = """What sampling temperature to use, between 0 and 2. 
Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.
We generally recommend altering this or top_p but not both."""

top_p = Parameter("top_p", 1, max_value=1.0)
top_p.description = """An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. 
So 0.1 means only the tokens comprising the top 10% probability mass are considered.
We generally recommend altering this or temperature but not both."""

max_tokens = Parameter("max_tokens", 1000, min_value=0)
max_tokens.description = """The total length of input tokens and generated tokens is limited by the model's context length.
If the limit is set to 0, the token count is limited to what the model supports"""

presence_penalty = Parameter("presence_penalty", 0, -2., 2.)
presence_penalty.description = """Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics."""

frequency_penalty = Parameter("frequency_penalty", 0., -2., 2.)
frequency_penalty.description = """Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim."""