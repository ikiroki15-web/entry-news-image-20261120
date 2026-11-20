#!/usr/bin/env python3
"""THE WORLD TODAY - Friday, 20 November 2026.

A one-image newspaper front page drawn entirely at runtime with the
Python standard library only. No photos, no fonts on disk, no network,
no clock, no randomness: every run produces byte-identical output.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   ->  out/entry.png
"""
import binascii
import os
import struct
import zlib

W = 1024
H = 1024

# --- palette -------------------------------------------------------------
PAPER = (247, 243, 232)
INK = (24, 28, 40)
NAVY = (20, 38, 74)
RED = (176, 30, 38)
GOLD = (201, 148, 38)
TEAL = (18, 110, 108)
SKY = (62, 120, 180)
GREEN = (46, 125, 50)
PLUM = (110, 52, 96)
GREY = (105, 108, 115)
LIGHT = (255, 252, 245)
SAND = (238, 230, 208)
DARKBAND = (24, 28, 40)


class Canvas:
    """Simple RGB pixel buffer with a handful of drawing primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def put(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(self.h, y1)):
            base = y * self.w
            for x in range(max(0, x0), min(self.w, x1)):
                i = (base + x) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = color

    def frame(self, x0, y0, x1, y1, color, t=2):
        self.rect(x0, y0, x1, y0 + t, color)
        self.rect(x0, y1 - t, x1, y1, color)
        self.rect(x0, y0, x0 + t, y1, color)
        self.rect(x1 - t, y0, x1, y1, color)

    def disc(self, cx, cy, r, color):
        r2 = r * r
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                dx, dy = x - cx, y - cy
                if dx * dx + dy * dy <= r2:
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
        import math
        steps = max(8, int(abs(a1 - a0) * r / 2))
        for s in range(steps + 1):
            a = a0 + (a1 - a0) * s / steps
            for rr in range(r - t, r + 1):
                self.put(int(cx + rr * math.cos(a)), int(cy + rr * math.sin(a)), color)


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


def draw_text(cv, x, y, s, scale, color):
    """Draw uppercase text; returns x just past the last glyph."""
    cx = x
    for ch in s.upper():
        glyph = GLYPHS.get(ch, GLYPHS[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "#":
                    cv.rect(cx + gx * scale, y + gy * scale,
                            cx + (gx + 1) * scale, y + (gy + 1) * scale, color)
        cx += CHAR_W * scale
    return cx


def draw_centered(cv, cx, y, s, scale, color):
    x = cx - text_width(s, scale) // 2
    draw_text(cv, x, y, s, scale, color)


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


# --- pictograms (simple flat icons, drawn with the primitives above) ------
def icon_summit(cv, cx, cy):
    """Three flags on poles: a trilateral summit."""
    for i, col in enumerate((RED, NAVY, GOLD)):
        x = cx - 90 + i * 90
        cv.rect(x, cy - 55, x + 5, cy + 60, INK)
        cv.rect(x + 5, cy - 55, x + 62, cy - 18, col)
        cv.disc(x + 2, cy - 62, 7, INK)
    cv.rect(cx - 150, cy + 60, cx + 150, cy + 66, INK)
    cv.ring(cx, cy + 78, 16, TEAL, 4)
    cv.rect(cx - 150, cy + 92, cx + 150, cy + 96, GREY)


def icon_court(cv, cx, cy):
    """Courthouse: pediment, columns, steps (compact)."""
    cv.tri(cx - 46, cy - 18, cx + 46, cy - 18, cx, cy - 42, NAVY)
    cv.rect(cx - 50, cy - 18, cx + 50, cy - 11, NAVY)
    for i in range(4):
        x = cx - 38 + i * 23
        cv.rect(x, cy - 8, x + 8, cy + 24, SKY)
    cv.rect(cx - 50, cy + 24, cx + 50, cy + 30, NAVY)
    cv.rect(cx - 56, cy + 34, cx + 56, cy + 39, INK)
    cv.rect(cx - 62, cy + 42, cx + 62, cy + 47, INK)
    cv.disc(cx, cy - 27, 5, GOLD)


def icon_clock(cv, cx, cy):
    """Clock face: a decision postponed (compact)."""
    cv.ring(cx, cy, 34, RED, 5)
    cv.line(cx, cy, cx, cy - 22, INK, 4)
    cv.line(cx, cy, cx + 17, cy + 9, INK, 4)
    cv.disc(cx, cy, 4, INK)
    for dx, dy in ((0, -34), (34, 0), (0, 34), (-34, 0)):
        cv.disc(cx + dx, cy + dy, 4, RED)


def icon_bridge(cv, cx, cy):
    """Bridge span over water, with a burst above it (compact)."""
    cv.rect(cx - 58, cy + 4, cx + 58, cy + 11, INK)
    cv.rect(cx - 42, cy - 28, cx - 35, cy + 4, NAVY)
    cv.rect(cx + 35, cy - 28, cx + 42, cy + 4, NAVY)
    cv.line(cx - 58, cy + 4, cx - 38, cy - 28, NAVY, 2)
    cv.line(cx - 38, cy - 28, cx + 38, cy - 28, NAVY, 2)
    cv.line(cx + 38, cy - 28, cx + 58, cy + 4, NAVY, 2)
    for i in range(5):
        x = cx - 48 + i * 24
        cv.line(x, cy - 28 + (i % 2) * 4, x, cy + 4, NAVY, 2)
    for i in range(3):
        y = cy + 22 + i * 8
        cv.line(cx - 54, y, cx + 54, y, SKY, 2)
    cv.disc(cx + 5, cy - 38, 8, GOLD)
    cv.disc(cx + 5, cy - 38, 4, RED)


def icon_cyclone(cv, cx, cy):
    """Spiral storm over a coastline (compact)."""
    import math
    for s in range(220):
        a = s * 0.11
        r = 3 + s * 0.16
        x = int(cx + r * math.cos(a))
        y = int(cy - 6 + r * math.sin(a) * 0.72)
        cv.disc(x, y, 3, TEAL)
    cv.disc(cx, cy - 6, 6, PAPER)
    cv.ring(cx, cy - 6, 7, TEAL, 2)
    cv.rect(cx - 56, cy + 34, cx + 56, cy + 38, SAND)
    cv.line(cx - 56, cy + 46, cx + 56, cy + 46, SKY, 2)


def icon_chart(cv, cx, cy):
    """Rising bars with an arrow: a record stock debut (compact)."""
    heights = (22, 34, 48, 66)
    for i, h in enumerate(heights):
        x = cx - 50 + i * 27
        cv.rect(x, cy + 34 - h, x + 19, cy + 34, TEAL if i < 3 else GOLD)
    cv.line(cx - 58, cy + 34, cx + 58, cy + 34, INK, 3)
    cv.line(cx - 48, cy + 10, cx + 40, cy - 40, RED, 4)
    cv.tri(cx + 40, cy - 40, cx + 24, cy - 38, cx + 38, cy - 22, RED)


def icon_cricket(cv, cx, cy):
    """Bat and ball (compact)."""
    cv.line(cx - 26, cy + 34, cx + 12, cy - 20, GOLD, 9)
    cv.rect(cx - 36, cy + 26, cx - 16, cy + 42, GOLD)
    cv.disc(cx + 32, cy - 18, 12, RED)
    cv.line(cx + 25, cy - 26, cx + 39, cy - 10, LIGHT, 2)
    cv.rect(cx - 56, cy + 44, cx + 56, cy + 49, GREEN)


# --- page layout -----------------------------------------------------------
def tag_chip(cv, x, y, label, color):
    w = text_width(label, 2) + 18
    cv.rect(x, y, x + w, y + 24, color)
    draw_text(cv, x + 9, y + 5, label, 2, LIGHT)
    return x + w


def card(cv, x, y, w, h, tag, tag_color, head1, head2, body, icon):
    cv.rect(x, y, x + w, y + h, LIGHT)
    cv.frame(x, y, x + w, y + h, INK, 2)
    cv.rect(x, y, x + w, y + 6, tag_color)
    tag_chip(cv, x + 12, y + 14, tag, tag_color)
    draw_text(cv, x + 12, y + 48, head1, 2, INK)
    draw_text(cv, x + 12, y + 68, head2, 2, INK)
    for i, line in enumerate(body):
        draw_text(cv, x + 12, y + 96 + i * 20, line, 2, NAVY if i == 0 else GREY)
    icon(cv, x + w - 68, y + h - 58)


def build_page():
    cv = Canvas(W, H, PAPER)
    m = 26
    cv.frame(m - 8, m - 8, W - m + 8, H - m + 8, INK, 3)
    cv.frame(m - 3, m - 3, W - m + 3, H - m + 3, GOLD, 1)

    # masthead
    draw_centered(cv, W // 2, 34, "THE WORLD TODAY", 9, NAVY)
    cv.rect(m, 112, W - m, 116, INK)
    cv.rect(m, 120, W - m, 122, GOLD)

    # date band - the single most important line on the page
    cv.rect(m, 130, W - m, 184, RED)
    draw_centered(cv, W // 2, 142, "FRIDAY, 20 NOVEMBER 2026", 5, LIGHT)
    draw_text(cv, m + 4, 192, "ONE IMAGE EDITION", 2, GREY)
    right = "WORLD NEWS IN BRIEF"
    draw_text(cv, W - m - 4 - text_width(right, 2), 192, right, 2, GREY)

    # lead story
    ly, lh = 216, 238
    cv.rect(m, ly, W - m, ly + lh, SAND)
    cv.frame(m, ly, W - m, ly + lh, INK, 2)
    tag_chip(cv, m + 14, ly + 14, "LEAD STORY - ASIA SUMMIT", RED)
    draw_text(cv, m + 14, ly + 52, "TRUMP, XI AND PUTIN", 4, INK)
    draw_text(cv, m + 14, ly + 86, "HOLD FIRST THREE-WAY TALKS", 4, INK)
    lead_body = (
        "FIRST-EVER TRILATERAL MEETING HELD IN SHENZHEN",
        "JOINT PLEDGE ON UN, NUCLEAR RISKS AND OIL OUTPUT",
        "TRUMP TO FACE PRESS AT THE WHITE HOUSE NEXT",
    )
    for i, line in enumerate(lead_body):
        draw_text(cv, m + 14, ly + 132 + i * 24, line, 2, NAVY)
    cv.rect(m + 14, ly + 202, W - m - 14, ly + 205, GOLD)
    draw_text(cv, m + 14, ly + 212, "AP / THE TIMES / REUTERS", 2, GREY)
    icon_summit(cv, W - m - 190, ly + 118)

    # six story cards, 3 across x 2 down
    gy = ly + lh + 14
    gw = (W - 2 * m - 24) // 3
    gh = 188
    cards = (
        ("WORLD - COURT", PLUM, "UN COURT: MYANMAR", "COMMITTED GENOCIDE",
         ("A FIRST FOR ICJ", "IN 80 YEARS", "SAFE RETURN"), icon_court),
        ("MIDEAST - IRAN", RED, "TRUMP: NO RUSH ON", "IRAN DECISION",
         ("WAR CALL TO 2027", "STRIKES SOUGHT", "GULF URGES CALM"), icon_clock),
        ("EUROPE - WAR", NAVY, "UKRAINE HITS CRIMEA", "BRIDGE THIRD TIME",
         ("RAIL HALTED", "BERLIN SUMMIT", "TALKS URGED"), icon_bridge),
        ("ASIA - WEATHER", TEAL, "CYCLONE AKVAN NEARS", "ODISHA COAST",
         ("LANDFALL FRIDAY", "300K EVACUATED", "423 TEAMS READY"), icon_cyclone),
        ("TECH - MARKETS", GOLD, "ANTHROPIC IPO IS", "BIGGEST EVER",
         ("$81B RAISED", "$1.5T VALUE", "OPENED UP 34%"), icon_chart),
        ("SPORT - CRICKET", GREEN, "NICHOLLS 113 NOT OUT", "RESCUES NEW ZEALAND",
         ("70/5 TO 243/5", "PHILLIPS RECORD", "WELLINGTON TEST"), icon_cricket),
    )
    for idx, (tag, tcol, h1, h2, body, icon) in enumerate(cards):
        cx = m + (idx % 3) * (gw + 12)
        cy = gy + (idx // 3) * (gh + 12)
        card(cv, cx, cy, gw, gh, tag, tcol, h1, h2, body, icon)

    # ticker
    ty = gy + 2 * gh + 26
    cv.rect(m, ty, W - m, ty + 44, DARKBAND)
    draw_text(cv, m + 12, ty + 15, "ALSO TODAY:", 2, GOLD)
    tick = "GTA 6 SALES PASS $1.8B + VOYAGER 1 HITS LIGHT-DAY MARK"
    draw_text(cv, m + 12 + text_width("ALSO TODAY: ", 2), ty + 15, tick, 2, LIGHT)
    draw_text(cv, m + 12, ty + 58, "HAYABUSA2 SKIPS ASTEROID LANDING + TRUMP EYES KIM MEETING", 2, NAVY)

    # sources + colophon
    sy = ty + 84
    cv.rect(m, sy, W - m, sy + 2, INK)
    draw_centered(cv, W // 2, sy + 10, "SOURCES: AP, REUTERS, CNN, BBC, THE HINDU, ICC - 20 NOV 2026", 2, GREY)
    draw_centered(cv, W // 2, sy + 30, "DRAWN AT RUNTIME IN PURE PYTHON - NO PHOTOS, NO FONTS, NO NETWORK", 2, GREY)
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
