#!/usr/bin/env python3
"""
Dashboard API — Lightweight HTTP server for the lead CRM dashboard.
Serves static files and JSON data endpoints with basic auth.
"""

import base64
import json
import os
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

import requests

DASHBOARD_DIR = Path(__file__).resolve().parent
BASE_DIR = DASHBOARD_DIR.parent
sys.path.insert(0, str(BASE_DIR))

from config import load_config  # noqa: E402

CONFIG = load_config()
BASIC_AUTH_USER = CONFIG["dashboard"]["user"]
BASIC_AUTH_PASS = CONFIG["dashboard"]["password"]


def load_json(path, default=None):
    path = Path(path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path, data):
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def _authorized(self):
        if not BASIC_AUTH_PASS:
            return True  # auth disabled if no password set
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        except Exception:
            return False
        return decoded == f"{BASIC_AUTH_USER}:{BASIC_AUTH_PASS}"

    def _require_auth(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Summit Dashboard"')
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Authentication required")

    def do_GET(self):
        parsed = urlparse(self.path)
        public_paths = {"/birthday-freebies.html"}

        if parsed.path not in public_paths and not self._authorized():
            self._require_auth()
            return

        if parsed.path == "/api/contacts":
            self.send_json(load_json(BASE_DIR / "nurture_contacts.json", {"contacts": []}))
        elif parsed.path == "/api/tracks":
            self.send_json(load_json(BASE_DIR / "nurture_tracks.json", {}))
        elif parsed.path == "/api/leads":
            self.send_json(load_json(BASE_DIR / "lead_log.json", []))
        elif parsed.path == "/api/state":
            self.send_json(load_json(BASE_DIR / "state.json", {}))
        elif parsed.path == "/api/nurture_log":
            self.send_json(load_json(BASE_DIR / "nurture_log.json", []))
        elif parsed.path == "/api/config":
            safe = {
                "simpletexting": {"account_phone": CONFIG.get("simpletexting", {}).get("account_phone", "")},
                "justin": CONFIG.get("justin", {}),
            }
            self.send_json(safe)
        elif parsed.path == "/api/status":
            status = {
                "lead_monitor": False,
                "nurture_engine": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for name, pidfile in [("lead_monitor", "monitor.pid"), ("nurture_engine", "nurture_engine.pid")]:
                pf = BASE_DIR / pidfile
                if pf.exists():
                    try:
                        pid = int(open(pf).read().strip())
                        os.kill(pid, 0)
                        status[name] = True
                    except (ProcessLookupError, ValueError, PermissionError):
                        pass
            self.send_json(status)
        elif parsed.path == "/api/credits":
            try:
                headers = {
                    "Authorization": f"Bearer {CONFIG['simpletexting']['api_key']}",
                    "Content-Type": "application/json",
                }
                r = requests.get("https://api-app2.simpletexting.com/v2/api/account", headers=headers, timeout=15)
                self.send_json(r.json() if r.status_code == 200 else {"error": r.text})
            except Exception as e:
                self.send_json({"error": str(e)})
        else:
            super().do_GET()

    def do_POST(self):
        if not self._authorized():
            self._require_auth()
            return
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len)) if content_len > 0 else {}

        if parsed.path == "/api/contacts/add":
            from nurture_engine import add_contact
            result = add_contact(
                name=body.get("name", ""),
                phone=body.get("phone", ""),
                track=body.get("track", "cold"),
                **{k: v for k, v in body.items() if k not in ("name", "phone", "track")},
            )
            self.send_json({"ok": result})
        elif parsed.path == "/api/contacts/deactivate":
            from nurture_engine import deactivate_contact
            self.send_json({"ok": deactivate_contact(body.get("phone", ""))})
        elif parsed.path == "/api/contacts/reactivate":
            from nurture_engine import reactivate_contact
            self.send_json({"ok": reactivate_contact(body.get("phone", ""), body.get("track"))})
        elif parsed.path == "/api/contacts/update_stage":
            self._update_stage(body)
        elif parsed.path == "/api/contacts/quick_action":
            self._quick_action(body)
        elif parsed.path == "/api/contacts/log_call":
            self._log_call(body)
        else:
            self.send_error(404)

    def _update_stage(self, body):
        contacts_path = BASE_DIR / "nurture_contacts.json"
        contacts_data = load_json(contacts_path, {"contacts": []})
        phone = body.get("phone", "")
        stage = body.get("stage", "")
        allowed_stages = {
            "initial_lead", "contact_attempted", "connected",
            "application", "closed", "won", "lost", "past_client",
        }
        if stage not in allowed_stages:
            self.send_json({"ok": False, "error": "invalid_stage"})
            return

        phone_digits = "".join(c for c in phone if c.isdigit())
        now = datetime.now(timezone.utc).isoformat()
        for c in contacts_data.get("contacts", []):
            if "".join(d for d in c.get("phone", "") if d.isdigit()) != phone_digits:
                continue
            if c.get("contact_type", "lead") != "lead":
                self.send_json({"ok": False, "error": "not_lead_contact"})
                return
            c.setdefault("pipeline", {})[stage] = now
            c["current_stage"] = stage

            if stage == "past_client":
                c["track"] = "past_client"
                c["active"] = True
            elif stage == "application" and c.get("track") in (None, "cold", "warm", "hot"):
                c["track"] = "active_preapproval"
                c["active"] = True
            elif stage in ("closed", "won", "lost"):
                c["active"] = True
            elif c.get("track") == "past_client" and stage != "past_client":
                c["track"] = "warm"
                c["active"] = True
            elif c.get("active") is False:
                c["active"] = True

            save_json(contacts_path, contacts_data)
            self.send_json({"ok": True, "stage": stage})
            return

        self.send_json({"ok": False, "error": "not_found"})

    def _quick_action(self, body):
        contacts_path = BASE_DIR / "nurture_contacts.json"
        contacts_data = load_json(contacts_path, {"contacts": []})
        phone = body.get("phone", "")
        action = body.get("action", "")
        phone_digits = "".join(c for c in phone if c.isdigit())
        now = datetime.now(timezone.utc).isoformat()

        for c in contacts_data.get("contacts", []):
            if "".join(d for d in c.get("phone", "") if d.isdigit()) != phone_digits:
                continue
            if c.get("contact_type", "lead") != "lead":
                self.send_json({"ok": False, "error": "not_lead_contact"})
                return

            c.setdefault("pipeline", {})

            if action == "called":
                c["last_call"] = now
                c["pipeline"].setdefault("contact_attempted", now)
            elif action == "texted":
                c["pipeline"].setdefault("contact_attempted", now)
                c["last_text"] = now
            elif action == "app_sent":
                c["current_stage"] = "application"
                c["pipeline"]["application"] = now
                if c.get("track") in (None, "cold", "warm", "hot"):
                    c["track"] = "active_preapproval"
            elif action == "toggle_referral":
                c["needs_referral"] = not bool(c.get("needs_referral"))
            else:
                self.send_json({"ok": False, "error": "invalid_action"})
                return

            save_json(contacts_path, contacts_data)
            self.send_json({"ok": True, "action": action})
            return

        self.send_json({"ok": False, "error": "not_found"})

    def _log_call(self, body):
        contacts_path = BASE_DIR / "nurture_contacts.json"
        contacts_data = load_json(contacts_path, {"contacts": []})
        phone_digits = "".join(c for c in body.get("phone", "") if c.isdigit())

        for c in contacts_data.get("contacts", []):
            if "".join(d for d in c.get("phone", "") if d.isdigit()) != phone_digits:
                continue
            c.setdefault("calls", []).append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notes": body.get("notes", ""),
            })
            c.setdefault("pipeline", {}).setdefault("called", datetime.now(timezone.utc).isoformat())
            save_json(contacts_path, contacts_data)
            self.send_json({"ok": True})
            return

        self.send_json({"ok": False})

    def send_json(self, data):
        response = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else CONFIG["dashboard"]["port"]
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"Dashboard server running on port {port}", flush=True)
    server.serve_forever()
