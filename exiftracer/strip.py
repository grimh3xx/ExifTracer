"""Removes metadata from images before they are shared."""
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from .extract import read


def clean_path(src, out_dir=None, in_place=False):
    src = Path(src)
    if in_place:
        return src
    target = src.with_name(f"{src.stem}.clean{src.suffix}")
    return Path(out_dir) / target.name if out_dir else target


def strip(src, dest):
    """Re-encode `src` into `dest` keeping only the pixels (and colour profile).

    Orientation is applied to the pixels first, so the photo still looks right once the
    EXIF orientation tag is gone. JPEGs that need no rotation keep their original
    quantization tables (no visible quality loss).
    """
    src, dest = Path(src), Path(dest)
    before = read(src)
    with Image.open(src) as img:
        fmt = img.format
        icc = img.info.get("icc_profile")
        needs_turn = img.getexif().get(0x0112, 1) not in (1, None)
        out = ImageOps.exif_transpose(img) if needs_turn else img.copy()
        kwargs = {"icc_profile": icc} if icc else {}
        if fmt == "JPEG":
            kwargs["comment"] = b""  # Pillow would otherwise copy the COM segment
            if needs_turn:
                kwargs.update(quality=95, subsampling=0)
            else:
                out = img  # quality="keep" needs the original JPEG object
                kwargs.update(quality="keep", subsampling="keep")
        elif fmt in ("WEBP", "HEIF"):
            kwargs["quality"] = 95
        # writing to a temp file first makes --in-place safe if encoding fails
        fd, tmp = tempfile.mkstemp(suffix=src.suffix, dir=dest.parent)
        os.close(fd)
        try:
            out.save(tmp, format=fmt, **kwargs)
            os.replace(tmp, dest)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    after = read(dest)
    return before, after
