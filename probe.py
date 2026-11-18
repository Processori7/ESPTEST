# -*- coding: utf-8 -*-
"""Аппаратный слой: связь с ESP через ROM-загрузчик (esptool) и тесты памяти.

Ничего внешнего не требуется: esptool вшит внутрь программы, Arduino IDE,
PlatformIO и ESP-IDF на машине не нужны.
"""

from __future__ import annotations

import os
import struct
import tempfile
import threading
import time

import esptool
from esptool.loader import StubFlasher
from esptool.util import FatalError

import chipdb


class Cancelled(Exception):
    """Пользователь прервал операцию."""


class ProbeError(Exception):
    """Понятная человеку ошибка связи с устройством."""


def _pretty_error(exc: BaseException) -> str:
    text = str(exc)
    low = text.lower()
    if "failed to connect" in low or "no serial data" in low or "wrong boot mode" in low:
        return (
            "Не удалось связаться с чипом.\n"
            "• проверьте USB-кабель (нужен data-кабель, не «только зарядка»);\n"
            "• установлен ли драйвер USB-UART (CP210x / CH340 / FTDI);\n"
            "• зажмите кнопку BOOT и, не отпуская, нажмите EN/RST, затем отпустите BOOT;\n"
            "• убедитесь, что выбран правильный COM-порт."
        )
    if "access is denied" in low or "permission" in low or "could not open port" in low:
        return (
            "Порт занят или недоступен. Закройте монитор порта / Arduino IDE / PlatformIO, "
            "другой терминал и повторите."
        )
    if "timed out" in low or "timeout" in low:
        return (
            "Чип не ответил вовремя. Попробуйте снизить скорость (115200) и повторить, "
            "либо перевести плату в режим загрузки вручную."
        )
    return text


def list_serial_ports() -> list:
    """Все COM-порты системы с описанием. USB-порты идут первыми.

    Возвращает список словарей: device, label, desc, vid, pid, priority.
    """
    ports = []
    seen = set()

    def add(device, desc="", vid=None, pid=None, hwid=""):
        if not device or device in seen:
            return
        seen.add(device)
        ports.append({"device": device, "desc": desc, "vid": vid, "pid": pid, "hwid": hwid})

    try:
        from serial.tools import list_ports

        for p in list_ports.comports():
            add(p.device, (p.description or "").strip(), p.vid, p.pid, p.hwid or "")
    except Exception:
        pass

    # резервный путь для Windows: реестр SERIALCOMM
    if not ports and os.name == "nt":
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM")
            idx = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, idx)
                except OSError:
                    break
                add(str(value), name)
                idx += 1
            winreg.CloseKey(key)
        except Exception:
            pass

    for p in ports:
        desc = p["desc"]
        # "Устройство с последовательным интерфейсом USB (COM8)" -> без хвоста
        for tail in (f" ({p['device']})", f"({p['device']})"):
            if desc.endswith(tail):
                desc = desc[: -len(tail)].strip()
        if not desc or desc.upper() == p["device"]:
            desc = p["hwid"] or "последовательный порт"

        vendor = chipdb.USB_UART_VENDORS.get(p["vid"]) if p["vid"] else None
        if vendor:
            short = vendor
            desc = f"{vendor} · {p['vid']:04X}:{p['pid']:04X}" if p["pid"] else vendor
            prio = 0 if p["vid"] == 0x303A else 1
        elif p["vid"]:
            short = desc
            desc = f"{desc} · {p['vid']:04X}:{p['pid']:04X}" if p["pid"] else desc
            prio = 2
        else:
            short = desc
            prio = 3
        if "ACPI" in p["hwid"].upper() or "PNP0501" in p["hwid"].upper():
            prio = 4
        p["desc"] = desc
        p["short"] = short if len(short) <= 30 else short[:29] + "…"
        p["priority"] = prio
        p["label"] = f"{p['device']} — {p['short']}"

    ports.sort(key=lambda p: (p["priority"], p["device"]))
    return ports


def _device_present(instance_id: str) -> bool:
    """Присутствует ли устройство в системе прямо сейчас (Windows, cfgmgr32)."""
    try:
        import ctypes
        from ctypes import wintypes

        cm = ctypes.WinDLL("cfgmgr32")
        cm.CM_Locate_DevNodeW.argtypes = [ctypes.POINTER(wintypes.DWORD),
                                          wintypes.LPCWSTR, wintypes.ULONG]
        cm.CM_Locate_DevNodeW.restype = wintypes.ULONG
        devinst = wintypes.DWORD()
        return cm.CM_Locate_DevNodeW(ctypes.byref(devinst), instance_id, 0) == 0
    except Exception:
        return True  # не смогли проверить — считаем, что есть


