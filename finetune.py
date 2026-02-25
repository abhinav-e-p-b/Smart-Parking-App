"""
finetune.py - Fine-tune license_plate_detector.pt on Indian number plate dataset
"""

from ultralytics import YOLO

# Load your existing trained model (transfer learning from it)
model = YOLO("license_plate_detector.pt")

results = model.train(
    data="content/number-plate-1/data.yaml",  # ← update this path
    
    epochs=100,           # start with 50; increase to 100 if val loss still improving
    imgsz=640,           # standard YOLOv8 input size
    batch=8,            # reduce to 8 if you get CUDA out-of-memory
    
    # Fine-tuning specific settings
    lr0=0.0001,           # lower learning rate than training from scratch (default 0.01)
    lrf=0.001,            # final LR = lr0 * lrf
    warmup_epochs=5,
    
    # Freeze backbone to preserve learned features, only train detection head
    freeze=0,           # freeze first 10 layers; set to 0 to unfreeze everything
    
    # Output
    project="runs/finetune",
    name="indian_plates",
    save=True,
    patience=20,          # early stopping if no improvement for 10 epochs
    
    # Hardware
    device=0,            # GPU index; use 'cpu' if no GPU
    workers=4,
    
    # Augmentation (helps with varied Indian plate conditions)
    hsv_h=0.02,
    hsv_s=0.8,
    hsv_v=0.5,
    degrees=10.0,         # slight rotation for angled plates
    translate=0.15,
    scale=0.6,
    mosaic=1.0,
    perspective=0.001,          # use mosaic augmentation to combine 4 images (good for small datasets)
    fliplr=0.0,          # don't flip — plates are directional
)

print(f"\nBest model saved to: {results.save_dir}/weights/best.pt")