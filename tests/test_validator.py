import pytest

from app.validator import ValidationError, validate


def test_accepts_minimal_valid_line():
    validate("[happy] Sahi jawab!")


def test_rejects_missing_tag():
    with pytest.raises(ValidationError):
        validate("Sahi jawab!")


def test_rejects_devanagari():
    with pytest.raises(ValidationError):
        validate("[neutral] सही जवाब")


def test_rejects_too_many_sentences():
    with pytest.raises(ValidationError):
        validate("[neutral] A. B. C. D.")


def test_rejects_extra_bracketed_token():
    with pytest.raises(ValidationError):
        validate("[happy] Wah! [bell] Try again.")
