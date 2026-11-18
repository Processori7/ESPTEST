# -*- coding: utf-8 -*-
"""Локализация интерфейса.

Русский — исходный язык, английский подключается словарём. Перевод применяется
на границе отображения: `tr()` для отдельных строк (в том числе с подстановками
вида «Портов: {}») и `tr_tree()` для готового дерева виджетов.
"""

from __future__ import annotations

import json
import os
import re

LANG = "ru"

# ---------------------------------------------------------------------------
# точные строки: русская -> английская
# ---------------------------------------------------------------------------
_UI = {
    # --- вкладки и шапка ---
    "Чип": "Chip",
    "Flash": "Flash",
    "ОЗУ": "RAM",
    "Отчёт": "Report",
    "Журнал": "Log",
    "ПОРТ · АВТО": "PORT · AUTO",
    "ПОРТ · ВРУЧНУЮ": "PORT · MANUAL",
    "не подключено": "not connected",
    "подключено": "connected",
    "плата отключена": "board disconnected",
    "связь потеряна": "link lost",
    "Подключиться": "Connect",
    "Отключиться": "Disconnect",
    "демо-режим": "demo mode",

    # --- карточки ---
    "ПРОВЕРКА": "CHECK",
    "СОЕДИНЕНИЕ": "CONNECTION",
    "ПРОШИТЬ .BIN": "FLASH .BIN",
    "СТЕРЕТЬ ПРОШИВКУ": "ERASE FIRMWARE",
    "ГЛУБОКИЙ ТЕСТ FLASH": "DEEP FLASH TEST",
    "ОПРЕДЕЛЁННОЕ УСТРОЙСТВО": "DETECTED DEVICE",
    "ВОЗМОЖНОСТИ ЧИПА": "CHIP CAPABILITIES",
    "БЕЗОПАСНОСТЬ И ПОДЛИННОСТЬ": "SECURITY AND AUTHENTICITY",
    "ПРОШИВКА НА ПЛАТЕ": "FIRMWARE ON THE BOARD",
    "СПРАВКА ПО ПАМЯТИ": "MEMORY REFERENCE",
    "РЕАЛЬНЫЙ ОБЪЁМ FLASH": "REAL FLASH SIZE",
    "ИДЕНТИФИКАЦИЯ ЧИПА FLASH": "FLASH CHIP IDENTIFICATION",
    "ЧТО ЗАЯВЛЕНО В ПРОШИВКЕ": "WHAT THE FIRMWARE CLAIMS",
    "ТАБЛИЦА РАЗДЕЛОВ": "PARTITION TABLE",
    "РЕЗУЛЬТАТ ГЛУБОКОГО ТЕСТА": "DEEP TEST RESULT",
    "ТЕСТ ЗАПИСИ/ЧТЕНИЯ SRAM": "SRAM READ/WRITE TEST",
    "ВСТРОЕННАЯ SRAM": "INTERNAL SRAM",
    "ВНЕШНЯЯ PSRAM": "EXTERNAL PSRAM",

    # --- кнопки и чекбоксы ---
    "▶  Полная проверка": "▶  Full check",
    "Только Flash": "Flash only",
    "Только ОЗУ": "RAM only",
    "■  Прервать": "■  Abort",
    "Сбросить плату (RST)": "Reset board (RST)",
    "Запустить глубокий тест": "Run deep test",
    "Стереть flash полностью": "Erase flash completely",
    "Сохранить отчёт в файл": "Save report to file",
    "Выбрать файл…": "Choose file…",
    "Прошить файл": "Flash file",
    "Искать плату на всех портах": "Search the board on all ports",
    "Подключаться автоматически": "Connect automatically",
    "Сохранять резервную копию": "Keep a backup copy",
    "Проверять": "Verify",
    "Перезагрузить": "Reboot",
    "Отмена": "Cancel",
    "Стереть навсегда": "Erase permanently",
    "Стирать и тестировать": "Erase and test",

    # --- подписи полей ---
    "Скорость": "Speed",
    "Порт": "Port",
    "Адрес": "Address",
    "Порты — нажмите, чтобы выбрать:": "Ports — click to select:",
    "файл не выбран": "no file selected",
    "Отчёт обновляется после каждой проверки": "The report is refreshed after every check",
    "esptool внутри · ничего доустанавливать не нужно":
        "esptool inside · nothing to install",

    # --- данные чипа ---
    "Модель": "Model",
    "Маркировка": "Marking",
    "Ревизия": "Revision",
    "Ядро": "Core",
    "Кварц": "Crystal",
    "Загрузчик": "Loader",
    "Особенности": "Features",
    "ROM + stub (полный доступ)": "ROM + stub (full access)",
    "ROM (ограниченный доступ)": "ROM (limited access)",
    "Wi-Fi": "Wi-Fi",
    "Bluetooth": "Bluetooth",
    "IEEE 802.15.4": "IEEE 802.15.4",
    "Встроенная flash": "Internal flash",
    "Встроенная PSRAM": "Internal PSRAM",
    "Процессор": "Processor",
    "MAC / производитель": "MAC / vendor",
    "Secure Boot": "Secure Boot",
    "Шифрование flash": "Flash encryption",
    "JTAG": "JTAG",
    "Chip ID (eFuse)": "Chip ID (eFuse)",
    "USB в загрузчике": "USB in loader",
    "Проект": "Project",
    "Версия": "Version",
    "Собрана": "Built",
    "Chip ID образа": "Image chip ID",
    "Chip ID в образе": "Chip ID in image",
    "Встроенная SRAM": "Internal SRAM",
    "Внешняя PSRAM": "External PSRAM",

    # --- flash ---
    "JEDEC ID": "JEDEC ID",
    "Производитель": "Manufacturer",
    "Объём по ID": "Size by ID",
    "Автоопределение": "Autodetect",
    "Заявленный объём": "Declared size",
    "Заголовок образа": "Image header",
    "Код ёмкости": "Density code",
    "Таблица разделов": "Partition table",
    "Суммарно разделов": "Partitions total",
    "Конец последнего": "End of last",
    "Скорость чтения": "Read speed",
    "Раздел": "Partition",
    "Тип": "Type",
    "Смещение": "Offset",
    "Размер": "Size",
    "Область теста": "Test region",
    "Проверено ячеек": "Cells tested",
    "Шина данных": "Data bus",
    "Шина адреса": "Address bus",

    # --- значения ---
    "выключен": "off",
    "выключено": "off",
    "ВКЛЮЧЁН": "ON",
    "ВКЛЮЧЕНО": "ON",
    "доступен": "available",
    "недоступен": "disabled",
    "нет": "no",
    "нет данных": "no data",
    "не выполнялся": "not run",
    "не проверено": "not checked",
    "неизвестно": "unknown",
    "не найдена": "not found",
    "не найден": "not found",
    "не определён": "unknown",
    "нет интерфейса PSRAM": "no PSRAM interface",
    "нет в корпусе (внешняя микросхема)": "not in the package (external chip)",
    "нет в корпусе": "not in the package",
    "SRAM работает": "SRAM works",
    "ошибки чтения/записи": "read/write errors",
    "ОШИБКА": "ERROR",
    "Объём подтверждён": "Capacity confirmed",
    "Объём не определён": "Capacity unknown",
    "Объём по ID чипа": "Size by chip ID",
    "Заявлено больше, чем есть": "Claims more than it has",
    "Заявлено меньше, чем есть": "Claims less than it has",
    "объём задан моделью чипа; ниже — проверка целостности ячеек":
        "capacity comes from the chip model; below is a cell integrity test",
    "не удалось": "failed",
    "есть": "present",
    "ВКЛ": "ON",

    # --- длинные пояснения ---
    "Стирает flash, пишет шаблон, сверяет чтением и восстанавливает прошивку из копии.":
        "Erases the flash, writes a pattern, verifies it by reading back and restores "
        "the firmware from the copy.",
    "Полностью очищает микросхему: загрузчик, таблицу разделов, NVS и файловую систему. "
    "Плата перестанет запускать прошивку — восстановить данные будет нельзя.":
        "Wipes the whole chip: bootloader, partition table, NVS and file system. "
        "The board will stop booting — the data cannot be recovered.",
    "Wi-Fi / Bluetooth / 802.15.4 — наличие радио в кристалле (по данным eFuse и ROM). "
    "Живую проверку (скан сетей, сопряжение) даёт только прошивка платы: загрузчик радио не включает.":
        "Wi-Fi / Bluetooth / 802.15.4 — the radio present in the silicon (from eFuse and ROM). "
        "A live test (scanning, pairing) can only be done by the board's firmware: "
        "the loader never powers the radio.",
    "В этом чипе внешняя PSRAM не поддерживается аппаратно — проверять нечего.":
        "This chip has no hardware support for external PSRAM — nothing to test.",
    "PSRAM нельзя измерить через ROM-загрузчик: она не инициализирована до запуска "
    "прошивки. Точный объём PSRAM показывает сама прошивка (esp_psram_get_size) или "
    "команда esptool flash_id по встроенному в модуль чипу.":
        "PSRAM cannot be measured through the ROM loader: it is not initialised before the "
        "firmware runs. The exact PSRAM size is reported by the firmware itself "
        "(esp_psram_get_size) or by esptool flash_id on the chip built into the module.",
    "Встроенная SRAM": "Internal SRAM",

    # --- диалоги ---
    "Ошибка": "Error",
    "Нужно подключение": "Connection required",
    "Сначала подключитесь к плате.": "Connect to the board first.",
    "Нет данных": "No data",
    "Сначала выполните проверку Flash — нужен объём чипа.":
        "Run the Flash check first — the chip size is required.",
    "Файл не выбран": "No file selected",
    "Нажмите «Выбрать файл…» и укажите .bin для прошивки.":
        "Click “Choose file…” and pick a .bin to flash.",
    "Неверный адрес": "Invalid address",
    "Адрес задаётся как 0x0, 0x10000 или 0.": "Use an address like 0x0, 0x10000 or 0.",
    "Адрес должен быть неотрицательным и кратным 4.":
        "The address must be non-negative and a multiple of 4.",
    "Подтверждение": "Confirmation",
    "Подтверждение стирания": "Erase confirmation",
    "⚠  ВНИМАНИЕ: ОПЕРАЦИЯ РАЗРУШАЮЩАЯ": "⚠  WARNING: DESTRUCTIVE OPERATION",
    "⚠  ПОЛНОЕ СТИРАНИЕ FLASH": "⚠  FULL FLASH ERASE",
    "Для подтверждения введите слово СТЕРЕТЬ:": "Type ERASE to confirm:",
    "Для подтверждения введите слово ERASE:": "Type ERASE to confirm:",
    "Сохранить отчёт": "Save report",
    "Текстовый файл": "Text file",
    "Все файлы": "All files",
    "Образ прошивки": "Firmware image",
    "Выберите файл прошивки": "Choose a firmware file",
    "Не удалось сохранить: {}": "Could not save: {}",
    "Отчёт сохранён: {}": "Report saved: {}",
}

