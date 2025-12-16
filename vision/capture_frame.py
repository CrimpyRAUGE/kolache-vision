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

    # warm-up
    time.sleep(1.0)

    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("Failed to capture frame")

    path = OUT / "calibration.jpg"
    cv2.imwrite(str(path), frame)
    print(f"Saved: {path}")

if __name__ == "__main__":
    main()
