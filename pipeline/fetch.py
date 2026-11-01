"""Download every source in sources.py and snapshot the raw responses to data/raw/.

Each snapshot is the untouched API response. data/raw/manifest.json records the
URL(s), UTC fetch time, HTTP status and SHA-256 of each file, so any later step
can be re-run offline against exactly the same bytes.
"""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

from .sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = "near-intents-thesis/0.1 (+https://nearhackathon.com)"


def _get(url, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except Exception as e:  # network hiccup: back off and retry
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def urls_for(src, now=None):
    if "url" in src:
        return [src["url"]]
    now = int(now or time.time())
    out, start = [], src["chunk_start"]
    while start < now:
        out.append(src["url_template"].format(start=start))
        start += src["chunk_days"] * 86400
    return out


def fetch_all(names=None):
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {"fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sources": {}}
    for name, src in SOURCES.items():
        if names and name not in names:
            continue
        urls = urls_for(src)
        parts = []
        statuses = []
        for u in urls:
            status, body = _get(u)
            statuses.append(status)
            parts.append(json.loads(body))
        payload = parts[0] if len(parts) == 1 else {"chunks": parts}
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        (RAW / f"{name}.json").write_bytes(data)
        manifest["sources"][name] = {
            "file": f"data/raw/{name}.json",
            "urls": urls,
            "provider": src["provider"],
            "what": src["what"],
            "http_status": statuses,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
        print(f"  fetched {name:<24} {len(data):>8} bytes")
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
