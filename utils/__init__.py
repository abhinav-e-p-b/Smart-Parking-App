"""
utils/__init__.py

Augment is training-only — import it explicitly in training scripts.
Importing it here causes albumentations warning to print on every
detect run, and crashes if albumentations is not installed.
"""
from .preprocess import preprocess_plate
from .ocr import read_plate, PlateReader
from .visualise import draw_detections, draw_plate_result
from .tracker import PlateTracker
