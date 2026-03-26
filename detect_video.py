"""
detect_video.py — Run the ANPR pipeline on a video file.

Architecture
------------
Three-gate efficiency system keeps CPU usage low on long videos:
  Gate 1 — Nth-frame sampler  : skip frames entirely
  Gate 2 — Motion check       : skip static scenes (parked camera)
  Gate 3 — YOLO + OCR + track : only on frames that pass both gates

Deduplication via BoT-SORT
---------------------------
The old cooldown-counter approach is replaced by a PlateTracker backed
by BoT-SORT.  Each physical plate receives one stable track ID for its
entire lifetime in the video (Kalman filter predicts through occlusion,
ReID re-identifies after re-entry).  A "confirmed" event fires EXACTLY
ONCE per track ID, so the same plate is never written to the CSV twice
regardless of how many frames it appears in.

Usage
-----
  python detect_video.py --source video.mp4
  python detect_video.py --source video.mp4 --output outputs/result.mp4 --nth 3
  python detect_video.py --source video.mp4 --show
  python detect_video.py --source video.mp4 --reid osnet_x0_25_msmt17.pt
"""

import argparse
import csv
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from utils.preprocess import preprocess_plate
from utils.ocr import PlateReader
from utils.tracker import PlateTracker
from utils.visualise import draw_detections, add_fps_overlay

# ---------------------------------------------------------------------------
# Defaults (override on the command line or via config.py)
# ---------------------------------------------------------------------------
DEFAULT_MODEL    = "models/best.pt"
CONF_THRESH      = 0.50
IOU_THRESH       = 0.45
OCR_MIN_CONF     = 0.30
NTH_FRAME        = 3      # process every Nth frame
MOTION_THRESH    = 15.0   # mean abs-diff threshold to consider a frame "moving"
CONFIRM_FRAMES   = 3      # frames a track must be seen before confirming
MAX_LOST         = 30     # frames without match before BoT-SORT prunes track