# ---------------------------------------------------------------------------
# шаблоны: {} — подстановка (в том числе из f-строк)
# ---------------------------------------------------------------------------
_TPL = [
    # --- порты ---
    ("Портов: {} ({})", "Ports: {} ({})"),
    ("Портов: {}", "Ports: {}"),
    ("Найден порт: {}", "Port found: {}"),
    ("Порт пропал: {}", "Port lost: {}"),
    ("Не удалось получить список портов: {}", "Could not list serial ports: {}"),
    ("авто: перебор {} порт(ов), плата ищется сама",
     "auto: scanning {} port(s), the board is found automatically"),
    ("выбран {} · {}", "selected {} · {}"),
    ("{} — сейчас не подключён, жду его", "{} — not connected now, waiting for it"),
    ("порт не выбран — нажмите строку в списке", "no port selected — click a row in the list"),
    ("COM-портов нет — проверьте кабель и драйвер", "no COM ports — check the cable and driver"),
    ("Выбран порт {}: автопоиск выключен, работаю только с ним.",
     "Port {} selected: autodetect is off, working with this port only."),
    ("Переключаюсь с {} на {}…", "Switching from {} to {}…"),
    ("Плата на {} — подключаюсь автоматически…", "Board on {} — connecting automatically…"),
    ("Плата на {} отключена. Жду подключения…", "Board on {} disconnected. Waiting…"),
    ("На {} подключена другая плата — переподключаюсь…",
     "A different board appeared on {} — reconnecting…"),
    ("USB-устройство {}:{} воткнуто, но COM-порт не создан — похоже, нет драйвера "
     "USB-UART (служба: {}). Поставьте драйвер CP210x / CH340 и нажмите ⟳.",
     "USB device {}:{} is present but no COM port was created — the USB-UART driver "
     "seems missing (service: {}). Install the CP210x / CH340 driver and press ⟳."),
    ("USB-устройств Espressif / USB-UART в системе нет: проверьте кабель "
     "(нужен data-кабель, не «только зарядка»), другой USB-порт и питание платы.",
     "No Espressif / USB-UART device in the system: check the cable (a data cable, not "
     "a charge-only one), another USB port and the board's power."),

    # --- журнал: общее ---
    ("Готов к работе. Плата ищется автоматически: подключите её по USB.",
     "Ready. The board is detected automatically: plug it in over USB."),
    ("Автопоиск включён: плата ищется на всех портах.",
     "Autodetect enabled: the board is searched on all ports."),
    ("Ручной режим: выберите порт в списке ниже.", "Manual mode: pick a port in the list below."),
    ("Подключение к плате…", "Connecting to the board…"),
    ("Читаю паспорт flash…", "Reading the flash identity…"),
    ("Тестирую SRAM…", "Testing SRAM…"),
    ("Проверка завершена", "Check complete"),
    ("Готово", "Done"),
    ("Flash: {}", "Flash: {}"),
    ("SRAM: {}", "SRAM: {}"),
    ("Отключено. Автоподключение возобновится при появлении новой платы.",
     "Disconnected. Auto-connect resumes when a new board appears."),
    ("Запрошено прерывание…", "Abort requested…"),
    ("Операция прервана.", "Operation aborted."),
    ("Плата перезагружена.", "Board rebooted."),
    ("Сброс не удался: {}", "Reset failed: {}"),
    ("Связь с платой потеряна (плата заменена или перезагружена).",
     "Lost the link to the board (replaced or rebooted)."),
    ("Плата перезагружена, сессия закрыта.", "Board rebooted, session closed."),
    ("Неизвестен объём flash — сначала выполните проверку Flash.",
     "Flash size is unknown — run the Flash check first."),
    ("Тест прерван сбоем: {}", "Test stopped by an error: {}"),
    ("Тест прерван, прошивка восстановлена.", "Test aborted, firmware restored."),

    # --- журнал: стирание ---
    ("Полное стирание flash — не отключайте плату…", "Full flash erase — do not unplug the board…"),
    ("Проверка чтением: начало flash чистое (0xFF).",
     "Read-back check: the beginning of flash is clean (0xFF)."),
    ("Внимание: после стирания в начале flash остались данные.",
     "Warning: data remains at the beginning of flash after erasing."),
    ("Flash стёрта за {} с ({}).", "Flash erased in {} s ({})."),
    ("Плата перезагружена. Прошивки на ней больше нет — прошейте её заново.",
     "Board rebooted. There is no firmware on it now — flash it again."),

    # --- журнал: прошивка .bin ---
    ("Выбран файл: {} ({})", "File selected: {} ({})"),
    ("Записано {} по адресу 0x{} за {} с ({} КБ/с).",
     "Wrote {} at 0x{} in {} s ({} KB/s)."),
    ("Проверка чтением: данные совпадают.", "Read-back check: data matches."),
    ("Проверка чтением: есть расхождения!", "Read-back check: mismatches found!"),
    ("Прошивка прервана — файл записан частично.", "Flashing aborted — the file is partially written."),
    ("Не удалось перечитать flash: {}", "Could not re-read the flash: {}"),
    ("Плата перезагружена — запущена новая прошивка.",
     "Board rebooted — the new firmware is running."),
    ("Запись завершена, плата не перезагружалась — нажмите «Сбросить плату (RST)» для запуска.",
     "Write complete, the board was not rebooted — press “Reset board (RST)” to start it."),

    # --- значения с единицами ---
    ("{} бод", "{} baud"),
    ("{} МГц", "{} MHz"),
    ("{} КБ/с", "{} KB/s"),
    ("{} (валидный)", "{} (valid)"),
    ("{} — совпадает", "{} — match"),
    ("{} — не совпадает", "{} — mismatch"),
    ("реально: {}   ·   заявлено прошивкой: {}", "real: {}   ·   declared by firmware: {}"),
    ("Идентификатор чипа и заголовок прошивки совпадают: {}.",
     "Chip ID and firmware header match: {}."),
    ("Идентификатор чипа и заголовок прошивки совпадают: ", "Chip ID and firmware header match: "),
    ("есть · {}", "present · {}"),
    ("{} (по документации)", "{} (per datasheet)"),
    ("Разделов: {}", "Partitions: {}"),
    ("Ошибок: {}", "Errors: {}"),
    ("Ячеек: {}", "Cells: {}"),

    # --- отчёт ---
    ("  ESP_TEST — ОТЧЁТ О ПРОВЕРКЕ ПАМЯТИ",
     "  ESP_TEST — MEMORY CHECK REPORT"),
    ("Дата: {}", "Date: {}"),
    ("ЧИП", "CHIP"),
    ("  Модель\t{}", "  Model\t{}"),
    ("  Маркировка\t{}", "  Marking\t{}"),
    ("  Ревизия\t{}", "  Revision\t{}"),
    ("  Ядро\t{}", "  Core\t{}"),
    ("  Кварц\t{}", "  Crystal\t{}"),
    ("  MAC\t{}", "  MAC\t{}"),
    ("  Порт / скорость\t{}", "  Port / speed\t{}"),
    ("ВОЗМОЖНОСТИ ЧИПА", "CHIP CAPABILITIES"),
    ("  Wi-Fi\t{}", "  Wi-Fi\t{}"),
    ("  Bluetooth\t{}", "  Bluetooth\t{}"),
    ("  IEEE 802.15.4\t{}", "  IEEE 802.15.4\t{}"),
    ("  Встроенная flash\t{}", "  Internal flash\t{}"),
    ("  Встроенная PSRAM\t{}", "  Internal PSRAM\t{}"),
    ("  Процессор\t{}", "  Processor\t{}"),
    ("БЕЗОПАСНОСТЬ И ПОДЛИННОСТЬ", "SECURITY AND AUTHENTICITY"),
    ("  MAC / OUI\t{}", "  MAC / OUI\t{}"),
    ("  Secure Boot\t{}", "  Secure Boot\t{}"),
    ("  Шифрование flash\t{}", "  Flash encryption\t{}"),
    ("  JTAG\t{}", "  JTAG\t{}"),
    ("  Chip ID (eFuse)\t{}", "  Chip ID (eFuse)\t{}"),
    ("FLASH", "FLASH"),
    ("  JEDEC ID\t{}", "  JEDEC ID\t{}"),
    ("  Производитель\t{}", "  Manufacturer\t{}"),
    ("  Объём по ID\t{}", "  Size by ID\t{}"),
    ("  Автоопределение\t{}", "  Autodetect\t{}"),
    ("  РЕАЛЬНЫЙ ОБЪЁМ\t{}", "  REAL SIZE\t{}"),
    ("  Заявлено в образе\t{}", "  Declared in image\t{}"),
    ("  Таблица разделов\t{}", "  Partition table\t{}"),
    ("  Занято разделами\t{}", "  Used by partitions\t{}"),
    ("  Скорость чтения\t{}", "  Read speed\t{}"),
    ("  Вердикт\t{}", "  Verdict\t{}"),
    ("ПРОШИВКА НА ПЛАТЕ", "FIRMWARE ON THE BOARD"),
    ("  Проект\t{}", "  Project\t{}"),
    ("  Версия\t{}", "  Version\t{}"),
    ("  ESP-IDF\t{}", "  ESP-IDF\t{}"),
    ("  Собрана\t{}", "  Built\t{}"),
    ("  Chip ID образа\t{}", "  Image chip ID\t{}"),
    ("  Разделы:", "  Partitions:"),
    ("    Имя\tТип\tСмещение\tРазмер", "    Name\tType\tOffset\tSize"),
    ("ГЛУБОКИЙ ТЕСТ FLASH", "DEEP FLASH TEST"),
    ("  Объём теста\t{}", "  Tested size\t{}"),
    ("  Ошибок\t{}", "  Errors\t{}"),
    ("  Без ошибок\t{}", "  Without errors\t{}"),
    ("  Восстановлено\t{}", "  Restored\t{}"),
    ("  Резервная копия\t{}", "  Backup\t{}"),
    ("СТИРАНИЕ FLASH (ПОЛНОЕ)", "FLASH ERASE (FULL)"),
    ("  Выполнено\t{}", "  Performed\t{}"),
    ("  Объём микросхемы\t{}", "  Chip size\t{}"),
    ("  Время\t{}", "  Time\t{}"),
    ("  Проверка 0xFF\t{}", "  0xFF check\t{}"),
    ("  Прошивка удалена — плату нужно прошить заново",
     "  Firmware erased — the board must be flashed again"),
    ("ПРОШИВКА ФАЙЛА", "FILE FLASHING"),
    ("  Файл\t{}", "  File\t{}"),
    ("  Адрес\t{}", "  Address\t{}"),
    ("  Размер\t{}", "  Size\t{}"),
    ("  Проверка чтением\t{}", "  Read-back check\t{}"),
    ("ОЗУ", "RAM"),
    ("  Встроенная SRAM\t{}", "  Internal SRAM\t{}"),
    ("  Тест данных\t{}", "  Data test\t{}"),
    ("  Тест адресов\t{}", "  Address test\t{}"),
    ("  Ячеек проверено\t{}", "  Cells tested\t{}"),
    ("  Внешняя PSRAM\t{}", "  External PSRAM\t{}"),
    ("  Ошибки:", "  Errors:"),
]

