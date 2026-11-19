import io
import json
import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, Signal, QTimer
import qrcode
import tinytuya
from tuya_sharing import LoginControl, Manager, SharingTokenListener
from core.database import get_setting, set_setting

CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
SCHEMA = "haauthorize"
TOKEN_FIELDS = ("t", "uid", "expire_time", "access_token", "refresh_token")

logger = logging.getLogger("SmartPlug")

class SmartPlugTokenListener(SharingTokenListener):
    def __init__(self, plug_manager):
        self.plug_manager = plug_manager

    def update_token(self, token_info: dict):
        self.plug_manager._on_token_refreshed(token_info)

class SmartPlugManager(QObject):
    # Signals
    status_changed = Signal(bool)          # True = ON (220V), False = OFF (0V)
    device_updated = Signal(str, str, str) # name, device_id, ip
    qr_ready = Signal(bytes)               # PNG image bytes of QR code
    auth_success = Signal(str)             # device_name
    auth_failed = Signal(str)              # error message
    cooldown_tick = Signal(int)            # remaining seconds
    cooldown_finished = Signal()           # cooldown ended, power turned off
    cooldown_cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = bool(get_setting("plug_enabled", False))
        self.device_id = str(get_setting("plug_device_id", ""))
        self.device_name = str(get_setting("plug_device_name", ""))
        self.local_key = str(get_setting("plug_local_key", ""))
        self.ip = str(get_setting("plug_ip", ""))
        self.cooldown_sec = int(get_setting("plug_cooldown_sec", 30))
        self.auto_power_off = bool(get_setting("plug_auto_power_off", True))
        self.auto_power_on = bool(get_setting("plug_auto_power_on", True))
        self.user_code = str(get_setting("tuya_user_code", ""))

        self._session = get_setting("tuya_session", None)
        self._manager: Optional[Manager] = None
        self._is_on = True
        self._target_power: Optional[bool] = None

        # Serialized power command queue to eliminate thread races
        self._cmd_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self._worker_thread.start()

        # Cooldown timer
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._on_cooldown_tick)
        self._remaining_cooldown = 0

        # QR login thread
        self._login_thread = None
        self._cancel_login = False

        # Initialize manager in background if session exists
        if self._session:
            threading.Thread(target=self._init_manager, daemon=True).start()

    def _init_manager(self):
        if not self._session:
            return
        try:
            listener = SmartPlugTokenListener(self)
            self._manager = Manager(
                self._session.get("client_id", CLIENT_ID),
                self._session.get("user_code", ""),
                self._session.get("terminal_id", ""),
                self._session.get("endpoint", "https://openapi.tuyaeu.com"),
                self._session.get("token_info", {}),
                listener=listener
            )
            self._manager.update_device_cache()
            devices = list(self._manager.device_map.values())
            if devices:
                # If no device_id saved yet, pick first or socket
                if not self.device_id:
                    dev = devices[0]
                    for d in devices:
                        if getattr(d, 'category', '') == 'cz':
                            dev = d
                            break
                    self.device_id = dev.id
                    self.device_name = dev.name
                    self.local_key = getattr(dev, 'local_key', '')
                    self.ip = getattr(dev, 'ip', '')
                    set_setting("plug_device_id", self.device_id)
                    set_setting("plug_device_name", self.device_name)
                    set_setting("plug_local_key", self.local_key)
                    set_setting("plug_ip", self.ip)
                    self.device_updated.emit(self.device_name, self.device_id, self.ip)
        except Exception as e:
            logger.error(f"Error initializing Tuya manager: {e}")

    def _on_token_refreshed(self, token_info: dict):
        if self._session:
            self._session["token_info"] = token_info
            set_setting("tuya_session", self._session)

    # --- QR Code Pairing Workflow ---

    def start_qr_login(self, user_code: str):
        """Starts asynchronous QR code generation and polling thread."""
        user_code = user_code.strip()
        if not user_code:
            self.auth_failed.emit("Введите код пользователя Smart Life")
            return

        self.user_code = user_code
        set_setting("tuya_user_code", user_code)

        self._cancel_login = False
        self._login_thread = threading.Thread(
            target=self._run_qr_login,
            args=(user_code,),
            daemon=True
        )
        self._login_thread.start()

    def cancel_qr_login(self):
        self._cancel_login = True

    def _run_qr_login(self, user_code: str):
        try:
            login = LoginControl()
            resp = login.qr_code(CLIENT_ID, SCHEMA, user_code)
            if not resp.get("success"):
                err_msg = resp.get("msg") or "Неверный код пользователя"
                self.auth_failed.emit(err_msg)
                return

            token = resp["result"]["qrcode"]

            # Generate PNG bytes for QPixmap display with Tuya app login payload URI
            qr_payload = f"tuyaSmart--qrLogin?token={token}"
            qr = qrcode.QRCode(
                box_size=6,
                border=2,
                error_correction=qrcode.constants.ERROR_CORRECT_M
            )
            qr.add_data(qr_payload)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()

            self.qr_ready.emit(png_bytes)

            # Poll login result (poll every 2 seconds, timeout 150 seconds)
            start_time = time.time()
            while time.time() - start_time < 150 and not self._cancel_login:
                time.sleep(2.0)
                try:
                    ok, result = login.login_result(token, CLIENT_ID, user_code)
                    if ok:
                        # Logged in successfully!
                        session = {
                            "client_id": CLIENT_ID,
                            "user_code": user_code,
                            "terminal_id": result.get("terminal_id"),
                            "endpoint": result.get("endpoint") or result.get("end_point"),
                            "token_info": {k: result.get(k) for k in TOKEN_FIELDS},
                        }
                        self._session = session
                        set_setting("tuya_session", session)

                        # Init manager and query devices
                        self._init_manager()
                        if self._manager and self._manager.device_map:
                            devices = list(self._manager.device_map.values())
                            dev = devices[0]
                            for d in devices:
                                if getattr(d, 'category', '') == 'cz':
                                    dev = d
                                    break
                            self.device_id = dev.id
                            self.device_name = dev.name
                            self.local_key = getattr(dev, 'local_key', '')
                            self.ip = getattr(dev, 'ip', '')

                            set_setting("plug_device_id", self.device_id)
                            set_setting("plug_device_name", self.device_name)
                            set_setting("plug_local_key", self.local_key)
                            set_setting("plug_ip", self.ip)
                            set_setting("plug_enabled", True)
                            self.enabled = True

                            self.device_updated.emit(self.device_name, self.device_id, self.ip)
                            self.auth_success.emit(self.device_name)
                        else:
                            self.auth_failed.emit("Устройства не найдены в аккаунте Smart Life")
                        return
                except Exception as e:
                    logger.debug(f"Polling check error: {e}")

            if self._cancel_login:
                self.auth_failed.emit("Привязка отменена")
            else:
                self.auth_failed.emit("Время ожидания сканирования истекло")
        except Exception as e:
            self.auth_failed.emit(str(e))

    # --- Power Control (Dual-Mode: Local LAN + Cloud API Fallback) ---

    def is_on(self) -> bool:
        if self._target_power is not None:
            return self._target_power
        return bool(self._is_on)

    def turn_on(self, force: bool = False) -> bool:
        self.cancel_cooldown()
        if not force and self.is_on():
            return True
        return self.set_power(True, force=force)

    def turn_off(self, force: bool = False) -> bool:
        if not force and not self.is_on():
            return True
        return self.set_power(False, force=force)

    def toggle(self) -> bool:
        return self.set_power(not self.is_on(), force=True)

    def set_power(self, is_on: bool, force: bool = False) -> bool:
        """Queues a power state change request for serial execution."""
        if not self.enabled:
            return False

        if not force and self._target_power == is_on:
            return True

        self._target_power = is_on
        self._cmd_queue.put(is_on)
        return True

    def _queue_worker(self):
        while True:
            try:
                target_state = self._cmd_queue.get()
                # Coalesce / drain queue so only the latest requested state executes
                while not self._cmd_queue.empty():
                    try:
                        target_state = self._cmd_queue.get_nowait()
                    except queue.Empty:
                        break

                self._execute_power_command(target_state)
            except Exception as e:
                logger.error(f"Error in plug worker queue: {e}")

    def _execute_power_command(self, is_on: bool):
        success = False

        # 1. Try local LAN via tinytuya ONLY if IP is a private LAN address (e.g. 192.168.x.x)
        if self.device_id and self.ip and self.local_key:
            try:
                import ipaddress
                ip_obj = ipaddress.ip_address(self.ip)
                if ip_obj.is_private:
                    plug = tinytuya.OutletDevice(self.device_id, self.ip, self.local_key)
                    plug.set_version(3.3)
                    plug.set_socketPersistent(False)
                    plug.set_socketTimeout(1.0)
                    res = plug.turn_on() if is_on else plug.turn_off()
                    if isinstance(res, dict) and "Error" not in res:
                        success = True
                        logger.info(f"Local LAN command successful: is_on={is_on}")
            except Exception as e:
                logger.debug(f"Local LAN command skipped or failed: {e}")

        # 2. Fast Cloud API via tuya_sharing (runs in ~350ms)
        if not success and self._manager and self.device_id:
            try:
                # Try standard Tuya socket DPS code "switch_1"
                self._manager.send_commands(self.device_id, [{"code": "switch_1", "value": is_on}])
                success = True
                logger.info(f"Cloud API command successful (switch_1): is_on={is_on}")
            except Exception:
                try:
                    # Fallback to "switch"
                    self._manager.send_commands(self.device_id, [{"code": "switch", "value": is_on}])
                    success = True
                    logger.info(f"Cloud API command successful (switch): is_on={is_on}")
                except Exception as e2:
                    logger.error(f"Cloud API command failed: {e2}")

        if success:
            self._is_on = is_on
            self.status_changed.emit(is_on)

    # --- Cooldown Automation ---

    def start_cooldown(self):
        """Starts countdown before cutting 220V power to allow fan to cool the COB LED."""
        if not self.enabled or not self.auto_power_off:
            return

        # Crucial guard: do not restart timer if cooldown is already running
        if self._cooldown_timer.isActive():
            return

        if self.cooldown_sec <= 0:
            self.turn_off()
            self.cooldown_finished.emit()
            return

        self._remaining_cooldown = self.cooldown_sec
        self._cooldown_timer.start()
        self.cooldown_tick.emit(self._remaining_cooldown)

    def cut_power_immediately(self):
        """Instantly cuts power without waiting for remaining cooldown timer."""
        self.cancel_cooldown()
        self.turn_off()
        self.cooldown_finished.emit()

    def cancel_cooldown(self):
        if self._cooldown_timer.isActive():
            self._cooldown_timer.stop()
            self._remaining_cooldown = 0
            self.cooldown_cancelled.emit()

    def is_cooling_down(self) -> bool:
        return self._cooldown_timer.isActive()

    def _on_cooldown_tick(self):
        self._remaining_cooldown -= 1
        if self._remaining_cooldown <= 0:
            self._cooldown_timer.stop()
            self.turn_off()
            self.cooldown_finished.emit()
        else:
            self.cooldown_tick.emit(self._remaining_cooldown)

    # --- Parameter Updates ---

    def update_settings(self, enabled: bool, cooldown_sec: int, auto_power_off: bool, auto_power_on: bool,
                        ip: str = "", device_id: str = "", local_key: str = "", device_name: str = ""):
        self.enabled = enabled
        self.cooldown_sec = max(0, min(300, cooldown_sec))
        self.auto_power_off = auto_power_off
        self.auto_power_on = auto_power_on

        set_setting("plug_enabled", self.enabled)
        set_setting("plug_cooldown_sec", self.cooldown_sec)
        set_setting("plug_auto_power_off", self.auto_power_off)
        set_setting("plug_auto_power_on", self.auto_power_on)

        if ip:
            self.ip = ip
            set_setting("plug_ip", self.ip)
        if device_id:
            self.device_id = device_id
            set_setting("plug_device_id", self.device_id)
        if local_key:
            self.local_key = local_key
            set_setting("plug_local_key", self.local_key)
        if device_name:
            self.device_name = device_name
            set_setting("plug_device_name", self.device_name)
