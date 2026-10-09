from zonelogic.engine import Engine, Rule, Zone

ZONE = Zone("waste", [(0.5, 0.5), (1.0, 0.5), (1.0, 1.0), (0.5, 1.0)])


def det(x, y, cls="bottle", conf=0.9, s=0.1):
    return {"cls": cls, "conf": conf, "box": [x, y, x + s, y + s]}


def run(rule, frames, fps=10):
    eng = Engine([ZONE], [rule])
    evs = []
    for i, dets in enumerate(frames):
        evs += eng.process(dets, i / fps)
    return evs


ENTER = Rule("r1", "waste", {"bottle"}, trigger="enter")


def test_enter_fires_once():
    path = [[det(0.30 + 0.04 * i, 0.60)] for i in range(12)]  # walks left to right into zone
    evs = run(ENTER, path)
    assert len(evs) == 1 and evs[0].cls == "bottle"


def test_present_from_first_frame_is_not_a_transition():
    assert run(ENTER, [[det(0.7, 0.6)]] * 20) == []


def test_reenter_fires_again():
    frames = [[det(0.30 + 0.04 * i, 0.60)] for i in range(12)]
    frames += [[det(0.78 - 0.04 * i, 0.60)] for i in range(12)]  # back out
    frames += [[det(0.30 + 0.04 * i, 0.60)] for i in range(12)]  # in again
    assert len(run(ENTER, frames)) == 2


def test_wrong_class_and_low_conf_ignored():
    path = lambda **kw: [[det(0.30 + 0.04 * i, 0.60, **kw)] for i in range(12)]
    assert run(ENTER, path(cls="cup")) == []
    assert run(ENTER, path(conf=0.2)) == []


def test_missed_detection_gap_does_not_duplicate():
    frames = [[det(0.30 + 0.04 * i, 0.60)] for i in range(8)]
    frames += [[], []]  # detector drops it for 0.2 s
    frames += [[det(0.62 + 0.01 * i, 0.60)] for i in range(10)]
    assert len(run(ENTER, frames)) == 1


def test_dwell():
    rule = Rule("r2", "waste", {"person"}, trigger="dwell", dwell_s=1.0)
    short = [[det(0.7, 0.6, "person")]] * 8     # 0.7 s inside
    long_ = [[det(0.7, 0.6, "person")]] * 25    # 2.4 s inside
    assert run(rule, short) == []
    assert len(run(rule, long_)) == 1


def test_overlap_anchor_catches_partial_entry():
    rule = Rule("r3", "waste", {"box"}, anchor="overlap", min_overlap=0.3, trigger="dwell", dwell_s=0.0)
    frames = [[det(0.42, 0.6, "box", s=0.2)]]  # right 0.12 of 0.2 width inside = 60%
    assert len(run(rule, frames)) == 1


def test_sparse_sampling_still_tracks():
    # 1 fps sidecar: box moves 0.12/step with width 0.1, so consecutive boxes have IoU 0.
    frames = [[det(0.30 + 0.12 * i, 0.60)] for i in range(5)]
    assert len(run(ENTER, frames, fps=1)) == 1


def test_far_apart_objects_are_not_merged():
    # Bottle disappears on the left, a different bottle appears far away inside the zone.
    frames = [[det(0.05, 0.60)], [det(0.80, 0.60)]]
    assert run(ENTER, frames, fps=1) == []
