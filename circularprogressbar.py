"""
Module storing the implementation of a circular progress bar in kivy.

.. note::

    Refer to the in-code documentation of the class and its methods to learn about the tool. Includes a usage example.

Authorship: Kacper Florianski
"""

from kivy.uix.widget import Widget
from kivy.app import App
from kivy.core.text import Label
from kivy.lang.builder import Builder
from kivy.graphics import Line, Rectangle, Color
from kivy.clock import Clock
from collections.abc import Iterable
from math import ceil
from kivy.properties import NumericProperty, ListProperty, ObjectProperty

# This constant enforces the cap argument to be one of the caps accepted by the kivy.graphics.Line class
_ACCEPTED_BAR_CAPS = {"round", "none", "square"}

# Declare the defaults for the modifiable values
_DEFAULT_THICKNESS = 10
_DEFAULT_CAP_STYLE = 'round'
_DEFAULT_PRECISION = 10
_DEFAULT_PROGRESS_COLOUR = (1, 0, 0, 1)
_DEFAULT_BACKGROUND_COLOUR = (0.26, 0.26, 0.26, 1)
_DEFAULT_MAX_PROGRESS = 100
_DEFAULT_MIN_PROGRESS = 0
_DEFAULT_WIDGET_SIZE = 200
_DEFAULT_TEXT_LABEL = Label(text="{}%", font_size=40)

# Declare the defaults for the normalisation function, these are used in the textual representation (multiplied by 100)
_NORMALISED_MAX = 1
_NORMALISED_MIN = 0