# ---------------------------------------------------------------------------
# дополнения: строки, которых нет в основном словаре
# ---------------------------------------------------------------------------
_UI.update({
    "Отчёт появится после проверки.": "The report will appear after a check.",
    "реальный объём Flash и RAM у ESP32": "real Flash and RAM size of an ESP32",
    "объём определяется моделью чипа": "the size comes from the chip model",
    "тест недоступен": "test unavailable",
    "не проверено": "not checked",
    "заголовок приложения не найден": "application header not found",
    "таблица разделов не найдена (плата не прошита?)":
        "partition table not found (board not flashed?)",
    "flash стёрта — таблицы разделов больше нет":
        "flash erased — the partition table is gone",
    "стёрта": "erased",
    "flash пуста": "flash is empty",
    "микросхема очищена полностью — прошивки на плате нет":
        "the chip is fully wiped — there is no firmware on the board",
    "Все данные удалены (загрузчик, разделы, NVS). Чтобы плата снова работала, "
    "прошейте её: esptool write_flash, Arduino IDE или ESP-IDF.":
        "All data is gone (bootloader, partitions, NVS). To make the board work again, "
        "flash it with esptool write_flash, Arduino IDE or ESP-IDF.",
    "Прошивка восстановлена и проверена.": "The firmware was restored and verified.",
    "⚠ Восстановление не подтверждено — прошейте плату заново.":
        "⚠ Restore not confirmed — flash the board again.",
    "нет в этой модели": "not in this model",
    "отключён": "disabled",
    "доступен": "available",
    "Espressif · нативный USB (VID 303A)": "Espressif · native USB (VID 303A)",
    "MAC": "MAC",
    "ESP-IDF": "ESP-IDF",
    "Загрузчик не вернул идентификатор flash-чипа.":
        "The loader did not return a flash chip ID.",
    "есть · {}": "present · {}",
    "прервано": "aborted",
    "Flash стёрта": "Flash erased",
    "да": "yes",
    "Последовательный порт": "Serial port",
    "последовательный порт": "serial port",
    "Стандартный последовательный порт": "Standard serial port",
    "USB-последовательный порт": "USB serial port",
    "Устройство с последовательным интерфейсом USB": "USB serial device",
    "Виртуальный последовательный порт": "Virtual serial port",
})