def process_video(
    source:        str,
    model_path:    str   = DEFAULT_MODEL,
    conf:          float = CONF_THRESH,
    iou:           float = IOU_THRESH,
    nth:           int   = NTH_FRAME,
    motion_thresh: float = MOTION_THRESH,
    reid_weights:  str   = None,
    show:          bool  = False,
    output:        str   = None,
    save_csv:      str   = None,
) -> list:
    """
    Run ANPR on a video file.

    Returns
    -------
    List of confirmed-plate dicts:
        [{"frame", "timestamp_s", "plate", "det_conf", "bbox"}, ...]
    """

    # ------------------------------------------------------------------
    # Open video
    # ------------------------------------------------------------------
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {source}")

    fps_in       = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video      : {source}")
    print(f"Resolution : {width}×{height}  |  FPS: {fps_in:.1f}  |  Frames: {total_frames}")
    print(f"Mode       : nth={nth}  motion_thresh={motion_thresh}  confirm={CONFIRM_FRAMES}")

    # ------------------------------------------------------------------
    # Video writer
    # ------------------------------------------------------------------
    writer = None
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output, fourcc, fps_in, (width, height))

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------
    detector = YOLO(model_path)
    reader   = PlateReader(gpu=False)   # set gpu=True if CUDA available

    # ------------------------------------------------------------------
    # BoT-SORT tracker
    # ------------------------------------------------------------------
    tracker = PlateTracker(
        reid_weights   = reid_weights,
        confirm_frames = CONFIRM_FRAMES,
        max_lost       = MAX_LOST,
        vote_thresh    = 0.5,
        device         = "cpu",
    )

    # ------------------------------------------------------------------
    # CSV writer
    # ------------------------------------------------------------------
    csv_file   = None
    csv_writer = None
    if save_csv:
        Path(save_csv).parent.mkdir(parents=True, exist_ok=True)
        csv_file   = open(save_csv, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            "frame", "timestamp_s", "plate", "det_conf",
            "x1", "y1", "x2", "y2"
        ])

    # ------------------------------------------------------------------
    # Processing state
    # ------------------------------------------------------------------
    frame_id      = 0
    prev_gray     = None
    all_confirmed = []       # confirmed plate records written to CSV / returned
    fps_display   = 0.0
    fps_timer     = time.perf_counter()

    # Per-frame annotation state (used only for drawing, not dedup)
    last_det_list    = []
    last_plate_texts = []

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_id += 1

            # ----------------------------------------------------------------
            # Gate 1 — Nth-frame sampler
            # ----------------------------------------------------------------
            if frame_id % nth != 0:
                if writer:
                    writer.write(frame)
                continue

            # ----------------------------------------------------------------
            # Gate 2 — Motion check
            # ----------------------------------------------------------------
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray).mean()
                if diff < motion_thresh:
                    prev_gray = gray
                    if writer:
                        writer.write(frame)
                    continue
            prev_gray = gray

            # ----------------------------------------------------------------
            # Gate 3 — YOLO detection + OCR
            # ----------------------------------------------------------------
            yolo_results = detector(frame, conf=conf, iou=iou, verbose=False)
            boxes        = yolo_results[0].boxes

            # Collect raw detections for the tracker
            raw_dets:    list = []
            det_list:    list = []    # for draw_detections()
            plate_texts: list = []    # for draw_detections()

            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                det_conf = float(box.conf[0])
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                processed  = preprocess_plate(crop)
                plate_text = reader.read(processed, min_conf=OCR_MIN_CONF)

                raw_dets.append((x1, y1, x2, y2, det_conf, plate_text))
                det_list.append((x1, y1, x2, y2, det_conf))
                plate_texts.append(plate_text)

            # ----------------------------------------------------------------
            # BoT-SORT update
            # Pass the full frame so BoT-SORT can extract ReID features.
            # Events fire at most once per unique physical plate.
            # ----------------------------------------------------------------
            events = tracker.update(raw_dets, frame)

            for event in events:
                if event["type"] == "confirmed":
                    plate_text = event["plate"]
                    timestamp  = round(frame_id / fps_in, 2)
                    x1, y1, x2, y2 = event["bbox"]

                    record = {
                        "frame":       frame_id,
                        "timestamp_s": timestamp,
                        "plate":       plate_text,
                        "det_conf":    round(event["conf"], 3),
                        "bbox":        (x1, y1, x2, y2),
                    }
                    all_confirmed.append(record)

                    print(
                        f"  [frame {frame_id:06d}]  t={timestamp:.1f}s  "
                        f"plate={plate_text}  conf={event['conf']:.2f}  "
                        f"track_id={event['track_id']}"
                    )

                    if csv_writer:
                        csv_writer.writerow([
                            frame_id, timestamp, plate_text,
                            round(event["conf"], 3),
                            x1, y1, x2, y2,
                        ])

            # ----------------------------------------------------------------
            # FPS
            # ----------------------------------------------------------------
            now         = time.perf_counter()
            fps_display = 1.0 / max(now - fps_timer, 1e-6)
            fps_timer   = now

            # ----------------------------------------------------------------
            # Annotate + write output
            # ----------------------------------------------------------------
            annotated = draw_detections(frame, det_list, plate_texts)
            annotated = add_fps_overlay(annotated, fps_display)

            if writer:
                writer.write(annotated)

            if show:
                cv2.imshow("Indian ANPR — Video", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("User quit.")
                    break

    finally:
        cap.release()
        if writer:
            writer.release()
        if csv_file:
            csv_file.close()
        cv2.destroyAllWindows()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*55}")
    print(f"Processed  : {frame_id} frames")
    print(f"Unique plates confirmed : {len(all_confirmed)}")
    if output:
        print(f"Output video : {output}")
    if save_csv:
        print(f"CSV log      : {save_csv}")
    print(f"{'='*55}")

    return all_confirmed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indian ANPR — video")
    parser.add_argument("--source",       required=True,
                        help="Path to input video file")
    parser.add_argument("--model",        default=DEFAULT_MODEL)
    parser.add_argument("--conf",         type=float, default=CONF_THRESH)
    parser.add_argument("--iou",          type=float, default=IOU_THRESH)
    parser.add_argument("--nth",          type=int,   default=NTH_FRAME,
                        help="Process every Nth frame (default: 3)")
    parser.add_argument("--motion-thresh",type=float, default=MOTION_THRESH)
    parser.add_argument("--reid",         default=None, dest="reid_weights",
                        help="Path to ReID weights (e.g. osnet_x0_25_msmt17.pt). "
                             "Omit for Kalman-only mode.")
    parser.add_argument("--show",         action="store_true",
                        help="Display annotated video in a window")
    parser.add_argument("--output",       default=None,
                        help="Save annotated video here")
    parser.add_argument("--csv",          default=None, dest="save_csv",
                        help="Save confirmed plate log as CSV")
    args = parser.parse_args()

    process_video(
        source        = args.source,
        model_path    = args.model,
        conf          = args.conf,
        iou           = args.iou,
        nth           = args.nth,
        motion_thresh = args.motion_thresh,
        reid_weights  = args.reid_weights,
        show          = args.show,
        output        = args.output,
        save_csv      = args.save_csv,
    )
