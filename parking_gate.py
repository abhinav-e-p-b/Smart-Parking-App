"""
parking_gate.py — Real-time ANPR for a single parking gate camera.

Run one instance per camera. The --mode flag sets whether this camera
logs ENTRYs or EXITs into the database.

Usage:
  # Entry gate (default webcam)
  python parking_gate.py --mode entry --source 0

  # Exit gate (second webcam)
  python parking_gate.py --mode exit --source 1

  # Entry gate with IP camera
  python parking_gate.py --mode entry --source rtsp://192.168.1.100/stream

  # Run both gates simultaneously (two terminals or use run_both_gates.py)
  python parking_gate.py --mode entry --source 0 &
  python parking_gate.py --mode exit  --source 1

Controls (OpenCV window):
  q — quit
  s — save current annotated frame
  r — reset plate log display
"""

import argparse
import queue
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from config import cfg
from utils.preprocess import preprocess_plate
from utils.ocr import PlateReader
from utils.tracker import PlateTracker
from utils.visualise import draw_detections, draw_occupancy_overlay, add_fps_overlay
from utils.snapshot import save_snapshot
from db import record_entry, record_exit, get_occupancy, lookup_registered_user

# ---------------------------------------------------------------------------
# Per-mode settings
# ---------------------------------------------------------------------------

MODE_LABELS = {
    "entry": cfg.camera.entry_label,
    "exit":  cfg.camera.exit_label,
}

LOG_MAXLEN = 12          # On-screen event log lines


# ---------------------------------------------------------------------------
# Camera reader thread
# ---------------------------------------------------------------------------

class CameraReader(threading.Thread):
    """
    Reads frames from the camera in a background thread.
    Only keeps the LATEST frame — old frames are dropped so the
    display never shows a stale image.
    """
    def __init__(self, source, width, height):
        super().__init__(daemon=True, name="cam-reader")

        # On Windows, MSMF (the default backend) has a known bug where it
        # passes isOpened() and even one test read(), but then throws a
        # cv2.error Mat assertion on subsequent reads when it can't sustain
        # the requested resolution. CAP_DSHOW is more stable for webcams,
        # so we try it FIRST for integer sources, then fall back to default.
        self.cap = None
        backends = [cv2.CAP_DSHOW, None] if isinstance(source, int) else [None]

        for backend in backends:
            try:
                cap = (cv2.VideoCapture(source, backend)
                       if backend is not None
                       else cv2.VideoCapture(source))
                if not cap.isOpened():
                    cap.release()
                    continue

                # Set resolution BEFORE the test read — MSMF negotiates
                # the stream format on the first read, and setting it after
                # can leave the stream in a broken state.
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                # Warm-up: discard a few frames — MSMF needs 2-3 reads
                # before it stabilises (first frame is often corrupt/empty).
                ok = False
                for _ in range(5):
                    ret, frm = cap.read()
                    if ret and frm is not None and frm.size > 0:
                        ok = True
                        break
                    time.sleep(0.05)

                if ok:
                    self.cap = cap
                    label = "CAP_DSHOW" if backend == cv2.CAP_DSHOW else "default (MSMF)"
                    print(f"  [camera] Opened with backend: {label}")
                    break
                cap.release()
            except Exception as e:
                print(f"  [camera] Backend attempt failed: {e}")
                try:
                    cap.release()
                except Exception:
                    pass

        if self.cap is None:
            raise RuntimeError(
                f"Cannot open camera source {source}. "
                "Check that no other app (Teams, Zoom, OBS) is holding the camera."
            )

        self._lock  = threading.Lock()
        self._frame = None
        self._ok    = False
        self._stop  = threading.Event()

    def run(self):
        consecutive_failures = 0
        while not self._stop.is_set():
            try:
                ret, frame = self.cap.read()
            except cv2.error as e:
                # Transient MSMF Mat assertion — skip this frame
                print(f"  [camera] Read error (skipping frame): {e}")
                consecutive_failures += 1
                if consecutive_failures > 20:
                    print("  [camera] Too many consecutive failures — stopping.")
                    break
                time.sleep(0.05)
                continue

            # Validate frame before storing — guards against corrupt Mat
            if ret and frame is not None and frame.size > 0:
                consecutive_failures = 0
                with self._lock:
                    self._ok    = True
                    self._frame = frame
            else:
                consecutive_failures += 1
                time.sleep(0.05)

    def read(self):
        """Return (ok, latest_frame). Non-blocking."""
        with self._lock:
            return self._ok, (self._frame.copy() if self._frame is not None else None)

    def stop(self):
        self._stop.set()
        self.cap.release()