def usb_esp_devices() -> list:
    """USB-устройства Espressif и мостов USB-UART, реально воткнутые в компьютер.

    Нужно, чтобы отличить «плата не подключена / плохой кабель» от «плата есть,
    но COM-порт не создан (нет драйвера)».
    """
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []

    vids = set(chipdb.USB_UART_VENDORS)
    found = []
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USB")
    except OSError:
        return []

    idx = 0
    while True:
        try:
            name = winreg.EnumKey(root, idx)
        except OSError:
            break
        idx += 1
        upper = name.upper()
        if not upper.startswith("VID_") or "PID_" not in upper:
            continue
        try:
            vid = int(upper[4:8], 16)
            pid = int(upper[upper.index("PID_") + 4 : upper.index("PID_") + 8], 16)
        except ValueError:
            continue
        if vid not in vids:
            continue
        try:
            dev_key = winreg.OpenKey(root, name)
        except OSError:
            continue
        j = 0
        while True:
            try:
                inst = winreg.EnumKey(dev_key, j)
            except OSError:
                break
            j += 1
            full_id = f"USB\\{name}\\{inst}"
            if not _device_present(full_id):
                continue
            service = ""
            try:
                with winreg.OpenKey(dev_key, inst) as inst_key:
                    service = winreg.QueryValueEx(inst_key, "Service")[0]
            except OSError:
                pass
            found.append({"vid": vid, "pid": pid, "instance": full_id, "service": service})
    return found


def _pattern(offset: int, size: int) -> bytes:
    """Детерминированный псевдослучайный шаблон, зависит от адреса."""
    buf = bytearray(size)
    x = (offset * 2654435761 + 0x9E3779B9) & 0xFFFFFFFF
    step = 4
    for i in range(0, size - size % step, step):
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        buf[i : i + 4] = struct.pack("<I", x)
    tail = size - size % step
    for i in range(tail, size):
        buf[i] = 0xA5
    return bytes(buf)


