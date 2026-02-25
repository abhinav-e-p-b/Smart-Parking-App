import yaml
from pathlib import Path

with open("number-plate-1/data.yaml") as f:
    cfg = yaml.safe_load(f)

for split in ["train", "val", "test"]:
    img_dir = Path(cfg[split])
    lbl_dir = img_dir.parent / "labels"   # <-- Correct logic

    imgs = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))
    lbls = list(lbl_dir.glob("*.txt"))

    print(f"{split}: {len(imgs)} images, {len(lbls)} labels")

    if len(imgs) != len(lbls):
        print("  ⚠️ MISMATCH — missing labels will hurt recall badly")
    else:
        print("  ✅ Perfect match")