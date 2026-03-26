"""
debug_ocr.py — Show exactly what EasyOCR reads before and after validation.

Usage
-----
  python debug_ocr.py --source crop.jpg
  python debug_ocr.py --source video.mp4 --video --max-crops 10
  python debug_ocr.py --source video.mp4 --video --save-crops outputs/crops/
"""

import argparse
import re
import sys
from pathlib import Path

import cv2
import easyocr
import numpy as np

VALID_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD",
    "DL", "DN", "GA", "GJ", "HR", "HP", "JK", "JH",
    "KA", "KL", "LA", "LD", "MP", "MH", "MN", "ML",
    "MZ", "NL", "OD", "PY", "PB", "RJ", "SK", "TN",
    "TS", "TR", "UP", "UK", "WB",
}
STANDARD_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$")
BH_PATTERN       = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")
LETTER_POS       = {0, 1, 4, 5}
DIGIT_POS        = {2, 3, 6, 7, 8, 9}
LETTER_FIXES     = {"0": "O", "1": "I", "l": "I", "8": "B", "5": "S"}
DIGIT_FIXES      = {"O": "0", "I": "1", "l": "1", "B": "8", "S": "5"}


def fix_characters(raw):
    chars = list(raw)
    for i, ch in enumerate(chars):
        if i in LETTER_POS and ch in LETTER_FIXES:
            chars[i] = LETTER_FIXES[ch]
        elif i in DIGIT_POS and ch in DIGIT_FIXES:
            chars[i] = DIGIT_FIXES[ch]
    return "".join(chars)


def normalise_raw(raw):
    return raw.upper().replace(" ", "").replace("-", "").replace(".", "")


def validate_plate(plate):
    if len(plate) < 8:
        return None, f"too short ({len(plate)} chars, need >= 8)"
    if BH_PATTERN.match(plate):
        return plate, "BH series match"
    if plate[:2] not in VALID_STATES:
        return None, f"invalid state code '{plate[:2]}'"
    if STANDARD_PATTERN.match(plate):
        return plate, "standard pattern match"
    return None, f"does not match SS DD LL DDDD pattern (got '{plate}')"


def get_variants(crop):
    try:
        from utils.preprocess import preprocess_plate
        return preprocess_plate(crop)
    except ImportError:
        up   = cv2.resize(crop, (crop.shape[1]*2, crop.shape[0]*2),
                          interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY) if len(up.shape)==3 else up
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return {"gray": clahe.apply(gray)}


