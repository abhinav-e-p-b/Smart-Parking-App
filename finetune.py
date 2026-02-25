"""
finetune.py - Fine-tune license_plate_detector.pt on Indian number plate dataset
"""

from ultralytics import YOLO

# Load your existing trained model (transfer learning from it)
model = YOLO("license_plate_detector.pt")

results = model.train(
    data="/c:/Users/abhin/Downloads/Smart-Parking-App/number-plate-1/data.yaml",  # ← update this path
    
    epochs=50,           # start with 50; increase to 100 if val loss still improving
    imgsz=640,           # standard YOLOv8 input size
    batch=16,            # reduce to 8 if you get CUDA out-of-memory
    
    # Fine-tuning specific settings
    lr0=0.001,           # lower learning rate than training from scratch (default 0.01)
    lrf=0.01,            # final LR = lr0 * lrf
    warmup_epochs=3,
    
    # Freeze backbone to preserve learned features, only train detection head
    freeze=10,           # freeze first 10 layers; set to 0 to unfreeze everything
    
    # Output
    project="runs/finetune",
    name="indian_plates",
    save=True,
    
    # Hardware
    device=0,            # GPU index; use 'cpu' if no GPU
    workers=4,
    
    # Augmentation (helps with varied Indian plate conditions)
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=5.0,         # slight rotation for angled plates
    translate=0.1,
    scale=0.5,
    fliplr=0.0,          # don't flip — plates are directional
)

print(f"\nBest model saved to: {results.save_dir}/weights/best.pt")