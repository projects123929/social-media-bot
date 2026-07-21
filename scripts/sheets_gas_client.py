"""Client for the Google Apps Script Web App (apps_script/Code.gs) that
bridges the dashboard sheet + Gmail — no Google Cloud project needed.

Auth: GAS_WEBAPP_URL (the deployed Web App URL) + GAS_SHARED_SECRET (must
match SHARED_SECRET in Code.gs), both read from env vars.
"""
import json
import os
import time

import requests

TIMEOUT = 30
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3


def _url():
    url = os.environ.get("GAS_WEBAPP_URL")
    if not url:
        raise RuntimeError("Missing GAS_WEBAPP_URL env var")
    return url


def _secret():
    secret = os.environ.get("GAS_SHARED_SECRET")
    if not secret:
        raise RuntimeError("Missing GAS_SHARED_SECRET env var")
    return secret


def _call(action, **params):
    # GET, not POST: Apps Script Web Apps always answer via a 302 to a
    # second "echo" URL, and POST requests through that redirect proved
    # unreliable across HTTP clients (lost body, 411s, empty responses).
    # GET has no body to lose, so its redirect just works normally.
    query = {"action": action, "secret": _secret()}
    for key, value in params.items():
        query[key] = json.dumps(value) if isinstance(value, (dict, list)) else value

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(_url(), params=query, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            last_error = e
            print(f"[sheets_gas_client] {action} attempt {attempt}/{MAX_ATTEMPTS} failed: {e}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)
            continue

        if "error" in data:
            raise RuntimeError(f"Apps Script error ({action}): {data['error']}")
        return data

    raise RuntimeError(f"Apps Script call ({action}) failed after {MAX_ATTEMPTS} attempts: {last_error}")


def get_rows():
    return _call("get_rows")["rows"]


def update_row(row_number, values: dict):
    _call("update_row", row=row_number, values=values)


def send_html_email(subject, html_body, to="ai@ms2.co.in"):
    _call("send_email", subject=subject, html_body=html_body, to=to)


def check_reply(subject_contains):
    return _call("check_reply", subject_contains=subject_contains)["result"]
