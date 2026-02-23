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
CONFIDENCE_THRESHOLD = 0.6      # Minimum OCR confidence to accept a reading
DEBOUNCE_SECONDS = 10           # Ignore same plate within this window
recent_detections: dict[str, float] = {}  # plate -> last_seen timestamp


def is_debounced(plate: str) -> bool:
    """Return True if this plate was recently processed (within debounce window)."""
    last = recent_detections.get(plate)
    if last and (time.time() - last) < DEBOUNCE_SECONDS:
        return True
    recent_detections[plate] = time.time()
    return False


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
    logger.info(f"Started [{camera_mode.upper()}] camera. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("Failed to read frame. Retrying in 2s...")
            time.sleep(2)
            cap = open_camera(camera_source)
            continue

        # ── 1. Detect plate region ──────────────────────────────────────────
        plate_crop = detect_plate(frame)
        if plate_crop is None:
            cv2.imshow(f"[{camera_mode.upper()}] Parking Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        # ── 2. OCR ──────────────────────────────────────────────────────────
        plate_text, confidence = read_plate(plate_crop)

        if plate_text is None:
            logger.debug("OCR returned no result")
        elif confidence < CONFIDENCE_THRESHOLD:
            logger.debug(f"Low confidence {confidence:.2f} for '{plate_text}' — skipped")
        elif is_debounced(plate_text):
            logger.debug(f"Debounced: {plate_text}")
        else:
            # ── 3. Log entry / exit ─────────────────────────────────────────
            logger.info(f"Detected: {plate_text} (conf={confidence:.2f})")
            if camera_mode == "entry":
                mark_entry(plate_text)
            else:
                if vehicle_inside(plate_text):
                    mark_exit(plate_text)
                else:
                    logger.warning(f"Exit scan for {plate_text} but no entry record found")

        # ── 4. Display ───────────────────────────────────────────────────────
        label = plate_text or "Detecting..."
        cv2.putText(frame, label, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
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
