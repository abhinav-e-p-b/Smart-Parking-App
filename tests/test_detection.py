"""
tests/test_detection.py - Unit tests for detection.py

Run with:
    pytest tests/test_detection.py -v
"""

import numpy as np
import pytest
import sys
import os

# Allow importing from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from detection import _complies_format, _format_plate, CHAR_TO_INT, INT_TO_CHAR


# ─────────────────────────────────────────────
# _complies_format() tests
# ─────────────────────────────────────────────


# In tests/test_detection.py — replace the TestCompliesFormat class

class TestCompliesFormat:

    def test_valid_indian_plate(self):
        assert _complies_format("MH12AB1234") is True

    def test_valid_with_substitutable_chars(self):
        assert _complies_format("MH12AB123O") is True   # O→0 at digit position
        assert _complies_format("OH12AB1234") is True   # O is valid letter

    def test_too_short(self):
        assert _complies_format("MH12AB123") is False   # 9 chars

    def test_too_long(self):
        assert _complies_format("MH12AB12345") is False  # 11 chars

    def test_empty_string(self):
        assert _complies_format("") is False

    def test_digit_in_letter_position(self):
        assert _complies_format("1H12AB1234") is False   # pos 0 must be letter

    def test_letter_in_digit_position_not_substitutable(self):
        assert _complies_format("MHZ2AB1234") is False   # Z not in CHAR_TO_INT

    def test_lowercase_rejected(self):
        assert _complies_format("mh12ab1234") is False

    def test_special_characters(self):
        assert _complies_format("MH12AB!234") is False

# In TestFormatPlate — update to 10-char plates
class TestFormatPlate:

    def test_no_substitution_needed(self):
        assert _format_plate("MH12AB1234") == "MH12AB1234"

    def test_O_at_digit_position_becomes_0(self):
        result = _format_plate("MH12AB123O")   # pos 9 is digit position
        assert result[9] == "0"

    def test_0_at_letter_position_becomes_O(self):
        result = _format_plate("0H12AB1234")   # pos 0 is letter position
        assert result[0] == "O"

    def test_output_length_unchanged(self):
        assert len(_format_plate("MH12AB1234")) == 10
# ─────────────────────────────────────────────
# _format_plate() tests
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
# Mapping dict sanity checks
# ─────────────────────────────────────────────

class TestMappingDicts:

    def test_char_to_int_values_are_digits(self):
        for k, v in CHAR_TO_INT.items():
            assert v.isdigit(), f"CHAR_TO_INT[{k!r}] = {v!r} is not a digit"

    def test_int_to_char_values_are_letters(self):
        for k, v in INT_TO_CHAR.items():
            assert v.isalpha(), f"INT_TO_CHAR[{k!r}] = {v!r} is not a letter"

    def test_mappings_are_consistent(self):
        """CHAR_TO_INT and INT_TO_CHAR should be inverses of each other."""
        for char, digit in CHAR_TO_INT.items():
            assert INT_TO_CHAR.get(digit) == char, (
                f"Inconsistency: CHAR_TO_INT[{char!r}]={digit!r} "
                f"but INT_TO_CHAR[{digit!r}]={INT_TO_CHAR.get(digit)!r}"
            )


# ─────────────────────────────────────────────
# Placeholder: detect_plate / read_plate
# (These require a real camera frame and model;
#  tested via integration tests, not unit tests)
# ─────────────────────────────────────────────

class TestDetectPlateContract:

    def test_returns_none_on_blank_frame(self):
        """
        detect_plate() should return None when no plate is visible.
        This test uses a blank black frame — the model should find nothing.

        NOTE: Skipped if model file is absent (CI environments).
        """
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "license_plate_detector.pt")
        if not os.path.exists(model_path):
            pytest.skip("license_plate_detector.pt not found — skipping model test")

        from detection import detect_plate
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detect_plate(blank)
        assert result is None

    def test_read_plate_returns_tuple(self):
        """
        read_plate() must always return a 2-tuple even on garbage input.
        """
        from detection import read_plate
        blank = np.zeros((30, 100), dtype=np.uint8)
        result = read_plate(blank)
        assert isinstance(result, tuple)
        assert len(result) == 2
