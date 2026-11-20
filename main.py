#!/usr/bin/env python3
"""THE WORLD TODAY - Friday, 20 November 2026 (improved front page).

A one-image newspaper front page drawn entirely at runtime with the
Python standard library only. No photos, no fonts on disk, no network,
no clock, no randomness: every run produces byte-identical output.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   ->  out/entry.png

Stories verified against 20 Nov 2026 reporting (WSJ, Reuters, CNN,
The Hindu, IMD, ESPNcricinfo). Visuals: gradient skies, shaded icons,
paper grain and drop shadows, all from hand-written primitives.
"""
import binascii
import math
import os
import struct
import zlib

W = 1024
H = 1024

# --- palette -------------------------------------------------------------
PAPER = (247, 243, 232)
PAPER2 = (240, 234, 216)
INK = (24, 28, 40)
NAVY = (20, 38, 74)
NAVY2 = (32, 58, 108)
RED = (176, 30, 38)
RED2 = (140, 20, 28)
GOLD = (201, 148, 38)
GOLD2 = (232, 184, 84)
TEAL = (18, 110, 108)
TEAL2 = (36, 146, 142)
SKY = (62, 120, 180)
SKY2 = (140, 190, 230)
GREEN = (46, 125, 50)
GREEN2 = (92, 168, 92)
PLUM = (110, 52, 96)
GREY = (105, 108, 115)
DGREY = (74, 78, 88)
LIGHT = (255, 252, 245)
SAND = (238, 230, 208)
SAND2 = (228, 218, 192)
DARKBAND = (24, 28, 40)
CREAM = (252, 248, 238)
SHADOW = (198, 192, 172)
ORANGE = (232, 122, 44)
DAWN = (250, 198, 110)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def darken(c, f=0.72):
    return tuple(int(v * f) for v in c)


def lighten(c, f=1.28):
    return tuple(min(255, int(v * f)) for v in c)


