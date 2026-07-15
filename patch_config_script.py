#!/usr/bin/env python3
"""Add config.js script tag to all HTML pages (once)."""

from pathlib import Path

SITE = Path(__file__).resolve().parent / "vectorpro-cz"
TAG = '  <script src="/assets/config.js"></script>\n'


def main():
    n = 0
    for html in SITE.rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        if "assets/config.js" in text:
            continue
        if "<script src=" not in text:
            continue
        text = text.replace("<script src=", TAG + "  <script src=", 1)
        html.write_text(text, encoding="utf-8")
        n += 1
    print(f"Patched {n} HTML files")


if __name__ == "__main__":
    main()
