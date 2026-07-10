"""Loads pipeline/config/.env into os.environ without external dependencies."""
import os

PIPELINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PIPELINE_ROOT, "config", ".env")


def load_env():
    if not os.path.exists(ENV_PATH):
        raise FileNotFoundError(
            f"Missing {ENV_PATH}. Copy config/.env.example to config/.env "
            "and fill in real values."
        )
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def require(key):
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing required env var: {key} (check config/.env)")
    return value
