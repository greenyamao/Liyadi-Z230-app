from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from qfluentwidgets import (
    CardWidget, PillPushButton, PushButton,
    TitleLabel, SubtitleLabel, BodyLabel, CaptionLabel,
    FluentIcon as FIF
)
from ui.common_widgets import NoWheelSlider
from core.i18n import tr

class StatusDot(QWidget):
    """Clean antialiased indicator dot showing Bluetooth connection state without numbers or odd badges."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = "#FFB900"  # default amber

    def set_status(self, status: str):
        if status == "connected":
            self._color = "#107C41"  # Fluent green
        elif status == "connecting":
            self._color = "#FFB900"  # Fluent amber
        else:
            self._color = "#D83B01"  # Fluent red
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(self._color)))
        painter.drawEllipse(1, 1, 8, 8)

class LightView(QWidget):
    brightness_changed = Signal(int)
    kelvin_changed = Signal(int)
    reconnect_requested = Signal()

    def __init__(self, ble_manager, parent=None):
        super().__init__(parent)
        self.ble = ble_manager
        self._block_signals = False
        self.last_status_code = "connecting"
        self.last_status_detail = ""

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        # Header Title and Connection Status
        title_box = QHBoxLayout()
        self.title_label = TitleLabel(tr("light_title"), self)
        title_box.addWidget(self.title_label)
        title_box.addStretch()

        self.status_dot = StatusDot(self)
        self.status_label = CaptionLabel(tr("status_connecting"), self)
        self.reconnect_btn = PushButton(FIF.SYNC, tr("btn_reconnect"), self)
        self.reconnect_btn.clicked.connect(self.reconnect_requested.emit)

        status_box = QHBoxLayout()
        status_box.setSpacing(8)
        status_box.setAlignment(Qt.AlignVCenter)
        status_box.addWidget(self.status_dot)
        status_box.addWidget(self.status_label)
        status_box.addWidget(self.reconnect_btn)
        title_box.addLayout(status_box)

        main_layout.addLayout(title_box)

        # 1. Brightness Card (0% = Standby / OFF)
        self.bright_card = CardWidget(self)
        b_layout = QVBoxLayout(self.bright_card)
        b_layout.setContentsMargins(24, 20, 24, 20)
        b_layout.setSpacing(16)

        b_header = QHBoxLayout()
        b_title_box = QVBoxLayout()
        b_title_box.setSpacing(4)
        self.b_title = SubtitleLabel(tr("card_brightness_title"), self.bright_card)
        self.b_sub = CaptionLabel(tr("card_brightness_desc"), self.bright_card)
        self.b_sub.setStyleSheet("color: gray;")
        b_title_box.addWidget(self.b_title)
        b_title_box.addWidget(self.b_sub)
        b_header.addLayout(b_title_box)
        b_header.addStretch()

        self.b_val_label = TitleLabel(self._format_brightness_label(self.ble.brightness), self.bright_card)
        self._apply_brightness_label_style(self.ble.brightness)
        b_header.addWidget(self.b_val_label)
        b_layout.addLayout(b_header)

        # Slider with wheel disabled to prevent accidental scrolling changes
        self.b_slider = NoWheelSlider(Qt.Horizontal, self.bright_card)
        self.b_slider.setRange(0, 100)
        self.b_slider.setValue(self.ble.brightness if self.ble.is_on else 0)
        b_layout.addWidget(self.b_slider)

        # Preset pills for brightness
        self.b_pills_layout = QHBoxLayout()
        self.b_pills_layout.setSpacing(10)
        self._build_brightness_pills()
        b_layout.addLayout(self.b_pills_layout)

        main_layout.addWidget(self.bright_card)

        # 2. Color Temperature (CCT) Card (Max 6500K)
        self.cct_card = CardWidget(self)
        c_layout = QVBoxLayout(self.cct_card)
        c_layout.setContentsMargins(24, 20, 24, 20)
        c_layout.setSpacing(16)

        c_header = QHBoxLayout()
        c_title_box = QVBoxLayout()
        c_title_box.setSpacing(4)
        self.c_title = SubtitleLabel(tr("card_cct_title"), self.cct_card)
        self.c_sub = CaptionLabel(tr("card_cct_desc"), self.cct_card)
        self.c_sub.setStyleSheet("color: gray;")
        c_title_box.addWidget(self.c_title)
        c_title_box.addWidget(self.c_sub)
        c_header.addLayout(c_title_box)
        c_header.addStretch()

        self.c_val_label = TitleLabel(f"{min(6500, self.ble.kelvin)}K", self.cct_card)
        self.c_val_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        c_header.addWidget(self.c_val_label)
        c_layout.addLayout(c_header)

        # Slider clamped between 2700K and 6500K
        self.c_slider = NoWheelSlider(Qt.Horizontal, self.cct_card)
        self.c_slider.setRange(2700, 6500)
        self.c_slider.setSingleStep(50)
        self.c_slider.setValue(min(6500, max(2700, self.ble.kelvin)))
        c_layout.addWidget(self.c_slider)

        # Visual gradient bar (2700K warm amber to 6500K cool daylight)
        grad_bar = QFrame(self.cct_card)
        grad_bar.setFixedHeight(8)
        grad_bar.setStyleSheet("""
            QFrame {
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0.0 #FF7700,
                    stop:0.25 #FFAA00,
                    stop:0.65 #FFF0CC,
                    stop:0.85 #E0FFFF,
                    stop:1.0 #99DDFF);
            }
        """)
        c_layout.addWidget(grad_bar)

        # Preset pills for Kelvin
        self.c_pills_layout = QHBoxLayout()
        self.c_pills_layout.setSpacing(10)
        self._build_kelvin_pills()
        c_layout.addLayout(self.c_pills_layout)

        main_layout.addWidget(self.cct_card)
        main_layout.addStretch()

    def _build_brightness_pills(self):
        while self.b_pills_layout.count():
            item = self.b_pills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        presets = [(0, tr("brightness_off")), (25, "25%"), (50, "50%"), (75, "75%"), (100, "100%")]
        for pct, label in presets:
            btn = PillPushButton(label, self.bright_card)
            btn.clicked.connect(lambda _, p=pct: self._on_preset_brightness(p))
            self.b_pills_layout.addWidget(btn)
        self.b_pills_layout.addStretch()

    def _build_kelvin_pills(self):
        while self.c_pills_layout.count():
            item = self.c_pills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        presets = [
            (tr("preset_warm"), 2700),
            (tr("preset_halogen"), 3200),
            (tr("preset_neutral"), 4500),
            (tr("preset_sun"), 5600),
            (tr("preset_cool"), 6500)
        ]
        for title, kelvin in presets:
            btn = PillPushButton(title, self.cct_card)
            btn.clicked.connect(lambda _, k=kelvin: self._on_preset_kelvin(k))
            self.c_pills_layout.addWidget(btn)
        self.c_pills_layout.addStretch()

    def retranslate_ui(self):
        """Called when interface language changes in Settings"""
        self.title_label.setText(tr("light_title"))
        self.reconnect_btn.setText(tr("btn_reconnect"))
        self.b_title.setText(tr("card_brightness_title"))
        self.b_sub.setText(tr("card_brightness_desc"))
        self.b_val_label.setText(self._format_brightness_label(self.b_slider.value()))
        self.c_title.setText(tr("card_cct_title"))
        self.c_sub.setText(tr("card_cct_desc"))
        self._build_brightness_pills()
        self._build_kelvin_pills()
        self._refresh_status_text()

    def _format_brightness_label(self, val: int) -> str:
        if val <= 0:
            return tr("brightness_off")
        return f"{val}%"

    def _apply_brightness_label_style(self, val: int):
        if val <= 0:
            self.b_val_label.setStyleSheet("color: #888888; font-weight: bold;")
        else:
            self.b_val_label.setStyleSheet("color: #0099FF; font-weight: bold;")

    def _connect_signals(self):
        self.b_slider.valueChanged.connect(self._on_brightness_slider)
        self.c_slider.valueChanged.connect(self._on_kelvin_slider)

    def _on_brightness_slider(self, val):
        self.b_val_label.setText(self._format_brightness_label(val))
        self._apply_brightness_label_style(val)
        if not self._block_signals:
            self.brightness_changed.emit(val)

    def _on_kelvin_slider(self, val):
        val = min(6500, max(2700, int(round(val / 50.0) * 50)))
        self.c_val_label.setText(f"{val}K")
        if not self._block_signals:
            self.kelvin_changed.emit(val)

    def _on_preset_brightness(self, pct):
        self.b_slider.setValue(pct)

    def _on_preset_kelvin(self, k):
        self.c_slider.setValue(min(6500, max(2700, k)))

    def update_hardware_state(self, is_on: bool, brightness: int, kelvin: int):
        self._block_signals = True
        try:
            display_b = brightness if is_on else 0
            self.b_slider.setValue(display_b)
            self.b_val_label.setText(self._format_brightness_label(display_b))
            self._apply_brightness_label_style(display_b)

            clamped_k = min(6500, max(2700, kelvin))
            self.c_slider.setValue(clamped_k)
            self.c_val_label.setText(f"{clamped_k}K")
        finally:
            self._block_signals = False

    def update_connection_status(self, status: str, detail: str = ""):
        self.last_status_code = status
        self.last_status_detail = detail
        self.status_dot.set_status(status)
        self._refresh_status_text()

    def _refresh_status_text(self):
        status = self.last_status_code
        detail = self.last_status_detail
        if status == "connected":
            dev_name = detail if detail else "Liadi Z230"
            self.status_label.setText(tr("status_connected", dev_name))
        elif status == "connecting":
            self.status_label.setText(tr("status_connecting"))
        elif status == "disconnected":
            self.status_label.setText(tr("status_disconnected"))
        elif status == "error":
            msg = f"{tr('status_error')}: {detail}" if detail else tr("status_error")
            self.status_label.setText(msg)
        else:
            self.status_label.setText(tr("status_connecting"))
