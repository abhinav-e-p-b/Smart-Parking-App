"""
config.py — Central configuration for the Parking ANPR system.

Import anywhere with:
    from config import cfg
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModelConfig:
    best_weights: Path = Path("models/best.pt")
    img_size: int = 640
    conf_thresh: float = 0.50    # Low — catches weak detections
    iou_thresh: float = 0.45
    whole_image_fraction: float = 0.70


@dataclass
class OCRConfig:
    gpu: bool = True
    languages: list = field(default_factory=lambda: ["en"])
    min_conf: float = 0.15


@dataclass
class VideoConfig:
    nth_frame: int = 2
    motion_thresh: float = 12.0
    cooldown_frames: int = 60    # frames before same plate is re-logged
    confirm_frames: int = 3      # tracker frames before emitting event
    max_lost: int = 15


@dataclass
class CameraConfig:
    # Camera IDs: 0/1/2 = webcam index, or RTSP/HTTP URL string
    entry_camera: object = 0       # laptop webcam / entry gate camera
    exit_camera: object = 1        # second webcam / exit gate camera

    # Human-readable labels stored in the DB
    entry_label: str = "GATE_ENTRY"
    exit_label: str = "GATE_EXIT"

    # Resolution to request from camera
    width: int = 1280
    height: int = 720


@dataclass
class ParkingConfig:
    total_slots: int = 50         # set to your actual lot capacity
    zone: str = "A"


@dataclass
class StorageConfig:
    # Set to a Supabase Storage bucket URL prefix to upload snapshots.
    # Leave empty to skip image upload.
    bucket_url: str = ""
    save_local_snapshots: bool = True
    snapshot_dir: Path = Path("outputs/snapshots")


@dataclass
class Config:
    model:   ModelConfig   = field(default_factory=ModelConfig)
    ocr:     OCRConfig     = field(default_factory=OCRConfig)
    video:   VideoConfig   = field(default_factory=VideoConfig)
    camera:  CameraConfig  = field(default_factory=CameraConfig)
    parking: ParkingConfig = field(default_factory=ParkingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)


cfg = Config()
