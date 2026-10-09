# Narrate

Voice-first, keyboard-navigable event history of a home camera for blind and low-vision users,
built for the VAST Builders Challenge (NYC, 2026-10-09).

Every spoken claim is cross-checked against YOLO detections for the cited clip. Claims the
detections do not support are flagged "unconfirmed" aloud. Narrate never certifies safety.

Data: Pack D (neighborhood, `neighborhood_cam-1`). Fallback: Pack C (warehouse).
Uses VAST retrieval skills, Cosmos3-Reason captions, YOLO11s detections, W&B serverless LLM.
See docs/PLAN.md.

## Layout
- narrate/verifier.py  caption-claim vs detection cross-check (pure logic, tested)
- tests/               pytest
- docs/PLAN.md         schedule, scope, cut list
