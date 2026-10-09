# Plan (deadline 4:30 PM ET; engine built at 12:07)
1. Inspect real YOLO sidecar boxes for a warehouse clip; test whether $YOLO_URL accepts a single frame.
   Fallback for custom video: local yolo11s via ultralytics.
2. Adapter: sidecar/endpoint -> {cls, conf, box normalized, t}. Engine stays source-independent.
3. FastAPI + canvas polygon editor + incident list (class, rule, time, screenshot, resolve button).
4. Demo A: warehouse clear-path zone (dwell rule). Demo B: staged bottle recording (enter rule).
5. Use Cosmos caption for the incident segment as context; flag contradictions via crosscheck.
6. Deploy with /deploy-app-no-registry, record demo, push, submit by 4:00.
Cut order: webcam live mode, Cosmos context, sound, polish.
