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

class TestCompliesFormat:

    def test_valid_uk_plate(self):
        """Standard UK-style 7-char plate: 2 letters, 2 digits, 3 letters."""
        assert _complies_format("AB12CDE") is True

    def test_valid_with_substitutable_chars(self):
        """Chars that map via CHAR_TO_INT / INT_TO_CHAR should still pass."""
        # '0' at position 2 is a valid digit
        assert _complies_format("AB02CDE") is True
        # 'O' at position 0 maps to '0' — but position 0 expects a letter, so O is valid as a letter
        assert _complies_format("OB12CDE") is True

    def test_too_short(self):
        assert _complies_format("AB1CDE") is False

    def test_too_long(self):
        assert _complies_format("AB12CDEF") is False

    def test_empty_string(self):
        assert _complies_format("") is False

    def test_digit_in_letter_position(self):
        """Position 0 and 1 must be letters or letter-substitutable chars."""
        assert _complies_format("1B12CDE") is False

    def test_letter_in_digit_position_not_substitutable(self):
        """Position 2–3 must be digits or CHAR_TO_INT keys."""
        # 'Z' is not in CHAR_TO_INT, so position 2 = 'Z' is invalid
        assert _complies_format("ABZZCDE") is False

    def test_substitutable_char_in_digit_position(self):
        """'O' maps to '0' so it's valid in a digit position."""
        assert _complies_format("ABOO CDE".replace(" ", "")) is False  # 7 chars check first
        assert _complies_format("ABOO" + "CDE") is False  # length 7 but 'O' at pos 2 OK, check pos 3 'O' OK
        # Actually ABOOCDE = A B O O C D E — positions 2,3 are 'O' which IS in CHAR_TO_INT
        assert _complies_format("ABOOCDE") is True

    def test_lowercase_rejected(self):
        """Input is expected to be uppercased before this call."""
        assert _complies_format("ab12cde") is False

    def test_special_characters(self):
        assert _complies_format("AB!2CDE") is False

    def test_spaces_rejected(self):
        assert _complies_format("AB 2CDE") is False


# ─────────────────────────────────────────────
# _format_plate() tests
# ─────────────────────────────────────────────

class TestFormatPlate:

    def test_no_substitution_needed(self):
        """A clean plate passes through unchanged."""
        assert _format_plate("AB12CDE") == "AB12CDE"

    def test_letter_O_at_digit_position(self):
        """'O' at position 2 or 3 should become '0'."""
        result = _format_plate("ABO2CDE")
        assert result[2] == "0"

    def test_digit_0_at_letter_position(self):
        """'0' at position 0, 1, 4, 5, 6 should become 'O'."""
        result = _format_plate("0B12CDE")
        assert result[0] == "O"

    def test_I_becomes_1_at_digit_position(self):
        result = _format_plate("ABI2CDE")
        assert result[2] == "1"

    def test_1_becomes_I_at_letter_position(self):
        result = _format_plate("1B12CDE")
        assert result[0] == "I"

    def test_S_becomes_5_at_digit_position(self):
        result = _format_plate("ABS2CDE")
        assert result[2] == "5"

    def test_5_becomes_S_at_letter_position(self):
        result = _format_plate("5B12CDE")
        assert result[0] == "S"

    def test_full_correction(self):
        """Simulate a realistic OCR error: 'O' where digit expected."""
        raw = "ABOOCDE"   # positions 2,3 are 'O' instead of '0'
        result = _format_plate(raw)
        assert result[2] == "0"
        assert result[3] == "0"
        assert result == "AB00CDE"

    def test_output_length_unchanged(self):
        """Substitution must not change string length."""
        plate = "OB1OCDE"
        assert len(_format_plate(plate)) == 7


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
