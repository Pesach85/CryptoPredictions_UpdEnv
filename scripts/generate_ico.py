"""Write a multi-size .ico from generated PNGs (Windows shortcut icons)."""

from __future__ import annotations

import struct
from pathlib import Path


def png_to_ico(png_paths: list[Path], ico_path: Path) -> Path:
    """Embed PNG images in an ICO container (Vista+)."""
    images = [p.read_bytes() for p in png_paths]
    count = len(images)
    offset = 6 + count * 16
    header = struct.pack("<HHH", 0, 1, count)
    entries = b""
    blobs = b""
    for data in images:
        # IHDR width/height at bytes 16..24 of PNG
        w = data[16:20]
        h = data[20:24]
        width = int.from_bytes(w, "big")
        height = int.from_bytes(h, "big")
        bw = 0 if width >= 256 else width
        bh = 0 if height >= 256 else height
        entries += struct.pack("<BBBBHHII", bw, bh, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    ico_path.write_bytes(header + entries + blobs)
    return ico_path


def main() -> None:
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    icons = root / "packaging" / "icons"
    spec = importlib.util.spec_from_file_location(
        "generate_icons", root / "scripts" / "generate_icons.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    sizes = [16, 32, 48, 64, 128, 256]
    paths = []
    for s in sizes:
        p = icons / f"cryptopredictions_{s}.png"
        mod.write_png(p, s)
        paths.append(p)
    mod.write_png(icons / "cryptopredictions.png", 256)
    ico = png_to_ico(paths, icons / "cryptopredictions.ico")
    print(f"ICO written: {ico}")


if __name__ == "__main__":
    main()
