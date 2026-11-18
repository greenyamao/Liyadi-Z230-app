from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QLabel
)
from qfluentwidgets import (
    CardWidget, SwitchButton, LineEdit, PushButton, PrimaryPushButton, TransparentPushButton,
    TitleLabel, SubtitleLabel, BodyLabel, CaptionLabel, ComboBox,
    FluentIcon as FIF, setTheme, Theme, InfoBar, InfoBarPosition
)
from core.autostart import is_autostart_enabled, set_autostart
from core.i18n import tr, set_language, get_language, LANGUAGES
from core.smart_plug import SmartPlugManager
from ui.common_widgets import NoWheelSpinBox

class SettingsView(QWidget):
    config_updated = Signal(dict)
    language_changed = Signal(str)
    scan_requested = Signal()

    def __init__(self, config: dict, plug: SmartPlugManager = None, parent=None):
        super().__init__(parent)
        self.config = config
        self.plug = plug
        self._init_ui()
        self._connect_plug_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        self.title_lbl = TitleLabel(tr("settings_title"), self)
        main_layout.addWidget(self.title_lbl)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background: transparent; }")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 16, 0)
        content_layout.setSpacing(16)

        # 1. System Integration Card
        sys_card = CardWidget(scroll_content)
        s_layout = QVBoxLayout(sys_card)
        s_layout.setContentsMargins(24, 20, 24, 20)
        s_layout.setSpacing(20)

        self.sec_win_lbl = SubtitleLabel(tr("sec_windows"), sys_card)
        s_layout.addWidget(self.sec_win_lbl)

        # Autostart row
        r_auto = QHBoxLayout()
        auto_info = QVBoxLayout()
        auto_info.setSpacing(4)
        self.lbl_auto_title = BodyLabel(tr("lbl_autostart"), sys_card)
        self.lbl_auto_desc = CaptionLabel(tr("desc_autostart"), sys_card)
        self.lbl_auto_desc.setStyleSheet("color: gray;")
        auto_info.addWidget(self.lbl_auto_title)
        auto_info.addWidget(self.lbl_auto_desc)
        r_auto.addLayout(auto_info)
        r_auto.addStretch()

        self.sw_auto = SwitchButton(sys_card)
        self.sw_auto.setOnText(tr("val_on"))
        self.sw_auto.setOffText(tr("val_off"))
        self.sw_auto.setChecked(is_autostart_enabled())
        self.sw_auto.checkedChanged.connect(self._on_autostart_toggled)
        r_auto.addWidget(self.sw_auto)
        s_layout.addLayout(r_auto)

        # Minimize to Tray row
        r_min = QHBoxLayout()
        min_info = QVBoxLayout()
        min_info.setSpacing(4)
        self.lbl_min_title = BodyLabel(tr("lbl_min_tray"), sys_card)
        self.lbl_min_desc = CaptionLabel(tr("desc_min_tray"), sys_card)
        self.lbl_min_desc.setStyleSheet("color: gray;")
        min_info.addWidget(self.lbl_min_title)
        min_info.addWidget(self.lbl_min_desc)
        r_min.addLayout(min_info)
        r_min.addStretch()

        self.sw_min = SwitchButton(sys_card)
        self.sw_min.setOnText(tr("val_on"))
        self.sw_min.setOffText(tr("val_off"))
        self.sw_min.setChecked(self.config.get("minimize_to_tray", True))
        self.sw_min.checkedChanged.connect(self._on_min_tray_toggled)
        r_min.addWidget(self.sw_min)
        s_layout.addLayout(r_min)

        # Close to Tray row
        r_close = QHBoxLayout()
        close_info = QVBoxLayout()
        close_info.setSpacing(4)
        self.lbl_close_title = BodyLabel(tr("lbl_close_tray"), sys_card)
        self.lbl_close_desc = CaptionLabel(tr("desc_close_tray"), sys_card)
        self.lbl_close_desc.setStyleSheet("color: gray;")
        close_info.addWidget(self.lbl_close_title)
        close_info.addWidget(self.lbl_close_desc)
        r_close.addLayout(close_info)
        r_close.addStretch()

        self.sw_close = SwitchButton(sys_card)
        self.sw_close.setOnText(tr("val_on"))
        self.sw_close.setOffText(tr("val_off"))
        self.sw_close.setChecked(self.config.get("close_to_tray", True))
        self.sw_close.checkedChanged.connect(self._on_close_tray_toggled)
        r_close.addWidget(self.sw_close)
        s_layout.addLayout(r_close)

        content_layout.addWidget(sys_card)

        # 2. Smart Plug (Tuya 220V) Card
        self.plug_card = CardWidget(scroll_content)
        p_layout = QVBoxLayout(self.plug_card)
        p_layout.setContentsMargins(24, 20, 24, 20)
        p_layout.setSpacing(16)

        self.sec_plug_lbl = SubtitleLabel(tr("sec_smart_plug"), self.plug_card)
        self.desc_plug_lbl = CaptionLabel(tr("desc_smart_plug"), self.plug_card)
        self.desc_plug_lbl.setStyleSheet("color: gray;")
        p_layout.addWidget(self.sec_plug_lbl)
        p_layout.addWidget(self.desc_plug_lbl)

        # Enable Switch Row
        r_enable_plug = QHBoxLayout()
        self.lbl_enable_plug = BodyLabel(tr("lbl_enable_plug"), self.plug_card)
        r_enable_plug.addWidget(self.lbl_enable_plug)
        r_enable_plug.addStretch()

        self.sw_plug_enable = SwitchButton(self.plug_card)
        self.sw_plug_enable.setOnText(tr("val_on"))
        self.sw_plug_enable.setOffText(tr("val_off"))
        self.sw_plug_enable.setChecked(self.plug.enabled if self.plug else False)
        self.sw_plug_enable.checkedChanged.connect(self._on_plug_enable_toggled)
        r_enable_plug.addWidget(self.sw_plug_enable)
        p_layout.addLayout(r_enable_plug)

        # Container for plug settings (hidden when plug disabled)
        self.plug_body_widget = QWidget(self.plug_card)
        pb_layout = QVBoxLayout(self.plug_body_widget)
        pb_layout.setContentsMargins(0, 8, 0, 0)
        pb_layout.setSpacing(16)

        # Connection status banner
        self.plug_status_card = CardWidget(self.plug_body_widget)
        psc_layout = QHBoxLayout(self.plug_status_card)
        psc_layout.setContentsMargins(18, 14, 18, 14)
        psc_layout.setSpacing(14)

        self.lbl_plug_status_icon = CaptionLabel("🔌", self.plug_status_card)
        self.lbl_plug_status_info = BodyLabel("", self.plug_status_card)
        psc_layout.addWidget(self.lbl_plug_status_icon)
        psc_layout.addWidget(self.lbl_plug_status_info)
        psc_layout.addStretch()

        self.btn_test_toggle = PushButton("⚡ " + tr("btn_test_plug"), self.plug_status_card)
        self.btn_test_toggle.clicked.connect(self._on_test_toggle_clicked)
        psc_layout.addWidget(self.btn_test_toggle)

        pb_layout.addWidget(self.plug_status_card)

        # Manual Control Row
        r_status = QHBoxLayout()
        r_status.setSpacing(12)
        self.lbl_plug_status_title = BodyLabel(tr("lbl_plug_status"), self.plug_body_widget)
        self.lbl_plug_device_name = BodyLabel(
            self.plug.device_name if (self.plug and self.plug.device_name) else "—",
            self.plug_body_widget
        )
        self.lbl_plug_device_name.setStyleSheet("font-weight: bold; color: #00bcd4;")
        r_status.addWidget(self.lbl_plug_status_title)
        r_status.addWidget(self.lbl_plug_device_name)
        r_status.addStretch()

        self.btn_plug_on = PushButton(tr("btn_plug_on"), self.plug_body_widget)
        self.btn_plug_on.clicked.connect(lambda: self.plug.turn_on() if self.plug else None)
        self.btn_plug_off = PushButton(tr("btn_plug_off"), self.plug_body_widget)
        self.btn_plug_off.clicked.connect(lambda: self.plug.turn_off() if self.plug else None)
        r_status.addWidget(self.btn_plug_on)
        r_status.addWidget(self.btn_plug_off)
        pb_layout.addLayout(r_status)

        # Separator line
        sep1 = QFrame(self.plug_body_widget)
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("color: rgba(255, 255, 255, 0.08);")
        pb_layout.addWidget(sep1)

        # Automation Row 1: Cut AC power after turning light off
        r_auto_off = QHBoxLayout()
        auto_off_box = QVBoxLayout()
        self.lbl_auto_off = BodyLabel(tr("lbl_auto_power_off"), self.plug_body_widget)
        self.lbl_auto_off_desc = CaptionLabel(tr("tip_cooldown_delay"), self.plug_body_widget)
        self.lbl_auto_off_desc.setStyleSheet("color: gray;")
        auto_off_box.addWidget(self.lbl_auto_off)
        auto_off_box.addWidget(self.lbl_auto_off_desc)
        r_auto_off.addLayout(auto_off_box)
        r_auto_off.addStretch()

        self.sw_auto_off = SwitchButton(self.plug_body_widget)
        self.sw_auto_off.setOnText(tr("val_on"))
        self.sw_auto_off.setOffText(tr("val_off"))
        self.sw_auto_off.setChecked(self.plug.auto_power_off if self.plug else True)
        self.sw_auto_off.checkedChanged.connect(self._save_plug_settings)
        r_auto_off.addWidget(self.sw_auto_off)
        pb_layout.addLayout(r_auto_off)

        # Automation Row 2: Cooldown delay (SpinBox)
        r_delay = QHBoxLayout()
        self.lbl_cooldown_delay = BodyLabel(tr("lbl_cooldown_delay"), self.plug_body_widget)
        r_delay.addWidget(self.lbl_cooldown_delay)
        r_delay.addStretch()

        self.in_cooldown_delay = NoWheelSpinBox(self.plug_body_widget)
        self.in_cooldown_delay.setRange(0, 180)
        self.in_cooldown_delay.setSingleStep(5)
        self.in_cooldown_delay.setValue(self.plug.cooldown_sec if self.plug else 30)
        self.in_cooldown_delay.valueChanged.connect(self._save_plug_settings)
        r_delay.addWidget(self.in_cooldown_delay)
        pb_layout.addLayout(r_delay)

        # Automation Row 3: Power on plug first when turning light on
        r_auto_on = QHBoxLayout()
        self.lbl_auto_on = BodyLabel(tr("lbl_auto_power_on"), self.plug_body_widget)
        r_auto_on.addWidget(self.lbl_auto_on)
        r_auto_on.addStretch()

        self.sw_auto_on = SwitchButton(self.plug_body_widget)
        self.sw_auto_on.setOnText(tr("val_on"))
        self.sw_auto_on.setOffText(tr("val_off"))
        self.sw_auto_on.setChecked(self.plug.auto_power_on if self.plug else True)
        self.sw_auto_on.checkedChanged.connect(self._save_plug_settings)
        r_auto_on.addWidget(self.sw_auto_on)
        pb_layout.addLayout(r_auto_on)

        # Separator line
        sep2 = QFrame(self.plug_body_widget)
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: rgba(255, 255, 255, 0.08);")
        pb_layout.addWidget(sep2)

        # QR Code Pairing Section
        qr_header = QVBoxLayout()
        self.lbl_qr_title = SubtitleLabel(tr("lbl_qr_pairing"), self.plug_body_widget)
        self.lbl_qr_desc = CaptionLabel(tr("ph_user_code"), self.plug_body_widget)
        self.lbl_qr_desc.setStyleSheet("color: gray;")
        qr_header.addWidget(self.lbl_qr_title)
        qr_header.addWidget(self.lbl_qr_desc)
        pb_layout.addLayout(qr_header)

        r_qr_input = QHBoxLayout()
        r_qr_input.setSpacing(8)
        self.in_user_code = LineEdit(self.plug_body_widget)
        self.in_user_code.setPlaceholderText(tr("lbl_user_code"))
        if self.plug and self.plug.user_code:
            self.in_user_code.setText(self.plug.user_code)
        self.in_user_code.textChanged.connect(self._on_user_code_changed)
        r_qr_input.addWidget(self.in_user_code, stretch=2)

        self.btn_save_code = PushButton(tr("btn_save_code"), self.plug_body_widget)
        self.btn_save_code.clicked.connect(self._on_save_code_clicked)
        r_qr_input.addWidget(self.btn_save_code)

        self.btn_gen_qr = PrimaryPushButton(tr("btn_gen_qr"), self.plug_body_widget)
        self.btn_gen_qr.clicked.connect(self._on_generate_qr_clicked)
        r_qr_input.addWidget(self.btn_gen_qr, stretch=1)
        pb_layout.addLayout(r_qr_input)

        self._update_plug_status_ui()

        # QR Code Display Container (initially hidden)
        self.qr_box = QWidget(self.plug_body_widget)
        qr_box_layout = QVBoxLayout(self.qr_box)
        qr_box_layout.setAlignment(Qt.AlignCenter)
        qr_box_layout.setSpacing(10)

        self.lbl_qr_img = QLabel(self.qr_box)
        self.lbl_qr_img.setAlignment(Qt.AlignCenter)
        self.lbl_qr_img.setFixedSize(200, 200)
        self.lbl_qr_img.setStyleSheet("background: white; border-radius: 8px; padding: 4px;")
        qr_box_layout.addWidget(self.lbl_qr_img, alignment=Qt.AlignCenter)

        self.lbl_qr_status = CaptionLabel(tr("lbl_scan_qr_desc"), self.qr_box)
        self.lbl_qr_status.setAlignment(Qt.AlignCenter)
        self.lbl_qr_status.setStyleSheet("color: #00bcd4; font-weight: bold;")
        qr_box_layout.addWidget(self.lbl_qr_status)

        self.btn_cancel_qr = TransparentPushButton(tr("btn_cancel_qr"), self.qr_box)
        self.btn_cancel_qr.clicked.connect(self._on_cancel_qr_clicked)
        qr_box_layout.addWidget(self.btn_cancel_qr, alignment=Qt.AlignCenter)

        self.qr_box.hide()
        pb_layout.addWidget(self.qr_box)

        self.plug_body_widget.setVisible(self.plug.enabled if self.plug else False)
        p_layout.addWidget(self.plug_body_widget)
        content_layout.addWidget(self.plug_card)

        # 3. Appearance Card
        theme_card = CardWidget(scroll_content)
        t_layout = QVBoxLayout(theme_card)
        t_layout.setContentsMargins(24, 20, 24, 20)
        t_layout.setSpacing(20)

        self.sec_app_lbl = SubtitleLabel(tr("sec_appearance"), theme_card)
        t_layout.addWidget(self.sec_app_lbl)

        # Language row
        lang_row = QHBoxLayout()
        lang_info = QVBoxLayout()
        lang_info.setSpacing(4)
        self.lbl_lang_title = BodyLabel(tr("lbl_language"), theme_card)
        self.lbl_lang_desc = CaptionLabel(tr("desc_language"), theme_card)
        self.lbl_lang_desc.setStyleSheet("color: gray;")
        lang_info.addWidget(self.lbl_lang_title)
        lang_info.addWidget(self.lbl_lang_desc)
        lang_row.addLayout(lang_info)
        lang_row.addStretch()

        self.lang_combo = ComboBox(theme_card)
        self._populate_language_combo()
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.lang_combo)
        t_layout.addLayout(lang_row)

        # Theme row
        theme_row = QHBoxLayout()
        theme_info = QVBoxLayout()
        theme_info.setSpacing(4)
        self.lbl_theme_title = BodyLabel(tr("lbl_theme"), theme_card)
        self.lbl_theme_desc = CaptionLabel(tr("desc_theme"), theme_card)
        self.lbl_theme_desc.setStyleSheet("color: gray;")
        theme_info.addWidget(self.lbl_theme_title)
        theme_info.addWidget(self.lbl_theme_desc)
        theme_row.addLayout(theme_info)
        theme_row.addStretch()

        self.theme_combo = ComboBox(theme_card)
        self.theme_combo.addItems(["Dark", "Light", "Auto"])
        self.theme_combo.setCurrentText(self.config.get("theme", "Dark"))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo)
        t_layout.addLayout(theme_row)

        content_layout.addWidget(theme_card)

        # 4. Device Hardware Info Card
        dev_card = CardWidget(scroll_content)
        self.d_layout = QVBoxLayout(dev_card)
        self.d_layout.setContentsMargins(24, 20, 24, 20)
        self.d_layout.setSpacing(12)

        self.sec_hw_lbl = SubtitleLabel(tr("sec_hardware"), dev_card)
        self.d_layout.addWidget(self.sec_hw_lbl)

        self.dev_rows_container = QVBoxLayout()
        self.dev_rows_container.setSpacing(10)
        self._build_hardware_rows(dev_card)
        self.d_layout.addLayout(self.dev_rows_container)

        content_layout.addWidget(dev_card)
        content_layout.addStretch()

        self.scroll.setWidget(scroll_content)
        main_layout.addWidget(self.scroll)

    def _connect_plug_signals(self):
        if not self.plug:
            return
        self.plug.qr_ready.connect(self._on_qr_ready)
        self.plug.auth_success.connect(self._on_auth_success)
        self.plug.auth_failed.connect(self._on_auth_failed)
        self.plug.device_updated.connect(lambda name, dev_id, ip: self.lbl_plug_device_name.setText(name))

    def _on_plug_enable_toggled(self, checked):
        if self.plug:
            self.plug.enabled = checked
            self._save_plug_settings()
        self.plug_body_widget.setVisible(checked)

    def _save_plug_settings(self):
        if not self.plug:
            return
        self.plug.update_settings(
            enabled=self.sw_plug_enable.isChecked(),
            cooldown_sec=self.in_cooldown_delay.value(),
            auto_power_off=self.sw_auto_off.isChecked(),
            auto_power_on=self.sw_auto_on.isChecked()
        )

    def _on_generate_qr_clicked(self):
        if not self.plug:
            return
        code = self.in_user_code.text().strip()
        if not code:
            InfoBar.warning(tr("sec_smart_plug"), tr("lbl_user_code"), parent=self)
            return
        self.btn_gen_qr.setEnabled(False)
        self.lbl_qr_status.setText(tr("lbl_qr_waiting"))
        self.qr_box.show()
        self.plug.start_qr_login(code)

    def _on_cancel_qr_clicked(self):
        if self.plug:
            self.plug.cancel_qr_login()
        self.qr_box.hide()
        self.btn_gen_qr.setEnabled(True)

    def _on_qr_ready(self, png_bytes: bytes):
        pix = QPixmap()
        pix.loadFromData(png_bytes)
        self.lbl_qr_img.setPixmap(pix.scaled(190, 190, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.lbl_qr_status.setText(tr("lbl_scan_qr_desc"))

    def _on_auth_success(self, dev_name: str):
        self.qr_box.hide()
        self.btn_gen_qr.setEnabled(True)
        self._update_plug_status_ui()
        InfoBar.success(
            tr("sec_smart_plug"),
            tr("msg_plug_auth_ok", dev_name),
            parent=self,
            duration=4000
        )

    def _on_auth_failed(self, err_msg: str):
        self.btn_gen_qr.setEnabled(True)
        self.lbl_qr_status.setText(err_msg)
        InfoBar.error(
            tr("sec_smart_plug"),
            tr("msg_plug_auth_err", err_msg),
            parent=self,
            duration=4000
        )

    def _update_plug_status_ui(self):
        if not hasattr(self, 'lbl_plug_status_icon'):
            return
        if not self.plug or not self.plug.device_id:
            self.lbl_plug_status_icon.setText("⚠️")
            self.lbl_plug_status_info.setText(tr("status_plug_not_linked"))
            self.lbl_plug_status_info.setStyleSheet("color: #ffb74d; font-weight: bold;")
            self.btn_test_toggle.setEnabled(False)
            self.lbl_plug_device_name.setText("—")
        else:
            self.lbl_plug_status_icon.setText("✅")
            dev_name = self.plug.device_name or "Smart Plug"
            self.lbl_plug_status_info.setText(tr("status_plug_linked", dev_name))
            self.lbl_plug_status_info.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.btn_test_toggle.setEnabled(True)
            self.lbl_plug_device_name.setText(dev_name)

    def _on_user_code_changed(self, text):
        from core.database import set_setting
        val = text.strip()
        set_setting("tuya_user_code", val)
        if self.plug:
            self.plug.user_code = val

    def _on_save_code_clicked(self):
        self._on_user_code_changed(self.in_user_code.text())
        InfoBar.success(
            tr("sec_smart_plug"),
            tr("msg_code_saved"),
            parent=self,
            duration=2500
        )

    def _on_test_toggle_clicked(self):
        if self.plug:
            self.plug.toggle()
            status_text = tr("val_on") if self.plug._is_on else tr("val_off")
            InfoBar.info(tr("sec_smart_plug"), f"{tr('lbl_plug_status')} {status_text}", parent=self, duration=2000)

    def _populate_language_combo(self):
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        current_code = self.config.get("language", get_language())
        current_idx = 0
        for i, (code, name) in enumerate(LANGUAGES.items()):
            self.lang_combo.addItem(f"{name} ({code})", userData=code)
            if code == current_code:
                current_idx = i
        self.lang_combo.setCurrentIndex(current_idx)
        self.lang_combo.blockSignals(False)

    def _build_hardware_rows(self, parent_widget):
        while self.dev_rows_container.count():
            item = self.dev_rows_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        info_items = [
            (tr("lbl_model"), "Liadi Z230 Bi-Color (COB LED 230W)"),
            (tr("lbl_ble_name"), self.config.get("device_name", "LTF_MWRGB")),
            (tr("lbl_mac"), self.config.get("device_mac", "12:22:33:44:D6:55")),
            (tr("lbl_gatt_svc"), "0000fff0-0000-1000-8000-00805f9b34fb"),
            (tr("lbl_gatt_tx"), "0000fff3-0000-1000-8000-00805f9b34fb"),
            (tr("lbl_gatt_rx"), "0000fff4-0000-1000-8000-00805f9b34fb"),
            (tr("lbl_lamp_mode"), tr("val_lamp_mode"))
        ]

        for label, val in info_items:
            row = QHBoxLayout()
            lbl = BodyLabel(label, parent_widget)
            lbl.setStyleSheet("color: gray;")
            val_lbl = BodyLabel(val, parent_widget)
            val_lbl.setStyleSheet("font-weight: 500;")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val_lbl)
            self.dev_rows_container.addLayout(row)

    def retranslate_ui(self):
        self.title_lbl.setText(tr("settings_title"))
        self.sec_win_lbl.setText(tr("sec_windows"))
        self.lbl_auto_title.setText(tr("lbl_autostart"))
        self.lbl_auto_desc.setText(tr("desc_autostart"))
        self.lbl_min_title.setText(tr("lbl_min_tray"))
        self.lbl_min_desc.setText(tr("desc_min_tray"))
        self.lbl_close_title.setText(tr("lbl_close_tray"))
        self.lbl_close_desc.setText(tr("desc_close_tray"))
        self.sw_auto.setOnText(tr("val_on"))
        self.sw_auto.setOffText(tr("val_off"))
        self.sw_min.setOnText(tr("val_on"))
        self.sw_min.setOffText(tr("val_off"))
        self.sw_close.setOnText(tr("val_on"))
        self.sw_close.setOffText(tr("val_off"))

        # Smart plug card retranslate
        self.sec_plug_lbl.setText(tr("sec_smart_plug"))
        self.desc_plug_lbl.setText(tr("desc_smart_plug"))
        self.lbl_enable_plug.setText(tr("lbl_enable_plug"))
        self.sw_plug_enable.setOnText(tr("val_on"))
        self.sw_plug_enable.setOffText(tr("val_off"))
        self.lbl_plug_status_title.setText(tr("lbl_plug_status"))
        self.btn_plug_on.setText(tr("btn_plug_on"))
        self.btn_plug_off.setText(tr("btn_plug_off"))
        self.lbl_auto_off.setText(tr("lbl_auto_power_off"))
        self.lbl_auto_off_desc.setText(tr("tip_cooldown_delay"))
        self.sw_auto_off.setOnText(tr("val_on"))
        self.sw_auto_off.setOffText(tr("val_off"))
        self.lbl_cooldown_delay.setText(tr("lbl_cooldown_delay"))
        self.lbl_auto_on.setText(tr("lbl_auto_power_on"))
        self.sw_auto_on.setOnText(tr("val_on"))
        self.sw_auto_on.setOffText(tr("val_off"))
        self.lbl_qr_title.setText(tr("lbl_qr_pairing"))
        self.lbl_qr_desc.setText(tr("ph_user_code"))
        self.in_user_code.setPlaceholderText(tr("lbl_user_code"))
        self.btn_gen_qr.setText(tr("btn_gen_qr"))
        self.btn_cancel_qr.setText(tr("btn_cancel_qr"))
        if hasattr(self, 'btn_save_code'):
            self.btn_save_code.setText(tr("btn_save_code"))
        if hasattr(self, 'btn_test_toggle'):
            self.btn_test_toggle.setText("⚡ " + tr("btn_test_plug"))
        self._update_plug_status_ui()

        self.sec_app_lbl.setText(tr("sec_appearance"))
        self.lbl_lang_title.setText(tr("lbl_language"))
        self.lbl_lang_desc.setText(tr("desc_language"))
        self.lbl_theme_title.setText(tr("lbl_theme"))
        self.lbl_theme_desc.setText(tr("desc_theme"))
        self.sec_hw_lbl.setText(tr("sec_hardware"))
        self._build_hardware_rows(self)

    def _on_language_changed(self, index):
        code = self.lang_combo.itemData(index)
        if code:
            set_language(code)
            self.config["language"] = code
            self.config_updated.emit(self.config)
            self.language_changed.emit(code)
            self.retranslate_ui()

    def _on_autostart_toggled(self, checked):
        set_autostart(checked)
        self.config["autostart"] = checked
        self.config_updated.emit(self.config)
        status = tr("val_on") if checked else tr("val_off")
        InfoBar.info(tr("lbl_autostart"), f"{tr('lbl_autostart')}: {status}", parent=self, duration=2000)

    def _on_min_tray_toggled(self, checked):
        self.config["minimize_to_tray"] = checked
        self.config_updated.emit(self.config)

    def _on_close_tray_toggled(self, checked):
        self.config["close_to_tray"] = checked
        self.config_updated.emit(self.config)

    def _on_theme_changed(self, theme_text):
        self.config["theme"] = theme_text
        if theme_text == "Dark":
            setTheme(Theme.DARK)
        elif theme_text == "Light":
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.AUTO)
        self.config_updated.emit(self.config)
