"""
utils/snapshot.py — Save plate crop snapshots to disk (and optionally Supabase Storage).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


def save_snapshot(
    frame: np.ndarray,
    bbox: tuple,
    plate: str,
    event_type: str,       # 'entry' or 'exit'
    out_dir: Path = Path("outputs/snapshots"),
) -> Optional[str]:
    """
    Crop the plate region from the frame, pad slightly, and save to disk.
    Returns the saved file path, or None on failure.
    """
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        pad = 10
        x1 = max(0, x1 - pad); y1 = max(0, y1 - pad)
        x2 = min(w, x2 + pad); y2 = min(h, y2 + pad)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        name = f"{event_type}_{plate}_{ts}.jpg"
        path = out_dir / name
        cv2.imwrite(str(path), crop)
        return str(path)
    except Exception as e:
        print(f"  [snapshot] Warning: {e}")
        return None
