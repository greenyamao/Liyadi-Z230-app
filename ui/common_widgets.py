from qfluentwidgets import Slider, SpinBox

class NoWheelSlider(Slider):
    """Slider that ignores mouse wheel events to prevent accidental value changes while scrolling."""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelSpinBox(SpinBox):
    """SpinBox that ignores mouse wheel events to prevent accidental value changes while scrolling."""
    def wheelEvent(self, event):
        event.ignore()
