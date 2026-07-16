"""Client for the Google Apps Script Web App (apps_script/Code.gs) that
bridges the dashboard sheet + Gmail — no Google Cloud project needed.

Auth: GAS_WEBAPP_URL (the deployed Web App URL) + GAS_SHARED_SECRET (must
match SHARED_SECRET in Code.gs), both read from env vars.
"""
import os

import requests

TIMEOUT = 30


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
    payload = {"action": action, "secret": _secret(), **params}
    resp = requests.post(_url(), json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Apps Script error ({action}): {data['error']}")
    return data


def get_rows():
    return _call("get_rows")["rows"]


def update_row(row_number, values: dict):
    _call("update_row", row=row_number, values=values)


def send_html_email(subject, html_body, to="ai@ms2.co.in"):
    _call("send_email", subject=subject, html_body=html_body, to=to)


def check_reply(subject_contains):
    return _call("check_reply", subject_contains=subject_contains)["result"]
