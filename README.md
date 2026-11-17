# Liadi Z230 Light Controller

Modern Windows 11 Fluent UI desktop controller for **Liadi Z230 Bi-Color** (and compatible LYD / LTF / Bough) studio LED lights via Bluetooth Low Energy (BLE).

## Highlights
- **Direct BLE CCT Control**: Brightness (0–100%, 0% = Standby), Color Temperature (2700K – 6500K).
- **2-Way Knob Sync**: Physical knob adjustments on the lamp reflect in the UI in real time.
- **Circadian Sun & Alarm Scheduler**: Automated step-by-step transitions simulating natural daylight or sunrise alarm.
- **FX & Custom Generator**: Bi-Color hardware effects (TV, Flash, Strobe, Candle) and software effects (Breathing, Lightning).
- **Windows Integration**: System tray minimization, autostart toggle, Fluent Design.
- **8 Languages**: English (default), Russian, Chinese, Japanese, German, French, Korean, Hindi.
- **Local SQLite Storage**: Saves all user parameters and schedules locally.

## Hardware Setup
Set the switch on the back panel of the light to **`MoD: 1`** (Direct Bluetooth GATT mode).

## Quick Start
```bash
pip install -r requirements.txt
python main.py
```
*(Or run `run_app.bat` on Windows)*
