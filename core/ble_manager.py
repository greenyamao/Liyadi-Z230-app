import asyncio
import threading
from PySide6.QtCore import QObject, Signal
from bleak import BleakScanner, BleakClient

SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
TX_CHAR_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"
RX_CHAR_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"

NAME_PREFIXES = ("LTF", "LYD", "Bough")

class BLEManager(QObject):
    connection_status_changed = Signal(str, str)  # status: "connected"|"disconnected"|"connecting"|"error", message
    state_updated = Signal(bool, int, int)         # is_on, brightness, kelvin
    error_occurred = Signal(str)

    def __init__(self, target_mac="12:22:33:44:D6:55", auto_connect=True):
        super().__init__()
        self.target_mac = target_mac
        self.auto_connect = auto_connect
        
        self.is_on = True
        self.brightness = 1
        self.kelvin = 4500
        
        self.client = None
        self.loop = None
        self.thread = None
        self.running = True
        self._connected = False
        self._send_queue = None

    def start(self):
        """Starts the dedicated asyncio thread"""
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main_worker())

    async def _main_worker(self):
        while self.running:
            if not self._connected and self.auto_connect:
                await self._try_connect()
            await asyncio.sleep(4.0)

    async def _try_connect(self):
        try:
            self.connection_status_changed.emit("connecting", "")
            dev = None
            
            # First try direct address if known
            if self.target_mac:
                try:
                    dev = await BleakScanner.find_device_by_address(self.target_mac, timeout=3.0)
                except Exception:
                    dev = None

            # If not found by address, scan for device with LTF name or service
            if not dev:
                devs = await BleakScanner.discover(timeout=4.0, return_adv=True)
                for d, adv in devs.values():
                    name = d.name or adv.local_name or ""
                    uuids = [u.lower() for u in adv.service_uuids]
                    if any(p.lower() in name.lower() for p in NAME_PREFIXES) or SERVICE_UUID in uuids:
                        dev = d
                        self.target_mac = d.address
                        break

            if not dev:
                self.connection_status_changed.emit("disconnected", "")
                return

            self.connection_status_changed.emit("connecting", dev.name or dev.address or "Liadi Z230")
            
            def disconnected_callback(client):
                self._connected = False
                self.connection_status_changed.emit("disconnected", "")

            self.client = BleakClient(dev, disconnected_callback=disconnected_callback, timeout=10.0)
            await self.client.connect()
            self._connected = True
            dev_name = dev.name or "Liadi Z230"
            self.connection_status_changed.emit("connected", dev_name)

            # Subscribe to hardware knob notifications (2-way sync)
            try:
                await self.client.start_notify(RX_CHAR_UUID, self._on_notification)
            except Exception as e:
                print(f"Notify error: {e}")

            # Send initial state sync
            await self._send_state_packet(self.is_on, self.brightness, self.kelvin)

            # Wait while connected
            while self.running and self._connected and self.client and self.client.is_connected:
                await asyncio.sleep(1.0)

        except Exception as e:
            self._connected = False
            self.connection_status_changed.emit("error", str(e))

    def _on_notification(self, sender, data: bytearray):
        """Called when user rotates physical knobs on the lamp"""
        if len(data) >= 4:
            mode = data[0]
            brightness = data[2]
            kelvin = data[3] * 100
            is_on = (mode != 0)
            
            # If lamp is in standby mode, treat brightness as 0
            if not is_on:
                brightness = 0

            # Update local state
            self.is_on = is_on
            self.brightness = brightness
            self.kelvin = kelvin
            
            # Emit signal to update UI sliders in real-time!
            self.state_updated.emit(is_on, brightness, kelvin)

    def _build_packet(self, power: bool, brightness: int, kelvin: int, fx_id: int = 0, speed: int = 100, freq: int = 0) -> bytearray:
        """
        10-byte packet protocol:
        [mode, submode, brightness, kelvin//100, hue_lo, hue_hi, sat, fx_id, speed, freq]
        """
        # 0% brightness is explicitly defined as Standby / OFF
        if brightness <= 0:
            power = False

        if fx_id > 0:
            mode = 3 if power else 0
            submode = max(1, min(24, fx_id))
        else:
            mode = 1 if power else 0
            submode = 1

        # Lamp hardware expects 1-100 when ON, 0 when Standby
        if power:
            p_val = max(1, min(100, int(brightness)))
        else:
            p_val = 0

        k_val = max(25, min(65, int(kelvin // 100)))
        return bytearray([mode, submode, p_val, k_val, 0, 0, 0, fx_id, speed, freq])

    async def _send_state_packet(self, power: bool, brightness: int, kelvin: int, fx_id: int = 0, speed: int = 100, freq: int = 0):
        if not self.client or not self._connected:
            return
        try:
            pkt = self._build_packet(power, brightness, kelvin, fx_id, speed, freq)
            await self.client.write_gatt_char(TX_CHAR_UUID, pkt, response=False)
        except Exception as e:
            print(f"Error sending BLE packet: {e}")

    # Public thread-safe methods to be called from Qt UI thread
    def set_cct(self, power: bool, brightness: int, kelvin: int):
        self.is_on = power
        self.brightness = brightness
        self.kelvin = kelvin
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._send_state_packet(power, brightness, kelvin),
                self.loop
            )

    def set_power(self, power: bool):
        self.set_cct(power, self.brightness, self.kelvin)

    def set_brightness(self, brightness: int):
        power = (brightness > 0)
        self.set_cct(power, brightness, self.kelvin)

    def set_kelvin(self, kelvin: int):
        self.set_cct(self.is_on, self.brightness, kelvin)

    def set_effect(self, fx_id: int, speed: int = 100, freq: int = 0, brightness: int = 50):
        self.is_on = True
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._send_state_packet(True, brightness, self.kelvin, fx_id=fx_id, speed=speed, freq=freq),
                self.loop
            )

    def reconnect(self):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._disconnect_and_reconnect(), self.loop)

    async def _disconnect_and_reconnect(self):
        if self.client and self.client.is_connected:
            try:
                await self.client.disconnect()
            except Exception:
                pass
        self._connected = False
        await self._try_connect()

    def stop(self):
        self.running = False
        if self.client and self._connected:
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
