"""Модульные тесты протокола обмена (JSON-сообщения, версии, файлы)."""
import json

import pytest

import protocol
from errors import (InputDataError, ModuleUnavailableError, ProtocolError,
                    VersionConflictError)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- is_number
@pytest.mark.parametrize("value", [1, 1.5, -2, 0.0, 1e300])
def test_is_number_accepts_numbers(value):
    assert protocol.is_number(value) is True


@pytest.mark.parametrize("value", [
    True, False, "1", None, [], {}, float("nan"), float("inf"),
])
def test_is_number_rejects_non_numbers(value):
    assert protocol.is_number(value) is False


def test_is_number_huge_integer():
    assert protocol.is_number(10 ** 400) is False


# ---------------------------------------------------------------- is_int
@pytest.mark.parametrize("value, expected", [
    (1, True), (-5, True), (0, True),
    (True, False), (1.0, False), ("1", False), (None, False),
])
def test_is_int(value, expected):
    assert protocol.is_int(value) is expected


# ------------------------------------------------------------- constructors
def test_build_request_structure():
    message = protocol.build_request("Привет")
    assert message == {"version": "1.0", "type": "text_request",
                       "payload": {"text": "Привет"}}


def test_build_response_copies_top_words():
    stats = {"chars": 5, "chars_no_spaces": 5, "words": 1, "sentences": 1,
             "unique_words": 1, "avg_word_length": 5.0,
             "longest_word": "Слово", "top_words": (("слово", 1),)}
    message = protocol.build_response(stats)
    assert message["payload"]["top_words"] == [["слово", 1]]
    assert isinstance(message["payload"]["top_words"][0], list)


def test_build_error_structure():
    message = protocol.build_error(protocol.ERR_PROTOCOL, "беда")
    assert message["payload"] == {"code": protocol.ERR_PROTOCOL,
                                  "message": "беда"}


# -------------------------------------------------------------- check_version
@pytest.mark.parametrize("version", ["1.0", "1.9", "1.00", "01.0"])
def test_check_version_accepts_compatible(version):
    assert protocol.check_version(version) is None


@pytest.mark.parametrize("version", ["2.0", "0.9", "10.0"])
def test_check_version_rejects_other_major(version):
    with pytest.raises(VersionConflictError):
        protocol.check_version(version)


@pytest.mark.parametrize("version", [
    1, 1.0, None, "1", "1.0.0", "a.b", "", ".", "1.", ".0", "1.a",
])
def test_check_version_rejects_bad_format(version):
    with pytest.raises(ProtocolError):
        protocol.check_version(version)


# ---------------------------------------------------------- raise_from_error
@pytest.mark.parametrize("code, exception", [
    (protocol.ERR_INVALID_DATA, InputDataError),
    (protocol.ERR_VERSION, VersionConflictError),
    (protocol.ERR_PROTOCOL, ProtocolError),
    ("unknown", ProtocolError),
    (None, ProtocolError),
])
def test_raise_from_error_maps_codes(code, exception):
    with pytest.raises(exception):
        protocol.raise_from_error({"code": code, "message": "причина"})


def test_raise_from_error_default_message():
    with pytest.raises(ProtocolError) as error:
        protocol.raise_from_error({})
    assert "причина не указана" in str(error.value)


# --------------------------------------------------------- validate_envelope
def test_validate_envelope_returns_payload():
    payload = protocol.validate_envelope(protocol.build_request("текст"),
                                         protocol.MSG_REQUEST)
    assert payload["text"] == "текст"


@pytest.mark.parametrize("message", [None, [], "text", 42])
def test_validate_envelope_rejects_non_objects(message):
    with pytest.raises(ProtocolError):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


@pytest.mark.parametrize("key", ["version", "type", "payload"])
def test_validate_envelope_requires_fields(key):
    message = protocol.build_request("текст")
    del message[key]
    with pytest.raises(ProtocolError) as error:
        protocol.validate_envelope(message, protocol.MSG_REQUEST)
    assert key in str(error.value)


def test_validate_envelope_checks_version():
    message = protocol.build_request("текст")
    message["version"] = "2.0"
    with pytest.raises(VersionConflictError):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


def test_validate_envelope_requires_payload_object():
    message = protocol.build_request("текст")
    message["payload"] = []
    with pytest.raises(ProtocolError):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


def test_validate_envelope_rejects_wrong_type():
    message = protocol.build_response(_stats_payload())
    with pytest.raises(ProtocolError) as error:
        protocol.validate_envelope(message, protocol.MSG_REQUEST)
    assert protocol.MSG_REQUEST in str(error.value)


def test_validate_envelope_transforms_error_message():
    message = protocol.build_error(protocol.ERR_INVALID_DATA, "нет текста")
    with pytest.raises(InputDataError):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


def test_validate_envelope_accepts_expected_error_message():
    message = protocol.build_error(protocol.ERR_PROTOCOL, "ошибка")
    payload = protocol.validate_envelope(message, protocol.MSG_ERROR)
    assert payload["code"] == protocol.ERR_PROTOCOL


# -------------------------------------------------------------- parse_request
def test_parse_request_returns_text():
    assert protocol.parse_request(protocol.build_request("Привет")) == "Привет"


def test_parse_request_requires_string():
    message = protocol.build_request("текст")
    message["payload"]["text"] = 42
    with pytest.raises(ProtocolError):
        protocol.parse_request(message)


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_parse_request_rejects_blank(text):
    with pytest.raises(InputDataError):
        protocol.parse_request(protocol.build_request(text))


def test_parse_request_size_boundaries():
    ok = protocol.build_request("я" * protocol.MAX_TEXT)
    assert len(protocol.parse_request(ok)) == protocol.MAX_TEXT
    too_big = protocol.build_request("я" * (protocol.MAX_TEXT + 1))
    with pytest.raises(InputDataError):
        protocol.parse_request(too_big)


