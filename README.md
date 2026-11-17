# Liadi Z230 Light Controller
Modern Windows 11 Fluent UI desktop controller for **Liadi Z230 Bi-Color** (and compatible LYD / LTF / Bough) studio LED lights via Bluetooth Low Energy (BLE).
## Download & Installation

1. **Option A: Portable (Recommended)**
   - Download `Liadi-Windows-Portable.zip` from [Releases](https://github.com/greenyamao/Liyadi-Z230-app/releases).
   - Unpack anywhere and launch `Liadi.exe`.

2. **Option B: Windows Installer**
   - Download `Liadi-UserSetup.exe` from [Releases](https://github.com/greenyamao/Liyadi-Z230-app/releases).
   - Installs to `%LOCALAPPDATA%\Programs\LiadiLight` (no administrator rights needed) and creates Start Menu and Desktop shortcuts.
<img width="1233" height="750" alt="pythonw_YZlQbT083W" src="https://github.com/user-attachments/assets/02149ded-effa-48f1-92c2-27e2d804bebf" />
<img width="1239" height="825" alt="pythonw_ezKrAS13wG" src="https://github.com/user-attachments/assets/4fd1ee54-5557-461d-b259-5cc2366f2603" />
<img width="1239" height="825" alt="pythonw_1Ukmlbaz5h" src="https://github.com/user-attachments/assets/28f2c2cc-3791-40a1-a44b-8fb50cfda54d" />

## Highlights
- **Direct BLE CCT Control**: Brightness (0–100%, 0% = Standby), Color Temperature (2700K – 6500K).
- **2-Way Knob Sync**: Physical knob adjustments on the lamp reflect in the UI in real time.
- **Circadian Sun & Alarm Scheduler**: Automated step-by-step transitions simulating natural daylight or sunrise alarm.
- **FX & Custom Generator**: Bi-Color hardware effects (TV, Flash, Strobe, Candle) and software effects (Breathing, Lightning).
- **Windows Integration**: System tray minimization, autostart toggle, Fluent Design.
- **8 Languages**: English (default), Russian, Chinese, Japanese, German, French, Korean, Hindi.
- **Local SQLite Storage**: Saves all user parameters and schedules locally.

> [!NOTE]
> **Windows SmartScreen Warning:** Because this is a free open-source project without a paid commercial certificate, Windows may show a blue *“Windows protected your PC”* banner. Click **“More info”** → **“Run anyway”**.

---

## Hardware Setup
Set the switch on the back panel of the light to **`MoD: 1`** (Direct Bluetooth GATT mode).

---

## Development & Build from Source

```bash
pip install -r requirements.txt
python main.py
```

To compile Portable ZIP and Installer:
```bash
python build_release.py
```
