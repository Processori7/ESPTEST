# -*- coding: utf-8 -*-
"""Точка входа ESP_TEST."""

import os
import sys


class _Null:
    """Заглушка stdout/stderr для оконного режима (esptool любит печатать)."""

    encoding = "utf-8"

    def write(self, *_args, **_kwargs):
        return 0

    def flush(self):
        pass

    def isatty(self):
        return False


def _prepare():
    if sys.stdout is None:
        sys.stdout = _Null()
    if sys.stderr is None:
        sys.stderr = _Null()

    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        if base not in sys.path:
            sys.path.insert(0, base)

    if os.name == "nt":
        try:
            import ctypes

            from version import APP_NAME, __version__

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"Processori7.{APP_NAME}.{__version__}"
            )
        except Exception:
            pass


def _selftest() -> int:
    """Проверка сборки: импорты, встроенные данные esptool, отрисовка интерфейса."""
    out = []
    try:
        import glob

        from version import APP_NAME, __version__

        out.append(f"app={APP_NAME} {__version__}")
        out.append(f"python={sys.version.split()[0]} frozen={getattr(sys, 'frozen', False)}")

        import serial
        import tkinter

        import esptool
        from esptool.loader import StubFlasher

        out.append(f"esptool={esptool.__version__}")
        out.append(f"pyserial={serial.VERSION}")
        out.append(f"tk={tkinter.TkVersion}")
        stubs = glob.glob(os.path.join(StubFlasher.STUB_DIR, "*", "*.json"))
        out.append(f"stub_json={len(stubs)} dir={StubFlasher.STUB_DIR}")

        from gui import App

        app = App(demo=True)
        app.update()
        app._load_demo()
        for _ in range(5):
            app.update()
        out.append(f"chip={app.kv['chip.name'].cget('text')}")
        out.append(f"flash={app.flash_big.cget('text')}")
        out.append(f"ram={app.ram_big.cget('text')}")
        out.append(f"report_len={len(app.report_text.get('1.0', 'end'))}")
        app.destroy()

        # проверяем, что esptool не падает при печати в оконном режиме
        from probe import EspProbe, ProbeError, list_serial_ports

        ports = list_serial_ports()
        out.append(f"ports={len(ports)}: " + " | ".join(p["label"] for p in ports))

        esptool.log.print("selftest log line")
        probe = EspProbe()
        try:
            probe.connect("COM77", 115200)
            out.append("connect=unexpected-success")
        except ProbeError:
            out.append("connect=friendly-error")
        except Exception as exc:  # noqa: BLE001
            out.append(f"connect=raw {type(exc).__name__}: {exc}")
        finally:
            probe.close()

        out.append("RESULT=OK")
    except Exception:  # noqa: BLE001
        import traceback

        out.append("RESULT=FAIL")
        out.append(traceback.format_exc())

    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
    try:
        with open(os.path.join(base, "_selftest.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(out))
    except Exception:
        pass
    return 0


def main():
    _prepare()
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    demo = "--demo" in sys.argv
    try:
        from gui import run

        run(demo=demo)
    except Exception as exc:  # noqa: BLE001
        import traceback

        tb = traceback.format_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "ESP_TEST — ошибка запуска",
                f"{exc}\n\n{tb[-1500:]}",
            )
            root.destroy()
        except Exception:
            print(tb)


if __name__ == "__main__":
    main()
