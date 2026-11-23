"""Общие настройки pytest: пути импорта и вспомогательные фикстуры."""
import os
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TESTS_DIR)
SRC_DIR = os.path.join(ROOT_DIR, "src")

for path in (SRC_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import processing_module  # noqa: E402


@pytest.fixture
def exchange_dir(tmp_path):
    """Каталог для файлов обмена request.json/response.json."""
    directory = tmp_path / "exchange"
    directory.mkdir()
    return str(directory)


@pytest.fixture
def inprocess_runner():
    """Заглушка запуска: модуль обработки вызывается как функция."""
    def runner(request_path, response_path, timeout):
        processing_module.process_files(request_path, response_path)
    return runner