# ---------------------------------------------------------------------------
# дополнительные шаблоны
# ---------------------------------------------------------------------------
_TPL += [
    # --- единицы измерения ---
    ("{} ГБ", "{} GB"),
    ("{} МБ", "{} MB"),
    ("{} КБ", "{} KB"),
    ("{} Б", "{} B"),
    ("{} КБ (по документации)", "{} KB (per datasheet)"),

    # --- справочник чипов ---
    ("до {} МБ внешней (опционально)", "up to {} MB external (optional)"),
    ("до {} МБ (редко, ESP8266 с PSRAM)", "up to {} MB (rare, ESP8266 with PSRAM)"),
    ("Классический ESP32: {} КБ SRAM, внешняя PSRAM только у некоторых модулей.",
     "Classic ESP32: {} KB SRAM, external PSRAM only on some modules."),
    ("ESP32-S2: {} КБ SRAM, без Bluetooth.", "ESP32-S2: {} KB SRAM, no Bluetooth."),
    ("ESP32-S3: {} КБ SRAM + кэш; PSRAM бывает 2/4/8 МБ.",
     "ESP32-S3: {} KB SRAM + cache; PSRAM comes in 2/4/8 MB."),
    ("ESP32-C3: {} КБ SRAM. Внешняя PSRAM не поддерживается.",
     "ESP32-C3: {} KB SRAM. External PSRAM is not supported."),
    ("ESP32-C6: {} КБ SRAM (HP) + LP-память.", "ESP32-C6: {} KB SRAM (HP) + LP memory."),
    ("ESP32-C2: {} КБ SRAM.", "ESP32-C2: {} KB SRAM."),
    ("ESP32-C5: {} КБ SRAM, dual-band Wi-Fi.", "ESP32-C5: {} KB SRAM, dual-band Wi-Fi."),
    ("ESP32-H2: {} КБ SRAM, только 802.15.4/BLE.", "ESP32-H2: {} KB SRAM, 802.15.4/BLE only."),
    ("ESP32-P4: {} КБ SRAM + LP-память.", "ESP32-P4: {} KB SRAM + LP memory."),
    ("ESP8266: {} КБ SRAM всего, ~80 КБ доступно приложению.",
     "ESP8266: {} KB SRAM total, ~80 KB available to the application."),
    ("Модель отсутствует в справочнике — объём SRAM неизвестен.",
     "The model is not in the reference — the SRAM size is unknown."),
    ("{} (1 ядро)", "{} (1 core)"),
    ("{} (2 ядра)", "{} (2 cores)"),
    ("{} (HP 1 ядро + LP)", "{} (HP 1 core + LP)"),
    ("{} (2 ядра, HP)", "{} (2 cores, HP)"),
    ("OUI {} не в списке Espressif", "OUI {} is not in the Espressif pool"),
    ("нет интерфейса PSRAM", "no PSRAM interface"),

    # --- вердикты по объёму flash ---
    ("Чип flash отвечает {}. Заголовок прошивки не найден (плата не прошита или образ "
     "повреждён) — сверить заявленный объём не с чем.",
     "The flash chip reports {}. No firmware header found (board not flashed or image "
     "damaged) — there is nothing to compare the declared size with."),
    ("В заголовке прошивки указано {}, а чип отвечает {}. Прошивка может не влезть / "
     "модуль размечен неверно.",
     "The firmware header says {} but the chip reports {}. The firmware may not fit / "
     "the module is mislabelled."),
    ("Чип реально {}, а прошивка собрана под {}. Часть памяти простаивает.",
     "The chip really has {}, while the firmware was built for {}. Part of the memory "
     "is unused."),
    ("{} ≠ {} — образ от другого чипа!", "{} ≠ {} — image is for another chip!"),

    # --- глубокий тест ---
    ("Запись и чтение всей flash ({}) без ошибок. Это подтверждает реальный объём.",
     "Writing and reading the whole flash ({}) produced no errors. This confirms the "
     "real size."),
    ("Найдено ошибок в {} блоках. Первый сбой: {}. Похоже, реальный объём ≈ {} "
     "(заявлено {}).",
     "Errors found in {} blocks. First failure: {}. The real size looks like ≈ {} "
     "(declared {})."),
    ("Резервная копия: {}", "Backup: {}"),
    ("Скорость: запись {} КБ/с, чтение {} КБ/с", "Speed: write {} KB/s, read {} KB/s"),

    # --- диалоги подтверждения ---
    ("Будет перезаписана вся flash ({}): прошивка, NVS, файловая система.\n\n"
     "Перед началом программа снимет полную резервную копию и восстановит её после "
     "теста. Не отключайте плату во время работы!\n\n"
     "Ожидаемое время: около {} мин.\n\n"
     "Если восстановление прервётся, плату придётся прошивать заново.",
     "The entire flash ({}) will be overwritten: firmware, NVS, file system.\n\n"
     "Before starting, the app takes a full backup and restores it after the test. "
     "Do not unplug the board while it runs!\n\n"
     "Expected time: about {} min.\n\n"
     "If the restore is interrupted, the board will have to be flashed again."),
    ("Будет очищена вся flash ({}) чипа {}:\n"
     "  • загрузчик (bootloader) и таблица разделов\n"
     "  • приложение и все его данные (NVS, SPIFFS/LittleFS, coredump)\n\n"
     "Резервная копия НЕ создаётся. После стирания плата не запустит прошивку — "
     "её нужно будет прошить заново (esptool, Arduino IDE или ESP-IDF).\n\n"
     "Не отключайте плату во время операции.",
     "The whole flash ({}) of the {} chip will be wiped:\n"
     "  • bootloader and partition table\n"
     "  • the application and all its data (NVS, SPIFFS/LittleFS, coredump)\n\n"
     "NO backup is made. After erasing, the board will not boot — you will have to "
     "flash it again (esptool, Arduino IDE or ESP-IDF).\n\n"
     "Do not unplug the board during the operation."),

    # --- подписи COM-портов от Windows ---
    ("COM{} — {}", "COM{} — {}"),

    # --- отступы в отчёте (переводим содержимое) ---
    ("    {}", "    {}"),

    # --- прочее ---
    ("Демо-режим: показаны данные виртуальной платы ESP32-S3.",
     "Demo mode: showing data of a virtual ESP32-S3 board."),
    ("{} (реально {})", "{} (real {})"),
]