# ---------------------------------------------------------------------------
# Inference worker thread
# ---------------------------------------------------------------------------

class InferenceWorker(threading.Thread):
    """
    Pulls frames from in_q, runs YOLO + OCR + DB, pushes
    annotated results to out_q. Runs entirely in background so
    the main thread (UI) is never blocked.
    """
    def __init__(self, mode, model_path, in_q, out_q, event_log):
        super().__init__(daemon=True, name=f"inference-{mode}")
        self.mode        = mode
        self.model_path  = model_path
        self.in_q        = in_q
        self.out_q       = out_q
        self.event_log   = event_log
        self.cooldown    = defaultdict(int)
        self._stop       = threading.Event()
        self._occ        = {"occupied": 0, "total": cfg.parking.total_slots, "vacant": cfg.parking.total_slots, "pct": 0}
        self._occ_lock   = threading.Lock()
        self.camera_label = MODE_LABELS[mode]

    def get_occ(self):
        with self._occ_lock:
            return dict(self._occ)

    def _refresh_occ(self):
        try:
            occ = get_occupancy()
            with self._occ_lock:
                self._occ = occ
        except Exception as e:
            print(f"  [occ] Warning: {e}")

    def run(self):
        from ultralytics import YOLO
        detector = YOLO(self.model_path)
        reader   = PlateReader(gpu=cfg.ocr.gpu)
        tracker  = PlateTracker(
            confirm_frames=cfg.video.confirm_frames,
            max_lost=cfg.video.max_lost,
        )

        while not self._stop.is_set():
            try:
                frame = self.in_q.get(timeout=0.1)
            except queue.Empty:
                continue

            # ---- YOLO ----
            h_frame, w_frame = frame.shape[:2]
            frame_area = w_frame * h_frame

            yolo_res = detector(frame,
                                conf=cfg.model.conf_thresh,
                                iou=cfg.model.iou_thresh,
                                verbose=False)
            boxes = yolo_res[0].boxes

            raw_dets    = []
            det_list    = []
            plate_texts = []
            statuses    = []
            reg_flags   = []

            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                det_conf = float(box.conf[0])

                if (x2 - x1) * (y2 - y1) / frame_area > cfg.model.whole_image_fraction:
                    continue

                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                # ---- OCR ----
                processed  = preprocess_plate(crop)
                plate_text = reader.read(processed, min_conf=cfg.ocr.min_conf)

                raw_dets.append((x1, y1, x2, y2, det_conf, plate_text))
                det_list.append((x1, y1, x2, y2, det_conf))
                plate_texts.append(plate_text)
                statuses.append(None)
                reg_flags.append(False)

            # ---- Tracker ----
            events = tracker.update(raw_dets)

            for event in events:
                if event["type"] != "confirmed":
                    continue

                plate = event["plate"]
                bbox  = event["bbox"]
                key   = plate

                if self.cooldown[key] > 0:
                    continue

                user     = lookup_registered_user(plate)
                is_reg   = user is not None
                reg_name = user["name"] if user else "unknown"

                snap_path = None
                if cfg.storage.save_local_snapshots:
                    snap_path = save_snapshot(
                        frame, bbox, plate, self.mode,
                        out_dir=cfg.storage.snapshot_dir,
                    )

                if self.mode == "entry":
                    record_entry(plate, self.camera_label, image_url=snap_path)
                    action = "ENTRY"
                else:
                    result = record_exit(plate, self.camera_label, image_url=snap_path)
                    action = "EXIT" if result else "EXIT (no session)"

                self._refresh_occ()
                occ = self.get_occ()

                ts  = datetime.now().strftime("%H:%M:%S")
                reg_tag  = f" [{reg_name}]" if is_reg else ""
                log_line = f"{ts}  {action}  {plate}{reg_tag}  vacant={occ['vacant']}"
                self.event_log.append((log_line, action, is_reg))
                print(f"  {log_line}")

                for i, (x1, y1, x2, y2, _c) in enumerate(det_list):
                    if iou_match(bbox, (x1, y1, x2, y2)):
                        statuses[i]  = self.mode
                        reg_flags[i] = is_reg

                self.cooldown[key] = cfg.video.cooldown_frames

            # Decrement cooldowns
            for k in list(self.cooldown):
                self.cooldown[k] = max(0, self.cooldown[k] - 1)

            self._push_result(frame, det_list, plate_texts, statuses, reg_flags)

    def _push_result(self, frame, det_list, plate_texts, statuses, reg_flags):
        result = (frame, det_list, plate_texts, statuses, reg_flags)
        # Drop oldest result if out_q is full — display always gets freshest frame
        try:
            self.out_q.put_nowait(result)
        except queue.Full:
            try:
                self.out_q.get_nowait()
            except queue.Empty:
                pass
            self.out_q.put_nowait(result)

    def stop(self):
        self._stop.set()


