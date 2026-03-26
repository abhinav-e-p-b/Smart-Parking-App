"""
detect_batch.py — Run ANPR on every image in a directory.

Deduplication
-------------
For images (static), BoT-SORT's temporal tracking is not applicable —
each image is independent.  Deduplication here means:
  1. Within one image: only the highest-confidence valid plate per
     bounding box cluster is reported.
  2. Across the whole batch: a global seen-plates set prevents the
     same plate string from appearing more than once in the CSV output.
     Toggle with --allow-duplicates if you need the raw repeat counts.

Usage
-----
  python detect_batch.py --source data/raw/
  python detect_batch.py --source data/raw/ --output outputs/batch/ --csv outputs/results.csv
  python detect_batch.py --source data/raw/ --workers 4
  python detect_batch.py --source data/raw/ --allow-duplicates
"""

import argparse
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
from ultralytics import YOLO

from utils.preprocess import preprocess_plate
from utils.ocr import PlateReader
from utils.visualise import draw_detections
from utils.constants import CONF_THRESH, IOU_THRESH, OCR_MIN_CONF

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "models/best.pt"
IMG_EXTS      = {".jpg", ".jpeg", ".png", ".bmp"}


def process_single(
    img_path:   Path,
    detector:   YOLO,
    reader:     PlateReader,
    conf:       float,
    iou:        float,
    output_dir: Path = None,
) -> dict:
    """
    Process one image.

    Returns
    -------
    dict with keys: file, plate, det_conf, n_detections, bbox, error
    """
    img = cv2.imread(str(img_path))
    if img is None:
        return {
            "file": img_path.name, "plate": None,
            "det_conf": None, "n_detections": 0,
            "error": "unreadable_file",
        }

    results = detector(img, conf=conf, iou=iou, verbose=False)
    boxes   = results[0].boxes

    det_list:    list = []
    plate_texts: list = []
    best_plate   = None
    best_conf    = 0.0
    best_bbox    = None

    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        det_conf = float(box.conf[0])
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        processed  = preprocess_plate(crop)
        # OCR_MIN_CONF now imported from constants — same value as video/webcam
        plate_text = reader.read(processed, min_conf=OCR_MIN_CONF)

        det_list.append((x1, y1, x2, y2, det_conf))
        plate_texts.append(plate_text)

        if plate_text and det_conf > best_conf:
            best_plate = plate_text
            best_conf  = det_conf
            best_bbox  = (x1, y1, x2, y2)

    if output_dir is not None and det_list:
        annotated = draw_detections(img, det_list, plate_texts)
        output_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_dir / img_path.name), annotated)

    return {
        "file":          img_path.name,
        "plate":         best_plate,
        "det_conf":      round(best_conf, 3) if best_plate else None,
        "n_detections":  len(boxes),
        "bbox":          best_bbox,
        "error":         None,
    }


def run_batch(
    source:          str,
    model_path:      str   = DEFAULT_MODEL,
    conf:            float = CONF_THRESH,
    iou_thresh:      float = IOU_THRESH,
    output:          str   = None,
    save_csv:        str   = None,
    workers:         int   = 1,
    allow_duplicates:bool  = False,
) -> list:
    """
    Run ANPR over a directory of images.

    Parameters
    ----------
    source           : directory path containing images
    model_path       : path to YOLOv8 weights
    conf             : detection confidence threshold
    iou_thresh       : NMS IoU threshold
    output           : directory for annotated images (optional)
    save_csv         : path for CSV results file (optional)
    workers          : thread-pool size (>1 helps with I/O, not GPU)
    allow_duplicates : if False (default) each unique plate string appears
                       at most once in the results / CSV

    Returns
    -------
    List of result dicts (one per image that returned a plate).
    """
    src    = Path(source)
    images = sorted([p for p in src.iterdir() if p.suffix.lower() in IMG_EXTS])

    if not images:
        print(f"No images found in {src}")
        return []

    print(f"Batch ANPR")
    print(f"  Source      : {src}  ({len(images)} images)")
    print(f"  Model       : {model_path}  conf={conf}  iou={iou_thresh}")
    print(f"  OCR min conf: {OCR_MIN_CONF}")
    print(f"  Workers     : {workers}")
    print(f"  Dedup       : {'off (allow-duplicates)' if allow_duplicates else 'on (unique plates only)'}")

    detector   = YOLO(model_path)
    reader     = PlateReader(gpu=False)
    output_dir = Path(output) if output else None

    seen_plates: set = set()

    t0          = time.perf_counter()
    all_results = []

    def _process_and_dedup(img_path: Path) -> dict:
        result = process_single(img_path, detector, reader, conf, iou_thresh, output_dir)
        plate  = result.get("plate")
        if plate and not allow_duplicates:
            if plate in seen_plates:
                result["plate"]     = None
                result["det_conf"]  = None
                result["note"]      = f"duplicate_of_earlier_{plate}"
            else:
                seen_plates.add(plate)
        return result

    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_process_and_dedup, p): p for p in images
            }
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                all_results.append(result)
                status = result.get("plate") or result.get("note") or result.get("error") or "no plate"
                print(f"  [{i:4d}/{len(images)}]  {result['file']:40s}  {status}")
    else:
        for i, img_path in enumerate(images, 1):
            result = _process_and_dedup(img_path)
            all_results.append(result)
            status = result.get("plate") or result.get("note") or result.get("error") or "no plate"
            print(f"  [{i:4d}/{len(images)}]  {result['file']:40s}  {status}")

    elapsed = time.perf_counter() - t0

    plates_found  = [r for r in all_results if r.get("plate")]
    unique_plates = set(r["plate"] for r in plates_found)
    success_rate  = len(plates_found) / len(all_results) * 100

    print(f"\n{'='*55}")
    print(f"Processed      : {len(all_results)} images in {elapsed:.1f}s")
    print(f"Plates read    : {len(plates_found)}")
    print(f"Unique plates  : {len(unique_plates)}")
    print(f"Success rate   : {success_rate:.1f}%")
    print(f"Avg speed      : {elapsed / len(all_results) * 1000:.0f}ms / image")
    print(f"{'='*55}")

    if save_csv:
        Path(save_csv).parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["file", "plate", "det_conf", "n_detections", "error", "note"]
        with open(save_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in all_results:
                writer.writerow({k: r.get(k, "") for k in fieldnames})
        print(f"CSV saved  : {save_csv}")

    if output:
        print(f"Annotated images : {output_dir}")

    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Indian ANPR — batch inference with cross-image deduplication"
    )
    parser.add_argument("--source",   required=True,
                        help="Directory of input images")
    parser.add_argument("--model",    default=DEFAULT_MODEL)
    parser.add_argument("--conf",     type=float, default=CONF_THRESH)
    parser.add_argument("--iou",      type=float, default=IOU_THRESH)
    parser.add_argument("--output",   default=None,
                        help="Save annotated images here")
    parser.add_argument("--csv",      default=None, dest="save_csv",
                        help="Save results to CSV")
    parser.add_argument("--workers",  type=int, default=1,
                        help="Parallel worker threads (default: 1)")
    parser.add_argument("--allow-duplicates", action="store_true",
                        help="Allow the same plate to appear multiple times in results")
    args = parser.parse_args()

    run_batch(
        source           = args.source,
        model_path       = args.model,
        conf             = args.conf,
        iou_thresh       = args.iou,
        output           = args.output,
        save_csv         = args.save_csv,
        workers          = args.workers,
        allow_duplicates = args.allow_duplicates,
    )
