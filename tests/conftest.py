"""Builds test images with known metadata (no binary fixtures in the repo)."""
from fractions import Fraction

import pytest
from PIL import ExifTags, Image


def dms(deg):
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = round(((deg - d) * 60 - m) * 60, 4)
    return (Fraction(d), Fraction(m), Fraction(s).limit_denominator(10000))


def make_image(path, lat=None, lon=None, fmt=None, orientation=None, serial=None, taken="2026:03:14 09:26:53",
               offset="+11:00", make="Canon", model="Canon EOS R6", artist=None, alt=None, size=(64, 48)):
    img = Image.new("RGB", size, (30, 90, 200))
    exif = img.getexif()
    exif[0x010F], exif[0x0110] = make, model
    exif[0x0131] = "Adobe Lightroom 7.2"
    if artist:
        exif[0x013B] = artist
    if orientation:
        exif[0x0112] = orientation
    sub = exif.get_ifd(ExifTags.IFD.Exif)
    sub[0x9003], sub[0x9011] = taken, offset
    if serial:
        sub[0xA431] = serial
    sub[0xA434] = "RF24-105mm F4 L IS USM"
    if lat is not None:
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        gps[1], gps[2] = ("N" if lat >= 0 else "S"), dms(lat)
        gps[3], gps[4] = ("E" if lon >= 0 else "W"), dms(lon)
        if alt is not None:
            gps[5], gps[6] = (1 if alt < 0 else 0), Fraction(abs(alt)).limit_denominator(100)
    img.save(path, fmt, exif=exif, **({"quality": 90} if (fmt or path.suffix.lower()) in ("JPEG", ".jpg") else {}))
    return path


@pytest.fixture
def gallery(tmp_path):
    d = tmp_path / "photos"
    (d / "trip").mkdir(parents=True)
    make_image(d / "opera.jpg", -33.8568, 151.2153, serial="032021004512", artist="Jane Doe", alt=-4)
    make_image(d / "trip" / "eiffel.jpg", 48.8584, 2.2945, taken="2026:03:16 18:02:11", offset="+01:00")
    make_image(d / "plain.png", fmt="PNG")
    Image.new("RGB", (10, 10)).save(d / "clean.jpg")
    (d / "notes.txt").write_text("not an image")
    return d