class Canvas:
    """Simple RGB pixel buffer with hand-written drawing primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def put(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def get(self, x, y):
        i = (y * self.w + x) * 3
        return (self.px[i], self.px[i + 1], self.px[i + 2])

    def rect(self, x0, y0, x1, y1, color):
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.w, x1), min(self.h, y1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            base = (y * self.w + x0) * 3
            self.px[base:base + len(row)] = row

    def frame(self, x0, y0, x1, y1, color, t=2):
        self.rect(x0, y0, x1, y0 + t, color)
        self.rect(x0, y1 - t, x1, y1, color)
        self.rect(x0, y0, x0 + t, y1, color)
        self.rect(x1 - t, y0, x1, y1, color)

    def vgrad(self, x0, y0, x1, y1, top, bottom):
        """Vertical gradient, row by row (deterministic)."""
        span = max(1, (y1 - y0 - 1))
        for y in range(y0, y1):
            self.rect(x0, y, x1, y + 1, lerp(top, bottom, (y - y0) / span))

    def hgrad(self, x0, y0, x1, y1, left, right):
        span = max(1, (x1 - x0 - 1))
        for x in range(x0, x1):
            self.rect(x, y0, x + 1, y1, lerp(left, right, (x - x0) / span))

    def disc(self, cx, cy, r, color):
        r2 = r * r
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                dx, dy = x - cx, y - cy
                if dx * dx + dy * dy <= r2:
                    self.put(x, y, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                dx, dy = (x - cx) / max(1, rx), (y - cy) / max(1, ry)
                if dx * dx + dy * dy <= 1.0:
                    self.put(x, y, color)

    def ring(self, cx, cy, r, color, t=3):
        r2 = r * r
        inner = (r - t) * (r - t)
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                dx, dy = x - cx, y - cy
                d = dx * dx + dy * dy
                if inner <= d <= r2:
                    self.put(x, y, color)

    def line(self, x0, y0, x1, y1, color, t=2):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        steps = max(dx, dy, 1)
        for s in range(steps + 1):
            x = x0 + (x1 - x0) * s // steps
            y = y0 + (y1 - y0) * s // steps
            for oy in range(t):
                for ox in range(t):
                    self.put(x + ox, y + oy, color)

    def tri(self, ax, ay, bx, by, cx, cy, color):
        minx, maxx = min(ax, bx, cx), max(ax, bx, cx)
        miny, maxy = min(ay, by, cy), max(ay, by, cy)
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if den == 0:
            return
        for y in range(miny, maxy + 1):
            for x in range(minx, maxx + 1):
                w1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
                w2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
                w3 = 1.0 - w1 - w2
                if w1 >= 0 and w2 >= 0 and w3 >= 0:
                    self.put(x, y, color)

    def arc(self, cx, cy, r, a0, a1, color, t=3):
        steps = max(8, int(abs(a1 - a0) * r / 2))
        for s in range(steps + 1):
            a = a0 + (a1 - a0) * s / steps
            for rr in range(r - t, r + 1):
                self.put(int(cx + rr * math.cos(a)), int(cy + rr * math.sin(a)), color)

    def shadow_box(self, x, y, w, h, fill, off=5):
        self.rect(x + off, y + off, x + w + off, y + h + off, SHADOW)
        self.rect(x, y, x + w, y + h, fill)

    def speckle(self, x0, y0, x1, y1, count, color):
        """Deterministic paper grain via integer hash (no RNG state)."""
        span_x = max(1, x1 - x0)
        span_y = max(1, y1 - y0)
        for i in range(count):
            hsh = (i * 2654435761 + 1013904223) & 0xFFFFFFFF
            x = x0 + (hsh % span_x)
            y = y0 + ((hsh >> 11) % span_y)
            self.put(x, y, color)


# --- 5x7 bitmap font (hand-drawn glyphs, uppercase + digits + basics) ----
GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."],
    "1": ["..#..", ".##..", "#.#..", "..#..", "..#..", "..#..", "#####"],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..#..", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", "..#.."],
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ",": [".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    ";": [".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."],
    "'": ["..#..", "..#..", ".#...", ".....", ".....", ".....", "....."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    "/": ["....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."],
    "(": ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."],
    ")": [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "$": ["..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."],
    "%": ["##..#", "##.#.", "...#.", "..#..", ".#...", ".#.##", "#..##"],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    "*": [".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
}

CHAR_W = 6  # 5 px glyph + 1 px gap, before scaling


def text_width(s, scale):
    return len(s) * CHAR_W * scale - scale


def draw_text(cv, x, y, s, scale, color, bold=False):
    """Draw uppercase text; bold adds a second strike for weight."""
    cx = x
    for ch in s.upper():
        glyph = GLYPHS.get(ch, GLYPHS[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "#":
                    cv.rect(cx + gx * scale, y + gy * scale,
                            cx + (gx + 1) * scale, y + (gy + 1) * scale, color)
                    if bold:
                        bo = 1 if scale <= 3 else 2
                        cv.rect(cx + gx * scale + bo, y + gy * scale,
                                cx + (gx + 1) * scale + bo,
                                y + (gy + 1) * scale, color)
        cx += CHAR_W * scale
    return cx


def draw_shadow_text(cv, x, y, s, scale, color, shadow, bold=False, off=2):
    draw_text(cv, x + off, y + off, s, scale, shadow, bold)
    draw_text(cv, x, y, s, scale, color, bold)


def draw_centered(cv, cx, y, s, scale, color, bold=False):
    x = cx - text_width(s, scale) // 2
    draw_text(cv, x, y, s, scale, color, bold)


def draw_centered_shadow(cv, cx, y, s, scale, color, shadow, bold=False, off=3):
    x = cx - text_width(s, scale) // 2
    draw_shadow_text(cv, x, y, s, scale, color, shadow, bold, off)


def png_bytes(cv):
    """Encode the canvas as a deterministic truecolor PNG."""
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# --- lead illustration: dawn over Shenzhen, skyline + three flags ---------
def lead_scene(cv, x0, y0, x1, y1):
    """Gradient dawn sky, sun, hills, lit skyline, shaded flags."""
    cv.vgrad(x0, y0, x1, y1, (38, 62, 116), DAWN)
    # sun with halo
    sx, sy = x0 + (x1 - x0) // 2, y0 + 42
    cv.disc(sx, sy, 30, (250, 214, 130))
    cv.disc(sx, sy, 22, (252, 228, 160))
    cv.disc(sx, sy, 15, LIGHT)
    # clouds
    for (cx, cy, rx) in ((x0 + 52, y0 + 26, 34), (x1 - 58, y0 + 20, 40),
                         (x0 + 92, y0 + 48, 26), (x1 - 96, y0 + 52, 24)):
        cv.ellipse(cx, cy, rx, 9, (236, 232, 226))
        cv.ellipse(cx, cy - 5, rx - 10, 7, LIGHT)
    # distant hills (Kylin Villa backdrop)
    hy = y1 - 52
    cv.tri(x0, hy, x0 + 130, y0 + 58, x0 + 240, hy, (52, 84, 96))
    cv.tri(x0 + 120, hy, x0 + 250, y0 + 48, x1, hy, (42, 72, 86))
    # skyline towers with lit windows (fixed pattern)
    towers = ((14, 50), (50, 72), (84, 58), (196, 78), (234, 54), (268, 66))
    base = y1 - 34
    for i, (tx, th) in enumerate(towers):
        bx = x0 + tx
        col = (30, 44, 78) if i % 2 == 0 else (38, 54, 92)
        cv.rect(bx, base - th, bx + 30, base, col)
        cv.rect(bx + 22, base - th, bx + 30, base, darken(col, 0.7))
        for wy in range(base - th + 6, base - 6, 11):
            for wx in range(bx + 5, bx + 26, 9):
                if (wx * 7 + wy * 13) % 3 != 0:
                    cv.rect(wx, wy, wx + 4, wy + 5, GOLD2)
    # ground + reflection strip
    cv.rect(x0, base, x1, y1, (30, 40, 66))
    cv.rect(x0, base, x1, base + 3, GOLD2)
    # three shaded flags in front
    cols = (RED, SKY2, GOLD)
    for i, col in enumerate(cols):
        fx = x0 + 138 + i * 52
        cv.rect(fx, base - 66, fx + 4, base, INK)
        cv.disc(fx + 2, base - 70, 5, GOLD2)
        cv.rect(fx + 4, base - 66, fx + 44, base - 40, col)
        cv.rect(fx + 4, base - 52, fx + 44, base - 40, darken(col, 0.78))
        cv.rect(fx + 4, base - 66, fx + 44, base - 62, lighten(col, 1.2))
    cv.frame(x0, y0, x1, y1, INK, 2)


# --- pictograms (shaded, more detailed than v1) ---------------------------
def icon_court(cv, cx, cy):
    cv.ellipse(cx, cy + 34, 44, 5, SHADOW)
    cv.tri(cx - 36, cy - 14, cx + 36, cy - 14, cx, cy - 34, NAVY)
    cv.tri(cx - 36, cy - 14, cx, cy - 14, cx, cy - 34, NAVY2)
    cv.rect(cx - 39, cy - 14, cx + 39, cy - 8, NAVY)
    cv.rect(cx - 39, cy - 10, cx + 39, cy - 8, GOLD2)
    for i in range(4):
        x = cx - 29 + i * 17
        cv.rect(x, cy - 5, x + 7, cy + 18, SKY2)
        cv.rect(x + 4, cy - 5, x + 7, cy + 18, SKY)
    cv.rect(cx - 39, cy + 18, cx + 39, cy + 23, NAVY)
    cv.rect(cx - 43, cy + 26, cx + 43, cy + 30, DGREY)
    cv.rect(cx - 47, cy + 32, cx + 47, cy + 36, INK)
    cv.disc(cx, cy - 22, 4, GOLD2)


def icon_clock(cv, cx, cy):
    cv.ellipse(cx, cy + 30, 29, 5, SHADOW)
    cv.disc(cx, cy, 27, RED2)
    cv.disc(cx, cy, 25, RED)
    cv.disc(cx, cy, 20, CREAM)
    cv.disc(cx - 6, cy - 6, 8, LIGHT)
    for k in range(12):
        a = k * math.pi / 6
        tx, ty = int(cx + 16 * math.cos(a)), int(cy + 16 * math.sin(a))
        cv.disc(tx, ty, 1, NAVY)
    cv.line(cx, cy, cx, cy - 15, INK, 3)
    cv.line(cx, cy, cx + 11, cy + 7, INK, 3)
    cv.disc(cx, cy, 3, INK)
    cv.disc(cx, cy, 1, GOLD2)


def icon_bridge(cv, cx, cy):
    cv.ellipse(cx, cy + 36, 44, 5, SHADOW)
    cv.rect(cx - 32, cy - 22, cx - 26, cy + 4, NAVY)
    cv.rect(cx + 26, cy - 22, cx + 32, cy + 4, NAVY)
    cv.line(cx - 44, cy + 4, cx - 29, cy - 22, NAVY2, 2)
    cv.line(cx - 29, cy - 22, cx + 29, cy - 22, NAVY2, 2)
    cv.line(cx + 29, cy - 22, cx + 44, cy + 4, NAVY2, 2)
    cv.rect(cx - 44, cy + 2, cx - 10, cy + 9, INK)
    cv.rect(cx + 13, cy + 2, cx + 44, cy + 9, INK)
    cv.line(cx - 10, cy + 6, cx + 1, cy + 19, INK, 3)
    cv.line(cx + 13, cy + 6, cx + 4, cy + 20, INK, 3)
    cv.disc(cx + 1, cy - 16, 8, GOLD)
    cv.disc(cx + 1, cy - 16, 4, RED)
    cv.disc(cx + 1, cy - 16, 2, LIGHT)
    for i in range(2):
        y = cy + 18 + i * 8
        for wx in range(cx - 40, cx + 38, 13):
            cv.arc(wx + 6, y, 6, math.pi, 2 * math.pi, SKY, 2)


def icon_cyclone(cv, cx, cy):
    cv.ellipse(cx, cy + 36, 42, 5, SHADOW)
    for s in range(220):
        a = s * 0.11
        r = 2 + s * 0.12
        x = int(cx + r * math.cos(a))
        y = int(cy - 6 + r * math.sin(a) * 0.72)
        col = lerp(TEAL2, NAVY, min(1.0, s / 220))
        cv.disc(x, y, 2, col)
    cv.disc(cx, cy - 6, 5, CREAM)
    cv.ring(cx, cy - 6, 6, TEAL, 2)
    for rx in range(cx - 36, cx + 40, 11):
        cv.line(rx, cy + 22, rx - 4, cy + 31, SKY, 2)
    cv.rect(cx - 42, cy + 33, cx + 42, cy + 36, SAND2)


def icon_chart(cv, cx, cy):
    cv.ellipse(cx, cy + 32, 44, 5, SHADOW)
    heights = (18, 28, 40, 54)
    for i, h in enumerate(heights):
        x = cx - 38 + i * 21
        col = TEAL if i < 3 else GOLD
        cv.rect(x, cy + 26 - h, x + 15, cy + 26, col)
        cv.rect(x + 10, cy + 26 - h, x + 15, cy + 26, darken(col, 0.75))
        cv.rect(x, cy + 26 - h, x + 15, cy + 28 - h, lighten(col, 1.25))
    cv.line(cx - 44, cy + 26, cx + 44, cy + 26, INK, 2)
    cv.line(cx - 36, cy + 8, cx + 30, cy - 32, RED, 3)
    cv.tri(cx + 30, cy - 32, cx + 17, cy - 30, cx + 28, cy - 17, RED)


def icon_cricket(cv, cx, cy):
    cv.ellipse(cx, cy + 36, 42, 5, SHADOW)
    cv.rect(cx - 42, cy + 32, cx + 42, cy + 37, GREEN)
    cv.rect(cx - 42, cy + 32, cx + 42, cy + 34, GREEN2)
    for i in range(3):
        x = cx - 32 + i * 8
        cv.rect(x, cy + 8, x + 4, cy + 32, GOLD)
        cv.rect(x + 2, cy + 8, x + 4, cy + 32, darken(GOLD, 0.75))
    cv.rect(cx - 32, cy + 6, cx - 12, cy + 9, GOLD2)
    cv.line(cx - 6, cy + 30, cx + 14, cy - 12, (196, 150, 84), 8)
    cv.line(cx - 4, cy + 28, cx + 14, cy - 10, (222, 186, 120), 3)
    cv.line(cx + 14, cy - 12, cx + 21, cy - 22, DGREY, 4)
    cv.disc(cx + 29, cy - 15, 9, RED2)
    cv.disc(cx + 28, cy - 16, 8, RED)
    cv.disc(cx + 25, cy - 19, 3, (222, 90, 90))
    cv.arc(cx + 29, cy - 15, 5, -0.9, 0.9, LIGHT, 1)


# --- page layout -----------------------------------------------------------
def tag_chip(cv, x, y, label, color):
    w = text_width(label, 2) + 18
    cv.rect(x + 3, y + 3, x + w + 3, y + 27, SHADOW)
    cv.rect(x, y, x + w, y + 24, color)
    cv.rect(x, y, x + w, y + 3, lighten(color, 1.3))
    draw_text(cv, x + 9, y + 5, label, 2, LIGHT, bold=True)
    return x + w


def card(cv, x, y, w, h, tag, tag_color, head1, head2, body, icon):
    cv.shadow_box(x, y, w, h, LIGHT, off=5)
    cv.frame(x, y, x + w, y + h, INK, 2)
    cv.rect(x, y, x + w, y + 7, tag_color)
    cv.rect(x, y, x + w, y + 2, lighten(tag_color, 1.35))
    tag_chip(cv, x + 12, y + 13, tag, tag_color)
    draw_text(cv, x + 12, y + 46, head1, 3, INK, bold=True)
    draw_text(cv, x + 12, y + 70, head2, 3, INK, bold=True)
    cv.rect(x + 12, y + 96, x + w - 12, y + 98, SAND2)
    for i, line in enumerate(body):
        draw_text(cv, x + 12, y + 104 + i * 17, line, 2, NAVY if i == 0 else DGREY)
    icon(cv, x + w - 54, y + h - 48)


def build_page():
    cv = Canvas(W, H, PAPER)
    m = 26
    # subtle paper gradient + grain (kept faint for legibility)
    cv.vgrad(m - 8, m - 8, W - m + 8, H - m + 8, PAPER, PAPER2)
    cv.speckle(m, m, W - m, H - m, 2600, (236, 229, 208))
    cv.speckle(m, m, W - m, H - m, 1200, (252, 249, 240))
    cv.frame(m - 8, m - 8, W - m + 8, H - m + 8, INK, 3)
    cv.frame(m - 3, m - 3, W - m + 3, H - m + 3, GOLD, 1)

    # masthead (largest type on the page)
    draw_centered_shadow(cv, W // 2, 30, "THE WORLD TODAY", 10, NAVY, SAND2,
                         bold=True, off=3)
    cv.rect(m, 108, W - m, 112, INK)
    cv.rect(m, 116, W - m, 118, GOLD)

    # date band - the single most important line on the page
    cv.vgrad(m, 124, W - m, 180, RED, RED2)
    cv.rect(m, 124, W - m, 127, (216, 92, 92))
    draw_centered_shadow(cv, W // 2, 134, "FRIDAY, 20 NOVEMBER 2026", 6, LIGHT,
                         RED2, bold=True, off=2)
    draw_text(cv, m + 4, 188, "ONE IMAGE EDITION", 2, DGREY, bold=True)
    right = "WORLD NEWS IN BRIEF"
    draw_text(cv, W - m - 4 - text_width(right, 2), 188, right, 2, DGREY, bold=True)

    # lead story: big headline left, tall dawn scene right
    ly, lh = 206, 244
    cv.shadow_box(m, ly, W - 2 * m, lh, SAND, off=5)
    cv.vgrad(m, ly, W - m, ly + lh, SAND, SAND2)
    cv.frame(m, ly, W - m, ly + lh, INK, 2)
    cv.rect(m, ly, W - m, ly + 7, RED)
    tag_chip(cv, m + 14, ly + 13, "LEAD STORY - ASIA SUMMIT", RED)
    draw_text(cv, m + 14, ly + 46, "TRUMP, XI AND", 6, INK, bold=True)
    draw_text(cv, m + 14, ly + 94, "PUTIN HOLD FIRST", 6, INK, bold=True)
    draw_text(cv, m + 14, ly + 142, "THREE-WAY TALKS", 6, INK, bold=True)
    lead_body = (
        "FIRST-EVER TRILATERAL IN SHENZHEN",
        "NUCLEAR WAR CANNOT BE WON, THEY SAY",
        "MORE REFINED OIL FOR ALL NATIONS",
    )
    for i, line in enumerate(lead_body):
        draw_text(cv, m + 14, ly + 192 + i * 17, line, 2, NAVY)
    # scene panel (right side, full height of the lead box)
    sx0, sy0, sx1, sy1 = W - m - 330, ly + 44, W - m - 14, ly + lh - 14
    lead_scene(cv, sx0, sy0, sx1, sy1)
    draw_text(cv, sx0 + 8, sy1 - 20, "SHENZHEN - KYLIN VILLA", 2, LIGHT, bold=True)

    # breaking strip: verified overnight development, 20 Nov
    by = ly + lh + 10
    cv.vgrad(m, by, W - m, by + 30, NAVY, NAVY2)
    cv.rect(m, by, m + 10, by + 30, RED)
    draw_text(cv, m + 20, by + 8, "BREAKING: RUSSIA POUNDS KYIV OVERNIGHT - 5 DEAD, 3 BRIDGES HIT",
              2, LIGHT, bold=True)

    # six story cards, 3 across x 2 down
    gy = by + 40
    gw = (W - 2 * m - 24) // 3
    gh = 176
    cards = (
        ("WORLD - COURT", PLUM, "MYANMAR GUILTY", "OF GENOCIDE",
         ("80-YEAR FIRST", "STATE GUILTY 9-6", "SAFE RETURN"), icon_court),
        ("MIDEAST - IRAN", RED, "TRUMP: NO RUSH", "ON IRAN STRIKES",
         ("PUSHED TO 2027", "SENATE VOTES 51-48", "ISRAEL SEEKS WAR"), icon_clock),
        ("EUROPE - WAR", NAVY, "CRIMEA BRIDGE", "SPAN DESTROYED",
         ("3RD HIT IN WEEK", "ROAD + RAIL CUT", "REVENGE VOWED"), icon_bridge),
        ("ASIA - WEATHER", TEAL, "CYCLONE AKVAN", "MAKES LANDFALL",
         ("AT GOPALPUR", "370K EVACUATED", "1,012 TEAMS READY"), icon_cyclone),
        ("TECH - MARKETS", GOLD, "ANTHROPIC IPO", "BIGGEST EVER",
         ("$81.3B RAISED", "$1.5T VALUE", "OPENED UP 34%"), icon_chart),
        ("SPORT - CRICKET", GREEN, "NICHOLLS 113*", "RESCUES NZ",
         ("70/5 TO 243/5", "PHILLIPS 94*", "5TH BASIN TON"), icon_cricket),
    )
    for idx, (tag, tcol, h1, h2, body, icon) in enumerate(cards):
        cx = m + (idx % 3) * (gw + 12)
        cy = gy + (idx // 3) * (gh + 12)
        card(cv, cx, cy, gw, gh, tag, tcol, h1, h2, body, icon)

    # ticker
    ty = gy + 2 * gh + 22
    cv.vgrad(m, ty, W - m, ty + 40, DARKBAND, (38, 44, 62))
    cv.rect(m, ty, W - m, ty + 3, GOLD)
    draw_text(cv, m + 12, ty + 13, "ALSO TODAY:", 2, GOLD2, bold=True)
    tick = "GTA 6 TOPS $2.36B ON DAY ONE + VOYAGER 1 ONE LIGHT-DAY OUT"
    draw_text(cv, m + 12 + text_width("ALSO TODAY: ", 2), ty + 13, tick, 2, LIGHT, bold=True)
    draw_text(cv, m + 12, ty + 50, "HAYABUSA2 DROPS 2031 LANDING FOR 2028 FLYBY + UK SENDS 1,000 DRONES", 2, NAVY, bold=True)

    # sources + colophon
    sy = ty + 74
    cv.rect(m, sy, W - m, sy + 2, INK)
    draw_centered(cv, W // 2, sy + 8, "SOURCES: WSJ, REUTERS, CNN, HINDU, IMD, CRICINFO - 20 NOV 2026", 2, DGREY)
    draw_centered(cv, W // 2, sy + 27, "DRAWN AT RUNTIME IN PURE PYTHON - NO PHOTOS, NO FONTS, NO NETWORK", 2, DGREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build_page()
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(png_bytes(cv))
    print("wrote", path)


if __name__ == "__main__":
    main()
