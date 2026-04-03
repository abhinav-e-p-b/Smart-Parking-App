import sys
sys.path.insert(0, '.')
from utils.tracker import PlateTracker
import numpy as np

# ── Test 1: Kalman-only mode (reid_weights=None) ─────────────────────────────
print("=== Test 1: Kalman-only (reid_weights=None) ===")
tracker = PlateTracker(
    reid_weights=None,
    confirm_frames=2,
    max_lost=30,
    vote_thresh=0.40,
    device='cpu',
    track_high_thresh=0.25,
    track_low_thresh=0.05,
    new_track_thresh=0.25,
    match_thresh=0.85,
    proximity_thresh=0.35,
    appearance_thresh=0.30,
)
print('Using botsort:', tracker._use_botsort)
frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
dets = [(100, 100, 300, 200, 0.9, 'MH12AB3456')]
all_events = []
for i in range(5):
    events = tracker.update(dets, frame)
    all_events.extend(events)
    print(f'  Frame {i+1}: seen={dict(tracker._seen)}  events={events}')
confirmed = [e for e in all_events if e['type']=='confirmed']
print(f'  >> Confirmed events: {confirmed}')

# ── Test 2: With ReID weights ─────────────────────────────────────────────────
print()
print("=== Test 2: With ReID weights (osnet_x0_25_msmt17.pt) ===")
tracker2 = PlateTracker(
    reid_weights='osnet_x0_25_msmt17.pt',
    confirm_frames=2,
    max_lost=30,
    vote_thresh=0.40,
    device='cpu',
    track_high_thresh=0.25,
    track_low_thresh=0.05,
    new_track_thresh=0.25,
    match_thresh=0.85,
    proximity_thresh=0.35,
    appearance_thresh=0.30,
)
print('Using botsort:', tracker2._use_botsort)
frame2 = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
dets2 = [(100, 100, 300, 200, 0.9, 'MH12AB3456')]
all_events2 = []
for i in range(5):
    events = tracker2.update(dets2, frame2)
    all_events2.extend(events)
    print(f'  Frame {i+1}: seen={dict(tracker2._seen)}  events={events}')
confirmed2 = [e for e in all_events2 if e['type']=='confirmed']
print(f'  >> Confirmed events: {confirmed2}')

# ── Test 3: Two plates, expect 2 confirmed events ────────────────────────────
print()
print("=== Test 3: Two separate plates, confirm_frames=2 ===")
tracker3 = PlateTracker(reid_weights=None, confirm_frames=2, max_lost=30)
det_a = (0,   0, 100, 50,  0.9, 'KL07BB1234')
det_b = (400, 0, 500, 50,  0.9, 'MH12AB3456')
all_events3 = []
for i in range(3):
    events = tracker3.update([det_a, det_b], frame)
    all_events3.extend(events)
    print(f'  Frame {i+1}: events={events}')
confirmed3 = [e for e in all_events3 if e['type']=='confirmed']
print(f'  >> Confirmed events: {confirmed3}')

print()
print("=== ALL DONE ===")
