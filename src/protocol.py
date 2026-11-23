"""Протокол обмена между модулями: JSON-сообщения (версия 1.x).

Формат сообщения (конверт)::

    {"version": "1.0", "type": "...", "payload": {...}}

Типы сообщений: text_request (ввод -> обработка),
stats_response (обработка -> вывод) и error (сообщение об ошибке).
"""
import json
import math
import os

from errors import (InputDataError, ModuleUnavailableError, ProtocolError,
                    VersionConflictError)

PROTOCOL_VERSION = "1.0"
SUPPORTED_MAJOR = 1

MSG_REQUEST = "text_request"
MSG_RESPONSE = "stats_response"
MSG_ERROR = "error"

ERR_INVALID_DATA = "invalid_data"
ERR_PROTOCOL = "protocol_error"
ERR_VERSION = "version_conflict"

MAX_TEXT = 200000
MAX_TOP = 10

# Коды завершения модуля обработки (часть интерфейса между модулями)
EXIT_OK = 0
EXIT_REPORTED_ERROR = 10  # в файл ответа записано сообщение error
EXIT_FAILURE = 3          # модуль не смог даже записать ответ


def is_number(value):
    """Конечное число (int или float), не bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        # Целые числа в JSON не ограничены, но в float не помещаются.
        return False


def is_int(value):
    """Целое число, не bool."""
    return isinstance(value, int) and not isinstance(value, bool)


def build_request(text):
    """Собирает сообщение text_request."""
    return {
        "version": PROTOCOL_VERSION,
        "type": MSG_REQUEST,
        "payload": {"text": text},
    }


def build_response(stats):
    """Собирает сообщение stats_response из словаря статистики."""
    return {
        "version": PROTOCOL_VERSION,
        "type": MSG_RESPONSE,
        "payload": {
            "chars": stats["chars"],
            "chars_no_spaces": stats["chars_no_spaces"],
            "words": stats["words"],
            "sentences": stats["sentences"],
            "unique_words": stats["unique_words"],
            "avg_word_length": stats["avg_word_length"],
            "longest_word": stats["longest_word"],
            "top_words": [list(item) for item in stats["top_words"]],
        },
    }


def build_error(code, message):
    """Собирает сообщение об ошибке."""
    return {
        "version": PROTOCOL_VERSION,
        "type": MSG_ERROR,
        "payload": {"code": code, "message": message},
    }


def check_version(version):
    """Проверяет совместимость версии протокола (major должен совпасть)."""
    if not isinstance(version, str):
        raise ProtocolError("поле version должно быть строкой")
    parts = version.split(".")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ProtocolError(f"неверный формат версии: {version!r}")
    if int(parts[0]) != SUPPORTED_MAJOR:
        raise VersionConflictError(
            f"несовместимая версия протокола {version}, "
            f"поддерживается {SUPPORTED_MAJOR}.x")


def raise_from_error(payload):
    """Превращает сообщение error в соответствующее исключение."""
    code = payload.get("code")
    message = str(payload.get("message", "причина не указана"))
    if code == ERR_INVALID_DATA:
        raise InputDataError(message)
    if code == ERR_VERSION:
        raise VersionConflictError(message)
    raise ProtocolError(message)


def validate_envelope(message, expected_type):
    """Проверяет конверт сообщения и возвращает payload."""
    if not isinstance(message, dict):
        raise ProtocolError("сообщение должно быть JSON-объектом")
    for key in ("version", "type", "payload"):
        if key not in message:
            raise ProtocolError(f"в сообщении нет поля {key!r}")
    check_version(message["version"])
    payload = message["payload"]
    if not isinstance(payload, dict):
        raise ProtocolError("поле payload должно быть объектом")
    if message["type"] == MSG_ERROR and expected_type != MSG_ERROR:
        raise_from_error(payload)
    if message["type"] != expected_type:
        raise ProtocolError(
            f"ожидался тип {expected_type!r}, получен {message['type']!r}")
    return payload


def parse_request(message):
    """Проверяет text_request и возвращает текст."""
    payload = validate_envelope(message, MSG_REQUEST)
    text = payload.get("text")
    if not isinstance(text, str):
        raise ProtocolError("поле text должно быть строкой")
    if len(text) > MAX_TEXT:
        raise InputDataError(
            f"текст длиннее {MAX_TEXT} символов: {len(text)}")
    if not text.strip():
        raise InputDataError("текст не должен быть пустым")
    return text


def parse_response(message):
    """Проверяет stats_response и возвращает словарь статистики."""
    payload = validate_envelope(message, MSG_RESPONSE)
    counters = ("chars", "chars_no_spaces", "words", "sentences",
                "unique_words")
    for name in counters:
        value = payload.get(name)
        if not is_int(value) or value < 0:
            raise ProtocolError(
                f"поле {name} должно быть неотрицательным целым")
    if not is_number(payload.get("avg_word_length")):
        raise ProtocolError("avg_word_length должно быть конечным числом")
    longest = payload.get("longest_word")
    if not isinstance(longest, str):
        raise ProtocolError("longest_word должно быть строкой")
    top = payload.get("top_words")
    if not isinstance(top, list):
        raise ProtocolError("top_words должен быть списком")
    if len(top) > MAX_TOP:
        raise ProtocolError(f"top_words длиннее {MAX_TOP} элементов")
    result = []
    for item in top:
        if (not isinstance(item, list) or len(item) != 2
                or not isinstance(item[0], str) or not is_int(item[1])
                or item[1] < 0):
            raise ProtocolError("элемент top_words должен быть [слово, число]")
        result.append((item[0], item[1]))
    return {
        "chars": payload["chars"],
        "chars_no_spaces": payload["chars_no_spaces"],
        "words": payload["words"],
        "sentences": payload["sentences"],
        "unique_words": payload["unique_words"],
        "avg_word_length": float(payload["avg_word_length"]),
        "longest_word": longest,
        "top_words": result,
    }


def _reject_constant(name):
    raise ProtocolError(f"недопустимая константа в JSON: {name}")


def dump_json(path, message):
    """Атомарно записывает сообщение в файл обмена."""
    temp_path = path + ".tmp"
    try:
        text = json.dumps(message, ensure_ascii=False, indent=2,
                          allow_nan=False)
        with open(temp_path, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        os.replace(temp_path, path)
    except (ValueError, TypeError) as exc:
        raise ProtocolError(f"сообщение нельзя записать: {exc}") from None
    except OSError as exc:
        raise ModuleUnavailableError(
            f"не удалось записать файл обмена: {exc}") from None


def load_json(path):
    """Читает сообщение из файла обмена."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle, parse_constant=_reject_constant)
    except FileNotFoundError:
        raise ModuleUnavailableError(
            f"файл обмена не найден: {path}") from None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProtocolError(f"некорректный JSON: {exc}") from None
    except OSError as exc:
        raise ModuleUnavailableError(
            f"не удалось прочитать файл обмена: {exc}") from None
