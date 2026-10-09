"""Write SYNTHETIC clips (made-up boxes) for local UI and API testing only. Not VAST data.

Camera "synthetic-cam": a car that stops for 6 s mid-frame, a person walking across,
and a bottle that moves from the left half into the right half.
"synthetic-video" additionally renders those boxes into 5 s .webm segments (needs OpenCV),
so the segment playlist player and box/video alignment can be checked without the VM.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS, DUR, SEG = 5, 20, 5.0
SYNTHETIC_CAPTIONS = [  # made up, to exercise the caption cross-check in the UI
    "Synthetic scene. A grey car drives toward the center of the frame while a person walks left.",
    "Synthetic scene. There are no vehicles in the scene; a person walks along the bottom edge.",
    "Synthetic scene. A person walks along the bottom edge of the frame.",
    "Synthetic scene. A grey car leaves the frame to the right.",
]


def box(cx, cy, w, h):
    return [round(cx - w / 2, 4), round(cy - h / 2, 4), round(cx + w / 2, 4), round(cy + h / 2, 4)]


def dets_at(t, car_stop):
    if t < car_stop:  # car drives left to right, holds at x=0.5 for 6 s
        cx = 0.05 + 0.45 * t / car_stop
    elif t < car_stop + 6:
        cx = 0.5
    else:
        cx = 0.5 + 0.5 * (t - car_stop - 6) / (DUR - car_stop - 6)
    dets = []
    if cx < 0.98:
        dets.append({"cls": "car", "conf": 0.88, "box": box(cx, 0.62, 0.16, 0.12)})
    dets.append({"cls": "person", "conf": 0.8, "box": box(0.9 - 0.04 * t, 0.8, 0.05, 0.18)})
    if 2 <= t <= 12:
        dets.append({"cls": "bottle", "conf": 0.7, "box": box(0.2 + 0.06 * (t - 2), 0.3, 0.03, 0.07)})
    return dets


def clip(clip_id, car_stop, fps=FPS):
    frames = [{"t": round(i / fps, 3), "dets": dets_at(i / fps, car_stop)} for i in range(int(DUR * fps) + 1)]
    return {"id": clip_id, "camera_id": "synthetic-cam", "source": "synthetic",
            "video_url": None, "duration": DUR, "frames": frames}


def render_segments(c, video_dir, size=(640, 360), fps=10):
    import cv2
    import numpy as np
    w, h = size
    colors = {"car": (180, 180, 180), "person": (60, 160, 230), "bottle": (60, 200, 90)}
    segs = []
    for k in range(int(DUR / SEG)):
        name = f"{c['id']}_segment_{k + 1:03d}.webm"
        out = cv2.VideoWriter(str(video_dir / name), cv2.VideoWriter_fourcc(*"VP80"), fps, size)
        if not out.isOpened():
            raise RuntimeError("OpenCV cannot write VP8 webm here")
        for i in range(int(SEG * fps)):
            t = k * SEG + i / fps
            img = np.full((h, w, 3), 40, np.uint8)
            for d in dets_at(t, 4):
                x1, y1, x2, y2 = d["box"]
                cv2.rectangle(img, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)), colors[d["cls"]], -1)
            cv2.putText(img, f"SYNTHETIC  t={t:4.1f}s", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            out.write(img)
        out.release()
        segs.append({"t0": k * SEG, "duration": SEG, "video": f"videos/{name}",
                     "caption": SYNTHETIC_CAPTIONS[k % len(SYNTHETIC_CAPTIONS)]})
    return segs


def write_all(clip_dir, video_dir=None):
    clip_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for cid, stop in (("synthetic-a", 4), ("synthetic-b", 9)):
        (clip_dir / f"{cid}.json").write_text(json.dumps(clip(cid, stop)))
        written.append(cid)
    if video_dir is not None:
        try:
            video_dir.mkdir(parents=True, exist_ok=True)
            c = clip("synthetic-video", 4, fps=10)
            c["segments"] = render_segments(c, video_dir)
            (clip_dir / "synthetic-video.json").write_text(json.dumps(c))
            written.append("synthetic-video")
        except (ImportError, RuntimeError) as e:
            print("skipped synthetic-video:", e, file=sys.stderr)
    return written


if __name__ == "__main__":
    print("wrote", write_all(ROOT / "data" / "clips", ROOT / "data" / "videos"))
