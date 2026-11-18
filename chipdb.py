# -*- coding: utf-8 -*-
"""Справочные данные: семейства чипов ESP, производители SPI-flash, коды объёма.

Все цифры взяты из официальных datasheet'ов Espressif (SRAM) и из спецификации
JEDEC (кодировка объёма flash в RDID).
"""

# ---------------------------------------------------------------------------
# Чипы. Ключи совпадают с esptool.CHIP_NAME.
# ---------------------------------------------------------------------------
CHIP_DB = {
    "ESP32": {
        "sram_kb": 520,
        "psram": "до 4 МБ внешней (опционально)",
        "core": "Xtensa LX6",
        "note": "Классический ESP32: 520 КБ SRAM, внешняя PSRAM только у некоторых модулей.",
    },
    "ESP32-S2": {
        "sram_kb": 320,
        "psram": "до 4 МБ внешней (опционально)",
        "core": "Xtensa LX7 (1 ядро)",
        "note": "ESP32-S2: 320 КБ SRAM, без Bluetooth.",
    },
    "ESP32-S3": {
        "sram_kb": 512,
        "psram": "до 8 МБ внешней (опционально)",
        "core": "Xtensa LX7 (2 ядра)",
        "note": "ESP32-S3: 512 КБ SRAM + кэш; PSRAM бывает 2/4/8 МБ.",
    },
    "ESP32-C3": {
        "sram_kb": 400,
        "psram": "нет интерфейса PSRAM",
        "core": "RISC-V (1 ядро)",
        "note": "ESP32-C3: 400 КБ SRAM. Внешняя PSRAM не поддерживается.",
    },
    "ESP32-C6": {
        "sram_kb": 512,
        "psram": "нет интерфейса PSRAM",
        "core": "RISC-V (HP 1 ядро + LP)",
        "note": "ESP32-C6: 512 КБ SRAM (HP) + LP-память.",
    },
    "ESP32-C2": {
        "sram_kb": 272,
        "psram": "нет интерфейса PSRAM",
        "core": "RISC-V (1 ядро)",
        "note": "ESP32-C2: 272 КБ SRAM.",
    },
    "ESP32-C5": {
        "sram_kb": 400,
        "psram": "до 8 МБ внешней (опционально)",
        "core": "RISC-V (1 ядро)",
        "note": "ESP32-C5: 400 КБ SRAM, dual-band Wi-Fi.",
    },
    "ESP32-H2": {
        "sram_kb": 320,
        "psram": "нет интерфейса PSRAM",
        "core": "RISC-V (1 ядро)",
        "note": "ESP32-H2: 320 КБ SRAM, только 802.15.4/BLE.",
    },
    "ESP32-P4": {
        "sram_kb": 768,
        "psram": "до 16 МБ внешней (опционально)",
        "core": "RISC-V (2 ядра, HP)",
        "note": "ESP32-P4: 768 КБ SRAM + LP-память.",
    },
    "ESP8266": {
        "sram_kb": 160,
        "psram": "до 16 МБ (редко, ESP8266 с PSRAM)",
        "core": "Xtensa L106",
        "note": "ESP8266: 160 КБ SRAM всего, ~80 КБ доступно приложению.",
    },
}

CHIP_DEFAULT = {
    "sram_kb": None,
    "psram": "неизвестно",
    "core": "—",
    "note": "Модель отсутствует в справочнике — объём SRAM неизвестен.",
}


def chip_entry(name: str) -> dict:
    """Вернуть запись справочника для имени чипа (с нормализацией)."""
    if not name:
        return dict(CHIP_DEFAULT)
    name = name.strip().upper().replace("_", "-")
    if name in CHIP_DB:
        return dict(CHIP_DB[name])
    # ESP32-S3 (QFN56) и т.п.
    for key in CHIP_DB:
        if name.startswith(key.upper()):
            return dict(CHIP_DB[key])
    return dict(CHIP_DEFAULT)


# ---------------------------------------------------------------------------
# Производители SPI NOR flash (байт 0 ответа RDID 0x9F)
# ---------------------------------------------------------------------------
FLASH_MANUFACTURERS = {
    0x01: "Spansion / Cypress",
    0x0B: "XTX Technology",
    0x0D: "Boya",
    0x1C: "EON Silicon",
    0x1F: "Adesto / Atmel",
    0x20: "Micron / ST",
    0x37: "AMIC",
    0x5E: "Zbit Semiconductor",
    0x62: "SANYO",
    0x68: "Boya / Microchip",
    0x6B: "SANYO",
    0x85: "Puya Semiconductor",
    0x86: "Puya Semiconductor",
    0x9D: "ISSI",
    0xA1: "Fudan Microelectronics",
    0xAB: "XMC",
    0xAD: "Hyundai",
    0xB0: "Qingxinyuan / XMC",
    0xBF: "SST / Microchip",
    0xC2: "Macronix",
    0xC8: "GigaDevice",
    0xCE: "Micron",
    0xE0: "Wuhan Xinxin",
    0xEF: "Winbond",
    0xF8: "Renesas",
}

