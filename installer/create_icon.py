"""Generate the AI Social Agent Windows .ico using only the Python standard library.

The generated ICO contains PNG-compressed 256/64/32/16px RGBA images, so the
installer and desktop shortcut use the same branded icon without committing a
binary asset to the repository.
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "AI-Social-Agent.ico"


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png(size: int) -> bytes:
    pixels = bytearray()
    cx = cy = (size - 1) / 2
    radius = size * 0.43
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            # Transparent rounded-square outside the brand mark.
            dx = abs(x - cx) - size * 0.36
            dy = abs(y - cy) - size * 0.36
            outside = math.hypot(max(dx, 0), max(dy, 0)) > size * 0.07 and max(dx, dy) > 0
            if outside:
                pixels.extend((0, 0, 0, 0))
                continue
            t = max(0.0, min(1.0, y / max(1, size - 1)))
            r = int(73 + 70 * t)
            g = int(43 + 35 * t)
            b = int(170 + 35 * t)
            # Three connected AI nodes.
            nodes = [(0.34, 0.35), (0.66, 0.35), (0.50, 0.67)]
            hit = any((x - nx * size) ** 2 + (y - ny * size) ** 2 <= (size * 0.075) ** 2 for nx, ny in nodes)
            edge = (x / size - 0.34) * (0.66 - 0.34) >= 0
            if hit:
                pixels.extend((255, 255, 255, 255))
            else:
                # White connector strokes between nodes.
                p1 = ((0.34 * size, 0.35 * size), (0.66 * size, 0.35 * size))
                p2 = ((0.34 * size, 0.35 * size), (0.50 * size, 0.67 * size))
                p3 = ((0.66 * size, 0.35 * size), (0.50 * size, 0.67 * size))
                near = False
                for (ax, ay), (bx, by) in (p1, p2, p3):
                    vx, vy = bx - ax, by - ay
                    denom = vx * vx + vy * vy or 1
                    u = max(0, min(1, ((x - ax) * vx + (y - ay) * vy) / denom))
                    qx, qy = ax + u * vx, ay + u * vy
                    if (x - qx) ** 2 + (y - qy) ** 2 <= (size * 0.018) ** 2:
                        near = True
                        break
                pixels.extend((245, 242, 255, 255) if near else (r, g, b, 255))
    raw = bytes(pixels)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def main() -> None:
    sizes = (256, 64, 32, 16)
    images = [png(size) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    directory = bytearray()
    offset = 6 + 16 * len(images)
    for size, data in zip(sizes, images):
        dimension = 0 if size >= 256 else size
        directory.extend(struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    OUT.write_bytes(header + directory + b"".join(images))
    print(f"Generated {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

# Task 10 release packaging marker: keep the branded icon generation in the release trigger path.
