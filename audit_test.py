"""
audit_test.py - Verify image/label counts match before training.
Run from: C:/Users/abhin/Downloads/Smart-Parking-App/
Command:  python audit_test.py
"""

import yaml
from pathlib import Path


def audit_split(split_name: str, img_dir: Path):
    """
    Check that every image has a corresponding label file.
    Your dataset structure is:
        number-plate-1/
            train/
                images/   ← img_dir points here
                labels/   ← sibling folder
            valid/
                images/
                labels/
            test/
                images/
                labels/
    """
    # Labels are in the sibling 'labels' folder next to 'images'
    lbl_dir = img_dir.parent.parent / "labels" / img_dir.name
    # Fallback: try direct sibling (e.g. valid/labels/ next to valid/images/)
    if not lbl_dir.exists():
        lbl_dir = img_dir.parent / "labels"

    imgs = sorted(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
    lbls = sorted(list(lbl_dir.glob("*.txt"))) if lbl_dir.exists() else []

    print(f"\n── {split_name.upper()} ──────────────────────────────────")
    print(f"  Images dir : {img_dir}")
    print(f"  Labels dir : {lbl_dir}")
    print(f"  Images     : {len(imgs)}")
    print(f"  Labels     : {len(lbls)}")

    if not img_dir.exists():
        print("  ❌ Images directory does NOT exist — check your path!")
        return

    if not lbl_dir.exists():
        print("  ❌ Labels directory does NOT exist — check your path!")
        return

    if len(imgs) == 0:
        print("  ⚠️  No images found (check .jpg / .png extensions)")
        return

    if len(imgs) != len(lbls):
        print(f"  ⚠️  MISMATCH — {abs(len(imgs) - len(lbls))} files differ!")
        # Show which images are missing labels
        img_stems = {p.stem for p in imgs}
        lbl_stems = {p.stem for p in lbls}
        missing_labels = img_stems - lbl_stems
        extra_labels   = lbl_stems - img_stems
        if missing_labels:
            print(f"  Missing labels for: {sorted(missing_labels)[:5]} ...")
        if extra_labels:
            print(f"  Labels without images: {sorted(extra_labels)[:5]} ...")
    else:
        print(f"  ✅ Perfect match — ready to train")

    # Sanity check: verify label format (should be YOLO: class cx cy w h)
    bad_labels = []
    for lbl_path in lbls[:20]:  # check first 20
        try:
            content = lbl_path.read_text().strip()
            if not content:
                bad_labels.append(f"{lbl_path.name} (empty)")
                continue
            for line in content.splitlines():
                parts = line.strip().split()
                if len(parts) != 5:
                    bad_labels.append(f"{lbl_path.name} (wrong columns: {len(parts)})")
                    break
                cls, cx, cy, w, h = parts
                if not all(0.0 <= float(v) <= 1.0 for v in [cx, cy, w, h]):
                    bad_labels.append(f"{lbl_path.name} (coords out of range)")
                    break
        except Exception as e:
            bad_labels.append(f"{lbl_path.name} ({e})")

    if bad_labels:
        print(f"  ⚠️  Malformed labels (first 5): {bad_labels[:5]}")
    elif lbls:
        print(f"  ✅ Label format looks valid (YOLO normalized coords)")


def main():
    # Load data.yaml — try from current dir, then from number-plate-1/
    yaml_candidates = [
        Path("number-plate-1/data.yaml"),
        Path("data.yaml"),
    ]
    cfg = None
    for candidate in yaml_candidates:
        if candidate.exists():
            with open(candidate) as f:
                cfg = yaml.safe_load(f)
            print(f"Loaded config: {candidate.resolve()}")
            break

    if cfg is None:
        print("❌ data.yaml not found. Run from Smart-Parking-App/ folder.")
        return

    print(f"\nClasses ({cfg['nc']}): {cfg['names']}")

    for split in ["train", "val", "test"]:
        if split not in cfg:
            print(f"\n── {split.upper()} — not defined in data.yaml (skipping)")
            continue

        img_dir = Path(cfg[split])

        # If path is absolute and doesn't exist, try making it relative
        if not img_dir.exists() and img_dir.is_absolute():
            # Try resolving relative to current working directory
            rel = Path(*img_dir.parts[img_dir.parts.index("number-plate-1"):])
            if rel.exists():
                img_dir = rel
            else:
                print(f"\n── {split.upper()} ──────────────────────────────────")
                print(f"  ❌ Path not found: {cfg[split]}")
                print(f"     Make sure you're running from Smart-Parking-App/")
                print(f"     Or update data.yaml to use relative paths.")
                continue

        audit_split(split, img_dir)

    print("\n" + "═" * 55)
    print("If all splits show ✅, you're ready to run finetune.py")
    print("═" * 55)


if __name__ == "__main__":
    main()