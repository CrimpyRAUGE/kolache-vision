import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "config" / "layout.json"
OUT_PATH = ROOT / "config" / "vision_rois.json"
IMG_PATH = ROOT / "captures" / "calibration.jpg"

SLOTS_PER_TRAY = 12

# --- click state ---
tray_results = []
tray_index = 0
slot_index = 0


def load_trays_ordered():
    """
    Load trays from layout.json and order:
    1) savory (by id)
    2) sweet (by id)
    """
    layout = json.loads(LAYOUT_PATH.read_text())
    trays = layout.get("trays", [])

    def cat_key(cat: str) -> int:
        c = (cat or "").strip().lower()
        if c == "savory":
            return 0
        if c == "sweet":
            return 1
        return 2  # unknown categories last

    trays_sorted = sorted(
        trays,
        key=lambda t: (cat_key(t.get("category")), int(t.get("id", 9999))),
    )
    return trays_sorted


def rect_from_two_points(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    return [int(x), int(y), int(w), int(h)]


def draw_overlay(img, tray_name, tray_idx, total_trays, slot_idx, slots_done):
    out = img.copy()

    # draw completed slots in green
    for r in slots_done:
        x, y, w, h = r
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # header
    cv2.rectangle(out, (10, 10), (980, 120), (0, 0, 0), -1)
    cv2.putText(
        out,
        f"Tray {tray_idx+1}/{total_trays}: {tray_name}",
        (20, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        out,
        f"Slot {slot_idx+1}/{SLOTS_PER_TRAY}: click TOP-LEFT then BOTTOM-RIGHT",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        out,
        "Keys: u=undo  r=reset tray  n=next tray  q=quit/save",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (200, 200, 200),
        1,
    )
    return out


def save(rois, img_w, img_h):
    # preserve existing camera settings if file already exists
    camera = {
        "source": 0,
        "resolution": [img_w, img_h],
        "rotate": 0,
        "interval_seconds": 3,
        "debug": True,
        "occupied_threshold": 12.0,
        "threshold_step": 0.5,
        "threshold_step_coarse": 2.0,
    }

    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text())
        if isinstance(existing, dict) and "camera" in existing:
            camera.update(existing["camera"])

    data = {"camera": camera, "trays": rois}
    OUT_PATH.write_text(json.dumps(data, indent=2))
    print(f"Saved: {OUT_PATH}")


def main():
    global tray_index, slot_index, tray_results

    if not IMG_PATH.exists():
        raise RuntimeError(f"Missing {IMG_PATH}. Run vision/capture_frame.py first.")

    trays = load_trays_ordered()
    if not trays:
        raise RuntimeError("No trays found in config/layout.json")

    img = cv2.imread(str(IMG_PATH))
    if img is None:
        raise RuntimeError("Failed to read calibration image")

    h, w = img.shape[:2]

    current_tray = trays[tray_index]
    current_name = current_tray["name"]

    slots_done = []
    temp_first_point = None

    def on_mouse(event, x, y, flags, param):
        nonlocal temp_first_point, slots_done
        global slot_index

        if event == cv2.EVENT_LBUTTONDOWN:
            if temp_first_point is None:
                temp_first_point = (x, y)
            else:
                rect = rect_from_two_points(temp_first_point, (x, y))
                temp_first_point = None

                # ignore accidental tiny boxes
                if rect[2] < 5 or rect[3] < 5:
                    return

                slots_done.append(rect)
                slot_index += 1

    cv2.namedWindow("calibrate", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("calibrate", on_mouse)

    total_trays = len(trays)

    while True:
        overlay = draw_overlay(img, current_name, tray_index, total_trays, slot_index, slots_done)
        cv2.imshow("calibrate", overlay)

        key = cv2.waitKey(20) & 0xFF

        # auto-advance when tray finished
        if slot_index >= SLOTS_PER_TRAY:
            tray_results.append({"name": current_name, "slots": slots_done.copy()})
            print(f"Captured tray '{current_name}' with {len(slots_done)} slots.")

            tray_index += 1
            if tray_index >= total_trays:
                break

            current_tray = trays[tray_index]
            current_name = current_tray["name"]
            slots_done = []
            slot_index = 0
            temp_first_point = None
            continue

        if key == ord("u"):
            if slots_done:
                slots_done.pop()
                slot_index = max(0, slot_index - 1)
                temp_first_point = None

        elif key == ord("r"):
            slots_done = []
            slot_index = 0
            temp_first_point = None

        elif key == ord("n"):
            tray_results.append({"name": current_name, "slots": slots_done.copy()})
            tray_index += 1
            if tray_index >= total_trays:
                break

            current_tray = trays[tray_index]
            current_name = current_tray["name"]
            slots_done = []
            slot_index = 0
            temp_first_point = None

        elif key == ord("q"):
            break

    cv2.destroyAllWindows()
    save(tray_results, w, h)


if __name__ == "__main__":
    main()
