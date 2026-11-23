"""Модульные тесты модуля вывода (форматирование отчёта)."""
import pytest

import output_module
from mapping import TextStats

pytestmark = pytest.mark.unit

STATS = TextStats(chars=24, chars_no_spaces=20, words=4, sentences=2,
                  unique_words=3, avg_word_length=4.5,
                  longest_word="Привет",
                  top_words=(("мир", 2), ("привет", 1), ("текста", 1)))


def test_format_stats_full_report():
    text = output_module.format_stats(STATS)
    assert text.split("\n")[0] == "Статистика текста"
    assert "Символов: 24" in text
    assert "Символов без пробелов: 20" in text
    assert "Слов: 4" in text
    assert "Предложений: 2" in text
    assert "Уникальных слов: 3" in text
    assert "Средняя длина слова: 4.50" in text
    assert "Самое длинное слово: Привет" in text
    assert "мир — 2" in text


def test_format_stats_without_words():
    stats = TextStats(chars=3, chars_no_spaces=3, words=0, sentences=0,
                      unique_words=0, avg_word_length=0.0,
                      longest_word="", top_words=())
    text = output_module.format_stats(stats)
    assert "Самое длинное слово: —" in text
    assert "(слов нет)" in text


@pytest.mark.parametrize("value, expected", [
    (0, "0.00"),
    (4.5, "4.50"),
    (4.567, "4.57"),
    (4.564, "4.56"),
    (-0.0, "0.00"),
    (-0.001, "0.00"),
    (100, "100.00"),
])
def test_format_number(value, expected):
    assert output_module.format_number(value) == expected


def test_format_number_custom_precision():
    assert output_module.format_number(1.2345, precision=1) == "1.2"
    assert output_module.format_number(1.2345, precision=0) == "1"


def test_format_top_limits_lines():
    top = (("а", 3), ("б", 2), ("в", 1))
    text = output_module.format_top(top, limit=2)
    assert text == "  а — 3\n  б — 2"


def test_format_top_without_words():
    assert output_module.format_top(()) == "  (слов нет)"


def test_show_writes_report():
    written = []
    output_module.show(STATS, written.append)
    assert written and written[0].startswith("Статистика текста")


def test_show_uses_print_by_default(capsys):
    output_module.show(STATS)
    assert "Слов: 4" in capsys.readouterr().out
