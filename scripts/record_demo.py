#!/usr/bin/env python3
"""Record `python -m semabi.demo` as an animated GIF for the README.

Runs the demo in a pseudo-terminal so it emits its real colours, keeps the real
arrival time of every chunk, and draws the result as a terminal window. Long
waits are shortened (see IDLE_CAP) because the demo prints its own elapsed time,
so the figure on screen stays the honest one.

Usage: python3 scripts/record_demo.py [-o docs/demo.gif]
"""
from __future__ import annotations

import argparse
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time
import fcntl
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
COLS, ROWS = 112, 34
FPS = 10
COALESCE = 0.08         # chunks closer together than this are one burst
LINES_PER_SEC = 11      # reveal rate; the program itself prints in two bursts
IDLE_CAP = 1.8          # seconds: the longest pause the recording will show
TAIL_HOLD = 3.0         # seconds to hold the final frame

BG, FG = "#0d1117", "#c9d1d9"
PALETTE = {"1": "#ffffff", "2": "#6e7681", "31": "#ff7b72",
           "32": "#3fb950", "33": "#d29922", "36": "#39c5cf"}
FONTS = ["/usr/share/fonts/TTF/Hack-Regular.ttf",
         "/usr/share/fonts/adobe-source-code-pro/SourceCodePro-Regular.otf",
         "/usr/share/fonts/Adwaita/AdwaitaMono-Regular.ttf",
         "/usr/share/fonts/liberation/LiberationMono-Regular.ttf"]


def capture(argv: list[str]) -> list[tuple[float, bytes]]:
    """Run the demo on a pty, returning (timestamp, bytes) as they arrived."""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
    env = dict(os.environ, TERM="xterm-256color", COLUMNS=str(COLS), LINES=str(ROWS))
    proc = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave,
                            cwd=ROOT, env=env, close_fds=True)
    os.close(slave)
    started, chunks = time.monotonic(), []
    while True:
        if not select.select([master], [], [], 0.05)[0]:
            if proc.poll() is not None:
                break
            continue
        try:
            data = os.read(master, 8192)
        except OSError:
            break
        if not data:
            break
        chunks.append((time.monotonic() - started, data))
    os.close(master)
    proc.wait()
    return chunks


def screens(chunks):
    """Replay the byte stream into (time, screen) states, one per change."""
    lines: list[list[tuple[str, str]]] = [[]]
    colour, states, pending, col = FG, [], "", 0
    for stamp, data in chunks:
        text = pending + data.decode("utf-8", "replace")
        pending = ""
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "\x1b":
                end = text.find("m", i)
                if end == -1:                      # split escape, wait for more
                    pending = text[i:]
                    break
                code = text[i + 1:end].lstrip("[")
                colour = PALETTE.get(code, FG) if code not in ("", "0") else FG
                i = end + 1
                continue
            if ch == "\n":
                lines.append([])
                col = 0
            elif ch == "\r":
                col = 0                            # a pty sends \r\n; never clears
            elif ch != "\x07":
                row = lines[-1]
                row.extend((" ", FG) for _ in range(col - len(row)))
                if col < len(row):
                    row[col] = (ch, colour)
                else:
                    row.append((ch, colour))
                col += 1
            i += 1
        states.append((stamp, [list(row) for row in lines]))

    # A pty hands over bytes in whatever sizes the reader happens to catch, so the
    # same run can arrive as 5 chunks or 70. Collapse anything that landed together
    # into one burst, which is what the program actually did.
    merged = []
    for stamp, screen in states:
        if merged and stamp - merged[-1][0] < COALESCE:
            merged[-1] = (stamp, screen)
        else:
            merged.append((stamp, screen))
    return merged


def frames(states):
    """Reveal the output line by line, pausing where the run actually paused.

    The demo prints in two bursts -- a header, then everything at once after the
    fit -- so replaying the capture verbatim gives two slides. Revealing it at a
    readable rate keeps every line legible; the pause stays at the line where the
    program really waited, and the elapsed time it prints there is its own.
    """
    final = states[-1][1]
    gaps = [(states[i][0] - states[i - 1][0], len(states[i - 1][1]))
            for i in range(1, len(states))]
    pause_at = max(gaps)[1] if gaps else 0

    out, carry = [], 0.0
    per_frame = LINES_PER_SEC / FPS
    shown = 0.0
    while shown < len(final):
        shown = min(shown + per_frame, len(final))
        n = int(shown)
        out.append(final[max(0, n - ROWS):n])
        if n == pause_at and carry == 0.0:          # hold where the fit happened
            out.extend([out[-1]] * int(IDLE_CAP * FPS))
            carry = 1.0
    out.extend([out[-1]] * int(TAIL_HOLD * FPS))
    return out


def draw(screen, font, cw, ch, pad):
    img = Image.new("RGB", (COLS * cw + 2 * pad, ROWS * ch + 2 * pad), BG)
    d = ImageDraw.Draw(img)
    for r, row in enumerate(screen):
        for c, (glyph, colour) in enumerate(row[:COLS]):
            if glyph != " ":
                d.text((pad + c * cw, pad + r * ch), glyph, font=font, fill=colour)
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", default=str(ROOT / "docs/demo.gif"))
    ap.add_argument("--python", default=str(ROOT / ".venv/bin/python"))
    args = ap.parse_args()

    path = next((p for p in FONTS if Path(p).exists()), None)
    if path is None:
        print("no monospace font found", file=sys.stderr)
        return 1
    font = ImageFont.truetype(path, 15)
    cw = round(font.getlength("M"))
    ch = font.getbbox("Ay")[3] + 6

    print("recording the demo on a pty ...")
    states = screens(capture([args.python, "-m", "semabi.demo"]))
    seq = frames(states)
    print(f"  {len(states)} output states -> {len(seq)} frames at {FPS}fps")

    images = [draw(s, font, cw, ch, 14) for s in seq]
    swatch = [BG, FG] + list(PALETTE.values())
    pal = Image.new("P", (1, 1))
    flat = [v for c in swatch for v in Image.new("RGB", (1, 1), c).getpixel((0, 0))]
    pal.putpalette(flat + [0] * (768 - len(flat)))
    images = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in images]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(out, save_all=True, append_images=images[1:],
                   duration=int(1000 / FPS), loop=0, optimize=True, disposal=1)
    print(f"  wrote {out} ({out.stat().st_size / 1e6:.1f} MB, "
          f"{images[0].width}x{images[0].height}, {len(images) / FPS:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
