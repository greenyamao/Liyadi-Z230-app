from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame
)
from qfluentwidgets import (
    CardWidget, SwitchButton, LineEdit, PushButton,
    TitleLabel, SubtitleLabel, BodyLabel, CaptionLabel, ComboBox,
    FluentIcon as FIF, setTheme, Theme, InfoBar, InfoBarPosition
)
from core.autostart import is_autostart_enabled, set_autostart
from core.i18n import tr, set_language, get_language, LANGUAGES

class SettingsView(QWidget):
    config_updated = Signal(dict)
    language_changed = Signal(str)
    scan_requested = Signal()

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        self.title_lbl = TitleLabel(tr("settings_title"), self)
        main_layout.addWidget(self.title_lbl)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
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

        # 2. Appearance & Language Card
        theme_card = CardWidget(scroll_content)
        t_layout = QVBoxLayout(theme_card)
        t_layout.setContentsMargins(24, 20, 24, 20)
        t_layout.setSpacing(18)

        self.sec_app_lbl = SubtitleLabel(tr("sec_appearance"), theme_card)
        t_layout.addWidget(self.sec_app_lbl)

        # Language Row
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

        # Theme Row
        theme_row = QHBoxLayout()
        theme_info = QVBoxLayout()
        theme_info.setSpacing(4)
        self.lbl_theme_title = BodyLabel(tr("lbl_theme"), theme_card)
        self.lbl_theme_desc = CaptionLabel(tr("desc_theme"), theme_card)
        theme_desc = self.lbl_theme_desc
        theme_desc.setStyleSheet("color: gray;")
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

        # 3. Device Hardware Info Card
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

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

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
