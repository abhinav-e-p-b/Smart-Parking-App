"""
camera.py - Real-time license plate detection for parking management
Supports webcam and IP camera (RTSP) sources
"""

import cv2
import time
import logging
import argparse
from detection import detect_plate, read_plate
from database import vehicle_inside, mark_entry, mark_exit
from collections import defaultdict, deque

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('parking.log')
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.6
DEBOUNCE_SECONDS = 10
recent_detections: dict[str, float] = {}


def is_debounced(plate: str) -> bool:
    """Return True if this plate was recently processed (within debounce window)."""
    last = recent_detections.get(plate)
    if last and (time.time() - last) < DEBOUNCE_SECONDS:
        return True
    recent_detections[plate] = time.time()
    return False


class TemporalConsistencyFilter:
    """
    A plate detection is only accepted if it appears in
    min_hits out of the last window frames.
    """
    def __init__(self, window: int = 5, min_hits: int = 3):
        self.window = window
        self.min_hits = min_hits
        self.history: dict[str, deque] = defaultdict(lambda: deque(maxlen=window))

    def update(self, plate: str) -> bool:
        """Call with detected plate. Returns True only if temporally stable."""
        self.history[plate].append(1)
        return sum(self.history[plate]) >= self.min_hits

    def miss(self, plates_seen: list[str]):
        """
        Call every frame with all detected plates to register misses
        for plates NOT seen this frame, allowing their scores to decay.
        """
        for plate in list(self.history.keys()):
            if plate not in plates_seen:
                self.history[plate].append(0)


def open_camera(source) -> cv2.VideoCapture:
    """Open webcam index or RTSP URL."""
    if isinstance(source, str) and source.startswith("rtsp"):
        logger.info(f"Connecting to IP camera: {source}")
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    else:
        logger.info(f"Opening webcam index: {source}")
        cap = cv2.VideoCapture(int(source))

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera source: {source}")

    # Prefer 720p for better plate resolution on laptop webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap


def run(camera_mode: str, camera_source):
    """
    Main detection loop.

    Args:
        camera_mode: 'entry' or 'exit'
        camera_source: webcam index (int/str) or RTSP URL
    """
    assert camera_mode in ("entry", "exit"), "camera_mode must be 'entry' or 'exit'"
    cap = open_camera(camera_source)
    tcf = TemporalConsistencyFilter(window=5, min_hits=3)
    logger.info(f"Started [{camera_mode.upper()}] camera. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("Failed to read frame. Retrying in 2s...")
            time.sleep(2)
            cap = open_camera(camera_source)
            continue

        plate_text = None
        confidence = 0.0
        detected_plates_this_frame = []

        # ── 1. Plate Detection ──────────────────────────────────
        plate_crop = detect_plate(frame, n_passes=5, consistency_threshold=0.6)

        if plate_crop is None:
            # FIX: register misses for all tracked plates
            tcf.miss([])
        else:
            # ── 2. OCR Ensemble ──────────────────────────────────
            plate_text, confidence = read_plate(plate_crop, n_variants=5)

            if plate_text:
                detected_plates_this_frame.append(plate_text)

            # FIX: register misses for plates not seen this frame
            tcf.miss(detected_plates_this_frame)

            # ── 3. High-Specificity Gate ──────────────────────────
            if plate_text and confidence >= CONFIDENCE_THRESHOLD:
                if tcf.update(plate_text):
                    if not is_debounced(plate_text):
                        logger.info(
                            f"HIGH-SPECIFICITY detection: "
                            f"{plate_text} (conf={confidence:.2f})"
                        )
                        if camera_mode == "entry":
                            mark_entry(plate_text)
                        else:
                            if vehicle_inside(plate_text):
                                mark_exit(plate_text)
                            else:
                                logger.warning(
                                    f"Exit scan for {plate_text} "
                                    f"but no entry record found"
                                )
                else:
                    tcf.update(plate_text)  # still accumulate hits

        # ── 4. Display ──────────────────────────────────────────
        label = plate_text if plate_text else "Detecting..."
        conf_label = f"  ({confidence:.2f})" if plate_text else ""
        color = (0, 255, 0) if plate_text else (0, 165, 255)

        cv2.putText(
            frame,
            label + conf_label,
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            color,
            3
        )
        cv2.putText(
            frame,
            f"MODE: {camera_mode.upper()}",
            (20, frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.imshow(f"[{camera_mode.upper()}] Parking Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    logger.info("Camera stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parking ANPR Camera")
    parser.add_argument("--mode", choices=["entry", "exit"], required=True,
                        help="Camera mode: entry or exit")
    parser.add_argument("--source", default="0",
                        help="Camera source: webcam index (0,1,...) or RTSP URL")
    args = parser.parse_args()
    run(args.mode, args.source)