# ---------------------------------------------------------------------------
# сообщения слоя железа (probe.py) — переводятся на границе отображения
# ---------------------------------------------------------------------------
_TPL += [
    ("Поиск загрузчика…", "Looking for the loader…"),
    ("Автопоиск платы: {}", "Board autodetect: {}"),
    ("Порт {}: пробую подключиться…", "Port {}: trying to connect…"),
    ("Порт {}: нет ответа", "Port {}: no response"),
    ("Чип определён: {} на {}", "Chip detected: {} on {}"),
    ("Запуск stub-загрузчика…", "Starting the stub loader…"),
    ("Stub-загрузчик запущен (полноскоростной режим)", "Stub loader started (full-speed mode)"),
    ("Stub не запустился ({}); работаю через ROM", "Stub failed ({}); using ROM"),
    ("Скорость обмена: {} бод", "Link speed: {} baud"),
    ("Не удалось поднять скорость ({}); остаюсь на 115200",
     "Could not raise the speed ({}); staying at 115200"),
    ("Связь установлена", "Link established"),
    ("Данные о безопасности недоступны: {}", "Security info unavailable: {}"),
    ("Не удалось прочитать JEDEC ID: {}", "Could not read the JEDEC ID: {}"),
    ("Автоопределение объёма flash не удалось: {}", "Flash size autodetect failed: {}"),
    ("Резервная копия flash → {}", "Flash backup → {}"),
    ("Резервная копия 0x{}", "Backup 0x{}"),
    ("Копия сохранена ({})", "Backup saved ({})"),
    ("Ошибка проверки на 0x{}", "Verify error at 0x{}"),
    ("Запись/проверка 0x{}", "Write/verify 0x{}"),
    ("Прерывание: возвращаю прошивку на место…", "Aborting: restoring the firmware…"),
    ("Сбой при записи ({}); восстанавливаю прошивку…",
     "Write failed ({}); restoring the firmware…"),
    ("Восстановление прошивки…", "Restoring the firmware…"),
    ("Восстановление 0x{}", "Restore 0x{}"),
    ("Проверка восстановления…", "Verifying the restore…"),
    ("Восстановление не удалось: {}", "Restore failed: {}"),
    ("На плате включён Secure Boot / шифрование flash: стирание заблокировано защитой чипа. "
     "Такую плату нельзя очистить без force-режима.",
     "Secure Boot / flash encryption is enabled on the board: erasing is blocked by the chip's "
     "protection. Such a board cannot be wiped without force mode."),
    ("Стираю всю flash ({}), это может занять до минуты…",
     "Erasing the whole flash ({}), this may take up to a minute…"),
    ("Стирание flash…", "Erasing flash…"),
    ("Стирание отклонено загрузчиком: {}", "Erase rejected by the loader: {}"),
    ("Проверяю результат…", "Checking the result…"),
    ("Не удалось прочитать flash после стирания: {}",
     "Could not read flash after erasing: {}"),
    ("После стирания в начале flash остались данные — проверьте плату.",
     "Data remains at the beginning of flash after erasing — check the board."),
    ("Адрес не кратен сектору: начинаю с 0x{} ({} байт 0xFF в начале).",
     "The address is not sector-aligned: starting at 0x{} ({} bytes of 0xFF at the front)."),
    ("Запись {} по адресу 0x{}…", "Writing {} at 0x{}…"),
    ("Запись 0x{}", "Write 0x{}"),
    ("Запись прервана — файл записан частично, плату нужно прошить заново.",
     "Write aborted — the file is partially written, the board must be flashed again."),
    ("Проверка записанного…", "Verifying the written data…"),
    ("Проверка 0x{}", "Verify 0x{}"),
    ("Расхождение при проверке: 0x{} (всего блоков с ошибкой: {})",
     "Mismatch on verify: 0x{} (blocks with errors: {})"),
    ("Автопоиск платы: ", "Board autodetect: "),
    ("Порт {}: ", "Port {}: "),
    ("Стирание запрещено: на чипе активен Secure Boot или шифрование flash.",
     "Erasing is forbidden: Secure Boot or flash encryption is active on the chip."),
    ("Это аппаратная защита — загрузчик не даёт стереть микросхему.",
     "This is hardware protection — the loader does not allow wiping the chip."),
    ("В системе не найдено ни одного COM-порта.", "No COM port found in the system."),
    ("USB-устройство {}:{} воткнуто, но COM-порт не создан — не установлен драйвер USB-UART "
     "(служба: {}).",
     "USB device {}:{} is present but no COM port was created — the USB-UART driver is missing "
     "(service: {})."),
    ("USB-устройств Espressif / USB-UART в системе нет вообще — проверьте кабель "
     "(нужен data-кабель) и USB-порт.",
     "There are no Espressif / USB-UART devices in the system at all — check the cable "
     "(a data cable is required) and the USB port."),
    ("Плата не отвечает.", "The board does not respond."),
    ("Загрузчик отказался стирать flash: {}", "The loader refused to erase the flash: {}"),
    ("Файл пустой — записывать нечего.", "The file is empty — nothing to write."),
    ("Файл не помещается во flash: 0x{} при объёме {}. Уменьшите адрес или файл.",
     "The file does not fit into flash: 0x{} with a capacity of {}. Lower the address or "
     "pick a smaller file."),
    ("Не удалось связаться с чипом.", "Could not talk to the chip."),
    ("• проверьте USB-кабель (нужен data-кабель, не «только зарядка»);",
     "• check the USB cable (a data cable, not a charge-only one);"),
    ("• установлен ли драйвер USB-UART (CP210x / CH340 / FTDI);",
     "• whether the USB-UART driver is installed (CP210x / CH340 / FTDI);"),
    ("• зажмите кнопку BOOT и, не отпуская, нажмите EN/RST, затем отпустите BOOT;",
     "• hold BOOT, press EN/RST, then release BOOT;"),
    ("• убедитесь, что выбран правильный COM-порт.",
     "• make sure the correct COM port is selected."),
    ("Порт занят или недоступен. Закройте монитор порта / Arduino IDE / PlatformIO, другой "
     "терминал и повторите.",
     "The port is busy or unavailable. Close the serial monitor / Arduino IDE / PlatformIO or "
     "any other terminal and try again."),
    ("Чип не ответил вовремя. Попробуйте снизить скорость (115200) и повторить, либо перевести "
     "плату в режим загрузки вручную.",
     "The chip did not answer in time. Try a lower speed (115200), or put the board into "
     "download mode manually."),
]