class EspProbe:
    """Одна сессия связи с платой."""

    CHUNK = 0x10000  # 64 КБ — блок чтения/записи
    SECTOR = 0x1000

    def __init__(self, log=None, progress=None, cancel=None):
        self._log_cb = log or (lambda *a, **k: None)
        self._progress_cb = progress or (lambda *a, **k: None)
        self._cancel_cb = cancel or (lambda: False)

        self.esp = None
        self.port = None
        self.baud = 115200
        self.has_stub = False
        self.stub_bss = None
        self.caps = {}
        self._closed = True

    # ------------------------------------------------------------------
    # служебное
    # ------------------------------------------------------------------
    def log(self, msg, level="info"):
        self._log_cb(msg, level)

    def progress(self, frac, text=""):
        self._progress_cb(max(0.0, min(1.0, frac)), text)

    def check_cancel(self):
        if self._cancel_cb():
            raise Cancelled()

    @property
    def connected(self) -> bool:
        return self.esp is not None and not self._closed

    def close(self):
        esp = self.esp
        self.esp = None
        self._closed = True
        if esp is None:
            return
        port = getattr(esp, "_port", None) or getattr(esp, "port", None)
        if port is not None:
            try:
                port.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # подключение
    # ------------------------------------------------------------------
    def connect(self, port=None, baud=921600):
        self.close()
        self._closed = False
        self.port = port
        self.progress(0.02, "Поиск загрузчика…")

        if port:
            candidates = [port]
        else:
            found = list_serial_ports()
            candidates = [p["device"] for p in found]
            if not candidates:
                usb = usb_esp_devices()
                if usb:
                    dev = usb[0]
                    hint = (f"USB-устройство {dev['vid']:04X}:{dev['pid']:04X} воткнуто, но COM-порт "
                            f"не создан — не установлен драйвер USB-UART "
                            f"(служба: {dev.get('service') or 'не назначена'}).")
                else:
                    hint = ("USB-устройств Espressif / USB-UART в системе нет вообще — "
                            "проверьте кабель (нужен data-кабель) и USB-порт.")
                raise ProbeError("В системе не найдено ни одного COM-порта.\n" + hint)
            self.log("Автопоиск платы: " + ", ".join(candidates), "info")

        esp = None
        last_err = None
        for dev in candidates:
            self.check_cancel()
            self.log(f"Порт {dev}: пробую подключиться…")
            try:
                esp = esptool.connect_esp(
                    port=dev,
                    chip="auto",
                    initial_baud=115200,
                    connect_attempts=2,
                )
                break
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                self.log(f"Порт {dev}: нет ответа", "warn")

        if esp is None:
            self._closed = True
            raise ProbeError(_pretty_error(last_err) if last_err else "Плата не отвечает.")

        self.esp = esp
        real_port = getattr(getattr(esp, "_port", None), "port", None)
        if real_port:
            self.port = real_port
        self.log(f"Чип определён: {getattr(esp, 'CHIP_NAME', '?')} на {self.port}", "ok")

        # --- stub-загрузчик: быстрее и умеет больше ---
        self.progress(0.05, "Запуск stub-загрузчика…")
        try:
            stub = StubFlasher(esp)
            self.stub_bss = getattr(stub, "bss_start", None)
            self.esp = esp.run_stub(stub)
            self.has_stub = True
            self.log("Stub-загрузчик запущен (полноскоростной режим)", "ok")
        except Exception as exc:
            self.has_stub = False
            self.log(f"Stub не запустился ({exc}); работаю через ROM", "warn")

        if baud and baud > 115200:
            try:
                self.esp.change_baud(baud)
                self.baud = baud
                self.log(f"Скорость обмена: {baud} бод", "ok")
            except Exception as exc:
                self.log(f"Не удалось поднять скорость ({exc}); остаюсь на 115200", "warn")
        self.progress(0.08, "Связь установлена")

    # ------------------------------------------------------------------
    # информация о чипе
    # ------------------------------------------------------------------
    def read_chip(self) -> dict:
        esp = self.esp
        info = {"name": getattr(esp, "CHIP_NAME", "?")}

        for key, fn in (
            ("desc", "get_chip_description"),
            ("revision", "get_chip_revision"),
            ("features", "get_chip_features"),
            ("crystal", "get_crystal_freq"),
        ):
            try:
                info[key] = getattr(esp, fn)()
            except Exception:
                info[key] = None

        features = info.get("features")
        if isinstance(features, (list, tuple)):
            info["features_list"] = [str(x) for x in features]
        elif isinstance(features, str):
            info["features_list"] = [s.strip() for s in features.split(",") if s.strip()]
        else:
            info["features_list"] = []
        info["features"] = ", ".join(info["features_list"]) or "—"

        try:
            mac = esp.read_mac("BASE_MAC")
            info["mac"] = ":".join(f"{b:02X}" for b in mac) if mac else "—"
        except Exception:
            info["mac"] = "—"

        # --- подлинность по MAC ---
        info["mac_check"] = chipdb.check_mac(info["mac"])
        info["usb_vid"] = None
        try:
            for port in list_serial_ports():
                if port["device"] == self.port:
                    info["usb_vid"] = port["vid"]
                    break
        except Exception:  # noqa: BLE001
            pass

        # --- возможности чипа (из eFuse/ROM) ---
        info["caps"] = chipdb.describe_features(info["features_list"])
        self.caps = info["caps"]
        info["image_chip_id"] = getattr(esp, "IMAGE_CHIP_ID", None)

        # --- состояние безопасности ---
        info["security"] = self._read_security(esp)

        info["stub"] = self.has_stub
        info["baud"] = self.baud
        info["port"] = self.port or "—"
        info["table"] = chipdb.chip_entry(info["name"])
        return info

    def _read_security(self, esp) -> dict | None:
        """Secure Boot, шифрование flash, JTAG, chip id."""
        if not hasattr(esp, "get_security_info"):
            return None
        try:
            si = esp.get_security_info()
        except Exception as exc:  # noqa: BLE001
            self.log(f"Данные о безопасности недоступны: {exc}", "warn")
            return None
        flags = si.get("parsed_flags") or {}
        try:
            encrypted = (bin(si.get("flash_crypt_cnt", 0)).count("1") % 2) != 0
        except Exception:
            encrypted = None
        jtag = "выключен (навсегда)"
        if not flags.get("HARD_DIS_JTAG"):
            jtag = "ограничен ПО" if flags.get("SOFT_DIS_JTAG") else "доступен"
        return {
            "secure_boot": bool(flags.get("SECURE_BOOT_EN")),
            "flash_enc": encrypted,
            "jtag": jtag,
            "usb_disabled": bool(flags.get("DIS_USB")),
            "chip_id": si.get("chip_id"),
            "flags": si.get("flags"),
        }

    # ------------------------------------------------------------------
    # flash: паспорт + анализ содержимого
    # ------------------------------------------------------------------
    def read_flash_info(self) -> dict:
        esp = self.esp
        res = {}

        # --- JEDEC ID ---
        fid = None
        try:
            fid = esp.flash_id()
        except Exception as exc:
            self.log(f"Не удалось прочитать JEDEC ID: {exc}", "warn")

        if fid:
            # esptool возвращает RDID как 24-битное число в порядке cap|dev|mfg
            mfg = fid & 0xFF
            dev_type = (fid >> 8) & 0xFF
            cap_code = (fid >> 16) & 0xFF
            res["jedec_id"] = f"{mfg:02X}{dev_type:02X}{cap_code:02X}"
            res["mfg_id"] = mfg
            mfg_name = chipdb.FLASH_MANUFACTURERS.get(mfg)
            if not mfg_name:
                if (self.caps or {}).get("flash"):
                    mfg_name = f"встроена в корпус чипа (ID 0x{mfg:02X})"
                else:
                    mfg_name = f"неизвестный (0x{mfg:02X})"
            res["mfg"] = mfg_name
            res["dev_type"] = dev_type
            res["cap_code"] = cap_code
            size_id = chipdb.FLASH_CAPACITY.get(cap_code)
            if not size_id:
                try:
                    from esptool.cmds import DETECTED_FLASH_SIZES

                    named = DETECTED_FLASH_SIZES.get(cap_code)
                    if named:
                        size_id = esptool.flash_size_bytes(named)
                except Exception:
                    pass
            res["size_jedec"] = size_id
        else:
            res.update(jedec_id=None, mfg="—", size_jedec=None, cap_code=None, dev_type=None)

        # --- объём, который видит сам загрузчик (SFDP / таблица esptool) ---
        size_detect = None
        try:
            detected = esptool.detect_flash_size(esp)
            if isinstance(detected, str):
                size_detect = esptool.flash_size_bytes(detected)
            elif isinstance(detected, int):
                size_detect = detected
        except Exception as exc:
            self.log(f"Автоопределение объёма flash не удалось: {exc}", "warn")
        res["size_detected"] = size_detect

        # --- заявленный объём из заголовка прошивки ---
        size_declared = None
        hdr = None
        for addr in (0x0, 0x1000):
            try:
                block = esp.read_flash(addr, 0x20)
            except Exception:
                continue
            if block and block[0] == chipdb.IMAGE_MAGIC:
                hdr = block
                res["hdr_addr"] = addr
                break
        if hdr:
            code = hdr[3] >> 4
            size_declared = chipdb.IMAGE_FLASH_SIZE.get(code)
            res["hdr_flash_code"] = code
            res["hdr_flash_freq"] = hdr[3] & 0x0F
            res["hdr_chip_id"] = struct.unpack("<H", hdr[12:14])[0]
        res["size_declared"] = size_declared

        # --- таблица разделов ---
        parts = []
        pt_addr = None
        for addr in (0x8000, 0x9000, 0x10000):
            try:
                data = esp.read_flash(addr, 0xC00)
            except Exception:
                continue
            parsed = self._parse_partition_table(data)
            if parsed:
                parts = parsed
                pt_addr = addr
                break
        res["partitions"] = parts
        res["pt_addr"] = pt_addr
        if parts:
            res["part_end"] = max(p["offset"] + p["size"] for p in parts)
            res["part_total"] = sum(p["size"] for p in parts)
        else:
            res["part_end"] = None
            res["part_total"] = None

        # --- что за прошивка залита в плату ---
        res["app"] = self._read_app_desc(esp, parts)

        # --- итоговый «реальный» объём ---
        real = res.get("size_jedec") or res.get("size_detected")
        res["size_real"] = real
        res["verdict"] = self._flash_verdict(res)

        # --- скорость чтения (небольшой замер) ---
        try:
            t0 = time.time()
            esp.read_flash(0x0, min(0x10000, real or 0x10000))
            dt = max(time.time() - t0, 1e-6)
            res["read_speed"] = int(min(0x10000, real or 0x10000) / dt)
        except Exception:
            res["read_speed"] = None

        return res

    def _read_app_desc(self, esp, parts):
        """Заголовок приложения: имя проекта, версия, ESP-IDF, дата сборки."""
        app = next((p for p in parts if p["type"] == "app"), None)
        if not app:
            return None
        try:
            data = esp.read_flash(app["offset"], 0xC0)
        except Exception:
            return None
        if len(data) < 0xB0 or data[0] != chipdb.IMAGE_MAGIC:
            return {"offset": app["offset"], "valid": False}

        magic = struct.unpack("<I", data[0x20:0x24])[0]
        chip_id = struct.unpack("<H", data[12:14])[0]
        if magic != 0xABCD5432:
            return {"offset": app["offset"], "valid": False, "chip_id": chip_id}

        def txt(off, length):
            return data[off : off + length].split(b"\x00")[0].decode("utf-8", "replace").strip()

        return {
            "offset": app["offset"],
            "valid": True,
            "chip_id": chip_id,
            "project": txt(0x50, 32) or "—",
            "version": txt(0x30, 32) or "—",
            "built": f"{txt(0x80, 16)} {txt(0x70, 16)}".strip() or "—",
            "idf": txt(0x90, 32) or "—",
        }

    @staticmethod
    def _parse_partition_table(data: bytes):
        parts = []
        for i in range(0, len(data) - 32, 32):
            entry = data[i : i + 32]
            if entry[:2] != b"\xaa\x50":
                break
            ptype, subtype = entry[2], entry[3]
            offset, size = struct.unpack("<II", entry[4:12])
            label = entry[12:28].split(b"\x00")[0].decode("utf-8", "replace")
            if size == 0 or offset > 0x10000000:
                break
            parts.append(
                {
                    "label": label or "—",
                    "type": chipdb.PART_TYPES.get(ptype, f"0x{ptype:02X}"),
                    "subtype": f"0x{subtype:02X}",
                    "offset": offset,
                    "size": size,
                }
            )
            if len(parts) >= 48:
                break
        return parts

    @staticmethod
    def _flash_verdict(res: dict) -> dict:
        real = res.get("size_real")
        declared = res.get("size_declared")
        if not real:
            return {
                "level": "warn",
                "title": "Объём не определён",
                "text": "Загрузчик не вернул идентификатор flash-чипа.",
            }
        if not declared:
            return {
                "level": "warn",
                "title": "Объём по ID чипа",
                "text": (
                    f"Чип flash отвечает {chipdb.human_size_short(real)}. "
                    "Заголовок прошивки не найден (плата не прошита или образ повреждён) — "
                    "сверить заявленный объём не с чем."
                ),
            }
        if declared > real * 1.05:
            return {
                "level": "err",
                "title": "Заявлено больше, чем есть",
                "text": (
                    f"В заголовке прошивки указано {chipdb.human_size_short(declared)}, "
                    f"а чип отвечает {chipdb.human_size_short(real)}. "
                    "Прошивка может не влезть / модуль размечен неверно."
                ),
            }
        if declared and declared < real * 0.95:
            return {
                "level": "warn",
                "title": "Заявлено меньше, чем есть",
                "text": (
                    f"Чип реально {chipdb.human_size_short(real)}, а прошивка собрана "
                    f"под {chipdb.human_size_short(declared)}. Часть памяти простаивает."
                ),
            }
        return {
            "level": "ok",
            "title": "Объём подтверждён",
            "text": (
                f"Идентификатор чипа и заголовок прошивки совпадают: "
                f"{chipdb.human_size_short(real)}."
            ),
        }

    # ------------------------------------------------------------------
    # низкоуровневая запись во flash
    # ------------------------------------------------------------------
    def _write_raw(self, addr: int, data: bytes):
        size = (len(data) + self.SECTOR - 1) // self.SECTOR * self.SECTOR
        if size != len(data):
            data = data + b"\xff" * (size - len(data))
        self.esp.flash_begin(size, addr, logging=False)
        seq = 0
        for off in range(0, size, self.SECTOR):
            self.esp.flash_block(data[off : off + self.SECTOR], seq)
            seq += 1
        self.esp.flash_finish(reboot=False)

    # ------------------------------------------------------------------
    # глубокий тест flash (разрушающий, с резервной копией)
    # ------------------------------------------------------------------
    def deep_test(self, capacity: int, backup_dir: str = None) -> dict:
        esp = self.esp
        cap = int(capacity)
        cap = min(cap, 32 << 20)
        cap = cap // self.SECTOR * self.SECTOR

        res = {
            "capacity": cap,
            "backup": None,
            "bad": [],
            "verified": 0,
            "restore_ok": None,
            "guess": cap,
            "read_speed": None,
            "write_speed": None,
            "ok": False,
        }

        # ---- 1. резервная копия -------------------------------------
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe_port = (self.port or "esp").replace(":", "").replace("\\", "").replace("/", "")
        path = os.path.join(
            backup_dir or tempfile.gettempdir(),
            f"esp_flash_backup_{safe_port}_{stamp}.bin",
        )
        self.log(f"Резервная копия flash → {path}")
        buf = bytearray()
        t0 = time.time()
        for off in range(0, cap, self.CHUNK):
            n = min(self.CHUNK, cap - off)
            buf += esp.read_flash(off, n)
            self.check_cancel()
            self.progress(0.02 + 0.23 * (off + n) / cap, f"Резервная копия 0x{off:06X}")
        dt = max(time.time() - t0, 1e-6)
        res["read_speed"] = int(cap / dt)
        with open(path, "wb") as fh:
            fh.write(buf)
        res["backup"] = path
        self.log(f"Копия сохранена ({chipdb.human_size(len(buf))})", "ok")

        # ---- 2. запись шаблона + проверка ---------------------------
        t0 = time.time()
        cancelled = False
        write_error = None
        try:
            for off in range(0, cap, self.CHUNK):
                n = min(self.CHUNK, cap - off)
                pat = _pattern(off, n)
                self._write_raw(off, pat)
                back = esp.read_flash(off, n)
                if back == pat:
                    res["verified"] += n
                else:
                    res["bad"].append(off)
                    self.log(f"Ошибка проверки на 0x{off:06X}", "err")
                self.check_cancel()
                self.progress(0.25 + 0.55 * (off + n) / cap, f"Запись/проверка 0x{off:06X}")
        except Cancelled:
            cancelled = True
            self.log("Прерывание: возвращаю прошивку на место…", "warn")
        except Exception as exc:  # noqa: BLE001
            write_error = exc
            self.log(f"Сбой при записи ({exc}); восстанавливаю прошивку…", "err")
        dt = max(time.time() - t0, 1e-6)
        res["write_speed"] = int(cap / dt)

        # ---- 3. восстановление (всегда, даже после сбоя) ------------
        self.progress(0.80, "Восстановление прошивки…")
        try:
            for off in range(0, cap, self.CHUNK):
                self._write_raw(off, bytes(buf[off : off + self.CHUNK]))
                self.progress(0.80 + 0.15 * (off + self.CHUNK) / cap, f"Восстановление 0x{off:06X}")
            check = min(cap, 1 << 20)
            back = esp.read_flash(0, check)
            res["restore_ok"] = back == bytes(buf[:check])
            self.progress(0.99, "Проверка восстановления…")
        except Exception as exc:  # noqa: BLE001
            res["restore_ok"] = False
            self.log(f"Восстановление не удалось: {exc}", "err")

        # ---- 4. выводы ---------------------------------------------
        if res["bad"]:
            first = min(res["bad"])
            guess = 1
            while guess * 2 <= first:
                guess *= 2
            res["guess"] = guess
        res["ok"] = not res["bad"]
        res["cancelled"] = cancelled
        res["error"] = str(write_error) if write_error is not None else None
        self.progress(1.0, "Готово")
        return res

    # ------------------------------------------------------------------
    # полное стирание flash
    # ------------------------------------------------------------------
    def erase_flash(self, force: bool = False) -> dict:
        """Стереть всю микросхему: загрузчик, таблицу разделов, NVS, ФС.

        Данные не восстанавливаются — это осознанно разрушающая операция.
        """
        esp = self.esp
        res = {
            "ok": False,
            "blank": None,
            "capacity": None,
            "secure_boot": None,
            "encrypted": None,
            "seconds": 0.0,
            "chip": getattr(esp, "CHIP_NAME", None),
            "error": None,
        }

        # --- объём и защита: снимаем ДО стирания ---
        try:
            cap = esptool.detect_flash_size(esp)
            if cap:
                # в esptool 5.x это строка вида '4MB', а не число байт
                res["capacity"] = int(esptool.flash_size_bytes(cap)) if isinstance(cap, str) else int(cap)
        except Exception:  # noqa: BLE001
            res["capacity"] = None
        try:
            res["secure_boot"] = bool(esp.get_secure_boot_enabled())
        except Exception:  # noqa: BLE001
            pass
        try:
            res["encrypted"] = bool(esp.get_flash_encryption_enabled())
        except Exception:  # noqa: BLE001
            pass

        if res["secure_boot"] or res["encrypted"]:
            self.log("На плате включён Secure Boot / шифрование flash: стирание заблокировано "
                     "защитой чипа. Такую плату нельзя очистить без force-режима.", "err")
            raise ProbeError(
                "Стирание запрещено: на чипе активен Secure Boot или шифрование flash.\n"
                "Это аппаратная защита — загрузчик не даёт стереть микросхему."
            )

        self.log(f"Стираю всю flash ({chipdb.human_size(res['capacity'])}), "
                 f"это может занять до минуты…", "warn")
        self.progress(0.05, "Стирание flash…")

        # esptool.erase_flash — одна блокирующая команда, реального прогресса нет:
        # двигаем полоску фоновым тикером, чтобы интерфейс не «замирал».
        stop = threading.Event()

        def ticker():
            frac = 0.05
            while not stop.wait(0.35):
                frac = min(0.9, frac + 0.012)
                self.progress(frac, "Стирание flash…")

        beat = threading.Thread(target=ticker, daemon=True)
        beat.start()
        t0 = time.time()
        try:
            esptool.erase_flash(esp, force=force)
        except FatalError as exc:
            stop.set()
            res["error"] = str(exc)
            self.log(f"Стирание отклонено загрузчиком: {exc}", "err")
            raise ProbeError("Загрузчик отказался стирать flash: " + str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            stop.set()
            res["error"] = str(exc)
            raise
        finally:
            stop.set()
            res["seconds"] = time.time() - t0

        # --- проверка: стёртая NOR-flash читается как 0xFF ---
        self.progress(0.94, "Проверяю результат…")
        try:
            n = min(res["capacity"] or self.CHUNK, self.CHUNK)
            head = esp.read_flash(0, n)
            res["blank"] = head == b"\xff" * n
        except Exception as exc:  # noqa: BLE001
            res["blank"] = None
            self.log(f"Не удалось прочитать flash после стирания: {exc}", "warn")

        res["ok"] = True
        self.progress(1.0, "Flash стёрта")
        if res["blank"] is False:
            self.log("После стирания в начале flash остались данные — проверьте плату.", "warn")
        return res

    # ------------------------------------------------------------------
    # запись произвольного .bin
    # ------------------------------------------------------------------
    WRITE_CHUNK = 0x4000  # стандартный блок записи esptool

    def write_bin(self, path: str, offset: int = 0, verify: bool = True) -> dict:
        """Записать любой .bin во flash по указанному адресу."""
        esp = self.esp
        with open(path, "rb") as fh:
            data = fh.read()
        if not data:
            raise ProbeError("Файл пустой — записывать нечего.")

        off = int(offset)
        res = {
            "path": path,
            "name": os.path.basename(path),
            "offset": off,
            "size": 0,
            "ok": False,
            "verified": None,
            "mismatch": [],
            "seconds": 0.0,
            "speed": None,
            "cancelled": False,
        }

        # начало записи должно быть выровнено на сектор: дополняем 0xFF сверху
        if off % self.SECTOR:
            pad = self.SECTOR - off % self.SECTOR
            off -= pad
            data = b"\xff" * pad + data
            self.log(f"Адрес не кратен сектору: начинаю с 0x{off:06X} "
                     f"({pad} байт 0xFF в начале).", "warn")
            res["offset"] = off

        size = (len(data) + self.SECTOR - 1) // self.SECTOR * self.SECTOR
        if size != len(data):
            data += b"\xff" * (size - len(data))
        res["size"] = size

        # не вылезаем за пределы микросхемы
        cap = None
        try:
            cap = esptool.detect_flash_size(esp)
            if isinstance(cap, str):
                cap = esptool.flash_size_bytes(cap)
        except Exception:  # noqa: BLE001
            cap = None
        if cap and off + size > cap:
            raise ProbeError(
                f"Файл не помещается во flash: 0x{off + size:06X} при объёме "
                f"{chipdb.human_size(cap)}. Уменьшите адрес или файл."
            )

        self.log(f"Запись {chipdb.human_size(size)} по адресу 0x{off:06X}…", "info")
        t0 = time.time()
        started = False
        try:
            esp.flash_begin(size, off, logging=False)
            started = True
            seq = 0
            for pos in range(0, size, self.WRITE_CHUNK):
                esp.flash_block(data[pos:pos + self.WRITE_CHUNK], seq)
                seq += 1
                self.check_cancel()
                self.progress(0.02 + 0.73 * (pos + self.WRITE_CHUNK) / size,
                              f"Запись 0x{off + pos:06X}")
        except Cancelled:
            res["cancelled"] = True
            self.log("Запись прервана — файл записан частично, плату нужно прошить заново.", "err")
        finally:
            if started:
                try:
                    esp.flash_finish(reboot=False)
                except Exception:  # noqa: BLE001
                    pass
        res["seconds"] = time.time() - t0
        res["speed"] = int(size / max(res["seconds"], 1e-6))
        if res["cancelled"]:
            return res

        # ---- проверка чтением ----
        if verify:
            self.progress(0.76, "Проверка записанного…")
            bad = []
            for pos in range(0, size, self.CHUNK):
                n = min(self.CHUNK, size - pos)
                back = esp.read_flash(off + pos, n)
                if back != data[pos:pos + n]:
                    bad.append(off + pos)
                self.check_cancel()
                self.progress(0.76 + 0.24 * (pos + n) / size, f"Проверка 0x{off + pos:06X}")
            res["verified"] = not bad
            res["mismatch"] = bad[:20]
            if bad:
                self.log(f"Расхождение при проверке: 0x{bad[0]:06X} "
                         f"(всего блоков с ошибкой: {len(bad)})", "err")
        res["ok"] = True
        self.progress(1.0, "Готово")
        return res

    # ------------------------------------------------------------------
    # тест SRAM: шина данных + шина адреса
    # ------------------------------------------------------------------
    def ram_test(self) -> dict:
        esp = self.esp
        res = {
            "available": False,
            "base": None,
            "bss": self.stub_bss,
            "data_ok": None,
            "addr_ok": None,
            "cells": 0,
            "errors": [],
            "note": "",
        }
        bss = self.stub_bss
        if not bss:
            res["note"] = (
                "Stub-загрузчик не запущен, безопасный участок SRAM неизвестен — "
                "тест записи/чтения пропущен."
            )
            return res

        base = (bss - 0x2000) & ~0x3F
        res["base"] = base
        res["available"] = True

        # --- шина данных: шаблоны + «шагающая единица» ---
        patterns = [0x00000000, 0xFFFFFFFF, 0x55555555, 0xAAAAAAAA]
        patterns += [1 << i for i in range(32)]
        patterns += [0xFFFFFFFF ^ (1 << i) for i in range(32)]
        data_ok = True
        original = None
        try:
            original = esp.read_reg(base)
        except Exception:
            pass
        for pat in patterns:
            self.check_cancel()
            try:
                esp.write_reg(base, pat)
                got = esp.read_reg(base)
            except Exception as exc:
                data_ok = False
                res["errors"].append(f"обрыв связи на шаблоне 0x{pat:08X}: {exc}")
                break
            if got != pat:
                data_ok = False
                res["errors"].append(f"0x{base:08X}: записано 0x{pat:08X}, прочитано 0x{got:08X}")
        res["data_ok"] = data_ok
        res["cells"] += 1
        if original is not None:
            try:
                esp.write_reg(base, original)
            except Exception:
                pass

        # --- шина адреса: 8 независимых ячеек ---
        addr_ok = True
        cells = [base + i * 4 for i in range(8)]
        values = [0xC0DE0000 + i for i in range(8)]
        try:
            for addr, val in zip(cells, values):
                esp.write_reg(addr, val)
            for addr, val in zip(cells, values):
                got = esp.read_reg(addr)
                if got != val:
                    addr_ok = False
                    res["errors"].append(
                        f"адрес 0x{addr:08X}: ожидалось 0x{val:08X}, получено 0x{got:08X}"
                    )
            for addr in cells:
                esp.write_reg(addr, 0)
        except Exception as exc:
            addr_ok = False
            res["errors"].append(f"обрыв связи при тесте адресов: {exc}")
        res["addr_ok"] = addr_ok
        res["cells"] += len(cells)
        return res

    # ------------------------------------------------------------------
    # прочее
    # ------------------------------------------------------------------
    def reset(self):
        try:
            esptool.reset_chip(self.esp)
        except Exception:
            pass
