"""Fetch VAST chunks (6 x 5 s segments) into ZoneLogic clip files. Run ON THE WORKSHOP VM.

    set -a && source /config/team-20.config && set +a
    python3 scripts/fetch_vast_clips.py --camera nyc_streets_cam-2 --sources sources.txt

sources.txt: one s3:// segment source per line (any segment of each chunk you want).
Writes data/clips/<chunk>.json and data/videos/<segment>.mp4. Standard library only.
Credentials come from the environment (INGRESS_URL, USERNAME, PASSWORD) and are never printed.
VAST data stays in data/, which is gitignored: do not commit it.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zonelogic.vast import parse_segment, segment_sources, sidecar_to_frames  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOGIN_PATH = "/api/v1/auth/login"           # confirmed by Cursor on the VM
PLAYBACK_PATH = "/api/v1/videos/playback-url"  # confirmed: ?source=&token=&expires_in= -> {"url": ...}
DETECTIONS_PATH = "/api/v1/videos/detections"  # VERIFY against .cursor/skills/retrieval/videos (param name too)
DETECTIONS_PARAM = "source"                    # VERIFY


def http_json(url, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(url, data, headers), timeout=60) as r:
        return json.loads(r.read())


def login(base):
    out = http_json(base + LOGIN_PATH, body={"username": os.environ["USERNAME"], "password": os.environ["PASSWORD"]})
    return out["access_token"]


def get_sidecar(base, token, source):
    q = urllib.parse.urlencode({DETECTIONS_PARAM: source})
    out = http_json(f"{base}{DETECTIONS_PATH}?{q}", token)
    if "frames" in out:
        return out
    for v in out.values():  # tolerate one level of wrapping, e.g. {"detections": {...}}
        if isinstance(v, dict) and "frames" in v:
            return v
    raise ValueError(f"no 'frames' in detections response; keys: {list(out)}")


def download_video(base, token, source, dest):
    q = urllib.parse.urlencode({"source": source, "token": token, "expires_in": 3600})
    url = http_json(f"{base}{PLAYBACK_PATH}?{q}", token)["url"]
    with urllib.request.urlopen(url, timeout=120) as r:
        dest.write_bytes(r.read())


def fetch_chunk(base, token, seed, camera, stride, clip_dir, video_dir):
    chunk, _, _ = parse_segment(seed)
    segments, frames, t0 = [], [], 0.0
    for src in segment_sources(seed):
        name = src.rsplit("/", 1)[-1]
        try:
            sc = get_sidecar(base, token, src)
            download_video(base, token, src, video_dir / name)
        except (urllib.error.HTTPError, ValueError) as e:
            print(f"  stop at {name}: {e}", file=sys.stderr)
            break  # keep the timeline contiguous: no gaps inside a clip
        dur = sc["frame_count"] / sc["fps"]
        frames += sidecar_to_frames(sc, t0=t0, stride=stride)
        segments.append({"t0": t0, "duration": dur, "video": f"videos/{name}", "source": src})
        print(f"  {name}: {len(sc['frames'])} frames, {sc.get('detection_count', '?')} detections")
        t0 += dur
    if not segments:
        return None
    clip = {"id": chunk, "camera_id": camera, "source": "vast", "video_url": None,
            "duration": round(t0, 3), "segments": segments, "frames": frames}
    (clip_dir / f"{chunk}.json").write_text(json.dumps(clip))
    return clip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", required=True, help="camera_id the chunks belong to, e.g. nyc_streets_cam-2")
    ap.add_argument("--sources", required=True, help="file with one s3:// segment source per line")
    ap.add_argument("--stride", type=int, default=3, help="keep every Nth frame (sidecars are 30 fps)")
    a = ap.parse_args()
    base = os.environ["INGRESS_URL"].rstrip("/")
    clip_dir, video_dir = ROOT / "data" / "clips", ROOT / "data" / "videos"
    clip_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    token = login(base)
    seeds = [l.strip() for l in Path(a.sources).read_text().splitlines() if l.strip()]
    seen = set()
    for seed in seeds:
        chunk = parse_segment(seed)[0]
        if chunk in seen:
            continue
        seen.add(chunk)
        print(chunk)
        c = fetch_chunk(base, token, seed, a.camera, a.stride, clip_dir, video_dir)
        print(f"  -> {len(c['segments'])} segments, {c['duration']} s" if c else "  -> nothing fetched")


if __name__ == "__main__":
    main()