_compiled = None


def _patterns():
    global _compiled
    if _compiled is None:
        out = []
        for ru, en in _TPL:
            parts = ru.split("{}")
            pat = "(.+?)".join(re.escape(p) for p in parts)
            # «удельный вес» шаблона: чем больше в нём фиксированного текста,
            # тем он точнее — такие совпадения выигрывают у общих вида "{} МБ"
            spec = len("".join(parts))
            out.append((re.compile("^" + pat + "$", re.S), en, spec))
        _compiled = out
    return _compiled


def get_lang() -> str:
    return LANG


def set_lang(code: str) -> None:
    global LANG
    LANG = "en" if str(code).lower().startswith("en") else "ru"


def is_en() -> bool:
    return LANG == "en"


def tr(text, _depth: int = 0):
    """Перевести строку. Неизвестные строки возвращаются как есть.

    Подстановки в шаблонах тоже переводятся (на один-два уровня вглубь), поэтому
    «  Встроенная SRAM\t512 КБ (по документации)» превращается в
    «  Internal SRAM\t512 KB (per datasheet)».
    """
    if LANG != "en" or not isinstance(text, str) or not text:
        return text
    hit = _UI.get(text)
    if hit is not None:
        return hit
    best = None
    for rx, en, spec in _patterns():
        m = rx.match(text)
        if m and (best is None or spec > best[0]):
            best = (spec, en, m.groups())
    if best is None:
        return text
    groups = best[2]
    if _depth < 3:
        groups = tuple(tr(g, _depth + 1) if isinstance(g, str) else g for g in groups)
    try:
        return best[1].format(*groups)
    except Exception:  # noqa: BLE001
        return text


