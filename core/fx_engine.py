import math
import random
from PySide6.QtCore import QObject, QTimer, Signal

class FXEngine(QObject):
    fx_started = Signal(str)
    fx_stopped = Signal()

    def __init__(self, ble_manager, parent=None):
        super().__init__(parent)
        self.ble = ble_manager
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        
        self.current_fx = None
        self.tick_count = 0
        self.fps = 15  # 15 updates per sec (BLE friendly)
        self.timer.setInterval(int(1000 / self.fps))
        
        # State for generator
        self.custom_params = {
            "min_b": 10,
            "max_b": 80,
            "min_k": 3200,
            "max_k": 5600,
            "speed_sec": 3.0,
            "wave": "sine"  # "sine" | "pulse" | "chaos"
        }
        
        # Internal animation vars
        self._storm_phase = 0
        self._storm_pause = 0
        self._bad_bulb_flutter = 0

    def start_hardware_fx(self, fx_id: int, speed: int = 100, freq: int = 0):
        """Starts a built-in lamp hardware effect"""
        self.stop()
        self.current_fx = f"hw_{fx_id}"
        self.ble.set_effect(fx_id, speed, freq, brightness=max(10, self.ble.brightness))
        self.fx_started.emit(self.current_fx)

    def start_software_fx(self, fx_type: str, custom_params: dict = None):
        """Starts a software-generated dynamic effect on the Bi-Color light"""
        self.stop()
        self.current_fx = fx_type
        self.tick_count = 0
        if custom_params:
            self.custom_params.update(custom_params)
            
        self.timer.start()
        self.fx_started.emit(self.current_fx)

    def stop(self):
        """Stops any active hardware or software effect and restores steady CCT light"""
        self.timer.stop()
        active = self.current_fx
        self.current_fx = None
        if active:
            # Restore normal steady CCT
            self.ble.set_cct(self.ble.is_on, self.ble.brightness, self.ble.kelvin)
            self.fx_stopped.emit()

    def _tick(self):
        if not self.current_fx or not self.ble.is_on:
            return

        self.tick_count += 1
        t = self.tick_count / float(self.fps)

        if self.current_fx == "lightning":
            self._tick_lightning()
        elif self.current_fx == "bad_bulb":
            self._tick_bad_bulb()
        elif self.current_fx == "breathing":
            self._tick_breathing(t)
        elif self.current_fx == "custom":
            self._tick_custom(t)

    def _tick_lightning(self):
        """Realistic lightning flashes with random pauses"""
        if self._storm_pause > 0:
            self._storm_pause -= 1
            # Dim ambient thunder glow
            self.ble.set_cct(True, 2, 5600)
            return

        if self._storm_phase == 0:
            # Random wait before next strike (1.5 to 4.5 seconds)
            self._storm_pause = random.randint(int(self.fps * 1.5), int(self.fps * 4.5))
            self._storm_phase = 1
        elif self._storm_phase == 1:
            # Flash 1 (Main strike, cold white)
            self.ble.set_cct(True, random.randint(90, 100), 7500)
            self._storm_phase = 2
        elif self._storm_phase == 2:
            # Drop
            self.ble.set_cct(True, random.randint(15, 30), 6500)
            self._storm_phase = 3
        elif self._storm_phase == 3:
            # Flash 2 (Echo strike)
            self.ble.set_cct(True, random.randint(70, 95), 8000)
            self._storm_phase = 4
        elif self._storm_phase == 4:
            # Fade out
            self.ble.set_cct(True, random.randint(5, 15), 5600)
            self._storm_phase = 0

    def _tick_bad_bulb(self):
        """Flickering fluorescent / defective lamp in old hallway"""
        base_b = max(40, self.ble.brightness)
        base_k = self.ble.kelvin

        if self._bad_bulb_flutter > 0:
            self._bad_bulb_flutter -= 1
            # Micro drop or flicker
            flicker_b = random.choice([0, 5, 12, int(base_b * 0.3)])
            self.ble.set_cct(flicker_b > 0, flicker_b, base_k)
            return

        # 8% chance per tick to initiate a flutter
        if random.random() < 0.08:
            self._bad_bulb_flutter = random.randint(1, 4)
            self.ble.set_cct(True, random.randint(5, 20), base_k)
        else:
            # Normal steady light with tiny realistic hum
            jitter = random.randint(-2, 2)
            self.ble.set_cct(True, max(1, min(100, base_b + jitter)), base_k)

    def _tick_breathing(self, t: float):
        """Smooth harmonic sine wave of brightness and gentle temperature oscillation"""
        speed = 4.0 # 4 second full breath
        phase = (t % speed) / speed * 2 * math.pi
        sin_val = 0.5 * (1.0 + math.sin(phase)) # 0.0 to 1.0

        b = int(10 + (80 - 10) * sin_val)
        k = int(3000 + (5600 - 3000) * sin_val)
        self.ble.set_cct(True, b, k)

    def _tick_custom(self, t: float):
        """User defined dynamic cycle"""
        p = self.custom_params
        speed = max(0.5, float(p.get("speed_sec", 3.0)))
        phase = (t % speed) / speed

        min_b = p.get("min_b", 10)
        max_b = p.get("max_b", 80)
        min_k = p.get("min_k", 3000)
        max_k = p.get("max_k", 5600)
        wave = p.get("wave", "sine")

        if wave == "sine":
            val = 0.5 * (1.0 + math.sin(phase * 2 * math.pi))
        elif wave == "pulse":
            # Sharp burst then decay
            val = math.exp(-4.0 * phase)
        else: # chaos
            val = random.random()

        b = int(min_b + (max_b - min_b) * val)
        k = int(min_k + (max_k - min_k) * val)
        self.ble.set_cct(True, max(1, min(100, b)), max(2500, min(6500, k)))