def test_parse_request_rejects_control_symbols():
    """Дефект BUG-2: управляющие символы не должны проходить по протоколу."""
    with pytest.raises(InputDataError):
        protocol.parse_request(protocol.build_request("текст\x00с нулём"))


# ------------------------------------------------------------- parse_response
def _stats_payload(**overrides):
    payload = {
        "chars": 12,
        "chars_no_spaces": 11,
        "words": 2,
        "sentences": 1,
        "unique_words": 2,
        "avg_word_length": 5.0,
        "longest_word": "Привет",
        "top_words": [["привет", 1], ["мир", 1]],
    }
    payload.update(overrides)
    return payload


def test_parse_response_returns_stats():
    message = protocol.build_response(_stats_payload())
    result = protocol.parse_response(message)
    assert result["words"] == 2
    assert result["top_words"] == [("привет", 1), ("мир", 1)]
    assert isinstance(result["avg_word_length"], float)


@pytest.mark.parametrize("field", ["chars", "chars_no_spaces", "words",
                                   "sentences", "unique_words"])
@pytest.mark.parametrize("value", [-1, 1.5, "1", True, None])
def test_parse_response_requires_non_negative_int(field, value):
    message = protocol.build_response(_stats_payload(**{field: value}))
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


@pytest.mark.parametrize("value", ["5.0", True, None, float("nan"),
                                   float("inf")])
def test_parse_response_requires_finite_average(value):
    message = protocol.build_response(
        _stats_payload(avg_word_length=value))
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


@pytest.mark.parametrize("value", [1, None, ["слово"]])
def test_parse_response_requires_longest_word_string(value):
    message = protocol.build_response(_stats_payload(longest_word=value))
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


@pytest.mark.parametrize("value", ["top", 1, None])
def test_parse_response_requires_top_words_list(value):
    message = protocol.build_response(_stats_payload())
    message["payload"]["top_words"] = value
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


def test_parse_response_limits_top_words_length():
    top = [["слово", 1]] * (protocol.MAX_TOP + 1)
    message = protocol.build_response(_stats_payload(top_words=top))
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


@pytest.mark.parametrize("item", [
    ["слово"],
    ["слово", 1, 2],
    [1, 1],
    ["слово", "1"],
    ["слово", -1],
    ["слово", 1.5],
    "слово",
])
def test_parse_response_rejects_bad_top_item(item):
    message = protocol.build_response(_stats_payload(top_words=[item]))
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


def test_parse_response_rejects_frequency_above_word_count():
    """Дефект BUG-3: частота слова не может превышать число слов."""
    message = protocol.build_response(
        _stats_payload(words=1, top_words=[["слово", 5]]))
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


def test_parse_response_accepts_empty_top_words():
    message = protocol.build_response(_stats_payload(top_words=[]))
    assert protocol.parse_response(message)["top_words"] == []


# ------------------------------------------------------- dump_json/load_json
def test_dump_and_load_roundtrip(tmp_path):
    path = tmp_path / "message.json"
    message = protocol.build_request("Привет, мир!")
    protocol.dump_json(str(path), message)
    assert protocol.load_json(str(path)) == message


def test_dump_json_keeps_cyrillic(tmp_path):
    path = tmp_path / "request.json"
    protocol.dump_json(str(path), protocol.build_request("Ёжик"))
    assert "Ёжик" in path.read_text(encoding="utf-8")


def test_dump_json_is_atomic(tmp_path):
    path = tmp_path / "message.json"
    protocol.dump_json(str(path), protocol.build_request("раз"))
    protocol.dump_json(str(path), protocol.build_request("два"))
    assert not (tmp_path / "message.json.tmp").exists()
    assert protocol.load_json(str(path))["payload"]["text"] == "два"


def test_dump_json_rejects_unserializable(tmp_path):
    with pytest.raises(ProtocolError):
        protocol.dump_json(str(tmp_path / "bad.json"), {"value": {1, 2}})


def test_dump_json_rejects_nan(tmp_path):
    with pytest.raises(ProtocolError):
        protocol.dump_json(str(tmp_path / "bad.json"),
                           {"value": float("nan")})


def test_dump_json_reports_unavailable_directory(tmp_path):
    path = tmp_path / "missing" / "message.json"
    with pytest.raises(ModuleUnavailableError):
        protocol.dump_json(str(path), protocol.build_request("текст"))


def test_load_json_missing_file(tmp_path):
    with pytest.raises(ModuleUnavailableError):
        protocol.load_json(str(tmp_path / "absent.json"))


@pytest.mark.parametrize("content", ["{broken", "", "[1, 2"])
def test_load_json_broken_document(tmp_path, content):
    path = tmp_path / "broken.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ProtocolError):
        protocol.load_json(str(path))


def test_load_json_invalid_utf8(tmp_path):
    path = tmp_path / "binary.json"
    path.write_bytes(b"\xff\xfe{\x00")
    with pytest.raises(ProtocolError):
        protocol.load_json(str(path))


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_load_json_rejects_json_constants(tmp_path, constant):
    path = tmp_path / "constant.json"
    path.write_text('{"value": %s}' % constant, encoding="utf-8")
    with pytest.raises(ProtocolError):
        protocol.load_json(str(path))


def test_load_json_unreadable_path(tmp_path):
    directory = tmp_path / "exchange"
    directory.mkdir()
    with pytest.raises(ModuleUnavailableError):
        protocol.load_json(str(directory))


def test_load_json_accepts_plain_numbers(tmp_path):
    path = tmp_path / "plain.json"
    path.write_text(json.dumps({"value": 1.5}), encoding="utf-8")
    assert protocol.load_json(str(path)) == {"value": 1.5}