def tr_lines(text):
    """Перевести многострочный блок построчно (каждая строка — отдельная фраза)."""
    if LANG != "en" or not isinstance(text, str) or not text:
        return text
    return "\n".join(tr(line) for line in text.split("\n"))


def confirm_word() -> str:
    """Слово-подтверждение для разрушающих операций."""
    return "ERASE" if LANG == "en" else "СТЕРЕТЬ"


def confirm_hint() -> str:
    """Подпись над полем ввода слова-подтверждения."""
    if LANG == "en":
        return f"Type {confirm_word()} to confirm:"
    return "Для подтверждения введите слово СТЕРЕТЬ:"


def tr_tree(root) -> None:
    """Перевести тексты готового дерева виджетов (вызывается после сборки/отрисовки)."""
    if LANG != "en":
        return

    def walk(w):
        yield w
        for c in w.winfo_children():
            yield from walk(c)

    for w in walk(root):
        try:
            cls = w.winfo_class()
            if cls in ("Label", "Button", "Checkbutton", "Radiobutton"):
                t = w.cget("text")
                if isinstance(t, str) and t:
                    new = tr(t)
                    if new != t:
                        w.configure(text=new)
            elif cls == "Toplevel":
                title = w.title()
                if title:
                    w.title(tr(title))
        except Exception:  # noqa: BLE001
            pass
        # свои кнопки рисуют текст на Canvas
        if hasattr(w, "set_text") and hasattr(w, "_text"):
            try:
                w.set_text(tr(w._text))
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------
# настройки (язык запоминается между запусками)
# ---------------------------------------------------------------------------
def _settings_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "ESP_TEST", "settings.json")


def load_settings() -> dict:
    try:
        with open(_settings_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {}


def save_settings(data: dict) -> None:
    path = _settings_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
    except Exception:  # noqa: BLE001
        pass
