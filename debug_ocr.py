"""
debug_ocr.py — Show exactly what PaddleOCR reads before and after validation.

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
_PLATE_RE        = re.compile(r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}")
_BH_RE           = re.compile(r"[0-9]{2}BH[0-9]{4}[A-Z]{1,2}")
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
    return (raw.upper()
               .replace(" ", "").replace("-", "")
               .replace(".", "").replace(":", "").replace(",", ""))


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


def extract_plate_from_noise(noisy):
    for pattern in (_BH_RE, _PLATE_RE):
        m = pattern.search(noisy)
        if m:
            candidate = fix_characters(m.group())
            result, _ = validate_plate(candidate)
            if result:
                return result, f"regex match at pos {m.start()}"
    for length in (10, 9, 8):
        for start in range(len(noisy) - length + 1):
            window = noisy[start : start + length]
            fixed  = fix_characters(window)
            result, _ = validate_plate(fixed)
            if result:
                return result, f"window[{start}:{start+length}] '{window}'→'{fixed}'"
    return None, "no plate found in any window"


def get_variants(crop):
    try:
        from utils.preprocess import preprocess_plate
        return preprocess_plate(crop)
    except ImportError:
        up    = cv2.resize(crop, (crop.shape[1]*2, crop.shape[0]*2),
                           interpolation=cv2.INTER_CUBIC)
        gray  = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY) if len(up.shape)==3 else up
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return {"gray": clahe.apply(gray)}


def save_variant_grid(variants: dict, out_path: Path):
    target_h = 100
    cells = []
    for name, img in variants.items():
        h, w = img.shape[:2]
        scale = target_h / h
        resized = cv2.resize(img, (max(1, int(w * scale)), target_h))
        if len(resized.shape) == 2:
            resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
        cv2.putText(resized, name, (2, 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
        cells.append(resized)
    if not cells:
        return
    cols = 4
    rows_imgs = []
    for row_start in range(0, len(cells), cols):
        row = cells[row_start : row_start + cols]
        while len(row) < cols:
            row.append(np.zeros_like(cells[0]))
        max_w = max(c.shape[1] for c in row)
        padded = []
        for c in row:
            if c.shape[1] < max_w:
                pad = np.zeros((c.shape[0], max_w - c.shape[1], 3), dtype=c.dtype)
                c = np.hstack([c, pad])
            padded.append(c)
        rows_imgs.append(np.hstack(padded))
    max_row_w = max(r.shape[1] for r in rows_imgs)
    final_rows = []
    for r in rows_imgs:
        if r.shape[1] < max_row_w:
            pad = np.zeros((r.shape[0], max_row_w - r.shape[1], 3), dtype=r.dtype)
            r = np.hstack([r, pad])
        final_rows.append(r)
    cv2.imwrite(str(out_path), np.vstack(final_rows))


# ---------------------------------------------------------------------------
# PaddleOCR helpers (shared with utils/ocr.py logic)
# ---------------------------------------------------------------------------

def _ensure_bgr(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def _parse_paddle_results(raw) -> list:
    """Normalise PaddleOCR output → list of (box, text, conf)."""
    if raw is None:
        return []
    parsed = []
    for page in raw:
        if page is None:
            continue
        for entry in page:
            try:
                if isinstance(entry, (list, tuple)) and len(entry) == 2:
                    box      = entry[0]
                    text_obj = entry[1]
                    if isinstance(text_obj, (list, tuple)) and len(text_obj) == 2:
                        text = str(text_obj[0])
                        conf = float(text_obj[1])
                    elif hasattr(text_obj, "text"):
                        text = str(text_obj.text)
                        conf = float(getattr(text_obj, "score", 1.0))
                    else:
                        continue
                    parsed.append((box, text, conf))
                elif isinstance(entry, dict):
                    box  = entry.get("bbox") or entry.get("box")
                    text = str(entry.get("text", ""))
                    conf = float(entry.get("score", entry.get("conf", 1.0)))
                    if box is not None and text:
                        parsed.append((box, text, conf))
            except Exception:
                continue
    return parsed


def _run_ocr(reader, img: np.ndarray) -> list:
    """Run PaddleOCR on one image; return parsed (box, text, conf) list."""
    img_bgr = _ensure_bgr(img)
    try:
        raw = reader.ocr(img_bgr, cls=True)
    except TypeError:
        raw = reader.ocr(img_bgr)
    return _parse_paddle_results(raw)


def _make_reader(gpu: bool = False):
    """
    Build a PaddleOCR reader compatible with v2 and v3.

    Detection order:
    1. paddleocr.__version__ major number (most reliable).
    2. Full MRO parameter scan — v3 uses deep inheritance so 'use_gpu'
       may not appear in __init__ directly.
    3. Runtime try/except fallback so a wrong static detection never crashes.
    """
    import os, inspect
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    import paddleocr
    from paddleocr import PaddleOCR

    # --- Step 1: version string ---
    api_ver = 2
    try:
        ver_str = getattr(paddleocr, "__version__", "") or ""
        major = int(ver_str.split(".")[0]) if ver_str and ver_str[0].isdigit() else 0
        if major >= 3:
            api_ver = 3
    except Exception:
        pass

    # --- Step 2: MRO scan fallback ---
    if api_ver == 2:
        try:
            all_params: set = set()
            for cls in type.mro(PaddleOCR):
                try:
                    all_params.update(inspect.signature(cls.__init__).parameters.keys())
                except (ValueError, TypeError):
                    continue
            if "use_gpu" not in all_params:
                api_ver = 3
        except Exception:
            pass

    def _try_v3():
        return PaddleOCR(device="gpu" if gpu else "cpu")

    def _try_v2():
        return PaddleOCR(use_angle_cls=True, lang="en", use_gpu=gpu, show_log=False)

    # --- Step 3: construct with runtime fallback ---
    if api_ver >= 3:
        try:
            return _try_v3()
        except (TypeError, ValueError):
            return _try_v2()
    else:
        try:
            return _try_v2()
        except (TypeError, ValueError):
            return _try_v3()


# ---------------------------------------------------------------------------
# Main debug routine
# ---------------------------------------------------------------------------

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
        results = _run_ocr(reader, vimg)

        if not results:
            print(f"  [{vname:18s}]  PaddleOCR returned NOTHING")
            continue

        for _, text, conf in results:
            flag = " ← LOW CONF" if conf < 0.15 else ""
            print(f"  [{vname:18s}]  box='{text}'  conf={conf:.3f}{flag}")

        # --- Strategy 1: per-box ---
        for _, text, conf in results:
            norm = normalise_raw(text)
            if len(norm) < 6:
                continue
            fixed = fix_characters(norm)
            plate, reason = validate_plate(fixed)
            if plate:
                print(f"  [{vname:18s}]  ✓ per-box direct: '{text}' → {plate}")
                print(f"\n  ✓ Found in variant '{vname}': {plate}")
                return plate
            plate, _ = extract_plate_from_noise(norm)
            if plate:
                print(f"  [{vname:18s}]  ✓ per-box extracted: '{text}' → {plate}")
                print(f"\n  ✓ Found in variant '{vname}': {plate}")
                return plate

        # --- Strategy 2 & 3: merged ---
        try:
            merged = "".join(
                t for _, t, _ in
                sorted(results, key=lambda r: min(pt[1] for pt in r[0]))
            )
        except (TypeError, IndexError):
            merged = "".join(t for _, t, _ in results)

        norm  = normalise_raw(merged)
        fixed = fix_characters(norm)
        plate, reason = validate_plate(fixed)

        print(f"  {'':18s}   merged='{merged}'  norm='{norm}'  fixed='{fixed}'")

        if plate:
            print(f"  {'':18s}   ✓ VALID (direct): {plate}")
            print(f"\n  ✓ Found in variant '{vname}': {plate}")
            return plate
        else:
            print(f"  {'':18s}   ✗ direct: {reason}")

        if len(norm) >= 8:
            plate, how = extract_plate_from_noise(norm)
            if plate:
                print(f"  {'':18s}   ✓ VALID (noise extract): {plate}  [{how}]")
                print(f"\n  ✓ Found in variant '{vname}': {plate}")
                return plate
            else:
                print(f"  {'':18s}   ✗ noise extract: {how}")

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

    detector = YOLO("models/best.pt")
    reader   = _make_reader(gpu=False)

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
        print("\nAll crops failed. Check _original.jpg files:")
        print("  → If the plate is visible but sideways, rot90 variants should work")
        print("  → If the crop only shows 1-3 chars, YOLO is cropping part of plate.")
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
        reader = _make_reader(gpu=False)
        debug_crop(img, reader, Path(args.source).name, save_dir)
