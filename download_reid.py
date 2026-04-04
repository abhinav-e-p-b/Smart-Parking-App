"""
download_reid.py — Download OSNet ReID weights for BoT-SORT.

Tries multiple sources in order of reliability:
  1. huggingface_hub  (Python library — most reliable, handles auth + resume)
  2. HuggingFace CDN direct HTTPS  (no library needed, works if HF is reachable)
  3. boxmot built-in downloader  (if boxmot is installed)
  4. GitHub releases  (last resort — may be blocked on restricted networks)

The script stops at the first strategy that succeeds.

Usage
-----
  python download_reid.py                          # downloads osnet_x0_25_msmt17.pt
  python download_reid.py --model osnet_x1_0_msmt17
  python download_reid.py --dest models/reid/      # save to a specific folder
  python download_reid.py --list                   # show all available models

Available models (smallest = fastest on CPU)
--------------------------------------------
  osnet_x0_25_msmt17   ~3 MB   fastest on CPU  (recommended)
  osnet_x0_5_msmt17    ~7 MB
  osnet_x0_75_msmt17   ~13 MB
  osnet_x1_0_msmt17    ~22 MB  most accurate

After downloading, pass the file to detect_video.py / detect_webcam.py:
  python detect_video.py --source video.mp4 --reid osnet_x0_25_msmt17.pt
"""

import argparse
import hashlib
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------
MODELS = {
    "osnet_x0_25_msmt17": {
        "filename":      "osnet_x0_25_msmt17.pt",
        # Primary HF repo: paulosantiago (exact .pt, verified 10 months ago)
        "hf_repo":       "paulosantiago/osnet_x0_25_msmt17",
        "hf_filename":   "osnet_x0_25_msmt17.pt",
        # Secondary HF repo: kaiyangzhou (original author, different filename)
        "hf_repo_2":     "kaiyangzhou/osnet",
        "hf_filename_2": (
            "osnet_x0_25_msmt17_combineall_256x128_amsgrad_ep150_"
            "stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth"
        ),
        "sha256":        "6f57607f",   # first 8 hex chars of SHA-256
        "size_mb":       3.1,
        "github_tag":    "v10.0.27",
    },
    "osnet_x0_5_msmt17": {
        "filename":      "osnet_x0_5_msmt17.pt",
        "hf_repo":       "mikel-brostrom/osnet_x0_5_msmt17",
        "hf_filename":   "osnet_x0_5_msmt17.pt",
        "hf_repo_2":     "kaiyangzhou/osnet",
        "hf_filename_2": (
            "osnet_x0_5_msmt17_combineall_256x128_amsgrad_ep150_"
            "stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth"
        ),
        "sha256":        None,
        "size_mb":       7.0,
        "github_tag":    "v10.0.27",
    },
    "osnet_x0_75_msmt17": {
        "filename":      "osnet_x0_75_msmt17.pt",
        "hf_repo":       "mikel-brostrom/osnet_x0_75_msmt17",
        "hf_filename":   "osnet_x0_75_msmt17.pt",
        "hf_repo_2":     "kaiyangzhou/osnet",
        "hf_filename_2": (
            "osnet_x0_75_msmt17_combineall_256x128_amsgrad_ep150_"
            "stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth"
        ),
        "sha256":        None,
        "size_mb":       13.0,
        "github_tag":    "v10.0.27",
    },
    "osnet_x1_0_msmt17": {
        "filename":      "osnet_x1_0_msmt17.pt",
        "hf_repo":       "mikel-brostrom/osnet_x1_0_msmt17",
        "hf_filename":   "osnet_x1_0_msmt17.pt",
        "hf_repo_2":     "kaiyangzhou/osnet",
        "hf_filename_2": (
            "osnet_x1_0_msmt17_combineall_256x128_amsgrad_ep150_"
            "stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth"
        ),
        "sha256":        None,
        "size_mb":       22.0,
        "github_tag":    "v10.0.27",
    },
}

