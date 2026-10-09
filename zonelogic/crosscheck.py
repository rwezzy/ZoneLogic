"""Second opinion on an incident: does the Cosmos caption for that segment agree with YOLO?

YOLO fires the rule; the caption is independent evidence from a different model. We only check
whether the caption mentions the detected class, mentions it negated ("no pedestrians"), or is silent.
"""
import re

# Caption words -> COCO classes they refer to.
SYNONYMS = {
    "person": {"person"}, "people": {"person"}, "pedestrian": {"person"}, "man": {"person"},
    "woman": {"person"}, "worker": {"person"}, "child": {"person"}, "individual": {"person"},
    "cyclist": {"person", "bicycle"}, "bicycle": {"bicycle"}, "bike": {"bicycle"},
    "car": {"car"}, "sedan": {"car"}, "suv": {"car"}, "taxi": {"car"}, "cab": {"car"},
    "van": {"car", "truck"}, "pickup": {"truck"}, "truck": {"truck"}, "bus": {"bus"},
    "vehicle": {"car", "truck", "bus", "motorcycle"}, "motorcycle": {"motorcycle"},
    "dog": {"dog"}, "bottle": {"bottle"}, "cup": {"cup"}, "chair": {"chair"}, "bench": {"bench"},
}
NEGATORS = {"no", "not", "without", "none", "nor", "zero"}
IRREGULAR = {"people": "people", "buses": "bus", "taxis": "taxi", "men": "man", "women": "woman",
             "children": "child", "boxes": "box"}


def _lemma(w):
    if w in IRREGULAR:
        return IRREGULAR[w]
    if w.endswith("s") and w[:-1] in SYNONYMS:
        return w[:-1]
    return w


def corroborate(cls, caption, window=4):
    """'agrees' | 'contradicts' | 'silent' for a YOLO class against a caption."""
    if not caption:
        return "silent"
    positive = negative = False
    for sentence in re.split(r"[.;!?]", caption.lower()):
        words = re.findall(r"[a-z]+", sentence)
        for i, w in enumerate(words):
            if cls not in SYNONYMS.get(_lemma(w), ()):
                continue
            if NEGATORS & set(words[max(0, i - window):i]):
                negative = True
            else:
                positive = True
    if positive:
        return "agrees"
    return "contradicts" if negative else "silent"
