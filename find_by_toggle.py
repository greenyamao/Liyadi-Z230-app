import asyncio
from bleak import BleakScanner, BleakClient

async def scan(duration=6.0):
    print(f"Сканирование эфира ({duration} сек)...")
    devices = await BleakScanner.discover(timeout=duration, return_adv=True)
    return devices

async def inspect_device(device):
    print(f"\n--- Подключение к {device.address} ({device.name or 'Без имени'}) ---")
    try:
        async with BleakClient(device, timeout=10.0) as client:
            print("Успешно подключено! Чтение сервисов и характеристик...")
            for service in client.services:
                print(f"\n[Сервис] {service.uuid} ({service.description})")
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    print(f"   [Характеристика] {char.uuid} | Свойства: [{props}] ({char.description})")
            return True
    except Exception as e:
        print(f"Ошибка при подключении: {e}")
        return False

async def main():
    print("=" * 60)
    print("  ПОИСК СВЕТИЛЬНИКА МЕТОДОМ ДИФФЕРЕНЦИАЛЬНОГО СКАНИРОВАНИЯ")
    print("=" * 60)
    print("\nШаг 1: Убедитесь, что светильник СЕЙЧАС ВКЛЮЧЕН.")
    input("Нажмите Enter, чтобы начать первое сканирование...")

    devices1 = await scan(6.0)
    print(f"Найдено устройств: {len(devices1)}")
    for d, adv in devices1.values():
        name = d.name or adv.local_name or "Без имени"
        print(f"  • {d.address} | {name} | RSSI: {adv.rssi}")

    print("\n" + "=" * 60)
    print("Шаг 2: Теперь ВЫКЛЮЧИТЕ светильник (кнопкой питания или из розетки).")
    input("После выключения нажмите Enter для второго сканирования...")

    devices2 = await scan(6.0)
    print(f"Найдено устройств: {len(devices2)}")

    addrs1 = set(devices1.keys())
    addrs2 = set(devices2.keys())
    disappeared_addrs = list(addrs1 - addrs2)

    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ:")
    if not disappeared_addrs:
        print("Ни одно устройство не пропало.")
        print("Возможно, светильник использует случайный MAC (BLE privacy) или выключается не сразу.")
        print("Попробуем сравнить изменения по RSSI (уровню сигнала)...")
        # Find devices whose signal was strong in scan 1
        strong = [d for d, adv in devices1.values() if adv.rssi > -60]
        if strong:
            print("\nУстройства с самым сильным сигналом в первом сканировании:")
            for d in strong:
                print(f"  • {d.address} ({d.name or 'Без имени'})")
        return

    print(f"Пропали следующие устройства (были включены, затем выключились):")
    candidates = []
    for addr in disappeared_addrs:
        d, adv = devices1[addr]
        name = d.name or adv.local_name or "Без имени"
        print(f"  --> {addr} | {name} | RSSI был: {adv.rssi}")
        candidates.append(d)

    target = candidates[0]
    print(f"\nГлавный кандидат: {target.address}")
    print("\nШаг 3: Включите светильник ОБРАТНО.")
    input("После включения нажмите Enter для подключения и проверки GATT...")

    # Re-scan quickly to find fresh handle
    print("Поиск светильника после включения...")
    fresh_devs = await scan(5.0)
    fresh_target = None
    for addr, (d, adv) in fresh_devs.items():
        if addr.lower() == target.address.lower():
            fresh_target = d
            break

    if not fresh_target:
        print(f"Светильник с адресом {target.address} пока не обнаружен. Попробуем подключиться напрямую...")
        fresh_target = target

    await inspect_device(fresh_target)

if __name__ == "__main__":
    asyncio.run(main())
