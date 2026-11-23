"""Модуль вывода: форматирование и печать статистики текста."""
PRECISION = 2


def format_number(value, precision=PRECISION):
    """Число с заданной точностью; «-0.00» заменяется на «0.00»."""
    rounded = round(value, precision)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.{precision}f}"


def format_top(top_words, limit=5):
    """Строки вида «слово — N» для первых limit частых слов."""
    if not top_words:
        return "  (слов нет)"
    return "\n".join(
        f"  {word} — {count}"
        for word, count in top_words[:limit]
    )


def format_stats(stats):
    """Отчёт о статистике текста."""
    return (
        "Статистика текста\n"
        f"Символов: {stats.chars}\n"
        f"Символов без пробелов: {stats.chars_no_spaces}\n"
        f"Слов: {stats.words}\n"
        f"Предложений: {stats.sentences}\n"
        f"Уникальных слов: {stats.unique_words}\n"
        f"Средняя длина слова: {format_number(stats.avg_word_length)}\n"
        f"Самое длинное слово: {stats.longest_word or '—'}\n"
        "Самые частые слова:\n"
        f"{format_top(stats.top_words)}"
    )


def show(stats, write=print):
    """Выводит отчёт (write можно подменить в тестах)."""
    write(format_stats(stats))
