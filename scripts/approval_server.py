"""Always-on local approval server.

Listens for GET /approve and /reject links clicked from the approval email.
Each pending run has a storage/pending/{date}/status.json file containing a
one-time token. Clicking the matching link updates that file's status and
(on approve) invokes the publish step.

Run with: python scripts/approval_server.py
"""
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_config import load_env, PIPELINE_ROOT

load_env()

HOST = os.environ.get("APPROVAL_SERVER_HOST", "localhost")
PORT = int(os.environ.get("APPROVAL_SERVER_PORT", "8765"))
PENDING_DIR = os.path.join(PIPELINE_ROOT, "storage", "pending")


def _status_path(date):
    return os.path.join(PENDING_DIR, date, "status.json")


def _load_status(date):
    path = _status_path(date)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_status(date, data):
    with open(_status_path(date), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class Handler(BaseHTTPRequestHandler):
    def _respond(self, message, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<html><body><h2>{message}</h2></body></html>".encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        date = params.get("date", [None])[0]
        token = params.get("token", [None])[0]

        if parsed.path not in ("/approve", "/reject"):
            self._respond("Not found", 404)
            return

        if not date or not token:
            self._respond("Missing date or token", 400)
            return

        status = _load_status(date)
        if status is None:
            self._respond(f"No pending run found for {date}", 404)
            return

        if status.get("token") != token:
            self._respond("Invalid or expired token", 403)
            return

        if status.get("status") not in ("Generated",):
            self._respond(f"Run already {status.get('status')}, ignoring", 200)
            return

        if parsed.path == "/approve":
            status["status"] = "Approved"
            _save_status(date, status)
            print(f"[approval_server] {date} approved. Triggering publish job...")
            self._trigger_publish(date)
            self._respond("Approved. Publish job triggered.")
        else:
            status["status"] = "Rejected"
            _save_status(date, status)
            print(f"[approval_server] {date} rejected.")
            self._respond("Rejected. No publish will happen.")

    def _trigger_publish(self, date):
        publish_script = os.path.join(PIPELINE_ROOT, "scripts", "publish.py")
        if os.path.exists(publish_script):
            subprocess.Popen([sys.executable, publish_script, "--date", date])
        else:
            print(
                f"[approval_server] publish.py not built yet (Phase 6). "
                f"Would publish {date}'s video now."
            )

    def log_message(self, format, *args):
        print(f"[approval_server] {self.address_string()} - {format % args}")


def main():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"[approval_server] Listening on http://{HOST}:{PORT} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[approval_server] Stopping.")


if __name__ == "__main__":
    main()
