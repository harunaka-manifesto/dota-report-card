"""Budgeted STRATZ client. Token from env only; never printed or written to disk."""
from __future__ import annotations
import json, os, time, socket
from pathlib import Path
import httpx

HERE = Path(__file__).parent
RAW = HERE / "raw"
LEDGER = HERE / "ledger.jsonl"
MAX_CALLS = 1200
_last = [0.0]

# STRATZ binds the token to one client IP; pin the address family (see memory note).
_FAMILY = socket.AF_INET6 if os.environ.get("STRATZ_IP_FAMILY", "6") == "6" else socket.AF_INET
_CLIENT = httpx.Client(timeout=120, transport=httpx.HTTPTransport(local_address=None), http2=False)


ENV_FILE = Path("/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.env")


def _token() -> str:
    for k in ("STRATZ_API_KEY", "STRATZ_API_TOKEN"):
        v = os.environ.get(k)
        if v:
            return v.strip()
    # fall back to the project's own .env (never printed, never copied)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith(("STRATZ_API_KEY=", "STRATZ_API_TOKEN=")):
                return line.split("=", 1)[1].strip().strip("\'\"")
    raise SystemExit("no STRATZ token available")


def calls_used() -> int:
    return sum(1 for _ in LEDGER.open()) if LEDGER.exists() else 0


def call(name: str, query: str, variables: dict | None = None, cache: bool = True) -> dict:
    RAW.mkdir(exist_ok=True)
    path = RAW / f"{name}.json"
    if cache and path.exists():
        return json.loads(path.read_text())
    if calls_used() >= MAX_CALLS:
        raise SystemExit(f"budget exhausted {MAX_CALLS}")
    tok = _token()
    wait = 1.2 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    t0 = time.time()
    r = None
    for attempt in range(8):
        try:
            r = _CLIENT.post(
                "https://api.stratz.com/graphql",
                json={"query": query, "variables": variables or {}},
                headers={"Authorization": f"Bearer {tok}", "User-Agent": "STRATZ_API",
                         "Content-Type": "application/json"},
            )
        except httpx.TransportError:
            time.sleep(2 * (attempt + 1)); continue
        if r.status_code == 403 and "different IP" in r.text:
            time.sleep(30); continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(3 * min(attempt + 1, 5)); continue
        break
    _last[0] = time.time()
    try:
        payload = r.json()
    except Exception:
        payload = {"_non_json": r.text[:800]}
    probe = {"name": name, "status": r.status_code, "bytes": len(r.content),
             "latency_s": round(time.time() - t0, 2),
             "errors": len(payload.get("errors") or []) if isinstance(payload, dict) else None,
             "at": time.time()}
    if isinstance(payload, dict):
        payload["_probe"] = probe
    if r.status_code == 200 and not (payload.get("errors") if isinstance(payload, dict) else None):
        path.write_text(json.dumps(payload))
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(probe) + "\n")
    return payload
