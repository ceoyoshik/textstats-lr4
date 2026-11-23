"""Модуль ввода: чтение и проверка текста.

Текст читается из файла или со стандартного ввода, проверяется на пустоту,
размер и недопустимые управляющие символы.
"""
import sys

import protocol
from errors import InputDataError


def parse_text(text, source="ввод"):
    """Проверяет текст: строка, не пустая, в пределах MAX_TEXT."""
    if not isinstance(text, str):
        raise InputDataError(f"{source}: текст должен быть строкой")
    if len(text) > protocol.MAX_TEXT:
        raise InputDataError(
            f"{source}: текст длиннее {protocol.MAX_TEXT} символов")
    if not text.strip():
        raise InputDataError(f"{source}: текст не должен быть пустым")
    protocol.check_text_symbols(text, source)
    return text


def read_file(path):
    """Читает текст из файла в кодировке UTF-8."""
    try:
        with open(path, encoding="utf-8") as handle:
            return parse_text(handle.read(), f"файл {path}")
    except FileNotFoundError:
        raise InputDataError(f"файл не найден: {path}") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise InputDataError(f"не удалось прочитать файл {path}: {exc}") \
            from None


def read_stdin(stream=None):
    """Читает текст со стандартного ввода до конца потока."""
    stream = stream if stream is not None else sys.stdin
    try:
        return parse_text(stream.read(), "стандартный ввод")
    except UnicodeDecodeError as exc:
        raise InputDataError(f"не удалось прочитать ввод: {exc}") from None


def load_source(path=None, stream=None):
    """Возвращает текст из файла path или со стандартного ввода."""
    if path is not None:
        return read_file(path)
    return read_stdin(stream)
