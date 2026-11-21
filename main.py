#!/usr/bin/env python3
"""THE WORLD TODAY - Friday, 20 November 2026 (round 3).

Copies the bundled front-page image to the output directory.
Deterministic: every run writes byte-identical output.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   ->  out/entry.png
Default output dir: /output
"""
import os
import shutil


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "image.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "entry.png")
    shutil.copyfile(src, dst)


if __name__ == "__main__":
    main()
