"""Source-independent rule engine: detections in, incident events out.

A detection is a dict: {"cls": str, "conf": float, "box": [x1, y1, x2, y2]} (normalized).
Feed one frame's detections at a time with its timestamp in seconds.
"""
from dataclasses import dataclass, field
from itertools import count

from .geometry import anchor_point, center_dist, iou, overlap_ratio, point_in_polygon


@dataclass
class Zone:
    name: str
    polygon: list  # [(x, y), ...] normalized


@dataclass
class Rule:
    id: str
    zone: str
    classes: set
    trigger: str = "enter"      # "enter": outside -> inside transition; "dwell": inside for dwell_s
    dwell_s: float = 0.0
    min_conf: float = 0.4
    anchor: str = "bottom"      # "bottom" | "center" | "overlap"
    min_overlap: float = 0.3    # used when anchor == "overlap"
    action: str = "alert"       # label only; the app decides what to do


@dataclass
class Event:
    id: int
    rule: str
    zone: str
    cls: str
    track_id: int
    t: float
    conf: float
    box: list
    trigger: str
    status: str = "open"


@dataclass
class _Track:
    id: int
    cls: str
    box: list
    conf: float
    last_t: float
    inside_since: dict = field(default_factory=dict)  # rule id -> t first seen inside
    was_inside: dict = field(default_factory=dict)    # rule id -> bool
    fired: set = field(default_factory=set)           # rule ids already fired for this entry


class Engine:
    def __init__(self, zones, rules, match_iou=0.2, max_gap_s=1.5, max_center_dist=0.15):
        self.zones = {z.name: z for z in zones}
        self.rules = list(rules)
        self.match_iou = match_iou
        self.max_gap_s = max_gap_s
        self.max_center_dist = max_center_dist  # fallback match when sampling is too sparse for IoU
        self.tracks = []
        self.events = []
        self._track_ids = count(1)
        self._event_ids = count(1)

    def _inside(self, rule, box):
        poly = self.zones[rule.zone].polygon
        if rule.anchor == "overlap":
            return overlap_ratio(box, poly) >= rule.min_overlap
        return point_in_polygon(*anchor_point(box, rule.anchor), poly)

    def _associate(self, dets, t):
        self.tracks = [k for k in self.tracks if t - k.last_t <= self.max_gap_s]
        used, out = set(), []
        for d in sorted(dets, key=lambda d: -d["conf"]):
            best, best_iou = None, self.match_iou
            for k in self.tracks:
                if k.id in used or k.cls != d["cls"]:
                    continue
                v = iou(k.box, d["box"])
                if v >= best_iou:
                    best, best_iou = k, v
            if best is None:  # no overlap: take the nearest same-class track, if close enough
                best_d = self.max_center_dist
                for k in self.tracks:
                    if k.id in used or k.cls != d["cls"]:
                        continue
                    dist = center_dist(k.box, d["box"])
                    if dist <= best_d:
                        best, best_d = k, dist
            if best is None:
                best = _Track(next(self._track_ids), d["cls"], d["box"], d["conf"], t)
                self.tracks.append(best)
            used.add(best.id)
            best.box, best.conf, best.last_t = d["box"], d["conf"], t
            out.append(best)
        return out

    def process(self, dets, t):
        new_events = []
        for k in self._associate(dets, t):
            for r in self.rules:
                if k.cls not in r.classes or k.conf < r.min_conf:
                    continue
                inside = self._inside(r, k.box)
                was = k.was_inside.get(r.id)
                if inside:
                    k.inside_since.setdefault(r.id, t)
                    fire = r.id not in k.fired and (
                        (r.trigger == "enter" and was is False)
                        or (r.trigger == "dwell" and t - k.inside_since[r.id] >= r.dwell_s)
                    )
                    if fire:
                        k.fired.add(r.id)
                        ev = Event(next(self._event_ids), r.id, r.zone, k.cls, k.id,
                                   t, k.conf, list(k.box), r.trigger)
                        self.events.append(ev)
                        new_events.append(ev)
                else:
                    k.inside_since.pop(r.id, None)
                    k.fired.discard(r.id)  # leaving re-arms the rule
                k.was_inside[r.id] = inside
        return new_events