class CircularProgressBar(Widget):
    """
    Widget used to create a circular progress bar.

    You can either modify the values within the code directly, or use the .kv language to pass them to the class.

    The following keyword values are currently used:

        1. thickness - thickness of the progress bar line (positive integer)
        2. cap_style - cap / edge of the bar, check the cap keyword argument in kivy.graphics.Line
        3. cap_precision - bar car sharpness, check the cap_precision keyword argument in kivy.graphics.Line
        4. progress_colour - Colour value of the progress bar, check values accepted by kivy.graphics.Color
        5. background_colour - Colour value of the background bar, check values accepted by kivy.graphics.Color
        6. max - maximum progress (value corresponding to 100%)
        7. min - minimum progress (value corresponding to 0%) - note that this sets the starting value to this value
        8. value - progress value, can you use it initialise the bar to some other progress different from the minimum
        9. widget_size - size of the widget, use this to avoid issues with size, width, height etc.
        10. label - kivy.graphics.Label textually representing the progress - pass a label with an empty text field to
        remove it, use "{}" as the progress value placeholder (it will be replaced via the format function)
        11. value_normalized - get the current progress but normalised, or set it using a normalised value

    .. note::

        You can execute this module to have a live example of the widget.

    .. warning::

        Apart from throwing kivy-specific errors, this class will throw TypeError and ValueError exceptions.

    Additionally, this class provides aliases to match the kivy.uix.progressbar.ProgressBar naming convention:

        1. get_norm_value - alternative name for get_normalised_progress
        2. set_norm_value - alternative name for set_normalised_progress
    """

    max = NumericProperty(_DEFAULT_MAX_PROGRESS)
    min = NumericProperty(_DEFAULT_MIN_PROGRESS)
    value = NumericProperty(_DEFAULT_MIN_PROGRESS)
    thickness = NumericProperty(_DEFAULT_THICKNESS)
    color = ListProperty(list(_DEFAULT_PROGRESS_COLOUR))
    background_color = ListProperty(list(_DEFAULT_BACKGROUND_COLOUR))
    widget_size = NumericProperty(_DEFAULT_WIDGET_SIZE)
    label = ObjectProperty(_DEFAULT_TEXT_LABEL)

    cap_style = ObjectProperty(_DEFAULT_CAP_STYLE)
    cap_precision = NumericProperty(_DEFAULT_PRECISION)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._default_label_text = self.label.text
        self._label_size = (0, 0)
        self.get_norm_value = self.get_normalised_progress
        self.set_norm_value = self.set_normalised_progress
        self.bind(
            value=self._on_value,
            max=self._on_max,
            min=self._on_min,
            thickness=self._on_thickness,
            widget_size=self._on_widget_size,
            label=self._on_label,
        )
        self._draw()

    def _on_value(self, instance, value):
        if not isinstance(value, int):
            raise TypeError("Progress must be an integer value, not {}!".format(type(value)))
        if value < self.min or value > self.max:
            raise ValueError("Progress must be between minimum ({}) and maximum ({}), not {}!".format(self.min, self.max, value))
        self._draw()

    def _on_max(self, instance, value):
        if not isinstance(value, int):
            raise TypeError("Maximum progress only accepts an integer value, not {}!".format(type(value)))
        if value <= self.min:
            raise ValueError("Maximum progress ({}) must be greater than minimum progress ({})!".format(value, self.min))
        if self.value > value:
            self.value = value
        self._draw()

    def _on_min(self, instance, value):
        if not isinstance(value, int):
            raise TypeError("Minimum progress only accepts an integer value, not {}!".format(type(value)))
        if value >= self.max:
            raise ValueError("Minimum progress ({}) must be less than maximum progress ({})!".format(value, self.max))
        if self.value < value:
            self.value = value
        self._draw()

    def _on_thickness(self, instance, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Circular bar thickness must be a positive integer, not {}!".format(value))
        self._draw()

    def _on_widget_size(self, instance, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Widget size must be a positive integer, not {}!".format(value))
        self._draw()

    def _on_label(self, instance, value):
        if not isinstance(value, Label):
            raise TypeError("Label must be a kivy.core.text.Label, not {}!".format(type(value)))
        self._default_label_text = value.text
        self._draw()

    @property
    def value_normalized(self):
        """
        Alias the for getting the normalised progress.

        Matches the property name in kivy.uix.progressbar.ProgressBar.

        :return: Current progress normalised to match the percentage constants
        """
        return self.get_normalised_progress()

    @value_normalized.setter
    def value_normalized(self, value):
        """
        Alias the for getting the normalised progress.

        Matches the property name in kivy.uix.progressbar.ProgressBar.

        :return: Current progress normalised to match the percentage constants
        """
        self.set_normalised_progress(value)

    def get_normalised_progress(self) -> float:
        """
        Function used to normalise the progress using the MIN/MAX normalisation

        :return: Current progress normalised to match the percentage constants
        """
        return _NORMALISED_MIN + (self.value - self.min) * (_NORMALISED_MAX - _NORMALISED_MIN) / (self.max - self.min)

    def set_normalised_progress(self, norm_progress: float):
        """
        Function used to set the progress value from a normalised value, using MIN/MAX normalisation

        :param norm_progress: Normalised value to update the progress with
        """
        if not isinstance(norm_progress, (float, int)):
            raise TypeError("Normalised progress must be a float or an integer, not {}!".format(type(norm_progress)))
        if norm_progress < _NORMALISED_MIN or norm_progress > _NORMALISED_MAX:
            raise ValueError("Normalised progress must be between {} and {}, got {}!".format(_NORMALISED_MIN, _NORMALISED_MAX, norm_progress))
        self.value = ceil(self.min + (norm_progress - _NORMALISED_MIN) * (self.max - self.min) / (_NORMALISED_MAX - _NORMALISED_MIN))

    def _refresh_text(self):
        """
        Function used to refresh the text of the progress label.

        Additionally updates the variable tracking the label's texture size
        """
        self.label.text = self._default_label_text.format(str(int(self.get_normalised_progress() * 100)))
        self.label.refresh()
        self._label_size = self.label.texture.size

    def _draw(self, *args):
        """
        Function used to draw the progress bar onto the screen.

        The drawing process is as follows:

            1. Clear the canvas
            2. Draw the background progress line (360 degrees)
            3. Draw the actual progress line (N degrees where n is between 0 and 360)
            4. Draw the textual representation of progress in the middle of the circle
        """

        with self.canvas:
            self.canvas.clear()
            self._refresh_text()
            # Draw background
            Color(*self.background_color)
            Line(circle=(self.pos[0] + self.widget_size / 2, self.pos[1] + self.widget_size / 2,
                         self.widget_size / 2 - self.thickness), width=self.thickness)
            # Draw progress
            Color(*self.color)
            Line(circle=(self.pos[0] + self.widget_size / 2, self.pos[1] + self.widget_size / 2,
                         self.widget_size / 2 - self.thickness, 0, self.get_normalised_progress() * 360),
                 width=self.thickness, cap=self.cap_style, cap_precision=self.cap_precision)
            # Draw label
            Color(1, 1, 1, 1)
            Rectangle(texture=self.label.texture, size=self._label_size,
                      pos=(self.widget_size / 2 - self._label_size[0] / 2 + self.pos[0],
                           self.widget_size / 2 - self._label_size[1] / 2 + self.pos[1]))


class _Example(App):

    # Simple animation to show the circular progress bar in action
    def animate(self, dt):
        for bar in self.root.children[:-1]:
            if bar.value < bar.max:
                bar.value += 1
            else:
                bar.value = bar.min

        # Showcase that setting the values using value_normalized property also works
        bar = self.root.children[-1]
        if bar.value < bar.max:
            bar.value_normalized += 0.01
        else:
            bar.value_normalized = 0

    # Simple layout for easy example
    def build(self):
        container = Builder.load_string('''
#:import Label kivy.core.text.Label           
#:set _label Label(text="\\nI am a label\\ninjected in kivy\\nmarkup string :)\\nEnjoy! --={}=--")
#:set _another_label Label(text="Loading...\\n{}%", font_size=10, color=(1,1,0.5,1), halign="center")
FloatLayout:
    CircularProgressBar:
        pos: 50, 100
        thickness: 15
        cap_style: "RouND"
        progress_colour: "010"
        background_colour: "001"
        cap_precision: 3
        max: 150
        min: 100
        widget_size: 300
        label: _label
    CircularProgressBar
        pos: 400, 100
    CircularProgressBar
        pos: 650, 100
        cap_style: "SqUArE"
        thickness: 5
        progress_colour: 0.8, 0.8, 0.5, 1
        cap_precision:100
        max: 10
        widget_size: 100
        label: _another_label''')

        # Animate the progress bar
        Clock.schedule_interval(self.animate, 0.05)
        return container


if __name__ == '__main__':
    _Example().run()