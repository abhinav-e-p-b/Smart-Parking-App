"""
utils/tracker.py — IoU-based multi-object plate tracker for video streams.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Track:
    track_id: int
    plate: Optional[str]
    bbox: Tuple[int, int, int, int]
    conf: float
    seen: int = 1
    lost: int = 0
    confirmed: bool = False
    votes: dict = field(default_factory=lambda: defaultdict(int))


def iou(a: tuple, b: tuple) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


class PlateTracker:
    def __init__(self, iou_thresh=0.35, confirm_frames=3, max_lost=10, vote_thresh=0.5):
        self.iou_thresh     = iou_thresh
        self.confirm_frames = confirm_frames
        self.max_lost       = max_lost
        self.vote_thresh    = vote_thresh
        self._tracks: List[Track] = []
        self._next_id = 0
        self._emitted: set = set()

    def update(self, detections: List[Tuple]) -> List[dict]:
        events = []
        matched_tracks = set()
        matched_dets   = set()

        for det_i, det in enumerate(detections):
            x1, y1, x2, y2, conf, plate = det
            best_iou, best_track = self.iou_thresh, None
            for track in self._tracks:
                if track.track_id in matched_tracks:
                    continue
                score = iou((x1, y1, x2, y2), track.bbox)
                if score > best_iou:
                    best_iou, best_track = score, track
            if best_track is not None:
                best_track.bbox = (x1, y1, x2, y2)
                best_track.conf = max(best_track.conf, conf)
                best_track.lost = 0
                best_track.seen += 1
                if plate:
                    best_track.votes[plate] += 1
                matched_tracks.add(best_track.track_id)
                matched_dets.add(det_i)

        for det_i, det in enumerate(detections):
            if det_i in matched_dets:
                continue
            x1, y1, x2, y2, conf, plate = det
            t = Track(track_id=self._next_id, plate=plate,
                      bbox=(x1, y1, x2, y2), conf=conf)
            if plate:
                t.votes[plate] += 1
            self._tracks.append(t)
            self._next_id += 1

        for track in self._tracks:
            if track.track_id not in matched_tracks:
                track.lost += 1

        for track in self._tracks:
            if track.seen >= self.confirm_frames and track.track_id not in self._emitted:
                best_plate = self._consensus(track)
                if best_plate:
                    events.append({"type": "confirmed", "track_id": track.track_id,
                                   "plate": best_plate, "conf": track.conf, "bbox": track.bbox})
                    track.plate = best_plate
                    track.confirmed = True
                    self._emitted.add(track.track_id)

        alive = []
        for track in self._tracks:
            if track.lost >= self.max_lost:
                if track.confirmed:
                    events.append({"type": "lost", "track_id": track.track_id, "plate": track.plate})
            else:
                alive.append(track)
        self._tracks = alive
        return events

    def _consensus(self, track: Track) -> Optional[str]:
        if not track.votes:
            return None
        total = sum(track.votes.values())
        best  = max(track.votes, key=track.votes.get)
        return best if track.votes[best] / total >= self.vote_thresh else None

    @property
    def active_tracks(self):
        return [t for t in self._tracks if t.lost == 0]

    def reset(self):
        self._tracks.clear()
        self._emitted.clear()
        self._next_id = 0
