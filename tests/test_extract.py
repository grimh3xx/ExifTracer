from exiftracer.extract import find_images, read
from conftest import make_image


def test_gps_signs_and_precision(tmp_path):
    m = read(make_image(tmp_path / "a.jpg", -33.8568, 151.2153))
    assert m.has_gps and abs(m.latitude + 33.8568) < 1e-4 and abs(m.longitude - 151.2153) < 1e-4
    m = read(make_image(tmp_path / "b.jpg", 40.7128, -74.006))
    assert m.latitude > 0 and m.longitude < 0


def test_device_time_and_people(tmp_path):
    m = read(make_image(tmp_path / "a.jpg", 1, 1, serial="SN123", artist="Jane", alt=-4))
    assert m.camera == "Canon EOS R6"          # make not repeated
    assert m.lens == "RF24-105mm F4 L IS USM"
    assert m.taken == "2026-03-14T09:26:53+11:00"
    assert m.body_serial == "SN123" and m.artist == "Jane"
    assert m.altitude == -4.0
    assert m.risk == "high"
    assert "serial number" in m.findings


def test_risk_levels(tmp_path):
    assert read(make_image(tmp_path / "s.jpg", serial="X1")).risk == "medium"
    assert read(make_image(tmp_path / "t.jpg")).risk == "low"
    from PIL import Image
    Image.new("RGB", (4, 4)).save(tmp_path / "c.jpg")
    assert read(tmp_path / "c.jpg").risk == "none"


def test_png_exif(tmp_path):
    m = read(make_image(tmp_path / "a.png", 10.5, 20.25, fmt="PNG"))
    assert m.format == "PNG" and m.has_gps


def test_zero_zero_is_not_a_location(tmp_path):
    assert not read(make_image(tmp_path / "z.jpg", 0.0, 0.0)).has_gps


def test_unreadable_file_reports_error(tmp_path):
    p = tmp_path / "broken.jpg"
    p.write_bytes(b"not a jpeg")
    m = read(p)
    assert m.error and not m.has_gps


def test_find_images(gallery):
    names = [p.name for p in find_images([gallery])]
    assert names == ["clean.jpg", "opera.jpg", "plain.png"]
    assert "eiffel.jpg" in [p.name for p in find_images([gallery], recursive=True)]
