"""Terminal tables, JSON/CSV export and the interactive HTML map."""
import base64
import csv
import html
import io
import json
from pathlib import Path

from PIL import Image, ImageOps
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__

ACCENT, ACCENT2 = "#3B82F6", "#22D3EE"
TITLE, TEXT, MUTED, DIM, BORDER = "#F1F5FB", "#C5CFDD", "#8B98AD", "#5B6678", "#1E2A3D"
OK, WARN, ERR = "#34D399", "#FBBF24", "#F87171"
RISK_STYLE = {"high": ERR, "medium": WARN, "low": ACCENT2, "none": OK}

console = Console(highlight=False)


def banner():
    t = Text()
    t.append("◉ ", style=ACCENT2)
    t.append("ExifTracer", style=f"bold {TITLE}")
    t.append(f"  v{__version__}", style=DIM)
    t.append("  ·  metadata & location tracing for images", style=MUTED)
    return t


def where(m):
    if not m.has_gps:
        return Text("—", style=DIM)
    place = ", ".join(p for p in (m.city, m.country) if p)
    t = Text(f"{m.latitude:.4f}, {m.longitude:.4f}", style=TEXT)
    if place:
        t.append(f"  {place}", style=ACCENT2)
    return t


def risk_text(m):
    return Text(f"● {m.risk}", style=RISK_STYLE[m.risk])


def scan_table(metas, base=None):
    t = Table(box=box.SIMPLE_HEAD, border_style=BORDER, header_style=f"bold {MUTED}", expand=True, pad_edge=False)
    t.add_column("file", style=TITLE, no_wrap=True, overflow="ellipsis", max_width=28)
    t.add_column("camera", style=TEXT, no_wrap=True, overflow="ellipsis", max_width=22)
    t.add_column("taken", style=MUTED, no_wrap=True)
    t.add_column("location", no_wrap=True, overflow="ellipsis", ratio=1)
    t.add_column("risk", no_wrap=True)
    for m in metas:
        name = str(Path(m.path).relative_to(base)) if base and Path(m.path).is_relative_to(base) else Path(m.path).name
        if m.error:
            t.add_row(name, Text("unreadable", style=ERR), "", Text(m.error[:60], style=DIM), "")
            continue
        taken = (m.taken or "—").replace("T", " ")[:16]
        t.add_row(name, m.camera or Text("—", style=DIM), taken, where(m), risk_text(m))
    return t


def summary(metas):
    ok = [m for m in metas if not m.error]
    gps = sum(m.has_gps for m in ok)
    serial = sum(bool(m.body_serial or m.lens_serial) for m in ok)
    clean = sum(m.risk == "none" for m in ok)
    t = Text()
    for label, val, color in (("images", len(metas), TITLE), ("with GPS", gps, ERR if gps else OK),
                              ("with serial numbers", serial, WARN if serial else OK), ("clean", clean, OK)):
        t.append(f"{val} ", style=f"bold {color}")
        t.append(f"{label}   ", style=MUTED)
    return t


def detail(m):
    """Everything known about one image, grouped."""
    rows = [
        ("File", [("path", m.path), ("format", m.format), ("size", f"{m.width} × {m.height}" if m.width else None)]),
        ("Device", [("camera", m.camera), ("lens", m.lens), ("body serial", m.body_serial),
                    ("lens serial", m.lens_serial), ("software", m.software), ("xmp creator", m.xmp_tool)]),
        ("People", [("artist", m.artist), ("owner", m.owner), ("copyright", m.copyright)]),
        ("Time", [("taken", m.taken), ("gps time (UTC)", m.gps_time)]),
        ("Location", [("coordinates", f"{m.latitude}, {m.longitude}" if m.has_gps else None),
                      ("altitude", f"{m.altitude} m" if m.altitude is not None else None),
                      ("facing", f"{m.direction}°" if m.direction is not None else None),
                      ("address", m.address),
                      ("map", f"https://www.openstreetmap.org/?mlat={m.latitude}&mlon={m.longitude}#map=18/{m.latitude}/{m.longitude}" if m.has_gps else None)]),
    ]
    g = Table.grid(padding=(0, 2))
    g.add_column(style=MUTED, no_wrap=True)
    g.add_column(style=TEXT, overflow="fold")
    for section, items in rows:
        items = [(k, v) for k, v in items if v not in (None, "")]
        if not items:
            continue
        g.add_row(Text(section.upper(), style=f"bold {ACCENT}"), "")
        for k, v in items:
            g.add_row(f"  {k}", Text(str(v), style=ERR if k in ("coordinates", "body serial", "lens serial", "address") else TEXT))
    exposes = Text("exposes: ", style=MUTED) + Text(", ".join(m.findings) or "nothing identifying", style=TEXT)
    return Panel(Group(g, Text(""), exposes), title=Text(f" {Path(m.path).name} ", style=f"bold {TITLE}"),
                 title_align="left", subtitle=risk_text(m), subtitle_align="right", border_style=BORDER, box=box.ROUNDED)


