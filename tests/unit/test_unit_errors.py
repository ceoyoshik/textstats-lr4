"""Модульные тесты иерархии исключений (errors)."""
import pytest

import errors

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("exception", [
    errors.InputDataError,
    errors.ProtocolError,
    errors.ModuleUnavailableError,
    errors.ModuleTimeoutError,
])
def test_integration_errors_share_base(exception):
    assert issubclass(exception, errors.IntegrationError)


def test_version_conflict_is_protocol_error():
    assert issubclass(errors.VersionConflictError, errors.ProtocolError)


def test_protocol_error_is_not_input_error():
    assert not issubclass(errors.ProtocolError, errors.InputDataError)


def test_exceptions_keep_message():
    error = errors.InputDataError("плохие данные")
    assert str(error) == "плохие данные"
    assert isinstance(error, errors.IntegrationError)


def test_base_error_can_be_caught_generically():
    with pytest.raises(errors.IntegrationError):
        raise errors.ModuleTimeoutError("тайм-аут")
