# ZoneLogic

Draw zones on camera footage, pick object classes, and get timestamped incident tickets with
evidence when a rule is breached. One rule engine, two demo configurations:
a clear-path zone (accessibility / egress) and a bottle-in-general-waste zone.

Built solo for the VAST Builders Challenge (NYC, 2026-10-09).

This is a rule engine over detections, not a validated monitoring product. YOLO does not know
what material a bottle is made of, and the clear-path zone does not measure wheelchair clearance.

## Layout
- zonelogic/geometry.py   point/polygon/box math (normalized coordinates)
- zonelogic/engine.py     tracker + enter/dwell rules, one event per entry (tested)
- zonelogic/crosscheck.py compares caption claims with detections (to be extended)
- zonelogic/clips.py      clip store; replays stored detections through the engine, per clip or per camera
- zonelogic/vast.py       VAST detection sidecar (pixel xyxy, 30 fps, per 5 s segment) -> normalized frames
- zonelogic/server.py     standard-library web server (no pip needed); video served with Range support
- zonelogic/static/       polygon editor, rule form, incident tickets, alert banner + beep
- scripts/fetch_vast_clips.py      pulls chunks (sidecars + segment videos) from the VSS API on the VM
- scripts/make_synthetic_clips.py  SYNTHETIC test clips for local UI work (not VAST data)
- tests/                  pytest

## Run
    python3 scripts/make_synthetic_clips.py          # optional synthetic test clips
    set -a && source /config/team-20.config && set +a   # on the workshop VM only
    python3 scripts/fetch_vast_clips.py --camera nyc_streets_cam-2 --sources sources.txt
    python3 -m zonelogic.server 8080                 # then open http://localhost:8080/

Only pytest is needed for tests. VAST footage and detections are fetched into data/ and are not committed.
- docs/PLAN.md            schedule and cut list
