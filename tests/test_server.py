import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import make_synthetic_clips  # noqa: E402

from zonelogic import clips, server  # noqa: E402

LANE = {"name": "lane", "polygon": [[0.4, 0.5], [0.6, 0.5], [0.6, 0.75], [0.4, 0.75]]}
RIGHT = {"name": "waste", "polygon": [[0.5, 0], [1, 0], [1, 0.5], [0.5, 0.5]]}
STOPPED = {"id": "r1", "zone": "lane", "classes": ["car"], "trigger": "dwell", "dwell_s": 3}
BOTTLE_IN = {"id": "r2", "zone": "waste", "classes": ["bottle"], "trigger": "enter"}


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    make_synthetic_clips.write_all(d / "clips")
    (d / "videos").mkdir()
    (d / "videos" / "x.mp4").write_bytes(bytes(range(256)) * 4)  # 1024 bytes
    old = clips.DATA_DIR
    clips.DATA_DIR = d / "clips"
    srv = server.make_server(port=0, host="127.0.0.1")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    clips.DATA_DIR = old


def get(url, headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {})) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_index_health_and_clips(base):
    assert get(base + "/")[0] == 200
    assert get(base + "/health")[0] == 200
    ids = [x["id"] for x in json.loads(get(base + "/api/clips")[1])]
    assert {"synthetic-a", "synthetic-b"} <= set(ids)
    assert get(base + "/api/clips/nope")[0] == 404


def test_evaluate_clip(base):
    code, body = post(base + "/api/clips/synthetic-a/evaluate", {"zones": [LANE, RIGHT], "rules": [STOPPED, BOTTLE_IN]})
    assert code == 200
    evs = body["events"]
    assert sorted((e["rule"], e["cls"]) for e in evs) == [("r1", "car"), ("r2", "bottle")]
    car = next(e for e in evs if e["rule"] == "r1")
    # bottom-center enters the lane at ~3.2 s (before the car stops at 4 s); dwell counts time inside
    assert 6.0 <= car["t"] <= 6.6


def test_evaluate_camera_runs_every_clip(base):
    _, body = post(base + "/api/cameras/synthetic-cam/evaluate", {"zones": [LANE], "rules": [STOPPED]})
    assert sorted(e["clip_id"] for e in body["events"]) == ["synthetic-a", "synthetic-b"]


def test_bad_requests(base):
    assert post(base + "/api/clips/synthetic-a/evaluate", {"zones": [LANE], "rules": [{**STOPPED, "zone": "x"}]})[0] == 400
    assert post(base + "/api/clips/synthetic-a/evaluate", {"rules": []})[0] == 400
    assert post(base + "/api/clips/nope/evaluate", {"zones": [], "rules": []})[0] == 404


def test_video_ranges_and_traversal(base):
    code, body, h = get(base + "/videos/x.mp4")
    assert code == 200 and len(body) == 1024 and h["Accept-Ranges"] == "bytes"
    code, body, h = get(base + "/videos/x.mp4", {"Range": "bytes=10-19"})
    assert code == 206 and body == bytes(range(10, 20)) and h["Content-Range"] == "bytes 10-19/1024"
    code, body, _ = get(base + "/videos/x.mp4", {"Range": "bytes=-4"})
    assert code == 206 and body == bytes(range(252, 256))
    assert get(base + "/videos/x.mp4", {"Range": "bytes=5000-"})[0] == 416
    assert get(base + "/videos/..%2Fclips%2Fsynthetic-a.json")[0] == 404


def test_events_carry_segment_caption_and_cosmos_verdict():
    frames = [{"t": i / 10, "dets": [{"cls": "car", "conf": 0.9, "box": [0.45, 0.55, 0.55, 0.7]}]} for i in range(100)]
    clip = {"id": "c", "segments": [
        {"t0": 0.0, "duration": 5.0, "caption": "A car is stopped on the crosswalk."},
        {"t0": 5.0, "duration": 5.0, "caption": "There are no vehicles in the scene."}],
        "frames": frames}
    early = {**STOPPED, "dwell_s": 3}
    late = {**STOPPED, "id": "r9", "dwell_s": 6}
    evs = {e["rule"]: e for e in clips.evaluate(clip, [LANE], [early, late])}
    assert evs["r1"]["cosmos"] == "agrees" and evs["r1"]["caption"].startswith("A car")
    assert evs["r9"]["cosmos"] == "contradicts"
    no_caption = clips.evaluate({**clip, "segments": None}, [LANE], [early])[0]
    assert no_caption["cosmos"] is None
