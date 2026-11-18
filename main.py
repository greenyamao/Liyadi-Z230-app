import sys
import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from qfluentwidgets import (
    MSFluentWindow, NavigationItemPosition, FluentIcon as FIF,
    setTheme, Theme
)

from core.i18n import tr, set_language, get_language
from core.config import load_config, save_config
from core.ble_manager import BLEManager
from core.scheduler import SchedulerEngine
from core.smart_plug import SmartPlugManager
from ui.light_view import LightView
from ui.scheduler_view import SchedulerView
from ui.effects_view import EffectsView
from ui.settings_view import SettingsView
from ui.tray_manager import TrayManager, create_tray_icon_pixmap

class MainWindow(MSFluentWindow):
    def __init__(self, config: dict, ble: BLEManager, scheduler: SchedulerEngine, plug: SmartPlugManager = None, start_minimized=False):
        super().__init__()
        self.config = config
        self.ble = ble
        self.scheduler = scheduler
        self.plug = plug
        self.start_minimized = start_minimized

        self.setWindowTitle(tr("app_title"))
        self.setWindowIcon(create_tray_icon_pixmap())
        self.setMicaEffectEnabled(False)
        self.resize(1020, 720)
        self.setMinimumSize(880, 600)

        self._init_sub_interfaces()
        self._init_tray()
        self._connect_signals()

    def _init_sub_interfaces(self):
        # 1. Light Interface
        self.light_view = LightView(self.ble, self)
        self.light_view.setObjectName("light_interface")
        self.addSubInterface(self.light_view, FIF.BRIGHTNESS, tr("nav_light"))

        # 2. Scheduler & Circadian Interface
        self.scheduler_view = SchedulerView(self.scheduler, self.config.get("schedules", []), self)
        self.scheduler_view.setObjectName("scheduler_interface")
        self.addSubInterface(self.scheduler_view, FIF.DATE_TIME, tr("nav_schedule"))

        # 3. Effects Interface
        self.effects_view = EffectsView(self.ble, self)
        self.effects_view.setObjectName("effects_interface")
        self.addSubInterface(self.effects_view, FIF.PALETTE, tr("nav_effects"))

        # 4. Settings Interface (at bottom)
        self.settings_view = SettingsView(self.config, self.plug, self)
        self.settings_view.setObjectName("settings_interface")
        self.addSubInterface(
            self.settings_view,
            FIF.SETTING,
            tr("nav_settings"),
            position=NavigationItemPosition.BOTTOM
        )

    def _init_tray(self):
        self.tray = TrayManager(self)
        self.tray.show()

    def _connect_signals(self):
        # Light view signals -> BLE & Persistence
        self.light_view.brightness_changed.connect(self._on_brightness_changed)
        self.light_view.kelvin_changed.connect(self._on_kelvin_changed)
        self.light_view.reconnect_requested.connect(self.ble.reconnect)

        # BLE signals -> UI update & Persistence
        self.ble.connection_status_changed.connect(self.light_view.update_connection_status)
        self.ble.state_updated.connect(self._on_hardware_state_updated)

        # Scheduler signals
        self.scheduler_view.rules_changed.connect(self._on_rules_changed)

        # Effects signals
        self.effects_view.effect_triggered.connect(self.ble.set_effect)
        self.effects_view.stop_effect_requested.connect(
            lambda: self.ble.set_cct(self.ble.is_on, self.ble.brightness, self.ble.kelvin)
        )

        # Settings signals
        self.settings_view.config_updated.connect(self._on_config_updated)
        self.settings_view.language_changed.connect(self._on_language_changed)

        # Smart plug cooldown signals -> Light view UI banner
        if self.plug:
            self.plug.cooldown_tick.connect(self.light_view.show_cooldown_progress)
            self.plug.cooldown_finished.connect(self.light_view.hide_cooldown_banner)
            self.plug.cooldown_cancelled.connect(self.light_view.hide_cooldown_banner)
            self.light_view.cut_power_requested.connect(self.plug.cut_power_immediately)

        # Tray signals
        self.tray.power_toggled.connect(self._toggle_power_from_tray)
        self.tray.preset_clicked.connect(lambda b, k: self._apply_cct_with_plug(b > 0, b, min(6500, k)))
        self.tray.show_window_requested.connect(self._restore_from_tray)
        self.tray.exit_requested.connect(self._quit_application)

    def _apply_cct_with_plug(self, power: bool, brightness: int, kelvin: int):
        if not power or brightness <= 0:
            self.ble.set_cct(False, 0, kelvin)
            if self.plug and self.plug.enabled and self.plug.auto_power_off:
                self.plug.start_cooldown()
        else:
            if self.plug:
                self.plug.cancel_cooldown()
                if self.plug.enabled and self.plug.auto_power_on:
                    self.plug.turn_on()
            self.ble.set_cct(True, brightness, kelvin)
            self.ble.wake_and_connect()

    def _on_language_changed(self, lang_code: str):
        set_language(lang_code)
        self.config["language"] = lang_code
        save_config(self.config)

        self.setWindowTitle(tr("app_title"))
        item_light = self.navigationInterface.widget("light_interface")
        if item_light:
            item_light.setText(tr("nav_light"))
        item_sched = self.navigationInterface.widget("scheduler_interface")
        if item_sched:
            item_sched.setText(tr("nav_schedule"))
        item_fx = self.navigationInterface.widget("effects_interface")
        if item_fx:
            item_fx.setText(tr("nav_effects"))
        item_sett = self.navigationInterface.widget("settings_interface")
        if item_sett:
            item_sett.setText(tr("nav_settings"))

        self.light_view.retranslate_ui()
        self.scheduler_view.retranslate_ui()
        self.effects_view.retranslate_ui()
        self.settings_view.retranslate_ui()
        self.tray.retranslate_ui()

    def _on_brightness_changed(self, val: int):
        if val <= 0:
            self.ble.set_brightness(0)
            if self.plug and self.plug.enabled and self.plug.auto_power_off:
                self.plug.start_cooldown()
        else:
            if self.plug:
                self.plug.cancel_cooldown()
                if self.plug.enabled and self.plug.auto_power_on:
                    self.plug.turn_on()
            self.ble.set_brightness(val)
            self.ble.wake_and_connect()

        self.config["last_brightness"] = val
        self.config["last_power"] = (val > 0)
        save_config(self.config)

    def _on_kelvin_changed(self, val: int):
        clamped_k = min(6500, max(2700, val))
        self.ble.set_kelvin(clamped_k)
        self.config["last_kelvin"] = clamped_k
        save_config(self.config)

    def _on_hardware_state_updated(self, is_on: bool, brightness: int, kelvin: int):
        clamped_k = min(6500, max(2700, kelvin))
        self.light_view.update_hardware_state(is_on, brightness, clamped_k)
        self.config["last_power"] = is_on
        self.config["last_brightness"] = brightness
        self.config["last_kelvin"] = clamped_k
        save_config(self.config)

    def _toggle_power_from_tray(self):
        new_power = not self.ble.is_on
        if new_power:
            target_b = self.ble.brightness if self.ble.brightness > 0 else 30
            if self.plug:
                self.plug.cancel_cooldown()
                if self.plug.enabled and self.plug.auto_power_on:
                    self.plug.turn_on()
            self.ble.set_cct(True, target_b, self.ble.kelvin)
            self.ble.wake_and_connect()
        else:
            self.ble.set_cct(False, 0, self.ble.kelvin)
            if self.plug and self.plug.enabled and self.plug.auto_power_off:
                self.plug.start_cooldown()
        self.config["last_power"] = new_power
        save_config(self.config)

    def _on_rules_changed(self, new_rules):
        self.config["schedules"] = new_rules
        save_config(self.config)

    def _on_config_updated(self, new_cfg):
        self.config = new_cfg
        save_config(self.config)

    def _restore_from_tray(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()

    def _quit_application(self):
        # Flush current state to SQLite before exit
        self.config["last_power"] = self.ble.is_on
        self.config["last_brightness"] = self.ble.brightness
        self.config["last_kelvin"] = self.ble.kelvin
        save_config(self.config)
        self.ble.stop()
        self.tray.hide()
        QApplication.quit()

    def changeEvent(self, event):
        # Minimize to tray
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized() and self.config.get("minimize_to_tray", True):
                self.hide()
                event.ignore()
                return
        super().changeEvent(event)

    def closeEvent(self, event):
        # Close button acts as minimize to tray if enabled
        if self.config.get("close_to_tray", True):
            self.hide()
            event.ignore()
        else:
            self._quit_application()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = load_config()

    # 1. Set Language (Default is English 'en')
    lang = config.get("language", "en")
    set_language(lang)

    # 2. Set Theme
    theme_str = config.get("theme", "Dark")
    if theme_str == "Dark":
        setTheme(Theme.DARK)
    elif theme_str == "Light":
        setTheme(Theme.LIGHT)
    else:
        setTheme(Theme.AUTO)

    start_minimized = "--minimized" in sys.argv

    # 3. Start BLE engine
    ble = BLEManager(target_mac=config.get("device_mac", "12:22:33:44:D6:55"))
    ble.is_on = config.get("last_power", True)
    ble.brightness = config.get("last_brightness", 1)
    ble.kelvin = min(6500, max(2700, config.get("last_kelvin", 4500)))
    ble.target_power = ble.is_on
    ble.target_brightness = ble.brightness
    ble.target_kelvin = ble.kelvin
    ble.start()

    # 4. Start smart plug manager
    plug = SmartPlugManager()

    # 5. Start scheduler
    scheduler = SchedulerEngine(ble, config.get("schedules", []), plug_manager=plug)

    # 6. Create window
    win = MainWindow(config, ble, scheduler, plug, start_minimized=start_minimized)

    if not start_minimized:
        win.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