HF_CDN = "https://huggingface.co/{repo}/resolve/main/{filename}"
GH_URL = "https://github.com/mikel-brostrom/boxmot/releases/download/{tag}/{filename}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _progress(block, block_size, total):
    done = block * block_size
    if total > 0:
        pct = min(done / total * 100, 100)
        bar = int(pct / 2)
        sys.stdout.write(
            f"\r  [{'█'*bar}{'░'*(50-bar)}] {pct:5.1f}%  "
            f"{_fmt_bytes(done)} / {_fmt_bytes(total)}"
        )
    else:
        sys.stdout.write(f"\r  {_fmt_bytes(done)} downloaded...")
    sys.stdout.flush()


def _check_sha256(path: Path, prefix: str) -> bool:
    if not prefix:
        return True
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual.startswith(prefix):
        print(f"  SHA256 ✓  ({actual[:16]}...)")
        return True
    print(f"  SHA256 ✗  expected {prefix}..., got {actual[:8]}...")
    return False


def _fetch(url: str, dest: Path) -> bool:
    """Download url → dest. Returns True on success."""
    try:
        print(f"  Trying: {url}")
        urllib.request.urlretrieve(url, dest, reporthook=_progress)
        print()
        if dest.stat().st_size < 4096:
            dest.unlink(missing_ok=True)
            print("  ✗ File too small — likely an error page, not a model.")
            return False
        print(f"  ✓ {_fmt_bytes(dest.stat().st_size)} saved to {dest}")
        return True
    except urllib.error.URLError as e:
        print(f"\n  ✗ URLError: {e.reason}")
    except Exception as e:
        print(f"\n  ✗ {type(e).__name__}: {e}")
    return False


# ---------------------------------------------------------------------------
# Download strategies  (tried in order)
# ---------------------------------------------------------------------------

def _try_huggingface_hub(info: dict, dest: Path) -> bool:
    """Strategy 1: huggingface_hub library — best option, handles mirrors."""
    print("\n[ Strategy 1 — huggingface_hub library ]")
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("  Not installed — skipping.  (pip install huggingface_hub)")
        return False

    candidates = [
        (info["hf_repo"],         info["hf_filename"]),
        (info.get("hf_repo_2"),   info.get("hf_filename_2")),
    ]

    for repo, filename in candidates:
        if not repo or not filename:
            continue
        try:
            print(f"  Trying repo={repo}  file={filename}")
            cached = Path(hf_hub_download(
                repo_id               = repo,
                filename              = filename,
                local_dir             = str(dest.parent),
                local_dir_use_symlinks= False,
            ))
            # Rename to the canonical .pt filename if needed
            if cached.resolve() != dest.resolve():
                shutil.copy2(cached, dest)
            if dest.exists() and dest.stat().st_size > 4096:
                print(f"  ✓ {_fmt_bytes(dest.stat().st_size)} saved to {dest}")
                return True
        except Exception as e:
            print(f"  ✗ {type(e).__name__}: {e}")

    return False


def _try_hf_cdn(info: dict, dest: Path) -> bool:
    """Strategy 2: HuggingFace CDN — no library, plain HTTPS."""
    print("\n[ Strategy 2 — HuggingFace CDN (direct HTTPS) ]")
    urls = [
        HF_CDN.format(repo=info["hf_repo"], filename=info["hf_filename"]),
    ]
    if info.get("hf_repo_2") and info.get("hf_filename_2"):
        urls.append(HF_CDN.format(
            repo=info["hf_repo_2"], filename=info["hf_filename_2"]
        ))
    for url in urls:
        if _fetch(url, dest):
            return True
    return False


def _try_boxmot(info: dict, dest: Path) -> bool:
    """Strategy 3: boxmot built-in downloader."""
    print("\n[ Strategy 3 — boxmot built-in download ]")
    try:
        from boxmot import download_models
        download_models(info["filename"])
        # boxmot may put the file in cwd or a cache directory
        search_dirs = [
            Path("."),
            Path.home() / ".boxmot",
            Path.home() / ".cache" / "boxmot",
            Path.home() / ".cache" / "torch" / "hub" / "checkpoints",
        ]
        for d in search_dirs:
            candidate = d / info["filename"]
            if candidate.exists() and candidate.stat().st_size > 4096:
                if candidate.resolve() != dest.resolve():
                    shutil.copy2(candidate, dest)
                print(f"  ✓ {_fmt_bytes(dest.stat().st_size)} saved to {dest}")
                return True
        print("  ✗ boxmot ran but file not found in expected cache locations.")
    except ImportError:
        print("  boxmot not installed — skipping.")
    except Exception as e:
        print(f"  ✗ {type(e).__name__}: {e}")
    return False


