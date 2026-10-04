"""Generate the app icons (PNG) using only the standard library.

Run once from the project root:  python scripts/make_icons.py
"""

import struct
import zlib
from pathlib import Path

BLUE = (37, 99, 235)
WHITE = (255, 255, 255)
OUT_DIR = Path(__file__).resolve().parent.parent / "app" / "static"
SAMPLES = 3  # 3x3 samples per pixel for smooth edges


def render(size: int) -> bytes:
    """Blue square with a white 'target' (ring plus dot) in the middle."""
    rows = []
    for py in range(size):
        row = bytearray([0])  # PNG filter type 0 (none) at the start of each row
        for px in range(size):
            hits = 0
            for sy in range(SAMPLES):
                for sx in range(SAMPLES):
                    dx = (px + (sx + 0.5) / SAMPLES) / size - 0.5
                    dy = (py + (sy + 0.5) / SAMPLES) / size - 0.5
                    distance = (dx * dx + dy * dy) ** 0.5
                    if 0.20 <= distance <= 0.30 or distance <= 0.08:
                        hits += 1
            t = hits / (SAMPLES * SAMPLES)
            row += bytes(round(BLUE[i] + (WHITE[i] - BLUE[i]) * t) for i in range(3))
        rows.append(bytes(row))
    return b"".join(rows)


def chunk(tag: bytes, data: bytes) -> bytes:
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def write_png(path: Path, size: int) -> None:
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(render(size), 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)
    print(f"wrote {path} ({size}x{size}, {len(png)} bytes)")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_png(OUT_DIR / "icon-192.png", 192)
    write_png(OUT_DIR / "icon-512.png", 512)
    write_png(OUT_DIR / "apple-touch-icon.png", 180)
