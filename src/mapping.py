"""Сопоставление объектов данных (mapping) между модулями.

Структуры данных модулей:

* модуль ввода     -> str (проверенный текст);
* модуль обработки -> TextStats(...);
* модуль вывода    -> текст отчёта.

Правила преобразования см. docs/integration.md (таблица соответствия).
"""
from dataclasses import dataclass
from typing import Tuple

import protocol


@dataclass(frozen=True)
class TextStats:
    """Результат статистической обработки текста."""
    chars: int
    chars_no_spaces: int
    words: int
    sentences: int
    unique_words: int
    avg_word_length: float
    longest_word: str
    top_words: Tuple[Tuple[str, int], ...]


def processing_to_response(stats):
    """TextStats -> stats_response."""
    return protocol.build_response({
        "chars": stats.chars,
        "chars_no_spaces": stats.chars_no_spaces,
        "words": stats.words,
        "sentences": stats.sentences,
        "unique_words": stats.unique_words,
        "avg_word_length": stats.avg_word_length,
        "longest_word": stats.longest_word,
        "top_words": stats.top_words,
    })


def response_to_stats(message):
    """stats_response -> TextStats."""
    data = protocol.parse_response(message)
    return TextStats(
        chars=data["chars"],
        chars_no_spaces=data["chars_no_spaces"],
        words=data["words"],
        sentences=data["sentences"],
        unique_words=data["unique_words"],
        avg_word_length=data["avg_word_length"],
        longest_word=data["longest_word"],
        top_words=tuple(data["top_words"]),
    )
