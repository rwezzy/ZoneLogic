"""Cross-check spoken claims against YOLO detections for the cited clip."""
from dataclasses import dataclass

# Caption words -> YOLO classes that would support them.
SYNONYMS = {
    "person": {"person"}, "man": {"person"}, "woman": {"person"}, "pedestrian": {"person"},
    "courier": {"person"}, "child": {"person"},
    "car": {"car"}, "vehicle": {"car", "truck", "bus"}, "suv": {"car"}, "truck": {"truck"},
    "van": {"car", "truck"}, "bus": {"bus"}, "bicycle": {"bicycle"}, "bike": {"bicycle"},
    "motorcycle": {"motorcycle"}, "dog": {"dog"},
}


@dataclass
class Verdict:
    status: str  # "confirmed" | "unconfirmed" | "unverifiable"
    missing: list


def verify_claim(claim_text, detections, min_conf=0.3):
    """detections: iterable of dicts with 'class' and optional 'confidence'."""
    seen = {d["class"] for d in detections if d.get("confidence", 1.0) >= min_conf}
    words = [w.strip(".,;:!?").lower() for w in claim_text.split()]
    mentioned = [w for w in words if w in SYNONYMS]
    if not mentioned:
        return Verdict("unverifiable", [])
    missing = [w for w in mentioned if not (SYNONYMS[w] & seen)]
    return Verdict("unconfirmed" if missing else "confirmed", missing)
