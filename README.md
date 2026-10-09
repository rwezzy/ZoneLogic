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
- tests/                  pytest
- docs/PLAN.md            schedule and cut list
