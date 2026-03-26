"""
test_tracker.py — Unit tests for PlateTracker (BoT-SORT wrapper).

The tests exercise the PUBLIC API only — they do not depend on boxmot
being installed.  When boxmot is absent the tracker automatically falls
back to the IoU-only path, and the same guarantees apply:
  - Confirmation fires exactly once per track
  - Lost event fires when a track disappears
  - Majority-vote consensus picks the correct plate text

Run with:
    python -m pytest test_tracker.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest
from utils.tracker import PlateTracker, iou


# ---------------------------------------------------------------------------
# iou() helper — unchanged, keep existing tests passing
# ---------------------------------------------------------------------------

class TestIou:
    def test_perfect_overlap(self):
        box = (0, 0, 100, 100)
        assert iou(box, box) == pytest.approx(1.0)

    def test_no_overlap(self):
        assert iou((0, 0, 50, 50), (60, 60, 110, 110)) == pytest.approx(0.0)

    def test_partial_overlap(self):
        score = iou((0, 0, 100, 100), (50, 50, 150, 150))
        assert 0.0 < score < 1.0

    def test_contained_box(self):
        score = iou((10, 10, 90, 90), (0, 0, 100, 100))
        assert score > 0.6


# ---------------------------------------------------------------------------
# PlateTracker — tests use the IoU fallback path so boxmot is not required.
# We force the fallback by monkeypatching the import inside __init__.
# ---------------------------------------------------------------------------

def make_tracker(**kwargs) -> PlateTracker:
    """
    Return a PlateTracker that always uses the IoU fallback path,
    regardless of whether boxmot is installed.
    """
    import utils.tracker as tm
    original = tm.__builtins__  # noqa

    # Patch BoTSORT import to raise ImportError → triggers fallback
    import builtins
    real_import = builtins.__import__

    def _mock_import(name, *args, **kwargs_):
        if name == "boxmot":
            raise ImportError("mocked absence")
        return real_import(name, *args, **kwargs_)

    builtins.__import__ = _mock_import
    try:
        tracker = PlateTracker(**kwargs)
    finally:
        builtins.__import__ = real_import

    return tracker


# Helper — build a detection tuple identical to what detect_video.py produces
DET = lambda plate, x1=100, y1=100, x2=300, y2=150: \
      (x1, y1, x2, y2, 0.9, plate)


class TestPlateTrackerConfirmation:
    def test_no_confirmation_before_threshold(self):
        """Track must be seen >= confirm_frames before confirming."""
        tracker = make_tracker(confirm_frames=3)
        events  = tracker.update([DET("KL07BB1234")])
        assert not any(e["type"] == "confirmed" for e in events)

    def test_confirms_after_threshold(self):
        """Exactly one confirmed event after confirm_frames frames."""
        tracker = make_tracker(confirm_frames=3)
        events  = []
        for _ in range(3):
            events += tracker.update([DET("KL07BB1234")])
        confirmed = [e for e in events if e["type"] == "confirmed"]
        assert len(confirmed) == 1
        assert confirmed[0]["plate"] == "KL07BB1234"

    def test_emits_only_once(self):
        """Confirmed fires at most once per track even over many frames."""
        tracker = make_tracker(confirm_frames=2)
        events  = []
        for _ in range(10):
            events += tracker.update([DET("MH12AB3456")])
        confirmed = [e for e in events if e["type"] == "confirmed"]
        assert len(confirmed) == 1

    def test_track_id_in_confirmed_event(self):
        """Confirmed event must carry a track_id field."""
        tracker = make_tracker(confirm_frames=2)
        events  = []
        for _ in range(2):
            events += tracker.update([DET("DL01AB1234")])
        confirmed = [e for e in events if e["type"] == "confirmed"]
        assert len(confirmed) == 1
        assert "track_id" in confirmed[0]

    def test_bbox_in_confirmed_event(self):
        """Confirmed event must carry a bbox tuple."""
        tracker = make_tracker(confirm_frames=2)
        events  = []
        for _ in range(2):
            events += tracker.update([DET("TN09CD5678")])
        confirmed = [e for e in events if e["type"] == "confirmed"]
        assert len(confirmed) == 1
        assert len(confirmed[0]["bbox"]) == 4


class TestPlateTrackerLostEvent:
    def test_lost_event_emitted_after_max_lost(self):
        """Lost event must fire once a confirmed track disappears."""
        tracker = make_tracker(confirm_frames=2, max_lost=2)
        # Confirm the track
        for _ in range(2):
            tracker.update([DET("KL07BB1234")])
        # Stop sending detections → track ages out
        events = []
        for _ in range(3):
            events += tracker.update([])
        lost = [e for e in events if e["type"] == "lost"]
        assert len(lost) == 1

    def test_unconfirmed_track_no_lost_event(self):
        """A track that was never confirmed should not emit a lost event."""
        tracker = make_tracker(confirm_frames=5, max_lost=2)
        tracker.update([DET("KL07BB1234")])   # seen only once
        events = []
        for _ in range(3):
            events += tracker.update([])
        lost = [e for e in events if e["type"] == "lost"]
        assert len(lost) == 0


class TestPlateTrackerMultipleTracks:
    def test_two_spatially_separate_tracks(self):
        """Detections far apart must create two independent tracks."""
        tracker = make_tracker(confirm_frames=3)
        det1 = DET("KL07BB1234", x1=0,   y1=0,   x2=100, y2=50)
        det2 = DET("MH12AB3456", x1=400, y1=0,   x2=500, y2=50)
        tracker.update([det1, det2])
        assert len(tracker.active_tracks) == 2

    def test_two_plates_each_confirmed_once(self):
        """Two different plates must each produce exactly one confirmed event."""
        tracker = make_tracker(confirm_frames=3)
        det1 = DET("KL07BB1234", x1=0,   y1=0,   x2=100, y2=50)
        det2 = DET("MH12AB3456", x1=400, y1=0,   x2=500, y2=50)
        events = []
        for _ in range(3):
            events += tracker.update([det1, det2])
        confirmed = [e for e in events if e["type"] == "confirmed"]
        plates    = {e["plate"] for e in confirmed}
        assert len(confirmed) == 2
        assert "KL07BB1234" in plates
        assert "MH12AB3456" in plates


class TestPlateTrackerVoting:
    def test_majority_vote_wins(self):
        """2-out-of-3 votes for one plate string must win."""
        tracker = make_tracker(confirm_frames=3, vote_thresh=0.5)
        tracker.update([DET("KL07BB1234")])
        tracker.update([DET("KL07BB1234")])
        events = tracker.update([DET("KL07XX9999")])   # one noisy read
        confirmed = [e for e in events if e["type"] == "confirmed"]
        assert len(confirmed) == 1
        assert confirmed[0]["plate"] == "KL07BB1234"

    def test_no_confirmation_without_consensus(self):
        """If no plate reaches vote_thresh, confirmed must not fire."""
        tracker = make_tracker(confirm_frames=3, vote_thresh=0.9)
        tracker.update([DET("KL07BB1234")])
        tracker.update([DET("MH12AB3456")])
        events = tracker.update([DET("TN09CD5678")])
        confirmed = [e for e in events if e["type"] == "confirmed"]
        assert len(confirmed) == 0


class TestPlateTrackerReset:
    def test_reset_clears_emitted(self):
        """After reset, the same plate can be confirmed again."""
        tracker = make_tracker(confirm_frames=2)
        for _ in range(2):
            tracker.update([DET("MH12AB3456")])
        tracker.reset()
        events = []
        for _ in range(2):
            events += tracker.update([DET("MH12AB3456")])
        confirmed = [e for e in events if e["type"] == "confirmed"]
        assert len(confirmed) == 1

    def test_reset_clears_active_tracks(self):
        """After reset, active_tracks must be empty."""
        tracker = make_tracker(confirm_frames=3)
        tracker.update([DET("KL07BB1234")])
        tracker.reset()
        assert len(tracker.active_tracks) == 0


class TestPlateTrackerEdgeCases:
    def test_empty_detections_no_crash(self):
        """Update with no detections must return an empty list, not crash."""
        tracker = make_tracker(confirm_frames=3)
        events  = tracker.update([])
        assert isinstance(events, list)

    def test_none_plate_text_tolerated(self):
        """Detections with plate=None (OCR failed) must not crash."""
        tracker = make_tracker(confirm_frames=3)
        det     = (100, 100, 300, 150, 0.8, None)
        events  = []
        for _ in range(3):
            events += tracker.update([det])
        # No confirmed event because plate text is None
        assert not any(e["type"] == "confirmed" for e in events)

    def test_conf_field_in_confirmed(self):
        """Confirmed event must carry a numeric conf field."""
        tracker = make_tracker(confirm_frames=2)
        events  = []
        for _ in range(2):
            events += tracker.update([DET("GJ01AA1111")])
        confirmed = [e for e in events if e["type"] == "confirmed"]
        assert len(confirmed) == 1
        assert isinstance(confirmed[0]["conf"], float)
