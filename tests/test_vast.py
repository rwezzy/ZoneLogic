import pytest

from zonelogic.vast import parse_segment, segment_sources, sidecar_to_frames

# Structure copied from a real nyc_streets_cam-2 sidecar (values trimmed).
SIDECAR = {
    "source": "yolo11_coco",
    "video_shape": [1080, 1920],
    "fps": 30.0,
    "frame_count": 3,
    "frames": [
        {"frame_index": 0, "time_sec": 0.0, "shape": [1080, 1920], "detections": [
            {"label": "truck", "confidence": 0.9001, "bbox": [1454, 623, 1918, 992]},
            {"label": "car", "confidence": 0.8944, "bbox": [722, 818, 1083, 989]}]},
        {"frame_index": 1, "time_sec": 0.0333, "shape": [1080, 1920], "detections": []},
        {"frame_index": 2, "time_sec": 0.0667, "shape": [1080, 1920], "detections": [
            {"label": "car", "confidence": 0.9, "bbox": [0, 0, 1920, 1080]}]},
    ],
}
SRC = "s3://team-20-vss-chunks-segments/segments/20261008_071123_IMG_0509_chunk_0001_segment_002_of_006.mp4"


def test_normalizes_pixels_with_hw_shape():
    f = sidecar_to_frames(SIDECAR)
    truck = f[0]["dets"][0]
    assert truck["cls"] == "truck" and truck["conf"] == 0.9001
    assert truck["box"] == [round(1454 / 1920, 4), round(623 / 1080, 4), round(1918 / 1920, 4), round(992 / 1080, 4)]
    assert f[2]["dets"][0]["box"] == [0.0, 0.0, 1.0, 1.0]


def test_offset_and_stride():
    f = sidecar_to_frames(SIDECAR, t0=5.0, stride=2)
    assert [x["t"] for x in f] == [5.0, 5.067]


def test_segment_names():
    assert parse_segment(SRC) == ("20261008_071123_IMG_0509_chunk_0001", 2, 6)
    srcs = segment_sources(SRC)
    assert len(srcs) == 6 and srcs[0].endswith("_chunk_0001_segment_001_of_006.mp4") and srcs[1] == SRC
    with pytest.raises(ValueError):
        parse_segment("s3://b/segments/whatever.mp4")
