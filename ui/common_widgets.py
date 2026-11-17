from PySide6.QtCore import QRect
from PySide6.QtWidgets import QTimeEdit
from qfluentwidgets import Slider, SpinBox

class NoWheelSlider(Slider):
    """Slider that ignores mouse wheel events to prevent accidental value changes while scrolling."""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelTimeEdit(QTimeEdit):
    """QTimeEdit that ignores mouse wheel events to prevent accidental value changes while scrolling."""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelSpinBox(SpinBox):
    """SpinBox that ignores mouse wheel events and ensures correct lineEdit geometry in PySide6/Qt6."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAccelerated(True)

    def wheelEvent(self, event):
        event.ignore()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fix_line_edit_geometry()

    def showEvent(self, e):
        super().showEvent(e)
        self._fix_line_edit_geometry()

    def _fix_line_edit_geometry(self):
        w, h = self.width(), self.height()
        btn_w = 0
        if hasattr(self, 'upButton') and hasattr(self, 'downButton') and self.upButton.isVisible():
            btn_w = self.upButton.width() + self.downButton.width() + 15
        elif hasattr(self, 'compactSpinButton') and self.compactSpinButton.isVisible():
            btn_w = self.compactSpinButton.width() + 10
        self.lineEdit().setGeometry(QRect(10, 2, max(10, w - btn_w - 15), h - 4))


