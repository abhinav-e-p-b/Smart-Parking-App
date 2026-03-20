"""
utils/visualise.py — Drawing helpers for parking ANPR.
"""

import cv2
import numpy as np

# Colour legend
COLOURS = {
    "entry":      (0,  200, 0),     # green — new entry
    "exit":       (0,  120, 255),   # orange — exit
    "registered": (255, 180, 0),    # gold — registered user
    "unknown":    (200, 200, 200),  # gray — unknown plate
    "error":      (0,   0, 200),    # red
}


def _colour_for(status: str, is_registered: bool) -> tuple:
    if is_registered:
        return COLOURS["registered"]
    return COLOURS.get(status, COLOURS["unknown"])


def draw_detections(
    frame: np.ndarray,
    detections: list,
    plate_texts: list = None,
    statuses: list = None,
    registered_flags: list = None,
    font_scale: float = 0.65,
    thickness: int = 2,
) -> np.ndarray:
    """
    Draw bounding boxes with plate text, event status, and registration badge.

    detections: [(x1,y1,x2,y2,conf), ...]
    statuses:   ['entry'|'exit'|None, ...]
    registered_flags: [True|False, ...]
    """
    out            = frame.copy()
    n              = len(detections)
    plate_texts    = plate_texts    or [None] * n
    statuses       = statuses       or [None] * n
    registered_flags = registered_flags or [False] * n

    for (x1, y1, x2, y2, conf), text, status, reg in zip(
            detections, plate_texts, statuses, registered_flags):
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        colour = _colour_for(status, reg)

        # Box
        cv2.rectangle(out, (x1, y1), (x2, y2), colour, thickness)

        # Label
        parts = [text or "???"]
        if status:
            parts.append(f"[{status.upper()}]")
        if reg:
            parts.append("✓REG")
        label = "  ".join(parts) + f"  {conf:.2f}"

        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        label_y = max(y1 - 8, th + 8)
        cv2.rectangle(out,
                      (x1, label_y - th - bl - 4),
                      (x1 + tw + 8, label_y + bl - 2),
                      colour, -1)
        cv2.putText(out, label, (x1 + 4, label_y - bl),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    (255, 255, 255), thickness, cv2.LINE_AA)

    return out


def draw_occupancy_overlay(
    frame: np.ndarray,
    occupied: int,
    total: int,
    camera_label: str = "",
) -> np.ndarray:
    """Overlay occupancy stats in the top-left corner."""
    out    = frame.copy()
    vacant = max(0, total - occupied)
    pct    = occupied / total * 100 if total else 0

    lines = [
        f"Camera : {camera_label}",
        f"Slots  : {occupied}/{total} occupied",
        f"Vacant : {vacant}  ({100-pct:.0f}% free)",
    ]

    bar_colour = (0, 200, 0) if pct < 70 else (0, 140, 255) if pct < 90 else (0, 0, 220)

    y = 28
    for line in lines:
        cv2.putText(out, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(out, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 1, cv2.LINE_AA)
        y += 22

    # Occupancy bar (bottom of frame)
    bh, bw = frame.shape[:2]
    bar_w  = int(bw * pct / 100)
    cv2.rectangle(out, (0, bh - 8), (bw, bh), (60, 60, 60), -1)
    cv2.rectangle(out, (0, bh - 8), (bar_w, bh), bar_colour, -1)

    return out


def add_fps_overlay(frame: np.ndarray, fps: float) -> np.ndarray:
    out  = frame.copy()
    text = f"FPS: {fps:.1f}"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    x = frame.shape[1] - tw - 12
    cv2.putText(out, text, (x, th + 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)
    return out
