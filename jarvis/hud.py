"""On-screen HUD for Jarvis — a movie-style reactor that reacts to state.

Runs a tiny localhost web server in a background thread inside the Jarvis
process (no extra dependencies). The voice loop calls `set_state()` as it moves
through idle -> listening -> thinking -> speaking, and the browser page
(`hud.html`) animates accordingly via Server-Sent Events.

Open http://127.0.0.1:8765 fullscreen on the Mac mini's display.
"""
import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config

_HTML = Path(__file__).resolve().parent / "hud.html"


class _State:
    """Thread-safe current state plus a fan-out to SSE subscribers."""

    def __init__(self):
        self._lock = threading.Lock()
        self._current = {"state": "idle", "text": "", "seq": 0}
        self._subscribers = set()

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._current)

    def update(self, state: str, text: str):
        with self._lock:
            self._current = {
                "state": state,
                "text": text,
                "seq": self._current["seq"] + 1,
            }
            payload = json.dumps(self._current)
            dead = []
            for q in self._subscribers:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._subscribers.discard(q)

    def subscribe(self) -> "queue.Queue[str]":
        q: "queue.Queue[str]" = queue.Queue(maxsize=32)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subscribers.discard(q)


def _make_handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence the default access log
            pass

        def do_GET(self):
            if self.path.startswith("/events"):
                self._serve_events()
            elif self.path.startswith("/state"):
                self._serve_bytes(
                    json.dumps(state.snapshot()).encode(), "application/json"
                )
            else:
                try:
                    body = _HTML.read_bytes()
                except FileNotFoundError:
                    body = b"<h1>Jarvis HUD</h1><p>hud.html is missing.</p>"
                self._serve_bytes(body, "text/html; charset=utf-8")

        def _serve_bytes(self, body: bytes, content_type: str):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _serve_events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = state.subscribe()
            try:
                self._send(json.dumps(state.snapshot()))
                while True:
                    try:
                        self._send(q.get(timeout=15))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")  # keep the connection warm
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                state.unsubscribe(q)

        def _send(self, data: str):
            self.wfile.write(f"data: {data}\n\n".encode())
            self.wfile.flush()

    return Handler


class Hud:
    """Background HUD server. A no-op when disabled in config."""

    def __init__(self):
        self._state = _State()
        self._server = None

    def start(self) -> "Hud":
        if not config.HUD_ENABLED:
            return self
        try:
            server = ThreadingHTTPServer(
                (config.HUD_HOST, config.HUD_PORT), _make_handler(self._state)
            )
        except OSError:
            # Port busy / unavailable — run without the HUD rather than crash.
            return self
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self._server = server
        return self

    def set_state(self, state: str, text: str = ""):
        if self._server is not None:
            self._state.update(state, text)
