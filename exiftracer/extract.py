"""Reads metadata from images and rates how much it gives away."""
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image, UnidentifiedImageError

try:  # HEIC/HEIF (iPhone photos) is optional: pip install exiftracer[heic]
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF = True
except ImportError:
    HEIF = False

EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".webp", ".heic", ".heif"}

TAGS = ExifTags.TAGS
GPS_IFD = ExifTags.IFD.GPSInfo
EXIF_IFD = ExifTags.IFD.Exif


@dataclass
class Meta:
    path: str
    format: str = None
    width: int = None
    height: int = None
    make: str = None
    model: str = None
    lens: str = None
    software: str = None
    taken: str = None          # ISO 8601, with offset when the camera recorded one
    artist: str = None
    copyright: str = None
    owner: str = None
    body_serial: str = None
    lens_serial: str = None
    latitude: float = None
    longitude: float = None
    altitude: float = None
    direction: float = None    # degrees the camera was facing
    gps_time: str = None
    xmp_tool: str = None
    tag_count: int = 0
    address: str = None
    city: str = None
    country: str = None
    error: str = None
    findings: list = field(default_factory=list)

    @property
    def has_gps(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def risk(self):
        """high: reveals where; medium: reveals who/which device/when; low: technical only; none."""
        if self.has_gps:
            return "high"
        if any((self.body_serial, self.lens_serial, self.owner, self.artist)):
            return "medium"
        if self.tag_count or self.xmp_tool:
            return "low"
        return "none"

    @property
    def camera(self):
        make, model = (self.make or "").strip(), (self.model or "").strip()
        if make and model.lower().startswith(make.lower()):
            return model
        return " ".join(p for p in (make, model) if p) or None

    def to_dict(self):
        d = asdict(self)
        d["risk"] = self.risk
        return d


def _text(v):
    if v is None:
        return None
    if isinstance(v, bytes):
        v = v.split(b"\x00", 1)[0].decode("utf-8", "replace")
    v = str(v).strip().strip("\x00")
    return v or None


def _dms(value, ref):
    """(deg, min, sec) rationals + N/S/E/W -> signed decimal degrees."""
    try:
        d, m, s = (float(x) for x in value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    deg = d + m / 60 + s / 3600
    return -deg if _text(ref) in ("S", "W") else deg


def _datetime(value, offset=None):
    value = _text(value)
    if not value:
        return None
    try:
        dt = datetime.strptime(value[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return value
    iso = dt.isoformat()
    offset = _text(offset)
    if offset and re.fullmatch(r"[+-]\d\d:\d\d", offset):
        iso += offset
    return iso


def _gps(meta, gps):
    if not gps:
        return
    lat = _dms(gps.get(2), gps.get(1))
    lon = _dms(gps.get(4), gps.get(3))
    if lat is not None and lon is not None and not (lat == 0 and lon == 0):
        meta.latitude, meta.longitude = round(lat, 7), round(lon, 7)
    if gps.get(6) is not None:
        try:
            alt = float(gps[6])
            meta.altitude = round(-alt if gps.get(5) in (1, b"\x01") else alt, 1)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    if gps.get(17) is not None:
        try:
            meta.direction = round(float(gps[17]), 1)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    date, time = _text(gps.get(29)), gps.get(7)
    if date and time:
        try:
            h, m, s = (float(x) for x in time)
            meta.gps_time = f"{date.replace(':', '-')}T{int(h):02d}:{int(m):02d}:{int(s):02d}Z"
        except (TypeError, ValueError, ZeroDivisionError):
            pass


def _xmp(img):
    raw = img.info.get("xmp") or img.info.get("XML:com.adobe.xmp")
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    m = re.search(r'CreatorTool(?:="|>)([^"<]+)', raw)
    return m.group(1).strip() if m else "present"


def read(path):
    """Metadata of one image. Never raises: problems are reported in .error."""
    meta = Meta(path=str(path))
    try:
        with Image.open(path) as img:
            meta.format, (meta.width, meta.height) = img.format, img.size
            exif = img.getexif()
            meta.xmp_tool = _xmp(img)
            base = dict(exif)
            sub = dict(exif.get_ifd(EXIF_IFD))
            gps = dict(exif.get_ifd(GPS_IFD))
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as e:
        meta.error = f"{type(e).__name__}: {e}"
        return meta

    meta.tag_count = len(base) + len(sub) + len(gps) - (EXIF_IFD in base) - (GPS_IFD in base)
    meta.make, meta.model = _text(base.get(0x010F)), _text(base.get(0x0110))
    meta.software, meta.artist = _text(base.get(0x0131)), _text(base.get(0x013B))
    meta.copyright = _text(base.get(0x8298))
    meta.lens = _text(sub.get(0xA434))
    meta.owner = _text(sub.get(0xA430))
    meta.body_serial, meta.lens_serial = _text(sub.get(0xA431)), _text(sub.get(0xA435))
    meta.taken = _datetime(sub.get(0x9003) or base.get(0x0132), sub.get(0x9011))
    _gps(meta, gps)

    if meta.has_gps:
        meta.findings.append("GPS location")
    if meta.body_serial or meta.lens_serial:
        meta.findings.append("serial number")
    if meta.owner or meta.artist:
        meta.findings.append("owner name")
    if meta.taken:
        meta.findings.append("date/time")
    if meta.camera:
        meta.findings.append("camera")
    if meta.software:
        meta.findings.append("software")
    return meta


def find_images(paths, recursive=False):
    """Expand files and directories into image paths, in a stable order."""
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            it = p.rglob("*") if recursive else p.iterdir()
            out.extend(sorted(f for f in it if f.is_file() and f.suffix.lower() in EXTENSIONS))
        elif p.exists():
            out.append(p)
    return out
