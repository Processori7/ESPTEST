# -*- coding: utf-8 -*-
"""Имя и версия программы — заданы в одном месте."""

APP_NAME = "ESP_TEST"
__version__ = "1.0.0"

# для файлового ресурса Windows (должно быть 4 числа)
VERSION_TUPLE = tuple(int(x) for x in __version__.split(".")) + (0,) * (4 - len(__version__.split(".")))
