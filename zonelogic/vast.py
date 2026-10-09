"""Convert VAST detection sidecars (yolo11_coco perception JSON) into ZoneLogic frames.

Sidecar shape (one per 5 s segment), as returned by the VSS detections API:
{"video_shape": [H, W], "fps": 30.0, "frames": [{"frame_index", "time_sec", "shape": [H, W],
  "detections": [{"label", "confidence", "bbox": [x1, y1, x2, y2]}]}]}   # bbox in pixels
"""
import re

SEGMENT_RE = re.compile(r"^(?P<chunk>.+_chunk_\d+)_segment_(?P<i>\d+)_of_(?P<n>\d+)\.mp4$")


def parse_segment(source):
    """'s3://b/segments/X_chunk_0001_segment_002_of_006.mp4' -> ('X_chunk_0001', 2, 6)."""
    name = source.rsplit("/", 1)[-1]
    m = SEGMENT_RE.match(name)
    if not m:
        raise ValueError(f"not a segment file name: {name}")
    return m["chunk"], int(m["i"]), int(m["n"])


def segment_sources(source):
    """All segment sources of the chunk that `source` belongs to, in order."""
    prefix = source.rsplit("/", 1)[0]
    chunk, _, n = parse_segment(source)
    return [f"{prefix}/{chunk}_segment_{i:03d}_of_{n:03d}.mp4" for i in range(1, n + 1)]


def sidecar_to_frames(sidecar, t0=0.0, stride=1):
    """Normalized frames with absolute time t0 + time_sec. Keeps every `stride`-th frame."""
    out = []
    for f in sidecar["frames"][::stride]:
        h, w = f.get("shape") or sidecar["video_shape"]
        dets = [{
            "cls": d["label"],
            "conf": round(d["confidence"], 4),
            "box": [round(min(max(v / s, 0.0), 1.0), 4) for v, s in zip(d["bbox"], (w, h, w, h))],
        } for d in f["detections"]]
        out.append({"t": round(t0 + f["time_sec"], 3), "dets": dets})
    return out