# Код ёмкости (байт 2 ответа RDID) -> байт
FLASH_CAPACITY = {
    0x10: 64 << 10,
    0x11: 128 << 10,
    0x12: 256 << 10,
    0x13: 512 << 10,
    0x14: 1 << 20,
    0x15: 2 << 20,
    0x16: 4 << 20,
    0x17: 8 << 20,
    0x18: 16 << 20,
    0x19: 32 << 20,
    0x1A: 64 << 20,
    0x1B: 128 << 20,
    0x1C: 256 << 20,
}

# Код размера flash в заголовке образа (байт 3, старший ниббл)
IMAGE_FLASH_SIZE = {
    0x0: 1 << 20,
    0x1: 2 << 20,
    0x2: 4 << 20,
    0x3: 8 << 20,
    0x4: 16 << 20,
    0x5: 32 << 20,
    0x6: 64 << 20,
    0x7: 128 << 20,
}

IMAGE_MAGIC = 0xE9

# Типы разделов (для читаемого отчёта)
PART_TYPES = {
    0x00: "app",
    0x01: "data",
}


def human_size(n, unit_suffix="Б") -> str:
    """1 048 576 -> '1.00 МБ'."""
    if n is None:
        return "—"
    n = float(n)
    for unit in ("", "К", "М", "Г"):
        if abs(n) < 1024.0 or unit == "Г":
            if unit == "":
                return f"{int(n)} {unit_suffix}"
            return f"{n:.2f} {unit}{unit_suffix}"
        n /= 1024.0
    return f"{n:.2f} Г{unit_suffix}"


def human_size_short(n) -> str:
    """1 048 576 -> '1 МБ' (без лишних нулей)."""
    if n is None:
        return "—"
    for unit, div in (("ГБ", 1 << 30), ("МБ", 1 << 20), ("КБ", 1 << 10)):
        if n >= div and n % div == 0:
            return f"{int(n // div)} {unit}"
    return human_size(n)


# ---------------------------------------------------------------------------
# Подлинность: пул MAC-адресов Espressif (OUI)
# ---------------------------------------------------------------------------
ESPRESSIF_OUIS = {
    "08:3A:F2", "14:63:93", "18:FE:34", "1C:9D:C2", "20:91:48", "24:0A:C4",
    "24:6F:28", "2C:3A:E8", "30:AE:A4", "34:94:54", "3C:61:05", "3C:71:BF",
    "40:F5:20", "44:17:93", "48:27:E2", "48:3F:DA", "4C:11:AE", "4C:75:25",
    "50:02:91", "54:5A:A6", "58:BF:25", "5C:CF:7F", "60:01:94", "68:C6:3A",
    "70:03:9F", "74:4D:BD", "78:21:84", "7C:9E:BD", "7C:DF:A1", "80:64:6F",
    "80:7D:3A", "84:0D:8E", "84:CC:A8", "84:F3:EB", "88:13:BF", "8C:4F:00",
    "8C:AA:B5", "8C:CE:4E", "90:38:0C", "94:B9:7E", "98:F4:AB", "9C:9C:1F",
    "A0:20:A6", "A4:7B:9D", "A4:CF:12", "A8:03:2A", "A8:48:FA", "AC:67:B2",
    "B4:E6:2D", "B8:F0:09", "BC:DD:C2", "C4:4F:33", "C4:5B:BE", "C8:C9:A3",
    "CC:50:E3", "D4:8A:FC", "D8:A0:1D", "D8:F1:5B", "DC:4F:22", "E0:98:06",
    "E8:68:E7", "E8:DB:84", "EC:62:60", "EC:FA:BC", "F0:08:D1", "F4:CF:A2",
    "F8:1B:0C", "FC:F5:C4",
}

# USB-VID производителей мостов USB-UART, которые ставят на платы ESP
USB_UART_VENDORS = {
    0x303A: "Espressif USB (native)",
    0x10C4: "Silicon Labs CP210x",
    0x1A86: "WCH CH340/CH9102",
    0x0403: "FTDI FT232",
    0x067B: "Prolific PL2303",
    0x1A8A: "Espressif (CDC)",
}


def check_mac(mac: str) -> dict:
    """Сверка MAC с известным пулом Espressif (справочная информация)."""
    if not mac or mac.count(":") != 5:
        return {"known": None, "text": "—", "level": "muted"}
    oui = mac[:8].upper()
    if oui in ESPRESSIF_OUIS:
        return {"known": True, "oui": oui, "level": "ok",
                "text": f"Espressif · OUI {oui}"}
    return {"known": False, "oui": oui, "level": "muted",
            "text": f"OUI {oui} не в списке Espressif"}


def describe_features(features) -> dict:
    """Разбор списка возможностей из ROM/eFuse в понятные флаги."""
    items = [str(x) for x in (features or [])]
    low = [x.lower() for x in items]

    def find(*keys):
        for item, l in zip(items, low):
            if any(k in l for k in keys):
                return item
        return None

    def find_bt():
        for item, l in zip(items, low):
            if l == "bt" or l.startswith("bt ") or "bluetooth" in l or l.startswith("bt5"):
                return item
        return None

    caps = {
        "wifi": find("wi-fi", "wifi"),
        "bt": find_bt(),
        "ieee154": find("802.15.4"),
        "flash": find("embedded flash"),
        "psram": find("embedded psram"),
        "cores": find("single core", "dual core", "quad core"),
        "freq": find("mhz"),
    }
    return caps
