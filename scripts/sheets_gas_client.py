"""Client for the Google Apps Script Web App (apps_script/Code.gs) that
bridges the dashboard sheet + Gmail — no Google Cloud project needed.

Auth: GAS_WEBAPP_URL (the deployed Web App URL) + GAS_SHARED_SECRET (must
match SHARED_SECRET in Code.gs), both read from env vars.
"""
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


def _post_following_redirect_as_get(url, payload):
    # Apps Script Web Apps always answer a POST to /exec with a 302 to a
    # second "echo" URL that serves the already-computed response (the
    # actual doPost() side effects, like writing to the sheet, already
    # happened during this first request). Letting requests/curl
    # auto-follow that redirect re-sends it as a POST without a proper
    # body/Content-Length, which Google rejects (411) or which comes back
    # empty. The correct move is to not auto-follow, and instead fetch the
    # redirect target ourselves with a plain GET (which never needs a body).
    resp = requests.post(url, json=payload, timeout=TIMEOUT, allow_redirects=False)
    if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
        resp = requests.get(resp.headers["Location"], timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def _call(action, **params):
    payload = {"action": action, "secret": _secret(), **params}
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = _post_following_redirect_as_get(_url(), payload)
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
