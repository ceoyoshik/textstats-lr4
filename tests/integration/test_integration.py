"""Интеграционные тесты: взаимодействие модулей ввода, обработки и вывода."""
import os
import subprocess
import sys

import pytest

import input_module
import mapping
import protocol
import textstat
from errors import InputDataError, ModuleTimeoutError, ModuleUnavailableError

pytestmark = pytest.mark.integration

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

SAMPLE = "Привет, мир! Мир текста."


# ------------------------------------------------ стенд: ввод -> обработка
def test_integrate_returns_stats(exchange_dir, inprocess_runner):
    stats = textstat.integrate(SAMPLE, exchange_dir, runner=inprocess_runner)
    assert stats.words == 4
    assert stats.sentences == 2
    assert stats.top_words[0] == ("мир", 2)


def test_integrate_writes_exchange_files(exchange_dir, inprocess_runner):
    textstat.integrate(SAMPLE, exchange_dir, runner=inprocess_runner)
    request = protocol.load_json(os.path.join(exchange_dir, "request.json"))
    response = protocol.load_json(os.path.join(exchange_dir, "response.json"))
    assert request["payload"]["text"] == SAMPLE
    assert response["payload"]["words"] == 4


def test_integrate_with_real_subprocess(exchange_dir):
    stats = textstat.integrate("Одно слово", exchange_dir)
    assert stats.words == 2
    assert stats.longest_word == "слово"


# ------------------------------------------------------------ устойчивость
def test_integrate_retries_after_failure(exchange_dir, inprocess_runner):
    calls = []

    def failing_once(request_path, response_path, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise ModuleUnavailableError("сбой запуска")
        inprocess_runner(request_path, response_path, timeout)

    stats = textstat.integrate("текст", exchange_dir, attempts=2,
                               runner=failing_once)
    assert stats.words == 1
    assert len(calls) == 2


def test_integrate_raises_after_all_attempts(exchange_dir):
    calls = []

    def always_fails(request_path, response_path, timeout):
        calls.append(1)
        raise ModuleTimeoutError("нет ответа")

    with pytest.raises(ModuleTimeoutError):
        textstat.integrate("текст", exchange_dir, attempts=3,
                           runner=always_fails)
    assert len(calls) == 3


def test_integrate_attempts_zero_tries_once(exchange_dir, inprocess_runner):
    calls = []

    def runner(request_path, response_path, timeout):
        calls.append(1)
        inprocess_runner(request_path, response_path, timeout)

    textstat.integrate("текст", exchange_dir, attempts=0, runner=runner)
    assert len(calls) == 1


def test_integrate_removes_stale_response(exchange_dir):
    stale = os.path.join(exchange_dir, "response.json")
    protocol.dump_json(stale, protocol.build_error("stale", "старый ответ"))

    def no_response(request_path, response_path, timeout):
        return None

    with pytest.raises(ModuleUnavailableError):
        textstat.integrate("текст", exchange_dir, attempts=1,
                           runner=no_response)


def test_integrate_propagates_module_error(exchange_dir):
    def writes_error(request_path, response_path, timeout):
        protocol.dump_json(response_path,
                           protocol.build_error(protocol.ERR_INVALID_DATA,
                                                "плохой текст"))

    with pytest.raises(InputDataError) as error:
        textstat.integrate("текст", exchange_dir, runner=writes_error)
    assert "плохой текст" in str(error.value)


# ------------------------------------------------ запуск внешнего процесса
def test_run_processing_subprocess_success(exchange_dir):
    request_path = os.path.join(exchange_dir, "request.json")
    response_path = os.path.join(exchange_dir, "response.json")
    protocol.dump_json(request_path, protocol.build_request("текст"))
    textstat.run_processing_subprocess(request_path, response_path,
                                       timeout=30)
    assert protocol.load_json(response_path)["type"] == protocol.MSG_RESPONSE


def test_run_processing_subprocess_timeout(tmp_path):
    slow = tmp_path / "slow.py"
    slow.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    with pytest.raises(ModuleTimeoutError):
        textstat.run_processing_subprocess(
            "request.json", "response.json", timeout=0.2,
            script=str(slow))


def test_run_processing_subprocess_bad_exit_code(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("import sys\nsys.exit(7)\n", encoding="utf-8")
    with pytest.raises(ModuleUnavailableError) as error:
        textstat.run_processing_subprocess(
            "request.json", "response.json", timeout=30,
            script=str(broken))
    assert "7" in str(error.value)


def test_run_processing_subprocess_missing_interpreter(monkeypatch):
    monkeypatch.setattr(textstat.sys, "executable", "/nonexistent/python")
    with pytest.raises(ModuleUnavailableError):
        textstat.run_processing_subprocess(
            "request.json", "response.json", timeout=30)


# ------------------------------------------------------- точка входа main
def test_main_success_with_file(tmp_path, exchange_dir):
    text = tmp_path / "text.txt"
    text.write_text(SAMPLE, encoding="utf-8")
    output = []
    code = textstat.main(["--file", str(text), "--workdir", exchange_dir],
                         write=output.append, runner=_slow_runner)
    assert code == textstat.EXIT_SUCCESS
    assert output and "Слов: 4" in output[0]
    assert os.path.exists(os.path.join(exchange_dir, "request.json"))


def _slow_runner(request_path, response_path, timeout):
    import processing_module
    processing_module.process_files(request_path, response_path)


def test_main_reads_stdin(tmp_path, monkeypatch, capsys):
    class FakeStdin:
        def read(self):
            return "Текст из потока."

    monkeypatch.setattr(input_module.sys, "stdin", FakeStdin())
    code = textstat.main([], runner=_slow_runner)
    assert code == textstat.EXIT_SUCCESS
    assert "Слов: 3" in capsys.readouterr().out


def test_main_uses_temporary_workdir(tmp_path):
    text = tmp_path / "text.txt"
    text.write_text("слово", encoding="utf-8")
    output = []
    code = textstat.main(["--file", str(text)], write=output.append,
                         runner=_slow_runner)
    assert code == textstat.EXIT_SUCCESS
    assert output


def test_main_data_error(tmp_path, capsys):
    text = tmp_path / "empty.txt"
    text.write_text("   ", encoding="utf-8")
    code = textstat.main(["--file", str(text)], runner=_slow_runner)
    assert code == textstat.EXIT_DATA_ERROR
    assert "Ошибка данных" in capsys.readouterr().err


def test_main_integration_error(tmp_path, capsys):
    text = tmp_path / "text.txt"
    text.write_text("текст", encoding="utf-8")

    def broken(request_path, response_path, timeout):
        raise ModuleTimeoutError("тайм-аут")

    code = textstat.main(["--file", str(text)], runner=broken)
    assert code == textstat.EXIT_INTEGRATION_ERROR
    assert "Ошибка интеграции" in capsys.readouterr().err


def test_main_custom_error_writer(monkeypatch):
    messages = []

    def failing(path=None, stream=None):
        raise InputDataError("нет ввода")

    monkeypatch.setattr(textstat.input_module, "load_source", failing)
    code = textstat.main([], write_err=messages.append)
    assert code == textstat.EXIT_DATA_ERROR
    assert messages == ["Ошибка данных: нет ввода"]


def test_main_timeout_option_is_passed(tmp_path, exchange_dir):
    text = tmp_path / "text.txt"
    text.write_text("текст", encoding="utf-8")
    seen = {}

    def runner(request_path, response_path, timeout):
        seen["timeout"] = timeout
        _slow_runner(request_path, response_path, timeout)

    textstat.main(["--file", str(text), "--workdir", exchange_dir,
                   "--timeout", "2.5"], runner=runner)
    assert seen["timeout"] == 2.5


def test_build_parser_defaults():
    args = textstat.build_parser().parse_args([])
    assert args.timeout == textstat.DEFAULT_TIMEOUT
    assert args.workdir is None
    assert args.file is None


# ------------------------------------------------------ сквозной запуск CLI
def run_cli(*args, stdin_text=None):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT_DIR, "src", "textstat.py"),
         *args],
        input=stdin_text, capture_output=True, text=True, timeout=60)


