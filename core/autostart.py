import os
import sys
import winreg

APP_NAME = "LiadiLightController"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_launch_command() -> str:
    """Returns the python/executable launch command with --minimized flag"""
    if getattr(sys, 'frozen', False):
        exe = sys.executable
        return f'"{exe}" --minimized'
    python_exe = sys.executable
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
    return f'"{exe}" "{script_path}" --minimized'

def is_autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"Error checking autostart: {e}")
        return False

def set_autostart(enable: bool) -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        try:
            if enable:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                print(f"Autostart enabled: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("Autostart removed")
                except FileNotFoundError:
                    pass
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"Error setting autostart: {e}")
        return False
