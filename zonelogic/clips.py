"""Clip store and rule evaluation over stored detections.

A clip file (data/clips/<id>.json) holds one camera's detections over time:
{"id", "camera_id", "source", "video_url" | null, "duration", "frames": [{"t": s, "dets": [...]}]}
Detections use the engine format: {"cls", "conf", "box": [x1, y1, x2, y2]} normalized.
"""
import json
import os
from dataclasses import asdict
from pathlib import Path

from .engine import Engine, Rule, Zone

DATA_DIR = Path(os.environ.get("ZL_DATA_DIR", Path(__file__).resolve().parent.parent / "data" / "clips"))


def list_clips():
    out = []
    for p in sorted(DATA_DIR.glob("*.json")):
        c = json.loads(p.read_text())
        out.append({k: c.get(k) for k in ("id", "camera_id", "source", "video_url", "duration")})
    return out


def load_clip(clip_id):
    p = DATA_DIR / f"{clip_id}.json"
    if p.parent != DATA_DIR or not p.exists():
        raise KeyError(clip_id)
    return json.loads(p.read_text())


def build(zones, rules):
    zs = [Zone(z["name"], [tuple(pt) for pt in z["polygon"]]) for z in zones]
    rs = [Rule(**{**r, "classes": set(r["classes"])}) for r in rules]
    return zs, rs


def evaluate(clip, zones, rules):
    """Replay a clip's detections through a fresh engine; returns event dicts."""
    eng = Engine(*build(zones, rules))
    for f in sorted(clip["frames"], key=lambda f: f["t"]):
        eng.process(f["dets"], f["t"])
    return [{**asdict(e), "clip_id": clip["id"]} for e in eng.events]


def evaluate_camera(camera_id, zones, rules):
    """Run one rule set over every stored clip from the same camera.

    Zones are drawn in image coordinates, so they only mean something on the camera they were drawn on.
    """
    events = []
    for meta in list_clips():
        if meta["camera_id"] == camera_id:
            events += evaluate(load_clip(meta["id"]), zones, rules)
    return events
