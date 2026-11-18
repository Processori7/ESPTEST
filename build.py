# -*- coding: utf-8 -*-
"""Сборка единого exe: python build.py

Требуется Python 3.10+ с tkinter, pyinstaller, esptool, pyserial.
Результат: dist/ESP_TEST.exe
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from version import APP_NAME, __version__, VERSION_TUPLE  # noqa: E402

NAME = APP_NAME


def make_version_file(path: str) -> str:
    """Файл ресурса версии для Windows: «Свойства → Подробно» в проводнике."""
    v = VERSION_TUPLE
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={v},
    prodvers={v},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [StringStruct('CompanyName', 'Processori7'),
           StringStruct('FileDescription', 'ESP_TEST - ESP32 memory tester (Flash and RAM)'),
           StringStruct('FileVersion', '{'.'.join(str(x) for x in v)}'),
           StringStruct('InternalName', '{NAME}'),
           StringStruct('OriginalFilename', '{NAME}.exe'),
           StringStruct('ProductName', '{NAME}'),
           StringStruct('ProductVersion', '{__version__}')])
      ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def make_icon(path: str):
    """Рисуем иконку «чип» и сохраняем как .ico."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow не установлен — собираю без иконки.")
        return None

    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # корпус
    d.rounded_rectangle((46, 46, 210, 210), radius=34, fill=(17, 26, 35, 255),
                        outline=(45, 212, 191, 255), width=10)
    # ножки
    for i in range(4):
        off = 74 + i * 36
        d.rounded_rectangle((off, 18, off + 18, 48), radius=5, fill=(45, 212, 191, 255))
        d.rounded_rectangle((off, 208, off + 18, 238), radius=5, fill=(45, 212, 191, 255))
        d.rounded_rectangle((18, off, 48, off + 18), radius=5, fill=(45, 212, 191, 255))
        d.rounded_rectangle((208, off, 238, off + 18), radius=5, fill=(45, 212, 191, 255))
    # кристалл
    d.rounded_rectangle((88, 88, 168, 168), radius=14, fill=(45, 212, 191, 255))
    d.rounded_rectangle((104, 104, 152, 152), radius=8, fill=(10, 43, 40, 255))

    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                          (128, 128), (256, 256)])
    return path


def main():
    os.chdir(HERE)
    icon = make_icon(os.path.join(HERE, "icon.ico"))

    for folder in ("build", "dist"):
        shutil.rmtree(os.path.join(HERE, folder), ignore_errors=True)
    spec = os.path.join(HERE, f"{NAME}.spec")
    if os.path.exists(spec):
        os.remove(spec)

    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    ver_file = make_version_file(os.path.join(HERE, "build", "version_info.txt"))

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", NAME,
        "--version-file", ver_file,
        "--collect-all", "esptool",
        "--hidden-import", "serial.tools.list_ports",
        "--hidden-import", "serial.tools.list_ports_windows",
        "--hidden-import", "rich",
        "--hidden-import", "rich.console",
    ]
    if icon:
        cmd += ["--icon", icon]
    cmd.append("main.py")

    print("Сборка:", " ".join(cmd))
    subprocess.check_call(cmd)

    exe = os.path.join(HERE, "dist", f"{NAME}.exe")
    if os.path.exists(exe):
        mb = os.path.getsize(exe) / (1024 * 1024)
        print(f"\nГотово: {exe}  ({mb:.1f} МБ, версия {__version__})")
    else:
        print("Сборка не дала exe — смотрите вывод выше.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
