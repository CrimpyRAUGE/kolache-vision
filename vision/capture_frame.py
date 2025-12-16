from pathlib import Path
import time
import json
import cv2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "captures"
OUT.mkdir(exist_ok=True)

ROIS_PATH = ROOT / "config" / "vision_rois.json"

def rotate_frame(frame, rotate):
    rotate = int(rotate or 0)
    if rotate == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotate == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    if rotate == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame

def main():
    cfg = {}
    if ROIS_PATH.exists():
        cfg = json.loads(ROIS_PATH.read_text()).get("camera", {})

    source = cfg.get("source", 0)
    width, height = cfg.get("resolution", [1280, 720])
    rotate = int(cfg.get("rotate", 0))

    warmup_seconds = float(cfg.get("warmup_seconds", 2.0))
    warmup_frames = int(cfg.get("warmup_frames", 20))

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera source {source}")

    # Force the same resolution as run_slots.py
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))

    # Warm-up: let exposure/white balance settle
    t_end = time.time() + warmup_seconds
    while time.time() < t_end:
        cap.read()
    for _ in range(warmup_frames):
        cap.read()

    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise RuntimeError("Failed to capture frame after warm-up")

    # IMPORTANT: Apply the same rotation as live
    frame = rotate_frame(frame, rotate)

    path = OUT / "calibration.jpg"
    cv2.imwrite(str(path), frame)
    print(f"Saved: {path}")
    print(f"Captured shape: {frame.shape} (H,W,C)")

if __name__ == "__main__":
    main()
