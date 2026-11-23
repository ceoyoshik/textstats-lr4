# ТекстСтат-11

Консольная программа на Python: считает статистику текста — количество
символов, слов, предложений, уникальных слов, среднюю длину слова, самое
длинное слово и самые частые слова.

Версия 1.1.0: программа состоит из трёх модулей (ввод, обработка, вывод),
которые обмениваются JSON-сообщениями. Версия протестирована в ЛР №4
(вариант 11): 321 тест, покрытие 100 %, CI на GitHub Actions.

## Структура проекта

```
textstats/
├── src/            # исходный код
│   ├── textstat.py           # точка входа, интеграция модулей
│   ├── input_module.py       # модуль ввода
│   ├── processing_module.py  # модуль обработки (статистика)
│   ├── output_module.py      # модуль вывода
│   ├── protocol.py           # JSON-протокол обмена
│   ├── mapping.py            # сопоставление данных модулей
│   └── errors.py             # исключения интеграции
├── tests/          # unit, whitebox, integration, regression
├── docs/           # план тестирования, баг-репорты, метрики, ревью
├── .github/        # CI (GitHub Actions)
├── requirements.txt
├── pytest.ini
├── README.md
└── .gitignore
```

## Требования к окружению

- Python 3.11 или новее (проверено на 3.11, 3.12 и 3.14);
- pytest, pytest-cov, flake8 (`pip install -r requirements.txt`).

## Запуск

```
python src/textstat.py --file text.txt
```

или текст читается со стандартного ввода:

```
python src/textstat.py < text.txt
```

Дополнительные параметры:

```
python src/textstat.py --file text.txt --workdir exchange
python src/textstat.py --file text.txt --timeout 5
```

Пример вывода:

```
Статистика текста
Символов: 24
Символов без пробелов: 20
Слов: 4
Предложений: 2
Уникальных слов: 3
Средняя длина слова: 4.50
Самое длинное слово: Привет
Самые частые слова:
  мир — 2
  привет — 1
  текста — 1
```

## Тестирование (ЛР №4)

```
pytest -q --cov=src --cov-report=term-missing
flake8 src tests
```

| Каталог | Маркер | Что проверяет |
| --- | --- | --- |
| `tests/unit` | `unit`, `whitebox` | модули по отдельности, классы эквивалентности, границы, покрытие решений и условий |
| `tests/integration` | `integration` | обмен JSON-файлами, подпроцесс, повторы, тайм-аут, CLI |
| `tests/regression` | `regression` | эталонные результаты и формат вывода |

Результаты: 321 тест, покрытие 100 % по операторам, решениям и условиям.

Документация:

- [docs/testing.md](docs/testing.md) — план, сценарии, протокол, покрытие;
- [docs/bug_reports.md](docs/bug_reports.md) — 3 баг-репорта;
- [docs/testing_metrics.md](docs/testing_metrics.md) — метрики;
- [docs/testing_methods.md](docs/testing_methods.md) — сравнение методов;
- [docs/code_review.md](docs/code_review.md) — инспекция кода и ревью тестов;
- [docs/integration.md](docs/integration.md) — протокол обмена и архитектура.

CI: [.github/workflows/testing.yml](.github/workflows/testing.yml) — flake8,
тесты с порогом покрытия 95 % на Python 3.11/3.12, задача регрессионных
тестов, запуск по push, pull request, тегу и по расписанию.

## Автор

Кудинов А.А., группа ИП-25-1, Липецкий государственный технический
университет, 2026.
