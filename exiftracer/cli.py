"""Command line: scan, show, strip."""
import argparse
import sys
from pathlib import Path

from rich.text import Text

from . import __version__, report
from .extract import HEIF, find_images, read
from .report import DIM, ERR, MUTED, OK, WARN, console

COMMANDS = ("scan", "show", "strip")


def parse_args(argv):
    p = argparse.ArgumentParser(prog="exiftracer", description="Find what your images give away: location, device, owner and time.",
                                epilog="Shortcut: `exiftracer PATH...` is the same as `exiftracer scan PATH...`.")
    p.add_argument("-V", "--version", action="version", version=f"exiftracer {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="COMMAND")

    s = sub.add_parser("scan", help="summarise images or folders, optionally map them and export")
    s.add_argument("paths", nargs="+", metavar="PATH")
    s.add_argument("-r", "--recursive", action="store_true", help="descend into sub-folders")
    s.add_argument("-m", "--map", metavar="FILE.html", help="write an interactive map of the geotagged images")
    s.add_argument("--open", action="store_true", help="open the map in the browser")
    s.add_argument("--json", metavar="FILE", help="export everything as JSON ('-' for stdout)")
    s.add_argument("--csv", metavar="FILE", help="export a CSV table")
    s.add_argument("--gps-only", action="store_true", help="list only images with coordinates")
    s.add_argument("--offline", action="store_true", help="don't resolve coordinates to addresses")

    d = sub.add_parser("show", help="everything one image reveals")
    d.add_argument("image")
    d.add_argument("--offline", action="store_true", help="don't resolve coordinates to an address")

    c = sub.add_parser("strip", help="remove metadata before sharing")
    c.add_argument("paths", nargs="+", metavar="PATH")
    c.add_argument("-r", "--recursive", action="store_true")
    where = c.add_mutually_exclusive_group()
    where.add_argument("-o", "--out", metavar="DIR", help="write clean copies here (default: next to each file, as NAME.clean.EXT)")
    where.add_argument("--in-place", action="store_true", help="overwrite the originals")

    if argv and argv[0] not in COMMANDS and not argv[0].startswith("-"):
        argv = ["scan", *argv]
    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        raise SystemExit(0)
    return args


def geocoder(offline):
    if offline:
        return None
    from .geo import Geocoder
    return Geocoder()


def cmd_scan(args):
    files = find_images(args.paths, args.recursive)
    if not files:
        console.print(Text("no images found", style=ERR))
        return 1
    with console.status(f"reading {len(files)} image(s)…", spinner="dots"):
        metas = [read(f) for f in files]
    g = geocoder(args.offline)
    gps = [m for m in metas if m.has_gps]
    if g and gps:
        from .geo import enrich
        with console.status(f"resolving {len(gps)} location(s) via OpenStreetMap…", spinner="dots"):
            enrich(gps, g)
    shown = gps if args.gps_only else metas
    base = Path(args.paths[0]) if len(args.paths) == 1 and Path(args.paths[0]).is_dir() else None
    console.print(report.banner())
    console.print(report.scan_table(shown, base))
    console.print(report.summary(metas))
    if args.json:
        report.write_json(metas, args.json)
        if args.json != "-":
            console.print(Text(f"  → JSON  {args.json}", style=MUTED))
    if args.csv:
        report.write_csv(metas, args.csv)
        console.print(Text(f"  → CSV   {args.csv}", style=MUTED))
    if args.map:
        n = report.write_map(metas, args.map)
        if n:
            console.print(Text(f"  → map   {args.map}  ({n} point{'s' if n > 1 else ''})", style=MUTED))
            if args.open:
                import webbrowser
                webbrowser.open(Path(args.map).resolve().as_uri())
        else:
            console.print(Text("  no geotagged images: map not written", style=DIM))
    return 0


def cmd_show(args):
    m = read(args.image)
    if m.error:
        console.print(Text(f"✗ {m.error}", style=ERR))
        return 1
    g = geocoder(args.offline)
    if g and m.has_gps:
        from .geo import enrich
        with console.status("resolving location via OpenStreetMap…", spinner="dots"):
            enrich([m], g)
    console.print(report.banner())
    console.print(report.detail(m))
    return 0


def cmd_strip(args):
    from .strip import clean_path, strip
    files = find_images(args.paths, args.recursive)
    if not files:
        console.print(Text("no images found", style=ERR))
        return 1
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
    console.print(report.banner())
    console.print()
    failed = 0
    for f in files:
        dest = clean_path(f, args.out, args.in_place)
        try:
            before, after = strip(f, dest)
        except (OSError, ValueError) as e:
            failed += 1
            console.print(Text("  ✗ ", style=ERR) + Text(f"{f.name}: {e}", style=MUTED))
            continue
        if before.tag_count:
            removed = "removed: " + (", ".join(before.findings) or f"{before.tag_count} technical tag(s)")
        else:
            removed = "already clean"
        left = after.tag_count
        line = Text("  ✓ " if not left else "  ! ", style=OK if not left else WARN)
        line += Text(f"{f.name}", style="bold") + Text(f"  →  {dest.name}", style=MUTED)
        line += Text(f"   {removed}", style=DIM)
        if left:
            line += Text(f"  ({left} tag(s) could not be removed)", style=WARN)
        console.print(line)
    return 1 if failed else 0


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if not HEIF and any(str(p).lower().endswith((".heic", ".heif")) for p in getattr(args, "paths", []) or []):
        console.print(Text("HEIC support needs: pip install pillow-heif", style=WARN))
    try:
        return {"scan": cmd_scan, "show": cmd_show, "strip": cmd_strip}[args.cmd](args)
    except KeyboardInterrupt:
        return 130
