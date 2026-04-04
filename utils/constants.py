"""
utils/constants.py — Single source of truth for all pipeline thresholds.

Import from here in every detect_*.py and debug script so that
OCR_MIN_CONF, CONF_THRESH etc. are never out of sync across modes.
"""

# YOLO detection
CONF_THRESH    = 0.25   # keep low — BotSort filters internally
IOU_THRESH     = 0.45

# OCR
OCR_MIN_CONF   = 0.15   # deliberately low; validator rejects bad reads

# Frame sampling
NTH_FRAME      = 3      # process every Nth frame
MOTION_THRESH  = 15.0   # min mean-abs-diff to count as "motion"

# Tracker
CONFIRM_FRAMES = 2      # frames a track must be seen before confirming
MAX_LOST       = 30     # frames without match before track is pruned
VOTE_THRESH    = 0.40   # min vote fraction for consensus plate text

# Webcam overrides (tighter sampling, slightly lower motion threshold)
WEBCAM_NTH_FRAME      = 2
WEBCAM_MOTION_THRESH  = 12.0