def save_variant_grid(variants: dict, out_path: Path):
    target_h = 100
    cells = []
    for name, img in variants.items():
        h, w = img.shape[:2]
        scale = target_h / h
        resized = cv2.resize(img, (max(1, int(w*scale)), target_h))
        if len(resized.shape) == 2:
            resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
        cv2.putText(resized, name, (2, 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
        cells.append(resized)
    if not cells:
        return
    cols = 4
    rows_imgs = []
    for i in range(0, len(cells), cols):
        row = cells[i:i+cols]
        while len(row) < cols:
            row.append(np.zeros_like(cells[0]))
        rows_imgs.append(np.hstack(row))
    cv2.imwrite(str(out_path), np.vstack(rows_imgs))


def debug_crop(crop_img, reader, crop_label="crop", save_dir=None):
    h, w = crop_img.shape[:2]
    print(f"\n{'─'*60}")
    print(f"  Crop: {crop_label}  |  size: {w}x{h}")
    print(f"{'─'*60}")

    variants = get_variants(crop_img)

    if save_dir:
        cv2.imwrite(str(save_dir / f"{crop_label}_original.jpg"), crop_img)
        save_variant_grid(variants, save_dir / f"{crop_label}_variants.jpg")
        print(f"  Saved → {save_dir}/{crop_label}_variants.jpg")

    for vname, vimg in variants.items():
        results = reader.readtext(vimg, detail=1, paragraph=False)

        if not results:
            print(f"  [{vname:18s}]  EasyOCR returned NOTHING")
            continue

        for _, text, conf in results:
            flag = " ← LOW CONF" if conf < 0.15 else ""
            print(f"  [{vname:18s}]  raw='{text}'  conf={conf:.3f}{flag}")

        merged     = "".join(t for _, t, _ in
                              sorted(results, key=lambda r: r[0][0][1]))
        normalised = normalise_raw(merged)
        fixed      = fix_characters(normalised)
        result, reason = validate_plate(fixed)

        print(f"  {'':18s}   → merged='{merged}'  normalised='{normalised}'"
              f"  fixed='{fixed}'")
        if result:
            print(f"  {'':18s}   ✓ VALID: {result}")
            print(f"\n  ✓ Found in variant '{vname}': {result}")
            return result
        else:
            print(f"  {'':18s}   ✗ {reason}")

    print(f"\n  ✗ No valid plate found for {crop_label}")
    return None


def debug_from_video(source, max_crops=10, save_crops_dir=None):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("pip install ultralytics"); sys.exit(1)

    from utils.constants import CONF_THRESH, IOU_THRESH, NTH_FRAME, MOTION_THRESH

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Cannot open: {source}"); sys.exit(1)

    w_vid = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_vid = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {w_vid}x{h_vid}")
    print(f"Extracting up to {max_crops} plate crops...\n")

    save_dir = None
    if save_crops_dir:
        save_dir = Path(save_crops_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        print(f"Saving to: {save_dir}\n")

    detector  = YOLO("models/best.pt")
    reader    = easyocr.Reader(["en"], gpu=False)
    crops     = []
    frame_id  = 0
    prev_gray = None

    while len(crops) < max_crops:
        ret, frame = cap.read()
        if not ret: break
        frame_id += 1
        if frame_id % NTH_FRAME != 0: continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            if cv2.absdiff(gray, prev_gray).mean() < MOTION_THRESH:
                prev_gray = gray; continue
        prev_gray = gray

        results = detector(frame, conf=CONF_THRESH, iou=IOU_THRESH, verbose=False)
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            det_conf = float(box.conf[0])
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0: continue
            crops.append((crop, frame_id, det_conf))
            if len(crops) >= max_crops: break

    cap.release()

    if not crops:
        print("No crops extracted — YOLO found 0 detections.")
        return

    valid_count = 0
    for i, (crop, fid, conf) in enumerate(crops):
        label  = f"frame{fid:05d}_det{i}_conf{conf:.2f}"
        result = debug_crop(crop, reader, label, save_dir)
        if result:
            valid_count += 1

    print(f"\n{'='*60}")
    print(f"Total crops  : {len(crops)}")
    print(f"Valid plates : {valid_count}")
    if valid_count == 0:
        print()
        print("All crops failed. Open outputs/crops/*_variants.jpg and look for")
        print("the variant where the plate text reads left-to-right horizontally.")
        print()
        print("If rot90_gray / rot270_gray shows readable text:")
        print("  → Camera is mounted sideways. The new preprocess.py handles this.")
        print("  → Make sure you replaced utils/preprocess.py with the new version.")
        print()
        print("If ALL variants show only 1-3 chars (individual characters):")
        print("  → YOLO is cropping PART of the plate, not the full plate.")
        print("  → Check *_original.jpg — is the full plate number visible in the crop?")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",     required=True)
    parser.add_argument("--video",      action="store_true")
    parser.add_argument("--max-crops",  type=int, default=10)
    parser.add_argument("--save-crops", default=None)
    args = parser.parse_args()

    if args.video:
        debug_from_video(args.source, args.max_crops, args.save_crops)
    else:
        img = cv2.imread(args.source)
        if img is None:
            print(f"Cannot read: {args.source}"); sys.exit(1)
        save_dir = None
        if args.save_crops:
            save_dir = Path(args.save_crops)
            save_dir.mkdir(parents=True, exist_ok=True)
        reader = easyocr.Reader(["en"], gpu=False)
        debug_crop(img, reader, Path(args.source).name, save_dir)
