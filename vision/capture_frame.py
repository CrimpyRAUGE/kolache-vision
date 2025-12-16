from pathlib import Path
import time
import cv2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "captures"
OUT.mkdir(exist_ok=True)

def main():
    cap = cv2.VideoCapture(0)  # built-in camera
    if not cap.isOpened():
        raise RuntimeError("Could not open camera 0")

    # =========================
    # Camera warm-up
    # =========================
    warmup_seconds = 2.0
    warmup_frames = 20

    # Let auto-exposure / white balance settle by time
    t_end = time.time() + warmup_seconds
    while time.time() < t_end:
        cap.read()

    # Flush several frames (autofocus usually stabilizes here)
    for _ in range(warmup_frames):
        cap.read()

    # =========================
    # Capture final frame
    # =========================
    ok, frame = cap.read()
    cap.release()

    if not ok or frame is None:
        raise RuntimeError("Failed to capture frame after warm-up")

    path = OUT / "calibration.jpg"
    cv2.imwrite(str(path), frame)
    print(f"Saved: {path}")

if __name__ == "__main__":
    main()