def _try_github(info: dict, dest: Path) -> bool:
    """Strategy 4: GitHub releases — may be blocked on some networks."""
    print("\n[ Strategy 4 — GitHub releases (may fail on restricted networks) ]")
    tag = info.get("github_tag", "v10.0.27")
    urls = [
        GH_URL.format(tag=tag, filename=info["filename"]),
        f"https://github.com/mikel-brostrom/boxmot/releases/latest/download/{info['filename']}",
    ]
    for url in urls:
        if _fetch(url, dest):
            return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def download(model_stem: str, dest_dir: Path) -> Path:
    # Normalise: allow passing full filename with or without extension
    stem = model_stem.replace(".pt", "").replace(".pth", "")
    if stem not in MODELS:
        raise ValueError(
            f"Unknown model '{model_stem}'.\n"
            f"Available: {', '.join(MODELS)}\n"
            f"Run with --list to see all options."
        )

    info    = MODELS[stem]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest    = dest_dir / info["filename"]

    # Already downloaded?
    if dest.exists() and dest.stat().st_size > 4096:
        print(f"\n✓ Already present: {dest}  ({_fmt_bytes(dest.stat().st_size)})")
        _check_sha256(dest, info["sha256"])
        return dest

    print(f"\n{'='*60}")
    print(f"  Model       : {info['filename']}")
    print(f"  Size        : ~{info['size_mb']:.1f} MB")
    print(f"  Destination : {dest.resolve()}")
    print(f"{'='*60}")

    for strategy in [_try_huggingface_hub, _try_hf_cdn, _try_boxmot, _try_github]:
        if strategy(info, dest):
            _check_sha256(dest, info["sha256"])
            print(f"\n{'='*60}")
            print(f"  Download complete!")
            print(f"  File: {dest.resolve()}")
            print(f"\n  Run with ReID:")
            print(f"    python detect_video.py --source video.mp4 --reid {dest.name}")
            print(f"    python detect_webcam.py --reid {dest.name}")
            print(f"\n  Run WITHOUT ReID (Kalman-only, still deduplicates):")
            print(f"    python detect_video.py --source video.mp4")
            print(f"{'='*60}\n")
            return dest

    # All strategies failed
    print(f"\n{'='*60}")
    print("  All download strategies failed.\n")
    print("  ── Manual download ──────────────────────────────────────")
    print("  Open this URL in your browser and save the file:")
    print(f"  {HF_CDN.format(repo=info['hf_repo'], filename=info['hf_filename'])}")
    print(f"  Save as: {dest.resolve()}")
    print()
    print("  ── Or install huggingface_hub and retry ─────────────────")
    print("    pip install huggingface_hub")
    print("    python download_reid.py")
    print()
    print("  ── Or run Kalman-only (no ReID, still deduplicates) ─────")
    print("    python detect_video.py --source video.mp4")
    print(f"{'='*60}\n")
    raise RuntimeError(f"Could not download {info['filename']}.")


def list_models():
    print("\nAvailable OSNet ReID models:\n")
    print(f"  {'Model stem':<30}  {'Size':>7}  Notes")
    print(f"  {'-'*30}  {'-'*7}  {'-'*28}")
    for stem, info in MODELS.items():
        note = "← recommended for CPU" if "x0_25" in stem else ""
        print(f"  {stem:<30}  {info['size_mb']:>5.1f} MB  {note}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download OSNet ReID weights for BoT-SORT tracker"
    )
    parser.add_argument(
        "--model", default="osnet_x0_25_msmt17",
        help="Model name or filename (default: osnet_x0_25_msmt17)",
    )
    parser.add_argument(
        "--dest", default=".",
        help="Destination directory (default: current working directory)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available models and exit",
    )
    args = parser.parse_args()

    if args.list:
        list_models()
        sys.exit(0)

    try:
        download(model_stem=args.model, dest_dir=Path(args.dest))
    except (ValueError, RuntimeError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)
