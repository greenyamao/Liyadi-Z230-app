from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from core.i18n import tr

def create_tray_icon_pixmap(color="#FFA500") -> QIcon:
    """Procedurally creates a glowing light bulb / sun icon for the Windows tray"""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    # Outer glow
    painter.setBrush(QBrush(QColor(255, 165, 0, 70)))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, 56, 56)

    # Core circle
    painter.setBrush(QBrush(QColor(color)))
    painter.drawEllipse(14, 14, 36, 36)

    # Inner bright center
    painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
    painter.drawEllipse(22, 22, 20, 20)

    painter.end()
    return QIcon(pix)

class TrayManager(QSystemTrayIcon):
    power_toggled = Signal()
    preset_clicked = Signal(int, int) # brightness, kelvin
    show_window_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(create_tray_icon_pixmap())
        self.setToolTip(tr("tray_tooltip"))
        
        self._init_menu()
        self.activated.connect(self._on_activated)

    def _init_menu(self):
        self.tray_menu = QMenu()

        self.title_act = self.tray_menu.addAction("💡 Liadi Z230 Control")
        self.title_act.setEnabled(False)
        self.tray_menu.addSeparator()

        self.power_act = self.tray_menu.addAction(tr("tray_power_toggle"))
        self.power_act.triggered.connect(self.power_toggled.emit)

        self.tray_menu.addSeparator()
        self.act_reading = self.tray_menu.addAction(f"☀️ {tr('tray_preset_reading')}")
        self.act_reading.triggered.connect(lambda: self.preset_clicked.emit(70, 5600))

        self.act_night = self.tray_menu.addAction(f"🌙 {tr('tray_preset_night')}")
        self.act_night.triggered.connect(lambda: self.preset_clicked.emit(10, 2700))

        self.tray_menu.addSeparator()
        self.show_act = self.tray_menu.addAction(tr("tray_show"))
        self.show_act.triggered.connect(self.show_window_requested.emit)

        self.exit_act = self.tray_menu.addAction(tr("tray_exit"))
        self.exit_act.triggered.connect(self.exit_requested.emit)

        self.setContextMenu(self.tray_menu)

    def retranslate_ui(self):
        self.setToolTip(tr("tray_tooltip"))
        self.power_act.setText(tr("tray_power_toggle"))
        self.act_reading.setText(f"☀️ {tr('tray_preset_reading')}")
        self.act_night.setText(f"🌙 {tr('tray_preset_night')}")
        self.show_act.setText(tr("tray_show"))
        self.exit_act.setText(tr("tray_exit"))

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window_requested.emit()
