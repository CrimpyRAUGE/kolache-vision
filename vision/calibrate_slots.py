import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "config" / "layout.json"
OUT_PATH = ROOT / "config" / "vision_rois.json"
IMG_PATH = ROOT / "captures" / "calibration.jpg"

SLOTS_PER_TRAY = 12

# --- click state ---
clicks = []  # store points [(x,y), (x,y)] per slot
current_tray_name = None
tray_results = []  # list of {"name":..., "slots":[...]}
tray_index = 0
slot_index = 0

def load_tray_names():
    layout = json.loads(LAYOUT_PATH.read_text())
    # keep only trays that exist in layout.json
    return [t["name"] for t in layout["trays"]]

def rect_from_two_points(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    return [int(x), int(y), int(w), int(h)]

def draw_overlay(img, tray_name, slot_idx, slots_done, last_rect=None):
    out = img.copy()

    # draw completed slots
    for r in slots_done:
        x, y, w, h = r
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # draw current in-progress rect
    if last_rect is not None:
        x, y, w, h = last_rect
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 215, 255), 2)

    # instruction text
    cv2.rectangle(out, (10, 10), (900, 110), (0, 0, 0), -1)
    cv2.putText(out, f"Tray: {tray_name}", (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(out, f"Slot {slot_idx+1}/{SLOTS_PER_TRAY}: click TOP-LEFT then BOTTOM-RIGHT",
                (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    cv2.putText(out, "Keys: n=next tray, u=undo slot, r=reset tray, q=quit/save",
                (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    return out

def save(rois, img_w, img_h):
    data = {
        "camera": {
            "source": 0,
            "resolution": [img_w, img_h],
            "rotate": 0,
            "interval_seconds": 3,
            "occupied_threshold": 12.0
        },
        "trays": rois
    }
    OUT_PATH.write_text(json.dumps(data, indent=2))
    print(f"Saved: {OUT_PATH}")

def main():
    global current_tray_name, tray_index, slot_index, clicks, tray_results

    if not IMG_PATH.exists():
        raise RuntimeError(f"Missing {IMG_PATH}. Run vision/capture_frame.py first.")

    tray_names = load_tray_names()
    if not tray_names:
        raise RuntimeError("No trays found in config/layout.json")

    img = cv2.imread(str(IMG_PATH))
    if img is None:
        raise RuntimeError("Failed to read calibration image")

    h, w = img.shape[:2]

    current_tray_name = tray_names[tray_index]
    slots_done = []
    temp_first_point = None

    def on_mouse(event, x, y, flags, param):
        nonlocal temp_first_point, slots_done, slot_index, img

        if event == cv2.EVENT_LBUTTONDOWN:
            if temp_first_point is None:
                temp_first_point = (x, y)
            else:
                # second click completes a rectangle
                rect = rect_from_two_points(temp_first_point, (x, y))
                temp_first_point = None

                # ignore accidental tiny boxes
                if rect[2] < 5 or rect[3] < 5:
                    return

                slots_done.append(rect)
                slot_index += 1

    cv2.namedWindow("calibrate", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("calibrate", on_mouse)

    while True:
        last_rect = None
        if temp_first_point is not None:
            # show a preview rectangle from first point to current mouse position (approx)
            mx, my = cv2.getWindowImageRect("calibrate")[0:2]  # not reliable for mouse pos
            # we'll skip live preview; you'll see the box after 2nd click
            last_rect = None

        overlay = draw_overlay(img, current_tray_name, slot_index, slots_done, last_rect)
        cv2.imshow("calibrate", overlay)

        key = cv2.waitKey(20) & 0xFF

        # auto-advance when tray finished
        if slot_index >= SLOTS_PER_TRAY:
            tray_results.append({"name": current_tray_name, "slots": slots_done.copy()})
            print(f"Captured tray '{current_tray_name}' with {len(slots_done)} slots.")
            tray_index += 1
            if tray_index >= len(tray_names):
                break
            current_tray_name = tray_names[tray_index]
            slots_done = []
            slot_index = 0
            temp_first_point = None

        if key == ord("u"):
            # undo last slot
            if slots_done:
                slots_done.pop()
                slot_index = max(0, slot_index - 1)
                temp_first_point = None

        if key == ord("r"):
            # reset current tray
            slots_done = []
            slot_index = 0
            temp_first_point = None

        if key == ord("n"):
            # next tray (even if incomplete)
            tray_results.append({"name": current_tray_name, "slots": slots_done.copy()})
            tray_index += 1
            if tray_index >= len(tray_names):
                break
            current_tray_name = tray_names[tray_index]
            slots_done = []
            slot_index = 0
            temp_first_point = None

        if key == ord("q"):
            break

    cv2.destroyAllWindows()

    # Save whatever we captured so far
    save(tray_results, w, h)

if __name__ == "__main__":
    main()
