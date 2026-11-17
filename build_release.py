import os
import sys
import shutil
import zipfile
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT_DIR, "dist")
APP_OUTPUT_DIR = os.path.join(DIST_DIR, "Liadi")
ZIP_NAME = "Liadi-v1.0.0-Windows-Portable.zip"
ZIP_PATH = os.path.join(DIST_DIR, ZIP_NAME)
ISS_PATH = os.path.join(ROOT_DIR, "installer.iss")

def generate_icons():
    """Generates resources/icon.ico and resources/icon.png if missing"""
    icon_ico = os.path.join(ROOT_DIR, "resources", "icon.ico")
    icon_png = os.path.join(ROOT_DIR, "resources", "icon.png")
    if os.path.exists(icon_ico) and os.path.exists(icon_png):
        return

    os.makedirs(os.path.join(ROOT_DIR, "resources"), exist_ok=True)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QRadialGradient, QLinearGradient
    from PySide6.QtCore import Qt, QPointF

    app = QApplication.instance() or QApplication([])
    size = 256
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    # Outer glow
    rg = QRadialGradient(QPointF(128, 128), 120)
    rg.setColorAt(0.0, QColor(255, 180, 0, 240))
    rg.setColorAt(0.5, QColor(255, 120, 0, 180))
    rg.setColorAt(0.85, QColor(255, 80, 0, 80))
    rg.setColorAt(1.0, QColor(255, 50, 0, 0))
    painter.setBrush(QBrush(rg))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(8, 8, 240, 240)

    # Rim
    lg = QLinearGradient(0, 0, 256, 256)
    lg.setColorAt(0.0, QColor(50, 50, 55))
    lg.setColorAt(1.0, QColor(20, 20, 25))
    painter.setBrush(QBrush(lg))
    painter.setPen(QPen(QColor(255, 170, 0, 200), 4))
    painter.drawEllipse(36, 36, 184, 184)

    # COB Center
    cg = QRadialGradient(QPointF(128, 128), 70)
    cg.setColorAt(0.0, QColor(255, 255, 240, 255))
    cg.setColorAt(0.3, QColor(255, 220, 100, 255))
    cg.setColorAt(0.7, QColor(255, 150, 0, 255))
    cg.setColorAt(1.0, QColor(230, 90, 0, 255))
    painter.setBrush(QBrush(cg))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(56, 56, 144, 144)

    painter.setPen(QPen(QColor(255, 255, 255, 220), 5))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(88, 88, 80, 80)
    painter.end()

    pix.save(icon_png, "PNG")
    pix.save(icon_ico, "ICO")
    print("Icon generated in resources/")

def build_portable():
    print("=== Step 1: Building with PyInstaller ===")
    icon_path = os.path.join(ROOT_DIR, "resources", "icon.ico")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--name", "Liadi",
        "--icon", icon_path,
        "--add-data", f"{os.path.join(ROOT_DIR, 'resources')};resources",
        "--hidden-import", "qfluentwidgets",
        "--hidden-import", "bleak",
        "--clean",
        "--noconfirm",
        os.path.join(ROOT_DIR, "main.py")
    ]
    subprocess.check_call(cmd)

    print("=== Step 2: Creating Portable ZIP ===")
    portable_marker = os.path.join(APP_OUTPUT_DIR, "portable.txt")
    with open(portable_marker, "w") as f:
        f.write("Liadi Portable Mode")

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(APP_OUTPUT_DIR):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file, APP_OUTPUT_DIR)
                zipf.write(abs_file, rel_path)

    print(f"Portable ZIP created: {ZIP_PATH} ({os.path.getsize(ZIP_PATH) // (1024*1024)} MB)")

def build_installer():
    print("=== Step 3: Checking Inno Setup ===")
    iscc_candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        shutil.which("iscc")
    ]
    iscc_exe = next((p for p in iscc_candidates if p and os.path.exists(p)), None)

    if iscc_exe:
        print(f"Compiling installer using {iscc_exe}...")
        subprocess.check_call([iscc_exe, ISS_PATH])
        print("Installer created successfully in dist/Liadi-v1.0.0-UserSetup.exe")
    else:
        print("Inno Setup (ISCC.exe) not found on local machine.")
        print("Tip: Install via 'choco install innosetup' or 'winget install JRSoftware.InnoSetup'.")
        print("Note: GitHub Actions will automatically compile the installer on tag push!")

def main():
    generate_icons()
    build_portable()
    build_installer()
    print("\nAll tasks completed successfully!")

if __name__ == "__main__":
    main()
