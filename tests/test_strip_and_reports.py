import csv
import json

from PIL import Image

from exiftracer import cli
from exiftracer.extract import read
from exiftracer.geo import Geocoder
from exiftracer.report import write_map
from exiftracer.strip import clean_path, strip
from conftest import make_image


def test_strip_removes_everything(tmp_path):
    src = make_image(tmp_path / "a.jpg", 1, 2, serial="SN", artist="Jane")
    before, after = strip(src, clean_path(src))
    assert before.risk == "high"
    assert after.tag_count == 0 and not after.has_gps and after.risk == "none"
    assert read(src).has_gps  # original untouched


def test_strip_applies_orientation(tmp_path):
    src = make_image(tmp_path / "r.jpg", orientation=6, size=(64, 48))  # rotate 90° on display
    _, after = strip(src, tmp_path / "r2.jpg")
    assert (after.width, after.height) == (48, 64)


def test_strip_png_and_in_place(tmp_path):
    src = make_image(tmp_path / "p.png", 5, 5, fmt="PNG")
    strip(src, clean_path(src, in_place=True))
    assert read(src).tag_count == 0


def test_cli_scan_exports(gallery, tmp_path, capsys):
    j, c, m = tmp_path / "o.json", tmp_path / "o.csv", tmp_path / "map.html"
    rc = cli.main(["scan", str(gallery), "-r", "--offline", "--json", str(j), "--csv", str(c), "--map", str(m)])
    assert rc == 0
    data = json.loads(j.read_text())
    assert {d["risk"] for d in data} >= {"high", "low", "none"}
    rows = list(csv.DictReader(c.open()))
    assert len(rows) == 4
    html = m.read_text()
    assert "leaflet" in html.lower() and "opera.jpg" in html and "data:image/jpeg;base64" in html
    out = capsys.readouterr().out
    assert "with GPS" in out


def test_cli_shortcut_and_show(gallery, capsys):
    assert cli.main([str(gallery / "opera.jpg"), "--offline"]) == 0
    assert cli.main(["show", str(gallery / "opera.jpg"), "--offline"]) == 0
    out = capsys.readouterr().out
    assert "032021004512" in out and "Jane Doe" in out


def test_cli_strip_to_dir(gallery, tmp_path):
    out = tmp_path / "clean"
    assert cli.main(["strip", str(gallery), "-r", "-o", str(out)]) == 0
    files = sorted(p.name for p in out.iterdir())
    assert "opera.clean.jpg" in files and "eiffel.clean.jpg" in files
    assert all(read(out / f).tag_count == 0 for f in files)


def test_map_without_gps_writes_nothing(tmp_path):
    Image.new("RGB", (4, 4)).save(tmp_path / "x.jpg")
    assert write_map([read(tmp_path / "x.jpg")], tmp_path / "m.html") == 0


class FakeSession:
    def __init__(self):
        self.calls = 0

    def get(self, url, params, headers, timeout):
        self.calls += 1
        assert "ExifTracer" in headers["User-Agent"]

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"display_name": "Sydney Opera House, Sydney, Australia",
                        "address": {"city": "Sydney", "country": "Australia"}}
        return R()


def test_geocoder_caches(tmp_path):
    s = FakeSession()
    g = Geocoder(tmp_path / "cache.json", min_interval=0, session=s)
    assert g.lookup(-33.8568, 151.2153)["city"] == "Sydney"
    g.lookup(-33.8568, 151.2153)
    assert s.calls == 1
    assert Geocoder(tmp_path / "cache.json", session=s).lookup(-33.8568, 151.2153)["country"] == "Australia"
    assert s.calls == 1
