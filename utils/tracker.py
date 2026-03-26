"""
utils/tracker.py — BoT-SORT-based plate tracker (boxmot v16 compatible).

boxmot v16 API vs v10:
  - Class name : boxmot.BotSort  (was BoTSORT)
  - device     : must be torch.device, not a plain string
  - Output     : [x1, y1, x2, y2, track_id, conf, cls, det_ind]  (unchanged)

Deduplication guarantee
------------------------
Each unique track ID emits a "confirmed" event EXACTLY ONCE (stored in
self._emitted).  BotSort's Kalman + ReID ensures one physical plate →
one track ID for its full lifetime, so no plate is ever logged twice.

Graceful fallback
-----------------
If boxmot is absent or fails to load, the tracker falls back to the
original IoU-only greedy matching automatically.  The public API is
identical in both paths.

Install
-------
    pip install boxmot>=16.0.0

ReID weights (optional but recommended)
----------------------------------------
    # Supply a local .pt path; file is auto-downloaded by boxmot if absent.
    tracker = PlateTracker(reid_weights="osnet_x0_25_msmt17.pt")

    # Kalman-only (no ReID, faster on CPU):
    tracker = PlateTracker(reid_weights=None)

Usage
-----
    tracker = PlateTracker(reid_weights="osnet_x0_25_msmt17.pt", device="cpu")

    for frame in video:
        dets   = [(x1,y1,x2,y2,conf,plate_text), ...]
        events = tracker.update(dets, frame)
        for e in events:
            if e["type"] == "confirmed":
                log(e["plate"])   # fires at most once per physical plate
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Dataclass — kept for backward-compat (test_tracker.py uses Track fields)
# ---------------------------------------------------------------------------

@dataclass
class Track:
    track_id:  int
    plate:     Optional[str]
    bbox:      Tuple[int, int, int, int]
    conf:      float
    seen:      int  = 1
    lost:      int  = 0
    confirmed: bool = False
    votes:     dict = field(default_factory=lambda: defaultdict(int))


# ---------------------------------------------------------------------------
# iou() — kept for backward-compat with test_tracker.py
# ---------------------------------------------------------------------------

def iou(a: tuple, b: tuple) -> float:
    """Intersection over Union for two (x1, y1, x2, y2) boxes."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1);  iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2);  iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


# ---------------------------------------------------------------------------
# PlateTracker
# ---------------------------------------------------------------------------