# ---------------------------------------------------------------------------
# Core gate loop
# ---------------------------------------------------------------------------

def run_gate(
    mode: str,
    source,
    model_path: str = str(cfg.model.best_weights),
    show: bool = True,
    headless: bool = False,
):
    assert mode in ("entry", "exit"), "mode must be 'entry' or 'exit'"

    camera_label = MODE_LABELS[mode]
    print(f"\n{'='*55}")
    print(f"  Parking ANPR — {mode.upper()} gate")
    print(f"  Camera : {source}  |  Label : {camera_label}")
    print(f"  Model  : {model_path}")
    print(f"{'='*55}\n")

    event_log = deque(maxlen=LOG_MAXLEN)

    # Queues between threads
    # in_q:  main → worker  (raw frames to process)
    # out_q: worker → main  (annotated results to display)
    in_q  = queue.Queue(maxsize=2)   # small — we drop old frames, not queue them
    out_q = queue.Queue(maxsize=2)

    # ---- Start camera reader ----
    cam = CameraReader(source, cfg.camera.width, cfg.camera.height)
    cam.start()

    # ---- Start inference worker ----
    worker = InferenceWorker(mode, model_path, in_q, out_q, event_log)
    worker.start()

    win_title  = f"Parking ANPR - {mode.upper()} gate"   # plain hyphen avoids cp1252 encoding issue
    fps_timer  = time.perf_counter()
    fps_disp   = 0.0
    frame_id   = 0
    prev_gray  = None
    motion_skip_count = 0

    # Latest annotated result (shown while worker is busy)
    last_annotated = None

    print(f"Running. Press 'q' to quit{', s = save frame' if not headless else ''}.")

    try:
        while True:
            # ------------------------------------------------------------------
            # 1. Grab latest camera frame (always live, never stale)
            # ------------------------------------------------------------------
            ok, frame = cam.read()
            if not ok or frame is None:
                time.sleep(0.01)
                if not headless:
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                continue

            frame_id += 1

            # ------------------------------------------------------------------
            # 2. Motion gate — only controls whether we SEND to worker.
            #    Never affects what is displayed (last_annotated persists).
            #    After 30 skipped frames, force-send anyway so a still plate
            #    sitting in frame is always eventually processed.
            # ------------------------------------------------------------------
            send_to_worker = False
            if frame_id % cfg.video.nth_frame == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray).mean()
                    motion_skip_count = motion_skip_count + 1 if diff < cfg.video.motion_thresh else 0
                    # Send if there's motion OR if plate has been still for >30 processed frames
                    send_to_worker = (diff >= cfg.video.motion_thresh) or (motion_skip_count > 30)
                    if send_to_worker and motion_skip_count > 30:
                        motion_skip_count = 0
                else:
                    send_to_worker = True  # always send first frame
                prev_gray = gray

            if send_to_worker:
                try:
                    in_q.put_nowait(frame.copy())
                except queue.Full:
                    pass   # worker is busy; skip this frame

            # ------------------------------------------------------------------
            # 3. Check if worker produced a new annotated result
            # ------------------------------------------------------------------
            try:
                last_annotated = out_q.get_nowait()
            except queue.Empty:
                pass   # no new result yet — reuse last_annotated

            # ------------------------------------------------------------------
            # 4. FPS
            # ------------------------------------------------------------------
            now       = time.perf_counter()
            fps_disp  = 0.8 * fps_disp + 0.2 * (1.0 / max(now - fps_timer, 1e-6))
            fps_timer = now

            # ------------------------------------------------------------------
            # 5. Render — ALWAYS uses the live camera frame as background.
            #    Bounding boxes from the last inference result are overlaid
            #    on top of the current live frame so video never looks frozen.
            # ------------------------------------------------------------------
            if not headless:
                occ = worker.get_occ()   # cached, no network call
                if last_annotated is not None:
                    (_ann_frame, det_list,
                     plate_texts, statuses, reg_flags) = last_annotated
                    # Draw boxes onto LIVE frame, not the stale ann_frame
                    annotated = draw_detections(frame, det_list, plate_texts,
                                                statuses, reg_flags)
                else:
                    annotated = frame.copy()

                annotated = draw_occupancy_overlay(
                    annotated, occ["occupied"], occ["total"], camera_label)
                annotated = add_fps_overlay(annotated, fps_disp)
                _draw_event_log(annotated, event_log)

                cv2.imshow(win_title, annotated)
                key_press = cv2.waitKey(1) & 0xFF   # ← always reached; window stays responsive
                if key_press == ord("q"):
                    break
                elif key_press == ord("s"):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    Path("outputs").mkdir(exist_ok=True)
                    cv2.imwrite(f"outputs/gate_{mode}_{ts}.jpg", annotated)
                    print(f"  Saved frame: outputs/gate_{mode}_{ts}.jpg")
                elif key_press == ord("r"):
                    event_log.clear()

    finally:
        worker.stop()
        cam.stop()
        cv2.destroyAllWindows()
        print(f"\n{mode.upper()} gate stopped. Processed {frame_id} frames.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iou_match(a: tuple, b: tuple, thresh: float = 0.3) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return False
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter) >= thresh


def _draw_event_log(frame: np.ndarray, event_log: deque):
    bh = frame.shape[0]
    colour_map = {"ENTRY": (0, 220, 0), "EXIT": (0, 140, 255)}
    for idx, (line, action, is_reg) in enumerate(reversed(event_log)):
        y_pos = bh - 30 - idx * 22
        if y_pos < 40:
            break
        colour = colour_map.get(action, (200, 200, 200))
        if is_reg:
            colour = (0, 200, 255)
        cv2.putText(frame, line, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, line, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, colour, 1, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parking ANPR — single gate camera")
    parser.add_argument("--mode",   required=True, choices=["entry", "exit"])
    parser.add_argument("--source", default=0)
    parser.add_argument("--model",  default=str(cfg.model.best_weights))
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    try:
        src = int(args.source)
    except (ValueError, TypeError):
        src = args.source

    run_gate(
        mode=args.mode,
        source=src,
        model_path=args.model,
        show=not args.headless,
        headless=args.headless,
    )
