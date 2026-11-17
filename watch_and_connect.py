import asyncio
import sys
from bleak import BleakScanner, BleakClient

# GATT UUIDs for LEDLYD / Liyadi lamps
SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
TX_CHAR_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"  # Команды
RX_CHAR_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"  # Ответы

def build_cct_packet(power=True, brightness=50, kelvin=5600):
    """Пакет обычного света CCT (выводит из стробоскопа)"""
    mode = 1 if power else 0
    submode = 1
    p_val = max(0, min(100, int(brightness)))
    k_val = max(25, min(99, int(kelvin // 100)))
    return bytearray([mode, submode, p_val, k_val, 0, 0, 0, 0, 100, 0])

async def control_session(client):
    print("\n" + "=" * 60)
    print("УСПЕШНОЕ ПОДКЛЮЧЕНИЕ К СВЕТИЛЬНИКУ!")
    print("=" * 60)
    
    # Сразу шлем команду обычного CCT света (5600K, 30%), чтобы вырубить стробоскоп
    print("Сбрасываем стробоскоп в нормальный белый свет (5600K, 30%)...")
    pkt = build_cct_packet(power=True, brightness=30, kelvin=5600)
    await client.write_gatt_char(TX_CHAR_UUID, pkt, response=False)
    print("Готово! Светильник должен светить ровным нейтральным светом.")

    print("\nКоманды управления:")
    print("  on          - включить")
    print("  off         - выключить")
    print("  b <0-100>   - яркость (например: b 80)")
    print("  k <2500-9900> - температура в Кельвинах (например: k 3200 или k 5600)")
    print("  q           - выйти\n")

    current_b = 30
    current_k = 5600
    is_on = True

    loop = asyncio.get_running_loop()
    while True:
        cmd = (await loop.run_in_executor(None, input, "> ")).strip()
        if not cmd:
            continue
        parts = cmd.split()
        op = parts[0].lower()

        if op in ("q", "quit", "exit"):
            break
        elif op == "on":
            is_on = True
            await client.write_gatt_char(TX_CHAR_UUID, build_cct_packet(is_on, current_b, current_k), response=False)
            print("Включен")
        elif op == "off":
            is_on = False
            await client.write_gatt_char(TX_CHAR_UUID, build_cct_packet(is_on, current_b, current_k), response=False)
            print("Выключен")
        elif op == "b" and len(parts) > 1:
            current_b = int(parts[1])
            await client.write_gatt_char(TX_CHAR_UUID, build_cct_packet(is_on, current_b, current_k), response=False)
            print(f"Яркость: {current_b}%")
        elif op == "k" and len(parts) > 1:
            current_k = int(parts[1])
            await client.write_gatt_char(TX_CHAR_UUID, build_cct_packet(is_on, current_b, current_k), response=False)
            print(f"Температура: {current_k}K")

async def main():
    print("=" * 60)
    print("МОНИТОРИНГ ЭФИРА И АВТОМАТИЧЕСКИЙ ПЕРЕХВАТ СВЕТИЛЬНИКА")
    print("=" * 60)
    print("ВАЖНО: Выключите Bluetooth на вашем iPhone (в Настройках iOS)!")
    print("Пока айфон подключен к лампе, лампа 'занята' и не видна ноутбуку.")
    print("\nЖдем освобождения светильника...")

    found_device = None
    stop_event = asyncio.Event()

    def detection_callback(device, adv):
        nonlocal found_device
        # Фильтруем слишком слабые сигналы соседей
        if adv.rssi < -75:
            return
            
        name = device.name or adv.local_name or "Без имени"
        uuids = [str(u).lower() for u in adv.service_uuids]
        
        # Если это Samsung TV или аудиоустройства - пропускаем
        if "samsung" in name.lower() or "jbl" in name.lower():
            return
            
        print(f"  [Вижу сигнал]: {device.address} | RSSI: {adv.rssi} dBm | Имя: {name}")

        # Проверяем сервис или подозрительно близкое устройство (RSSI > -60)
        is_lamp = SERVICE_UUID in uuids or any(k in name for k in ["LYD", "LTF", "Bough"])
        # Либо это наш кандидат E9:D4:6F:64:C3:24 или устройство прямо вплотную
        if is_lamp or device.address.upper() == "E9:D4:6F:64:C3:24" or (adv.rssi > -55 and name == "Без имени"):
            print(f"\n>>> ОБНАРУЖЕН СВЕТИЛЬНИК: {device.address} (RSSI: {adv.rssi} dBm)! <<<")
            found_device = device
            stop_event.set()

    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=40.0)
    except asyncio.TimeoutError:
        print("\nВремя ожидания истекло. Светильник так и не появился в эфире.")
        await scanner.stop()
        return

    await scanner.stop()

    if found_device:
        print(f"Подключение к {found_device.address}...")
        try:
            async with BleakClient(found_device, timeout=12.0) as client:
                await control_session(client)
        except Exception as e:
            print(f"Ошибка при подключении/управлении: {e}")

if __name__ == "__main__":
    asyncio.run(main())
