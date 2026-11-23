"""Модульные тесты сопоставления данных (mapping)."""
import dataclasses

import pytest

import mapping
import protocol
from errors import ProtocolError

pytestmark = pytest.mark.unit

STATS = mapping.TextStats(chars=12, chars_no_spaces=11, words=2,
                          sentences=1, unique_words=2,
                          avg_word_length=5.0, longest_word="Привет",
                          top_words=(("привет", 1), ("мир", 1)))


def test_text_stats_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        STATS.words = 3


def test_processing_to_response_maps_fields():
    message = mapping.processing_to_response(STATS)
    assert message["type"] == protocol.MSG_RESPONSE
    payload = message["payload"]
    assert payload["chars"] == 12
    assert payload["longest_word"] == "Привет"
    assert payload["top_words"] == [["привет", 1], ["мир", 1]]


def test_response_to_stats_returns_dataclass():
    message = mapping.processing_to_response(STATS)
    restored = mapping.response_to_stats(message)
    assert restored == STATS
    assert isinstance(restored.top_words, tuple)


def test_response_to_stats_propagates_protocol_error():
    with pytest.raises(ProtocolError):
        mapping.response_to_stats({"type": "bad"})


def test_text_stats_equality():
    assert mapping.TextStats(**dataclasses.asdict(STATS)) == STATS
