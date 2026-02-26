"""
finetune.py - Fine-tune YOLOv8 on Indian number plate dataset.

Run from: C:/Users/abhin/Downloads/Smart-Parking-App/
Command:  python finetune.py

Dataset structure expected:
    Smart-Parking-App/
        number-plate-1/
            data.yaml         <- must use relative paths (see data.yaml fix)
            train/images/  train/labels/
            valid/images/  valid/labels/
            test/images/   test/labels/
        finetune.py           <- this file
"""

from ultralytics import YOLO
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
# Run from Smart-Parking-App/ — relative path works on any machine
DATA_YAML = "number-plate-1/data.yaml"

# For Google Colab — uncomment and update:
# DATA_YAML = "/content/number-plate-1/data.yaml"

# yolov8n.pt = fastest (good for real-time webcam on CPU/integrated GPU)
# yolov8s.pt = best accuracy/speed balance (RECOMMENDED)
BASE_MODEL = "yolov8s.pt"   # downloads ~22MB automatically on first run

# ── Validate paths before starting ───────────────────────────────────────────
if not Path(DATA_YAML).exists():
    raise FileNotFoundError(
        f"\n❌ Dataset not found at: {DATA_YAML}\n"
        f"   Make sure you're running from the Smart-Parking-App/ folder:\n"
        f"   cd C:/Users/abhin/Downloads/Smart-Parking-App\n"
        f"   python finetune.py\n"
        f"   Also ensure data.yaml uses relative paths (not absolute C:\\ paths)."
    )

print(f"✅ Dataset found: {DATA_YAML}")
print(f"✅ Base model: {BASE_MODEL}")

model = YOLO(BASE_MODEL)

results = model.train(
    data=DATA_YAML,

    epochs=100,
    patience=20,

    imgsz=640,
    batch=8,                # safe for 8GB RAM + no dedicated GPU
                            # increase to 16-32 on Colab T4/A100

    lr0=0.001,
    lrf=0.01,
    warmup_epochs=3,

    freeze=10,              # train head only; set 0 to train all layers

    hsv_h=0.02,
    hsv_s=0.8,
    hsv_v=0.5,
    degrees=10.0,
    translate=0.15,
    scale=0.6,
    mosaic=1.0,
    perspective=0.001,
    fliplr=0.0,             # NO flip — plates have directional text

    project="runs/finetune",
    name="indian_plates",
    save=True,
    exist_ok=True,

    device='0',           # change to 0 if you have a dedicated NVIDIA GPU
    workers=2,
)

best_model_path = Path(results.save_dir) / "weights" / "best.pt"
print(f"\n{'='*55}")
print(f"✅ Training complete!")
print(f"   Best model: {best_model_path}")
print(f"   Copy it to your project root as: best.pt")
print(f"{'='*55}")