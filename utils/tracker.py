"""
utils/tracker.py — BoT-SORT plate tracker (boxmot v10 / v16 compatible).

Fixes applied vs previous version
-----------------------------------
1. boxmot import handles both v10 (BoTSORT) and v16 (BotSort) class names
   so the fallback to IoU-only is never triggered silently by a rename.

2. det_ind bound check fixed: was comparing against len(plate_by_idx)
   (count of dets WITH a plate) instead of len(detections) (total dets).
   This caused valid plate reads to be silently dropped.

3. Lost-track cleanup now discards track_id from _emitted so a plate
   that re-enters the frame after its track is lost will fire "confirmed"
   again correctly (important for webcam / long video sessions).

4. _votes read happens before pop in lost-track loop (ordering fix).

boxmot v16 API notes
---------------------
  - Class   : boxmot.BotSort  (was BoTSORT in v10)
  - device  : must be torch.device, not a plain string
  - Output  : [x1, y1, x2, y2, track_id, conf, cls, det_ind]

Install
-------
    pip install boxmot>=10.0.0

Usage
-----
    tracker = PlateTracker(reid_weights="osnet_x0_25_msmt17.pt", device="cpu")
    events  = tracker.update(raw_dets, frame)   # call once per frame
    for e in events:
        if e["type"] == "confirmed":
            print(e["plate"])   # fires at most once per physical plate
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import inspect
from typing import Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Backward-compat dataclass
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
# Standalone iou() — kept for test_tracker.py backward-compat
# ---------------------------------------------------------------------------

def iou(a: tuple, b: tuple) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    a_ = (ax2 - ax1) * (ay2 - ay1)
    b_ = (bx2 - bx1) * (by2 - by1)
    return inter / (a_ + b_ - inter)


# ---------------------------------------------------------------------------
# PlateTracker
# ---------------------------------------------------------------------------

class PlateTracker:
    """
    BotSort-backed plate tracker with guaranteed single-fire confirmation.

    Parameters
    ----------
    reid_weights : str | None
        Local path to ReID weights (.pt).  None → Kalman-only mode.
    confirm_frames : int
        Track must be seen this many frames before "confirmed" fires.
    max_lost : int
        Frames without a match before the track is pruned.
    vote_thresh : float
        Fraction of votes the winning plate text needs.
    device : str
        "cpu" or "cuda:0".
    track_high_thresh : float
        Must match the YOLO conf threshold used in detect_*.py.
    new_track_thresh : float
        Must be >= track_high_thresh.
    match_thresh : float
        IoU+cosine combined gate.
    """

    def __init__(
        self,
        reid_weights:      Optional[str] = None,
        confirm_frames:    int   = 2,
        max_lost:          int   = 30,
        vote_thresh:       float = 0.40,
        device:            str   = "cpu",
        track_high_thresh: float = 0.25,
        track_low_thresh:  float = 0.05,
        new_track_thresh:  float = 0.25,
        match_thresh:      float = 0.85,
        proximity_thresh:  float = 0.35,
        appearance_thresh: float = 0.30,
    ):
        self.confirm_frames = confirm_frames
        self.vote_thresh    = vote_thresh
        self.max_lost       = max_lost

        self._votes:       Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._seen:        Dict[int, int]            = defaultdict(int)
        self._conf:        Dict[int, float]          = defaultdict(float)
        self._bbox:        Dict[int, tuple]          = {}
        self._emitted:     set                       = set()
        self._prev_active: set                       = set()

        self._use_botsort = False

        try:
            import torch

            # ----------------------------------------------------------------
            # FIX 1: Handle both boxmot v10 (BoTSORT) and v16 (BotSort)
            # ----------------------------------------------------------------
            try:
                from boxmot import BotSort          # boxmot >= v16
            except ImportError:
                from boxmot import BoTSORT as BotSort  # boxmot v10

            torch_device = torch.device(device)
            with_reid    = (reid_weights is not None)

            # Resolve default ReID path only when ReID is actually requested.
            # This avoids init failures on versions that validate the path
            # even when running in Kalman-only mode.
            if with_reid:
                if reid_weights:
                    weights_path = Path(reid_weights)
                else:
                    candidates = [
                        Path("osnet_x0_25_msmt17.pt"),
                        Path("models/osnet_x0_25_msmt17.pt"),
                    ]
                    weights_path = next((p for p in candidates if p.exists()), candidates[0])
            else:
                weights_path = None

            init_sig = inspect.signature(BotSort.__init__)
            init_params = set(init_sig.parameters.keys())

            kwargs = {
                "device":            torch_device if "device" in init_params else device,
                "half":              False,
                "track_high_thresh": track_high_thresh,
                "track_low_thresh":  track_low_thresh,
                "new_track_thresh":  new_track_thresh,
                "track_buffer":      max_lost,
                "match_thresh":      match_thresh,
                "proximity_thresh":  proximity_thresh,
                "appearance_thresh": appearance_thresh,
                "with_reid":         with_reid,
            }
            if "reid_weights" in init_params:
                kwargs["reid_weights"] = weights_path
            elif "model_weights" in init_params:
                kwargs["model_weights"] = weights_path

            kwargs = {k: v for k, v in kwargs.items() if k in init_params}
            self._tracker = BotSort(**kwargs)
            self._use_botsort = True
            reid_mode = "Kalman + ReID" if reid_weights else "Kalman-only"
            print(f"[PlateTracker] BotSort ready — {reid_mode}  device={device}")
            print(f"[PlateTracker] thresholds: "
                  f"high={track_high_thresh}  new={new_track_thresh}  "
                  f"confirm={confirm_frames}frames")

        except ImportError as exc:
            print(
                f"[PlateTracker] WARNING: {exc}\n"
                "  Falling back to IoU-only tracker.\n"
                "  Fix: pip install boxmot>=10.0.0"
            )
            self._init_iou_fallback(proximity_thresh)
        except Exception as exc:
            print(f"[PlateTracker] WARNING: BotSort init failed — {exc}\n"
                  "  Falling back to IoU-only tracker.")
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
        frame:      Optional[np.ndarray] = None,
    ) -> List[dict]:
        """
        Update tracker with this frame's detections.

        Parameters
        ----------
        detections : list of (x1, y1, x2, y2, conf, plate_text_or_None)
        frame      : current BGR frame (required for ReID; None = skip ReID)

        Returns
        -------
        List of {"type": "confirmed"|"lost", "track_id", "plate", "conf", "bbox"}
        """
        if self._use_botsort:
            return self._update_botsort(detections, frame)
        return self._update_iou(detections)

    @property
    def active_tracks(self) -> List[Track]:
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
    # BotSort path
    # ------------------------------------------------------------------

    def _update_botsort(
        self,
        detections: List[Tuple],
        frame:      Optional[np.ndarray],
    ) -> List[dict]:
        events: List[dict] = []

        if frame is None:
            frame = np.zeros((2, 2, 3), dtype=np.uint8)

        # Build detection numpy array and plate-text side-table
        plate_by_idx: Dict[int, str]               = {}
        det_bboxes:   List[Tuple[int,int,int,int]] = []
        total_dets:   int                          = 0  # FIX 2: track real count

        if detections:
            rows = []
            for i, det in enumerate(detections):
                x1, y1, x2, y2, conf, plate = det
                rows.append([float(x1), float(y1), float(x2), float(y2),
                              float(conf), 0.0])
                det_bboxes.append((x1, y1, x2, y2))
                if plate:
                    plate_by_idx[i] = plate
            total_dets = len(rows)  # FIX 2: total detections, not just ones with plates
            dets_np = np.array(rows, dtype=np.float32)
        else:
            dets_np = np.empty((0, 6), dtype=np.float32)

        # Run BotSort — returns [x1, y1, x2, y2, track_id, conf, cls, det_ind]
        tracks = self._tracker.update(dets_np, frame)

        current_ids: set = set()

        if tracks is not None and len(tracks) > 0:
            for row in tracks:
                if isinstance(row, np.ndarray):
                    row = row.tolist()

                if isinstance(row, (list, tuple)):
                    x1, y1, x2, y2 = int(row[0]), int(row[1]), int(row[2]), int(row[3])
                    track_id = int(row[4])
                    conf     = float(row[5]) if len(row) > 5 else 0.0
                    det_idx  = int(row[7]) if len(row) > 7 else -1
                else:
                    # Object-style output compatibility.
                    x1, y1, x2, y2 = map(int, getattr(row, "xyxy", row.tlbr))
                    track_id = int(getattr(row, "id", getattr(row, "track_id")))
                    conf     = float(getattr(row, "conf", 0.0))
                    det_idx  = int(getattr(row, "det_ind", -1))

                current_ids.add(track_id)
                self._seen[track_id]  += 1
                self._conf[track_id]   = max(self._conf[track_id], conf)
                self._bbox[track_id]   = (x1, y1, x2, y2)

                # --- Resolve plate text ---
                plate_text = None

                # ----------------------------------------------------------------
                # FIX 2: Bound check against total_dets, not len(plate_by_idx)
                # Previously: 0 <= det_idx < len(plate_by_idx)
                #   len(plate_by_idx) = number of dets WITH a plate (sparse)
                #   so det_idx=2 was rejected if only dets 0,1 had plates
                # Correctly: bound against total number of detections sent to tracker
                # ----------------------------------------------------------------
                if 0 <= det_idx < total_dets:
                    plate_text = plate_by_idx.get(det_idx)

                # Fallback: det_ind is -1 or out of range (re-activated lost
                # track with no direct match) → find closest detection by IoU
                if plate_text is None and det_bboxes:
                    track_box = (x1, y1, x2, y2)
                    best_iou  = 0.20   # minimum IoU to bother
                    best_idx  = -1
                    for di, db in enumerate(det_bboxes):
                        s = iou(track_box, db)
                        if s > best_iou:
                            best_iou = s
                            best_idx = di
                    if best_idx >= 0:
                        plate_text = plate_by_idx.get(best_idx)

                if plate_text:
                    self._votes[track_id][plate_text] += 1

                # --- Emit confirmed exactly once ---
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

        # ----------------------------------------------------------------
        # FIX 3: Read consensus plate BEFORE popping _votes
        #         Then also discard from _emitted so re-entry can re-confirm
        # ----------------------------------------------------------------
        for tid in self._prev_active - current_ids:
            if tid in self._emitted:
                plate_for_lost = self._consensus_plate(tid)  # read before pop
                events.append({
                    "type":     "lost",
                    "track_id": tid,
                    "plate":    plate_for_lost,
                })
                self._emitted.discard(tid)  # allow re-confirmation if plate returns

            self._seen.pop(tid, None)
            self._conf.pop(tid, None)
            self._bbox.pop(tid, None)
            self._votes.pop(tid, None)   # safe to pop now

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
            if best_track:
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
            if track.lost >= self.max_lost:
                if track.confirmed:
                    events.append({"type": "lost",
                                    "track_id": track.track_id,
                                   "plate": track.plate})
                    self._emitted.discard(track.track_id)  # allow re-confirm
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
