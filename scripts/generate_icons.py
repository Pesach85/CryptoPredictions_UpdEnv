"""Generate app icons (PNG) for desktop installers — no external assets required."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path, size: int = 256) -> Path:
    """Minimal geometric logo: dark teal field + gold chevron (research / forecast)."""
    rows = []
    for y in range(size):
        row = [0]  # filter none
        for x in range(size):
            # background
            r, g, b = 18, 42, 58
            # circle badge
            cx, cy = size / 2, size / 2
            dist = math.hypot(x - cx, y - cy)
            if dist < size * 0.42:
                r, g, b = 25, 113, 194
            # upward chevron (forecast)
            if size * 0.28 < y < size * 0.55:
                left = size * 0.5 - (size * 0.55 - y) * 0.7
                right = size * 0.5 + (size * 0.55 - y) * 0.7
                if left < x < right and abs(x - size * 0.5) > size * 0.04:
                    r, g, b = 255, 212, 59
            # baseline
            if size * 0.62 < y < size * 0.68 and size * 0.28 < x < size * 0.72:
                r, g, b = 233, 236, 239
            row.extend([r, g, b, 255])
        rows.append(bytes(row))
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw, 9)) + _png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "packaging" / "icons"
    for s in (256, 128, 64, 48, 32):
        write_png(out / f"cryptopredictions_{s}.png", s)
    write_png(out / "cryptopredictions.png", 256)
    print(f"Icons written to {out}")


if __name__ == "__main__":
    main()