# ------------------------------------------------------------- exports
CSV_FIELDS = ["path", "risk", "make", "model", "lens", "body_serial", "lens_serial", "software", "taken",
              "latitude", "longitude", "altitude", "direction", "city", "country", "address", "artist", "owner", "error"]


def write_json(metas, dest):
    text = json.dumps([m.to_dict() for m in metas], indent=2, ensure_ascii=False)
    if str(dest) == "-":
        print(text)
    else:
        Path(dest).write_text(text + "\n", encoding="utf-8")


def write_csv(metas, dest):
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for m in metas:
            w.writerow(m.to_dict())


def _thumb(path, size=220):
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((size, size))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=72)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except OSError:
        return None


def write_map(metas, dest):
    """Self-contained HTML map: numbered markers in time order, a route line, thumbnails in popups."""
    import folium

    pts = sorted((m for m in metas if m.has_gps), key=lambda m: m.taken or m.gps_time or "")
    if not pts:
        return 0
    fmap = folium.Map(tiles=None, control_scale=True)
    folium.TileLayer("OpenStreetMap", name="Map").add_to(fmap)
    folium.TileLayer(  # no API key needed
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri", name="Satellite").add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)
    coords = [(m.latitude, m.longitude) for m in pts]
    if len(coords) > 1:
        folium.PolyLine(coords, color=ACCENT2, weight=2.5, opacity=0.7, dash_array="6 8",
                        tooltip="route in the order the photos were taken").add_to(fmap)
    for i, m in enumerate(pts, 1):
        thumb = _thumb(m.path)
        rows = "".join(
            f"<tr><td style='color:#8B98AD;padding-right:10px'>{k}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in (("taken", (m.taken or "—").replace("T", " ")), ("camera", m.camera or "—"),
                         ("coords", f"{m.latitude:.6f}, {m.longitude:.6f}"), ("place", m.address or "—")))
        img = f"<img src='{thumb}' style='width:100%;border-radius:6px;margin:6px 0'>" if thumb else ""
        popup = (f"<div style='font:12px Inter,system-ui,sans-serif;width:240px'>"
                 f"<b style='font-size:13px'>#{i} · {html.escape(Path(m.path).name)}</b>{img}"
                 f"<table style='font-size:11.5px'>{rows}</table></div>")
        icon = folium.DivIcon(html=(
            f"<div style='width:26px;height:26px;border-radius:13px;background:{ACCENT};border:2px solid {ACCENT2};"
            f"color:#fff;font:700 12px Inter,system-ui,sans-serif;display:flex;align-items:center;"
            f"justify-content:center;box-shadow:0 0 12px {ACCENT}'>{i}</div>"), icon_size=(26, 26), icon_anchor=(13, 13))
        folium.Marker((m.latitude, m.longitude), icon=icon, popup=folium.Popup(popup, max_width=260),
                      tooltip=f"#{i} {Path(m.path).name}").add_to(fmap)
    fmap.fit_bounds([[min(c[0] for c in coords), min(c[1] for c in coords)],
                     [max(c[0] for c in coords), max(c[1] for c in coords)]], padding=(40, 40), max_zoom=16)
    title = (f"<div style='position:fixed;top:12px;left:56px;z-index:9999;background:#111826ee;color:#F1F5FB;"
             f"padding:8px 14px;border:1px solid #1E2A3D;border-radius:10px;font:13px Inter,system-ui,sans-serif'>"
             f"<b style='color:#22D3EE'>◉ ExifTracer</b> &nbsp;{len(pts)} geotagged image(s)</div>")
    fmap.get_root().html.add_child(folium.Element(title))
    fmap.save(str(dest))
    return len(pts)