def test_cli_end_to_end_with_file(tmp_path):
    text = tmp_path / "text.txt"
    text.write_text(SAMPLE, encoding="utf-8")
    completed = run_cli("--file", str(text))
    assert completed.returncode == 0
    assert "Слов: 4" in completed.stdout
    assert "мир — 2" in completed.stdout


def test_cli_end_to_end_with_stdin():
    completed = run_cli(stdin_text="Одно предложение.")
    assert completed.returncode == 0
    assert "Предложений: 1" in completed.stdout


def test_cli_reports_bad_input(tmp_path):
    text = tmp_path / "empty.txt"
    text.write_text("", encoding="utf-8")
    completed = run_cli("--file", str(text))
    assert completed.returncode == textstat.EXIT_DATA_ERROR
    assert "Ошибка данных" in completed.stderr


def test_cli_processing_module_directly(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path), protocol.build_request("Текст."))
    completed = subprocess.run(
        [sys.executable,
         os.path.join(ROOT_DIR, "src", "processing_module.py"),
         "--request", str(request_path),
         "--response", str(response_path)],
        capture_output=True, text=True, timeout=60)
    assert completed.returncode == protocol.EXIT_OK
    response = protocol.load_json(str(response_path))
    assert response["payload"]["words"] == 1


def test_cli_processing_module_broken_request(tmp_path):
    request_path = tmp_path / "request.json"
    request_path.write_text("{bad}", encoding="utf-8")
    completed = subprocess.run(
        [sys.executable,
         os.path.join(ROOT_DIR, "src", "processing_module.py"),
         "--request", str(request_path),
         "--response", str(tmp_path / "response.json")],
        capture_output=True, text=True, timeout=60)
    assert completed.returncode == protocol.EXIT_REPORTED_ERROR
    response = protocol.load_json(str(tmp_path / "response.json"))
    assert response["payload"]["code"] == protocol.ERR_PROTOCOL


def test_integrate_returns_dataclass(exchange_dir, inprocess_runner):
    stats = textstat.integrate("слово", exchange_dir,
                               runner=inprocess_runner)
    assert isinstance(stats, mapping.TextStats)
