"""Модуль обработки: статистика текста.

Считает символы, слова, предложения, уникальные слова, среднюю длину
слова, самое длинное слово и самые частые слова.

Может использоваться как библиотека (handle_request) и как отдельная
программа, обменивающаяся JSON-файлами::

    python processing_module.py --request req.json --response resp.json
"""
import argparse
import math
import re
import sys
from collections import Counter

import mapping
import protocol
from errors import (InputDataError, IntegrationError, ProtocolError,
                    VersionConflictError)

WORD_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+(?:[-'][0-9A-Za-zА-Яа-яЁё]+)*")
SENTENCE_RE = re.compile(r"[.!?…]+")

DEFAULT_TOP = 3


def tokenize(text):
    """Слова текста в исходном написании (порядок сохраняется)."""
    return WORD_RE.findall(text)


def split_sentences(text):
    """Предложения текста (по знакам конца предложения)."""
    parts = SENTENCE_RE.split(text)
    return [part.strip() for part in parts if part.strip()]


def top_words(words, limit=DEFAULT_TOP):
    """Самые частые слова: сначала по частоте, затем по алфавиту."""
    if limit < 1:
        return ()
    counts = Counter(word.casefold() for word in words)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return tuple(ordered[:limit])


def analyze(text):
    """Считает статистику текста и возвращает TextStats."""
    words = tokenize(text)
    sentences = split_sentences(text)
    longest = max(words, key=len) if words else ""
    average = math.fsum(len(word) for word in words) / len(words) \
        if words else 0.0
    return mapping.TextStats(
        chars=len(text),
        chars_no_spaces=sum(1 for symbol in text if not symbol.isspace()),
        words=len(words),
        sentences=len(sentences),
        unique_words=len({word.casefold() for word in words}),
        avg_word_length=round(average, 2),
        longest_word=longest,
        top_words=top_words(words),
    )


def handle_request(request):
    """Обрабатывает text_request, всегда возвращает сообщение-ответ."""
    try:
        text = protocol.parse_request(request)
        return mapping.processing_to_response(analyze(text))
    except VersionConflictError as exc:
        return protocol.build_error(protocol.ERR_VERSION, str(exc))
    except InputDataError as exc:
        return protocol.build_error(protocol.ERR_INVALID_DATA, str(exc))
    except ProtocolError as exc:
        return protocol.build_error(protocol.ERR_PROTOCOL, str(exc))


def process_files(request_path, response_path):
    """Читает запрос, пишет ответ. True, если ответ не является error."""
    try:
        response = handle_request(protocol.load_json(request_path))
    except ProtocolError as exc:
        response = protocol.build_error(protocol.ERR_PROTOCOL, str(exc))
    protocol.dump_json(response_path, response)
    return response["type"] != protocol.MSG_ERROR


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--request", required=True,
                        help="файл с сообщением text_request")
    parser.add_argument("--response", required=True,
                        help="файл для сообщения-ответа")
    args = parser.parse_args(argv)
    try:
        ok = process_files(args.request, args.response)
    except IntegrationError as exc:
        print(f"Модуль обработки: {exc}", file=sys.stderr)
        return protocol.EXIT_FAILURE
    return protocol.EXIT_OK if ok else protocol.EXIT_REPORTED_ERROR


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
