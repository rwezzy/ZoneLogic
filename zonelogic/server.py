"""ZoneLogic web app, standard library only (the workshop VM and deploy image have no pip).

Run: python -m zonelogic.server [port]   (or PORT env var; default 8080)
The frontend uses relative URLs; the workshop /app ingress strips its prefix before it reaches us.
"""
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import clips

STATIC = Path(__file__).resolve().parent / "static"
STATIC_FILES = {"/": ("index.html", "text/html; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8")}
SAFE_NAME = re.compile(r"[A-Za-z0-9][\w.-]*")


def video_dir():
    return Path(os.environ.get("ZL_VIDEO_DIR", clips.DATA_DIR.parent / "videos"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep the console readable
        if os.environ.get("ZL_LOG"):
            super().log_message(fmt, *args)

    def _send(self, code, body, ctype, extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _error(self, code, msg):
        self._json({"detail": msg}, code)

    def _video(self, name):
        path = video_dir() / name
        if not SAFE_NAME.fullmatch(name) or not path.is_file():
            return self._error(404, "no such video")
        size = path.stat().st_size
        ctype = "video/webm" if name.endswith(".webm") else "video/mp4"
        start, end = 0, size - 1
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m and (m[1] or m[2]):
            if m[1]:
                start, end = int(m[1]), min(int(m[2]) if m[2] else size - 1, size - 1)
            else:  # suffix range: last N bytes
                start = max(0, size - int(m[2]))
            if start > end:
                return self._send(416, b"", ctype, [("Content-Range", f"bytes */{size}")])
        with open(path, "rb") as fh:
            fh.seek(start)
            body = fh.read(end - start + 1)
        if m and (m[1] or m[2]):
            self._send(206, body, ctype, [("Accept-Ranges", "bytes"), ("Content-Range", f"bytes {start}-{end}/{size}")])
        else:
            self._send(200, body, ctype, [("Accept-Ranges", "bytes")])

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        try:
            if path in STATIC_FILES:
                name, ctype = STATIC_FILES[path]
                return self._send(200, (STATIC / name).read_bytes(), ctype)
            if path == "/health":
                return self._json({"ok": True})
            if path == "/api/clips":
                return self._json(clips.list_clips())
            if m := re.fullmatch(r"/api/clips/([^/]+)", path):
                try:
                    return self._json(clips.load_clip(m[1]))
                except KeyError:
                    return self._error(404, f"no clip {m[1]}")
            if m := re.fullmatch(r"/videos/([^/]+)", path):
                return self._video(m[1])
            self._error(404, "not found")
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser cancelled a video request

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            zones, rules = body["zones"], body["rules"]
        except (ValueError, KeyError):
            return self._error(400, "body must be JSON with 'zones' and 'rules'")
        try:
            if m := re.fullmatch(r"/api/clips/([^/]+)/evaluate", path):
                try:
                    clip = clips.load_clip(m[1])
                except KeyError:
                    return self._error(404, f"no clip {m[1]}")
                return self._json({"events": clips.evaluate(clip, zones, rules)})
            if m := re.fullmatch(r"/api/cameras/([^/]+)/evaluate", path):
                return self._json({"events": clips.evaluate_camera(m[1], zones, rules)})
        except (KeyError, TypeError, ValueError) as e:
            return self._error(400, f"bad zone or rule: {e}")
        self._error(404, "not found")


def make_server(port=None, host="0.0.0.0"):
    return ThreadingHTTPServer((host, int(port or os.environ.get("PORT", 8080))), Handler)


if __name__ == "__main__":
    srv = make_server(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"ZoneLogic on http://localhost:{srv.server_address[1]}  (clips: {clips.DATA_DIR})")
    srv.serve_forever()
