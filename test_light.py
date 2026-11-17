import asyncio
import sys
from bleak import BleakScanner, BleakClient

# UUIDs discovered from the official LEDLYD app
SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
TX_CHAR_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"  # Write commands here
RX_CHAR_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"  # Receive status feedback here

# Known name prefixes
NAME_PREFIXES = ("LYD", "LTF", "Bough")

class LightController:
    def __init__(self):
        self.client = None
        self.is_on = True
        self.brightness = 50   # 0 - 100%
        self.kelvin = 5600     # 2500 - 9900K

    def build_packet(self, power: bool, brightness: int, kelvin: int) -> bytearray:
        """
        10-byte packet structure:
        [mode, submode, brightness, kelvin//100, hue_lo, hue_hi, sat, fx_mode, speed, freq]
        """
        mode = 1 if power else 0
        submode = 1
        p_val = max(0, min(100, int(brightness)))
        k_val = max(25, min(99, int(kelvin // 100)))
        return bytearray([mode, submode, p_val, k_val, 0, 0, 0, 0, 100, 0])

    def notification_handler(self, sender, data: bytearray):
        """Called whenever the lamp sends status updates (e.g. if knob is turned)"""
        if len(data) >= 4:
            mode = data[0]
            brightness = data[2]
            kelvin = data[3] * 100
            self.is_on = (mode != 0)
            self.brightness = brightness
            self.kelvin = kelvin
            state_str = "ВКЛ" if self.is_on else "ВЫКЛ"
            print(f"\n[Обратная связь от светильника]: Состояние: {state_str}, Яркость: {brightness}%, Цветовая температура: {kelvin}K\n> ", end="", flush=True)

    async def scan_and_connect(self):
        print("Поиск светильника по Bluetooth...")
        devices = await BleakScanner.discover(timeout=7.0, return_adv=True)
        target_device = None

        for d, adv in devices.values():
            name = d.name or adv.local_name or ""
            uuids = [u.lower() for u in adv.service_uuids]
            
            # Match by name or service UUID
            if any(p.lower() in name.lower() for p in NAME_PREFIXES) or SERVICE_UUID in uuids:
                print(f"Найден светильник: {name} [{d.address}] (RSSI: {adv.rssi})")
                target_device = d
                break

        if not target_device:
            print("Светильник не найден автоматически по имени.")
            print("Список всех найденных BLE устройств:")
            idx_list = []
            for i, (d, adv) in enumerate(devices.values()):
                name = d.name or adv.local_name or "Без имени"
                print(f"  [{i}] {d.address} | {name} | RSSI: {adv.rssi}")
                idx_list.append(d)
            
            if not idx_list:
                print("Bluetooth устройств рядом вообще не обнаружено. Проверьте, включен ли свет и Bluetooth на ноутбуке.")
                return False
                
            choice = input("\nВведите номер устройства для подключения (или Enter для отмены): ").strip()
            if choice.isdigit() and int(choice) < len(idx_list):
                target_device = idx_list[int(choice)]
            else:
                return False

        print(f"Подключение к {target_device.address}...")
        self.client = BleakClient(target_device)
        await self.client.connect()
        print("Успешно подключено!")

        # Subscribe to notifications
        try:
            await self.client.start_notify(RX_CHAR_UUID, self.notification_handler)
            print("Подписка на обновления статуса активна.")
        except Exception as e:
            print(f"Предупреждение: не удалось подписаться на уведомления: {e}")

        return True

    async def send_state(self):
        if not self.client or not self.client.is_connected:
            print("Ошибка: светильник не подключен.")
            return
        packet = self.build_packet(self.is_on, self.brightness, self.kelvin)
        await self.client.write_gatt_char(TX_CHAR_UUID, packet, response=False)
        state_str = "ВКЛ" if self.is_on else "ВЫКЛ"
        print(f"Отправлено: {state_str} | Яркость: {self.brightness}% | Температура: {self.kelvin}K | Пакет: {packet.hex(' ')}")

    async def turn_on(self):
        self.is_on = True
        await self.send_state()

    async def turn_off(self):
        self.is_on = False
        await self.send_state()

    async def set_brightness(self, val: int):
        self.brightness = max(0, min(100, val))
        await self.send_state()

    async def set_kelvin(self, val: int):
        self.kelvin = max(2500, min(9900, val))
        await self.send_state()

async def async_input(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)

async def main():
    ctrl = LightController()
    connected = await ctrl.scan_and_connect()
    if not connected:
        return

    print("\n--- Управление светильником Liadi / Liyadi Z230 ---")
    print("Команды:")
    print("  on          - включить")
    print("  off         - выключить")
    print("  b <0-100>   - установить яркость (например: b 80)")
    print("  k <2500-9900> - установить температуру (например: k 4500)")
    print("  set <k> <b> - установить и температуру, и яркость (например: set 3200 40)")
    print("  q           - выйти\n")

    while True:
        try:
            cmd = (await async_input("> ")).strip()
            if not cmd:
                continue
            parts = cmd.split()
            op = parts[0].lower()

            if op == "q" or op == "quit" or op == "exit":
                break
            elif op == "on":
                await ctrl.turn_on()
            elif op == "off":
                await ctrl.turn_off()
            elif op == "b" and len(parts) > 1:
                await ctrl.set_brightness(int(parts[1]))
            elif op == "k" and len(parts) > 1:
                await ctrl.set_kelvin(int(parts[1]))
            elif op == "set" and len(parts) > 2:
                ctrl.kelvin = int(parts[1])
                ctrl.brightness = int(parts[2])
                await ctrl.send_state()
            else:
                print("Неизвестная команда. Доступны: on, off, b <число>, k <число>, set <k> <b>, q")
        except Exception as e:
            print("Ошибка выполнения команды:", e)

    if ctrl.client and ctrl.client.is_connected:
        await ctrl.client.disconnect()
        print("Отключено.")

if __name__ == "__main__":
    asyncio.run(main())