class PlateTracker:
    """
    BotSort-based plate tracker with deduplication (boxmot v16).

    Parameters
    ----------
    reid_weights : str | None
        Path to ReID weights (.pt).  None → Kalman-only (no ReID).
    confirm_frames : int
        Frames a track must be seen before "confirmed" fires. Default 3.
    max_lost : int
        Frames without a match before BotSort prunes the track. Default 30.
    vote_thresh : float
        Vote fraction the winning plate text must reach. Default 0.5.
    device : str
        "cpu" or "cuda" / "cuda:0".
    track_high_thresh : float
        High-conf detection threshold for first association. Default 0.50.
    track_low_thresh : float
        Low-conf detection threshold for second association. Default 0.10.
    new_track_thresh : float
        Min confidence to start a new track. Default 0.60.
    match_thresh : float
        Combined IoU+cosine matching threshold. Default 0.80.
    proximity_thresh : float
        IoU gate for first association. Default 0.50.
    appearance_thresh : float
        Cosine distance gate for ReID. Default 0.25.
    """

    def __init__(
        self,
        reid_weights:      Optional[str] = None,
        confirm_frames:    int   = 3,
        max_lost:          int   = 30,
        vote_thresh:       float = 0.5,
        device:            str   = "cpu",
        track_high_thresh: float = 0.50,
        track_low_thresh:  float = 0.10,
        new_track_thresh:  float = 0.60,
        match_thresh:      float = 0.80,
        proximity_thresh:  float = 0.50,
        appearance_thresh: float = 0.25,
    ):
        self.confirm_frames = confirm_frames
        self.vote_thresh    = vote_thresh

        # Per-track accumulators (keyed by BotSort track_id)
        self._votes:       Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._seen:        Dict[int, int]            = defaultdict(int)
        self._conf:        Dict[int, float]          = defaultdict(float)
        self._bbox:        Dict[int, tuple]          = {}
        self._emitted:     set                       = set()
        self._prev_active: set                       = set()

        self._use_botsort = False

        try:
            import torch
            from boxmot import BotSort          # boxmot v16 class name

            torch_device  = torch.device(device)
            weights_path  = (Path(reid_weights) if reid_weights
                             else Path("osnet_x0_25_msmt17.pt"))

            self._tracker = BotSort(
                reid_weights      = weights_path,
                device            = torch_device,
                half              = False,
                track_high_thresh = track_high_thresh,
                track_low_thresh  = track_low_thresh,
                new_track_thresh  = new_track_thresh,
                track_buffer      = max_lost,
                match_thresh      = match_thresh,
                proximity_thresh  = proximity_thresh,
                appearance_thresh = appearance_thresh,
                with_reid         = (reid_weights is not None),
            )
            self._use_botsort = True
            mode = "Kalman + ReID" if reid_weights else "Kalman-only (no ReID)"
            print(f"[PlateTracker] BotSort loaded — {mode}  device={device}")

        except ImportError as exc:
            print(
                f"[PlateTracker] WARNING: boxmot import failed ({exc})\n"
                "  Falling back to IoU-only tracker.\n"
                "  Fix with:  pip install boxmot>=16.0.0"
            )
            self._init_iou_fallback(proximity_thresh)

        except Exception as exc:
            print(
                f"[PlateTracker] WARNING: BotSort init failed — {exc}\n"
                "  Falling back to IoU-only tracker."
            )
            self._init_iou_fallback(proximity_thresh)

    def _init_iou_fallback(self, iou_thresh: float) -> None:
        self._use_botsort = False
        self._iou_thresh  = iou_thresh
        self._tracks_iou: List[Track] = []
        self._next_id:    int         = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        detections: List[Tuple],
        frame: Optional[np.ndarray] = None,
    ) -> List[dict]:
        """
        Update tracker with detections from the current frame.

        Parameters
        ----------
        detections : list of (x1, y1, x2, y2, conf, plate_text_or_None)
        frame : np.ndarray | None
            Current BGR frame — needed for ReID feature extraction.
            Pass None to skip ReID.

        Returns
        -------
        List of event dicts:
            {"type": "confirmed", "track_id": int, "plate": str,
             "conf": float, "bbox": (x1, y1, x2, y2)}
            {"type": "lost",      "track_id": int, "plate": str}
        """
        if self._use_botsort:
            return self._update_botsort(detections, frame)
        return self._update_iou(detections)

    @property
    def active_tracks(self) -> List[Track]:
        """Currently active Track objects (compatibility shim)."""
        return [
            Track(
                track_id  = tid,
                plate     = self._consensus_plate(tid),
                bbox      = self._bbox.get(tid, (0, 0, 0, 0)),
                conf      = self._conf.get(tid, 0.0),
                seen      = seen,
                confirmed = tid in self._emitted,
            )
            for tid, seen in self._seen.items()
        ]

    def reset(self) -> None:
        """Reset all state (call between unrelated video clips)."""
        if self._use_botsort:
            try:
                self._tracker.reset()
            except AttributeError:
                pass
        else:
            self._tracks_iou.clear()
            self._next_id = 0
        self._votes.clear()
        self._seen.clear()
        self._conf.clear()
        self._bbox.clear()
        self._emitted.clear()
        self._prev_active.clear()

    # ------------------------------------------------------------------
    # BotSort update path
    # ------------------------------------------------------------------

    def _update_botsort(
        self,
        detections: List[Tuple],
        frame: Optional[np.ndarray],
    ) -> List[dict]:
        events: List[dict] = []

        if frame is None:
            frame = np.zeros((2, 2, 3), dtype=np.uint8)

        # Build  [x1, y1, x2, y2, conf, class_id]  detection array
        plate_by_idx: Dict[int, str] = {}
        if detections:
            rows = []
            for i, det in enumerate(detections):
                x1, y1, x2, y2, conf, plate = det
                rows.append([float(x1), float(y1), float(x2), float(y2),
                              float(conf), 0.0])
                if plate:
                    plate_by_idx[i] = plate
            dets_np = np.array(rows, dtype=np.float32)
        else:
            dets_np = np.empty((0, 6), dtype=np.float32)

        # BotSort returns  [x1, y1, x2, y2, track_id, conf, cls, det_ind]
        tracks = self._tracker.update(dets_np, frame)

        current_ids: set = set()

        if tracks is not None and len(tracks) > 0:
            for row in tracks:
                x1, y1, x2, y2 = int(row[0]), int(row[1]), int(row[2]), int(row[3])
                track_id = int(row[4])
                conf     = float(row[5])
                det_idx  = int(row[7]) if len(row) > 7 else -1

                current_ids.add(track_id)
                self._seen[track_id]  += 1
                self._conf[track_id]   = max(self._conf[track_id], conf)
                self._bbox[track_id]   = (x1, y1, x2, y2)

                if det_idx >= 0 and det_idx in plate_by_idx:
                    self._votes[track_id][plate_by_idx[det_idx]] += 1

                # Fire "confirmed" exactly once per track
                if (self._seen[track_id] >= self.confirm_frames
                        and track_id not in self._emitted):
                    best = self._consensus_plate(track_id)
                    if best:
                        events.append({
                            "type":     "confirmed",
                            "track_id": track_id,
                            "plate":    best,
                            "conf":     self._conf[track_id],
                            "bbox":     self._bbox[track_id],
                        })
                        self._emitted.add(track_id)

        # Detect vanished tracks → "lost"
        for tid in self._prev_active - current_ids:
            if tid in self._emitted:
                events.append({
                    "type":     "lost",
                    "track_id": tid,
                    "plate":    self._consensus_plate(tid),
                })
            self._seen.pop(tid, None)
            self._conf.pop(tid, None)
            self._bbox.pop(tid, None)
            self._votes.pop(tid, None)

        self._prev_active = current_ids
        return events

    # ------------------------------------------------------------------
    # IoU-only fallback
    # ------------------------------------------------------------------

    def _update_iou(self, detections: List[Tuple]) -> List[dict]:
        events:         List[dict] = []
        matched_tracks: set        = set()
        matched_dets:   set        = set()

        for det_i, det in enumerate(detections):
            x1, y1, x2, y2, conf, plate = det
            best_score = self._iou_thresh
            best_track = None

            for track in self._tracks_iou:
                if track.track_id in matched_tracks:
                    continue
                score = iou((x1, y1, x2, y2), track.bbox)
                if score > best_score:
                    best_score = score
                    best_track = track

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
            self._tracks_iou.append(t)
            self._next_id += 1

        for track in self._tracks_iou:
            if track.track_id not in matched_tracks:
                track.lost += 1

        for track in self._tracks_iou:
            if (track.seen >= self.confirm_frames
                    and track.track_id not in self._emitted):
                best = self._consensus_plate_iou(track)
                if best:
                    events.append({
                        "type":     "confirmed",
                        "track_id": track.track_id,
                        "plate":    best,
                        "conf":     track.conf,
                        "bbox":     track.bbox,
                    })
                    track.confirmed = True
                    self._emitted.add(track.track_id)

        alive = []
        for track in self._tracks_iou:
            if track.lost >= 10:
                if track.confirmed:
                    events.append({"type": "lost",
                                   "track_id": track.track_id,
                                   "plate": track.plate})
            else:
                alive.append(track)
        self._tracks_iou = alive
        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _consensus_plate(self, track_id: int) -> Optional[str]:
        votes = self._votes.get(track_id, {})
        if not votes:
            return None
        total = sum(votes.values())
        best  = max(votes, key=votes.get)
        return best if votes[best] / total >= self.vote_thresh else None

    def _consensus_plate_iou(self, track: Track) -> Optional[str]:
        if not track.votes:
            return None
        total = sum(track.votes.values())
        best  = max(track.votes, key=track.votes.get)
        return best if track.votes[best] / total >= self.vote_thresh else None
