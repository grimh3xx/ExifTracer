"""Reverse geocoding through OpenStreetMap Nominatim, with a disk cache.

Nominatim's usage policy allows at most one request per second and requires a real
User-Agent; results are cached so repeated scans don't hit the service again.
"""
import json
import os
import time
from pathlib import Path

import requests

from . import __version__

URL = "https://nominatim.openstreetmap.org/reverse"
UA = f"ExifTracer/{__version__} (+https://github.com/grimh3xx/ExifTracer)"


def cache_path():
    base = os.environ.get("XDG_CACHE_HOME") or (
        os.environ.get("LOCALAPPDATA") if os.name == "nt" else None) or "~/.cache"
    return Path(base).expanduser() / "exiftracer" / "geocode.json"


class Geocoder:
    def __init__(self, path=None, min_interval=1.1, session=None):
        self.path = Path(path) if path else cache_path()
        self.min_interval = min_interval
        self.session = session or requests.Session()
        self._last = 0.0
        try:
            self.cache = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.cache = {}

    @staticmethod
    def key(lat, lon):
        return f"{lat:.5f},{lon:.5f}"  # ~1 m: same spot, same answer

    def lookup(self, lat, lon):
        k = self.key(lat, lon)
        if k in self.cache:
            return self.cache[k]
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        try:
            r = self.session.get(URL, params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 18},
                                 headers={"User-Agent": UA}, timeout=15)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError):
            return None
        a = data.get("address", {})
        result = {
            "address": data.get("display_name"),
            "city": a.get("city") or a.get("town") or a.get("village") or a.get("municipality"),
            "country": a.get("country"),
        }
        self.cache[k] = result
        self._save()
        return result

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.cache, indent=1), encoding="utf-8")
        except OSError:
            pass


def enrich(metas, geocoder):
    for m in metas:
        if m.has_gps:
            hit = geocoder.lookup(m.latitude, m.longitude)
            if hit:
                m.address, m.city, m.country = hit["address"], hit["city"], hit["country"]
