import json
import time
from pathlib import Path
from datetime import datetime

# OpenCV will be installed on laptop/Pi (not Termux)
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "inventory.json"
LAYOUT_PATH = ROOT / "config" / "layout.json"
ROIS_PATH = ROOT / "config" / "vision_rois.json"

def load_layout():
    return json.loads(LAYOUT_PATH.read_text())["trays"]

def load_rois():
    return json.loads(ROIS_PATH.read_text())

def rotate_frame(frame, rotate):
    if rotate == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotate == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    if rotate == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame

def slot_score(gray_crop):
    """
    Compute an "occupied score" from a slot crop.
    Higher = more texture/edges (usually occupied).
    """
    blur = cv2.GaussianBlur(gray_crop, (5, 5), 0)

    # Edge energy
    lap = cv2.Laplacian(blur, cv2.CV_64F)
    edge_energy = float(np.mean(np.abs(lap)))

    # Brightness
    brightness = float(np.mean(blur))

    # Combine (tune later)
    # We weight edges more because empty slots tend to be smoother.
    return 0.85 * edge_energy + 0.15 * (255.0 - brightness)

def is_occupied(score, threshold):
    return score >= threshold

def draw_slot(frame, rect, occupied, score, label=None):
    x, y, w, h = rect
    color = (0, 255, 0) if occupied else (0, 0, 255)  # green/red
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    txt = f"{score:.1f}"
    if label:
        txt = f"{label} {txt}"
    cv2.putText(frame, txt, (x, max(15, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

def main():
    rois = load_rois()
    camera_cfg = rois["camera"]
    trays_cfg = rois["trays"]
    layout = load_layout()

    # Build lookup for max counts by tray name
    max_by_name = {t["name"]: int(t["max"]) for t in layout}

    source = camera_cfg.get("source", 0)
    width, height = camera_cfg.get("resolution", [1280, 720])
    rotate = int(camera_cfg.get("rotate", 0))

    # Global threshold (we will tune this using calibration)
    threshold = float(camera_cfg.get("occupied_threshold", 12.0))

debug = bool(camera_cfg.get("debug", True))
window_name = "kolache-debug"
if debug:
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not cap.isOpened():
        raise RuntimeError("Could not open camera/video source")

    print("Slot occupancy running. Ctrl+C to stop.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Frame read failed; retrying...")
            time.sleep(1)
            continue

        frame = rotate_frame(frame, rotate)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

       counts = {}
y_cursor = 28  # for on-screen tray summaries (top-left)

for tray in trays_cfg:
    name = tray["name"]
    slots = tray["slots"]

    occupied_count = 0

    for i, (x, y, w, h) in enumerate(slots):
        crop = gray[y:y+h, x:x+w]
        if crop.size == 0:
            score = 0.0
            occ = False
        else:
            score = slot_score(crop)
            occ = is_occupied(score, threshold)

        if occ:
            occupied_count += 1

        if debug:
            draw_slot(frame, [x, y, w, h], occ, score)

    mx = int(max_by_name.get(name, len(slots)))
    counts[name] = max(0, min(mx, occupied_count))

    if debug:
        # tray summary text (left side)
        cv2.putText(
            frame,
            f"{name}: {counts[name]}/{mx}",
            (12, y_cursor),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        y_cursor += 22

        STORE.write_text(json.dumps(counts, indent=2))
print(datetime.now().strftime("%H:%M:%S"), "wrote inventory.json")

if debug:
    # show threshold on screen
    cv2.putText(frame, f"threshold={threshold:.1f}  (q to quit)",
                (12, frame.shape[0] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.imshow(window_name, frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

time.sleep(float(camera_cfg.get("interval_seconds", 3)))

if __name__ == "__main__":
    main()

cap.release()
if debug:
    cv2.destroyAllWindows()
